"""ローカル LLM の速さのノートの図を作る（matplotlib）。

lab/runs.jsonl（bench.py の出力）と lab/gguf.json（gguf_bytes.py の出力）から、次の図を作る。
- speed_by_length.webp : 入力の長さごとの prefill と decode の速さ（モデル別、中央値）
- decode_ceiling.webp  : 帯域から計算した decode の上限と実測
- decode_bytes.webp    : 1 トークンで読むバイト数（重み + KV キャッシュ）と 1 トークンの時間
- reuse_concept.webp  : prefill と decode で、読んだ重みを何本のベクトルに掛けるか（手書きの SVG）
- prefill_time.webp   : 入力を読み終えるまでの時間（prefill の秒数）
- runs_excluded.webp   : qwen3:8b の各回の decode の速さと、除いた回（画像生成と重なった回）

使い方:
    python3 figures.py
"""
import json
import os
import statistics
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import tempfile  # noqa: E402
import subprocess  # noqa: E402
from pathlib import Path  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "lab")
IMG = os.path.join(HERE, "images")

plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 13,
                     "axes.edgecolor": "#666666", "axes.labelcolor": "#1f1f1f",
                     "xtick.color": "#1f1f1f", "ytick.color": "#1f1f1f"})
BANDWIDTH = 256e9          # Ryzen AI Max+ 395 の 256-bit LPDDR5X-8000 の理論値（バイト毎秒）

# モデル名 -> (表示名, gguf.json のキー, 色, 印)
MODELS = {
    "qwen3:8b": ("qwen3:8b（dense）", "qwen3-8b", "#7aa6c2", "o"),
    "qwen3-coder:30b": ("qwen3-coder:30b（MoE）", "qwen3-coder-30b", "#d4a24c", "s"),
    "hf.co/ggml-org/gpt-oss-20b-GGUF:latest": ("gpt-oss-20b（MoE）", "gpt-oss-20b", "#8fae86", "^"),
}


# 印は付いていないが除く回。ComfyUI の生成（prompt 953 の終わりの 6 秒後、954 の始まりの 2 秒前）に挟まれ、
# 同じ条件の他の 3 回（37.8〜37.9 トークン毎秒）より decode が 3 割遅かった
EXCLUDE = {"2026-11-11T12:38:44"}


def load_runs():
    runs = [json.loads(line) for line in open(os.path.join(LAB, "runs.jsonl"))]
    return [r for r in runs if not r["disturbed"] and r["time"] not in EXCLUDE]


def kv_bytes_per_token(g, n_ctx):
    """decode の 1 トークンで読む KV キャッシュのバイト数（f16、K と V）。n_ctx はその時点のトークン数。"""
    per_layer = g["head_count_kv"] * g["key_length"] * 2 * 2
    if g["sliding_window"]:   # gpt-oss: 半分の層は直近 128 トークンだけを見る
        full = g["block_count"] // 2
        return per_layer * (full * n_ctx + (g["block_count"] - full) * min(n_ctx, g["sliding_window"]))
    return per_layer * g["block_count"] * n_ctx


def medians(runs):
    """(モデル, 行数) -> 入力トークン・prefill・decode の中央値。"""
    groups = defaultdict(list)
    for r in runs:
        groups[(r["model"], r["lines"])].append(r)
    out = {}
    for k, rs in groups.items():
        out[k] = {"n": len(rs),
                  "tokens": statistics.median(r["prompt_eval_count"] for r in rs),
                  "prefill": statistics.median(r["prefill_tps"] for r in rs),
                  "decode": statistics.median(r["decode_tps"] for r in rs),
                  "prefill_s": statistics.median(r["prompt_eval_s"] for r in rs)}
    return out


def save(fig, name):
    """PNG（dpi 200）に描いてから WebP にして images/ に置く。"""
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "fig.png")
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight")
        Image.open(png).convert("RGB").save(os.path.join(IMG, name), "WEBP", quality=90, method=6)
    plt.close(fig)


