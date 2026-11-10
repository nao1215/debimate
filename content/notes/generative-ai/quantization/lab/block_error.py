"""1 つの重み行列を自分で Q8_0 と 4 bit に丸め、FP16 との誤差を測る。

Ollama の q8_0・q4_K_M のファイルに入っている同じ行列も復元して並べる。

使い方:
    python3 block_error.py <fp16 の GGUF> <q8_0 の GGUF> <q4_K_M の GGUF> [結果の JSON]
"""
import json
import sys

import numpy as np

from gguf_header import read_gguf

TENSOR = "blk.0.ffn_gate.weight"   # 2048 x 6144。どちらの量子化でも整数に丸められている層


def load_raw(path, name):
    """GGUF から 1 つのテンソルのバイト列を、行（ne0 方向）ごとに読み出す。"""
    _, _, tensors, data_start = read_gguf(path)
    t = next(x for x in tensors if x["name"] == name)
    return t, np.memmap(path, mode="r", offset=data_start + t["offset"], dtype=np.uint8)


def load_f16(path, name):
    t, raw = load_raw(path, name)
    n = int(np.prod(t["shape"]))
    return raw[: n * 2].view(np.float16).astype(np.float32)


# --- 自分で丸める ------------------------------------------------------------

def roundf(x):
    """C の roundf と同じく、ちょうど 0.5 は 0 から遠い側に丸める（np.round は偶数側）。"""
    t = np.trunc(x)
    return t + np.where(np.abs(x - t) >= 0.5, np.sign(x), 0)


def quant_q8_0(x):
    """32 個ごとに d = max|x| / 127 を求め、x / d を -127〜127 の整数に丸める。
    llama.cpp の quantize_row_q8_0_ref と同じく、丸めには FP32 の d の逆数を使い、
    d を FP16 にするのはファイルに書く時だけ。"""
    b = x.reshape(-1, 32)
    d32 = np.abs(b).max(axis=1) / np.float32(127)
    inv = np.divide(np.float32(1), d32, out=np.zeros_like(d32), where=d32 != 0)
    q = roundf(b * inv[:, None]).astype(np.int8)
    d = d32.astype(np.float16)                                 # ファイルには FP16 で入る
    return q, d, (q * d.astype(np.float32)[:, None]).reshape(-1)


def quant_q4_0(x):
    """32 個ごとに、絶対値が最大の値を -8 に合わせた d を持ち、-8〜7 の整数に丸める。"""
    b = x.reshape(-1, 32)
    idx = np.abs(b).argmax(axis=1)
    mx = b[np.arange(len(b)), idx]                           # 符号付きの最大値
    d32 = mx / np.float32(-8)
    inv = np.divide(np.float32(1), d32, out=np.zeros_like(d32), where=d32 != 0)
    q = np.clip(np.floor(b * inv[:, None] + 8.5), 0, 15).astype(np.int8) - 8   # (int8_t)(x + 8.5f)
    d = d32.astype(np.float16)                                 # Q8_0 と同じく FP16 は保存用
    return q, d, (q * d.astype(np.float32)[:, None]).reshape(-1)


def quant_q4_min(x):
    """32 個ごとに最小値 m と幅 d を持ち、(x - m) / d を 0〜15 の整数に丸める（Q4_K の小ブロックと同じ形）。"""
    b = x.reshape(-1, 32)
    lo, hi = b.min(axis=1), b.max(axis=1)
    d = ((hi - lo) / 15).astype(np.float16).astype(np.float32)
    lo = lo.astype(np.float16).astype(np.float32)
    inv = np.divide(1.0, d, out=np.zeros_like(d), where=d != 0)
    q = np.clip(np.round((b - lo[:, None]) * inv[:, None]), 0, 15).astype(np.int8)
    return q, d, (q * d[:, None] + lo[:, None]).reshape(-1)


# --- Ollama のファイルを復元する（llama.cpp の dequantize_row_q8_0 / q4_K と同じ計算）--

def dequant_q8_0(raw, n):
    blocks = raw[: n // 32 * 34].reshape(-1, 34)
    d = blocks[:, :2].copy().view(np.float16).astype(np.float32)   # (nb, 1)
    q = blocks[:, 2:].copy().view(np.int8).astype(np.float32)
    return (q * d).reshape(-1)


def dequant_q4_k(raw, n):
    """256 個の大ブロック = FP16 の d と dmin、6 bit の scale と min が 8 組、4 bit の整数 256 個。"""
    blocks = raw[: n // 256 * 144].reshape(-1, 144)
    d = blocks[:, 0:2].copy().view(np.float16).astype(np.float32)[:, 0]
    dmin = blocks[:, 2:4].copy().view(np.float16).astype(np.float32)[:, 0]
    s = blocks[:, 4:16].astype(np.int32)
    qs = blocks[:, 16:144]
    sc = np.empty((len(blocks), 8), np.int32)
    mn = np.empty((len(blocks), 8), np.int32)
    for j in range(8):                                   # get_scale_min_k4()
        if j < 4:
            sc[:, j] = s[:, j] & 63
            mn[:, j] = s[:, j + 4] & 63
        else:
            sc[:, j] = (s[:, j + 4] & 0xF) | ((s[:, j - 4] >> 6) << 4)
            mn[:, j] = (s[:, j + 4] >> 4) | ((s[:, j] >> 6) << 4)
    out = np.empty((len(blocks), 256), np.float32)
    for k in range(4):                                   # 64 個ずつ: 下位 4 bit が前半 32 個、上位が後半
        q = qs[:, k * 32:(k + 1) * 32]
        for half, vals in ((0, q & 0xF), (1, q >> 4)):
            j = 2 * k + half
            out[:, j * 32:(j + 1) * 32] = (d * sc[:, j])[:, None] * vals - (dmin * mn[:, j])[:, None]
    return out.reshape(-1)


def rel_rmse(x, y):
    return float(np.sqrt(np.mean((x - y) ** 2)) / np.sqrt(np.mean(x ** 2)))


def main():
    fp16_path, q8_path, q4_path = sys.argv[1:4]
    out_path = sys.argv[4] if len(sys.argv) > 4 else None
    w = load_f16(fp16_path, TENSOR)
    n = w.size

    # 1 ブロック（32 個）の数値例。絶対値が最大の値（32 個目）を含む後ろの 8 個を表示する
    blk = w[:32]
    q8, d8, r8 = quant_q8_0(blk)
    q4, d4, r4 = quant_q4_0(blk)
    print(f"{TENSOR}: {n:,} weights, first block (32 weights), last 8 shown")
    print(f"  FP16        : {np.array2string(blk[24:], precision=4, floatmode='fixed')}")
    print(f"  Q8_0  d={float(d8[0]):.6f}  ints: {q8[0, 24:].tolist()}")
    print(f"        restored: {np.array2string(r8[24:], precision=4, floatmode='fixed')}")
    print(f"  Q4_0  d={float(d4[0]):.6f}  ints: {q4[0, 24:].tolist()}")
    print(f"        restored: {np.array2string(r4[24:], precision=4, floatmode='fixed')}")
    print(f"  max |error| in this block: Q8_0 {np.abs(blk - r8).max():.5f}, "
          f"Q4_0 {np.abs(blk - r4).max():.5f}  (max |w| {np.abs(blk).max():.5f})")

    # 行列全体の誤差
    _, raw8 = load_raw(q8_path, TENSOR)
    _, raw4 = load_raw(q4_path, TENSOR)
    mine8 = quant_q8_0(w)[2]
    olla8 = dequant_q8_0(raw8, n)
    rows = {
        "Q8_0 (mine)": mine8,
        "Q8_0 (Ollama q8_0 file)": olla8,
        "Q4_0 (mine)": quant_q4_0(w)[2],
        "Q4 scale+min (mine)": quant_q4_min(w)[2],
        "Q4_K (Ollama q4_K_M file)": dequant_q4_k(raw4, n),
    }
    print(f"\nwhole matrix ({n:,} weights), error relative to FP16")
    result = {"tensor": TENSOR, "n": n, "rel_rmse": {}}
    for k, v in rows.items():
        e = rel_rmse(w, v)
        result["rel_rmse"][k] = e
        print(f"  {k:27s} relative RMSE {e * 100:6.3f} %   max |error| {np.abs(w - v).max():.5f}")
    same = int(np.sum(mine8 == olla8))
    print(f"\nQ8_0 mine vs Ollama: {same:,} / {n:,} weights identical ({same / n * 100:.4f} %)")
    result["q8_identical"] = same

    # 誤差のヒストグラム用（図に使う）
    hist = {}
    edges = np.linspace(-0.02, 0.02, 81)
    for k in ("Q8_0 (Ollama q8_0 file)", "Q4_K (Ollama q4_K_M file)"):
        h, _ = np.histogram(rows[k] - w, bins=edges)
        hist[k] = h.tolist()
    result["hist_edges"] = edges.tolist()
    result["hist"] = hist
    result["block"] = {"w": blk.tolist(), "q8": r8.tolist(), "q4": r4.tolist()}
    if out_path:
        with open(out_path, "w") as f:
            json.dump(result, f, indent=1)


if __name__ == "__main__":
    main()