def speed_by_length(med):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for model, (label, _, color, marker) in MODELS.items():
        pts = sorted((v["tokens"], v["prefill"], v["decode"]) for (m, _), v in med.items() if m == model)
        if not pts:
            continue
        x = [p[0] for p in pts]
        axes[0].plot(x, [p[1] for p in pts], color=color, marker=marker, lw=2.5, ms=8, label=label)
        axes[1].plot(x, [p[2] for p in pts], color=color, marker=marker, lw=2.5, ms=8, label=label)
    for ax, title in zip(axes, ["prefill（入力を読む）", "decode（1 トークンずつ生成）"]):
        ax.set_xscale("log")
        ax.set_xticks([500, 1000, 4000, 16000, 32000])
        ax.set_xticklabels(["500", "1K", "4K", "16K", "32K"])
        ax.set_xlabel("入力のトークン数")
        ax.set_ylabel("トークン毎秒")
        ax.set_title(title, fontsize=15, color="#1f1f1f")
        ax.set_ylim(bottom=0)
        ax.grid(True, color="#e5e5e5")
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].legend(frameon=False, fontsize=12)
    fig.tight_layout()
    save(fig, "speed_by_length.webp")


def decode_ceiling(med, gguf):
    fig, ax = plt.subplots(figsize=(9, 3.6))
    labels, ceil, meas = [], [], []
    for model, (label, key, color, _) in MODELS.items():
        short = [v for (m, n), v in med.items() if m == model]
        if not short:
            continue
        v = min(short, key=lambda v: v["tokens"])
        g = gguf[key]
        read = g["decode_read_bytes"] + kv_bytes_per_token(g, v["tokens"])
        labels.append(label)
        ceil.append(BANDWIDTH / read)
        meas.append(v["decode"])
    y = range(len(labels))
    ax.barh([i + 0.2 for i in y], ceil, height=0.38, color="#ffffff", edgecolor="#666666", label="帯域 256 GB/s から計算した上限")
    colors = [MODELS[m][2] for m in MODELS if any(k[0] == m for k in med)]
    ax.barh([i - 0.2 for i in y], meas, height=0.38, color=colors, label="実測（中央値。色はモデル）")
    for i in y:
        ax.text(ceil[i] + 1, i + 0.2, f"{ceil[i]:.0f}", va="center", fontsize=12, color="#666666")
        ax.text(meas[i] + 1, i - 0.2, f"{meas[i]:.0f}（{meas[i] / ceil[i] * 100:.0f}%）", va="center", fontsize=12)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("decode の速さ（トークン毎秒）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=11, loc="upper right")
    ax.set_xlim(0, max(ceil) * 1.18)
    fig.tight_layout()
    save(fig, "decode_ceiling.webp")


def decode_bytes(med, gguf):
    fig, ax = plt.subplots(figsize=(8, 4.4))
    xmax = 0
    for model, (label, key, color, marker) in MODELS.items():
        pts = sorted(((v["tokens"], v) for (m, _), v in med.items() if m == model), key=lambda t: t[0])
        if not pts:
            continue
        g = gguf[key]
        xs = [(g["decode_read_bytes"] + kv_bytes_per_token(g, t)) / 1e9 for t, _ in pts]
        ys = [1000 / v["decode"] for _, v in pts]
        xmax = max(xmax, max(xs))
        ax.plot(xs, ys, color=color, marker=marker, lw=2, ms=8, label=label)
    xs = [0, xmax * 1.1]
    ax.plot(xs, [x * 1e9 / BANDWIDTH * 1000 for x in xs], color="#666666", ls="--", lw=1.5,
            label="256 GB/s で読み切った時")
    ax.set_xlabel("1 トークンで読むバイト数（重み + KV キャッシュ、GB）")
    ax.set_ylabel("1 トークンの時間（ミリ秒）")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(True, color="#e5e5e5")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=11)
    fig.tight_layout()
    save(fig, "decode_bytes.webp")


def reuse_concept():
    """prefill は重みを 1 回読んで多くのトークンに掛け、decode はトークンごとに読み直して 1 本に掛ける。"""
    w, h = 960, 420
    font = "Noto Sans CJK JP, sans-serif"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def t(x, y, s, size=22, color="#1f1f1f"):
        o.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{color}" '
                 f'text-anchor="middle">{s}</text>')

    def r(x, y, rw, rh, fill, stroke, sw=2):
        o.append(f'<rect x="{x}" y="{y}" width="{rw}" height="{rh}" rx="4" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')

    # 左: prefill
    t(230, 44, "prefill（入力をまとめて読む）", 26)
    r(60, 90, 150, 150, "#eaf1f5", "#7aa6c2", 3)
    t(135, 172, "重み行列")
    t(240, 172, "×", 30, "#666666")
    for i in range(10):
        r(275 + i * 13, 90, 9, 150, "#f8eed8", "#d4a24c", 1.5)
    t(340, 265, "数千本のトークン", 20, "#666666")
    t(230, 330, "重みを 1 回読み、全部に掛ける")
    t(230, 366, "→ 計算の速さで決まる", 22, "#666666")
    o.append('<line x1="470" y1="30" x2="470" y2="390" stroke="#d0d0d0" stroke-width="2"/>')
    # 右: decode
    t(715, 44, "decode（1 トークンずつ生成）", 26)
    for k in range(3):
        x = 510 + k * 150
        r(x, 110, 90, 90, "#eaf1f5", "#7aa6c2", 3)
        t(x + 45, 162, "重み", 20)
        r(x + 100, 110, 9, 90, "#f8eed8", "#d4a24c", 1.5)
        t(x + 55, 230, f"{k + 1} トークン目", 20, "#666666")
    t(715, 330, "トークンごとに読み直し、1 本に掛ける")
    t(715, 366, "→ メモリから読む速さ（帯域）で決まる", 22, "#666666")
    o.append("</svg>")
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text("\n".join(o) + "\n", encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(os.path.join(IMG, "reuse_concept.webp"), "WEBP",
                                            quality=90, method=6)


def prefill_time(med):
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for model, (label, _, color, marker) in MODELS.items():
        pts = sorted((v["tokens"], v["prefill_s"]) for (m, _), v in med.items() if m == model)
        if pts:
            ax.plot([p[0] / 1000 for p in pts], [p[1] for p in pts], color=color, marker=marker,
                    lw=2.5, ms=8, label=label)
            ax.text(pts[-1][0] / 1000 + 0.6, pts[-1][1], f"{pts[-1][1]:.0f} 秒", va="center", fontsize=11)
    ax.set_xlabel("入力のトークン数（千）")
    ax.set_ylabel("読み終えるまでの秒数")
    ax.set_xlim(0, 40)
    ax.set_ylim(bottom=0)
    ax.grid(True, color="#e5e5e5")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=11, loc="upper left")
    fig.tight_layout()
    save(fig, "prefill_time.webp")


def runs_excluded():
    """qwen3:8b の全ての回の decode の速さ。除いた 4 回は黄土の白抜きで示す。"""
    runs = [json.loads(line) for line in open(os.path.join(LAB, "runs.jsonl"))]
    runs = [r for r in runs if r["model"] == "qwen3:8b"]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    kept = [r for r in runs if not r["disturbed"] and r["time"] not in EXCLUDE]
    out = [r for r in runs if r["disturbed"] or r["time"] in EXCLUDE]
    ax.scatter([r["prompt_eval_count"] for r in kept], [r["decode_tps"] for r in kept], s=70,
               color="#7aa6c2", zorder=3, label="使った回")
    ax.scatter([r["prompt_eval_count"] for r in out], [r["decode_tps"] for r in out], s=90,
               facecolors="#ffffff", edgecolors="#d4a24c", linewidths=2.5, zorder=3,
               label="除いた回（画像生成と重なった回など）")
    ax.set_xscale("log")
    ax.set_xticks([500, 1000, 4000, 16000, 32000])
    ax.set_xticklabels(["500", "1K", "4K", "16K", "32K"])
    ax.set_xlabel("入力のトークン数")
    ax.set_ylabel("decode（トークン毎秒）")
    ax.set_ylim(0, 45)
    ax.grid(True, color="#e5e5e5")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=11, loc="lower left")
    fig.tight_layout()
    save(fig, "runs_excluded.webp")


def main():
    os.makedirs(IMG, exist_ok=True)
    runs = load_runs()
    gguf = json.load(open(os.path.join(LAB, "gguf.json")))
    med = medians(runs)
    for (m, n), v in sorted(med.items()):
        print(f"{m:40s} lines {n:4d} n={v['n']} tokens {v['tokens']:7.0f} prefill {v['prefill']:7.1f} "
              f"({v['prefill_s']:.2f} s) decode {v['decode']:5.1f}")
    speed_by_length(med)
    decode_ceiling(med, gguf)
    decode_bytes(med, gguf)
    runs_excluded()
    prefill_time(med)
    reuse_concept()


if __name__ == "__main__":
    main()
