"""Blob のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

lab/output/ の実験の出力（basics.txt、calldata_gas.txt、mainnet_*.json）を読む。
手数料の値は lab/blobfee.py の式で、ヘッダーの excessBlobGas から計算する。
matplotlib で PNG（dpi 200、白い背景）に描き、Pillow で WebP にする。

- overview_figure(): 表紙。トランザクションの calldata と blob が、どこに置かれ、誰が読めるか。
- contract_view_figure(): 5 バイトの blob と、コントラクトから見える versioned hash。
- spike_figure(): 2024-03-27 の mainnet。blob の単価が 1 wei から上がる様子の動画（実時間の 1000 倍速）。
- reserve_figure(): 2026-11-12 の mainnet。target を下回っても単価が下限に留まる。
- crossover_figure(): データの大きさごとの calldata と blob の費用。
"""

from pathlib import Path
import io
import json
import math
import sys
import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
sys.path.insert(0, str(HERE / "lab"))
import blobfee as bf  # noqa: E402

INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#4e79a7", "#e15759", "#fbe3e3"
GREEN_PALE = "#e6f2e6"
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP",
    "font.size": 11,
    "axes.edgecolor": SUB,
    "axes.labelcolor": INK,
    "xtick.color": SUB,
    "ytick.color": SUB,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def save_plot(fig, name):
    """matplotlib の図 -> PNG（dpi 200、白） -> images/<name>（WebP）。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(buf).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def box(ax, x, y, w, h, text, fc="#ffffff", ec="#9a9a9a", size=11, color=INK, ls="-", ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fc, ec=ec, lw=1.2, ls=ls))
    tx = x + w / 2 if ha == "center" else x + 0.15
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=size, color=color, linespacing=1.5)


def arrow(ax, x0, y0, x1, y1, color=SUB, text=None, dy=0.12):
    ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4))
    if text:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, text, ha="center", va="bottom", fontsize=9.5, color=SUB)


def overview_figure():
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    # 左: 送るトランザクション
    ax.add_patch(FancyBboxPatch((0.1, 0.35), 2.9, 3.85, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=FILL, ec="#bdbdbd", lw=1))
    ax.text(1.55, 3.95, "blob を添えたトランザクション", ha="center", fontsize=10.5, color=INK)
    box(ax, 0.45, 2.85, 2.2, 0.8, "calldata\n（input）", fc="#ffffff")
    box(ax, 0.45, 1.75, 2.2, 0.7, "versioned hash\n32 バイト × blob の数", fc="#ffffff", size=10)
    box(ax, 0.45, 0.55, 2.2, 0.9, "blob\n1 個 131,072 バイト", fc=RED_PALE, ec=RED)

    # 右上: 実行レイヤー
    ax.add_patch(FancyBboxPatch((4.0, 2.45), 5.75, 1.75, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=PALE, ec="#9cabb5", lw=1))
    ax.text(4.2, 3.95, "実行レイヤー（EVM が動き、ブロックに残り続ける）", fontsize=11, color=INK)
    box(ax, 4.25, 2.8, 2.4, 0.9, "calldata の中身\nCALLDATALOAD で読める", size=10)
    box(ax, 7.05, 2.8, 2.45, 0.9, "versioned hash だけ\nBLOBHASH で読める", size=10)
    arrow(ax, 2.65, 3.25, 4.25, 3.25)
    arrow(ax, 2.65, 2.1, 8.2, 2.8)

    # 右下: コンセンサス・レイヤー
    ax.add_patch(FancyBboxPatch((4.0, 0.35), 5.75, 1.75, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc="#ffffff", ec="#bdbdbd", lw=1, ls="--"))
    ax.text(4.2, 1.85, "コンセンサス・レイヤー（beacon node が blob を提供する）", fontsize=11, color=INK)
    arrow(ax, 2.65, 1.0, 4.25, 1.0)
    # 時間の帯: 4096 epoch は配る、その先は保証されない
    x0, x1, x2 = 4.3, 8.2, 9.5
    ax.add_patch(plt.Rectangle((x0, 0.75), x1 - x0, 0.45, fc=RED_PALE, ec=RED, lw=1))
    ax.text((x0 + x1) / 2, 0.975, "4096 epoch（約 18 日）は提供する義務がある", ha="center", va="center",
            fontsize=9.5, color=INK)
    ax.add_patch(plt.Rectangle((x1, 0.75), x2 - x1, 0.45, fc="#ffffff", ec="#bdbdbd", lw=1, ls=":"))
    ax.text((x1 + x2) / 2, 0.975, "保証なし", ha="center", va="center", fontsize=9.5, color=SUB)
    ax.text(x0, 0.5, "取り込まれた時", fontsize=9, color=SUB)
    ax.text(x2, 0.5, "時間", fontsize=9, color=SUB, ha="right")
    save_plot(fig, "blob_overview.webp")


def read_basics():
    out = {}
    for line in (OUT / "basics.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("slot0"):
            out["hash"] = line.split()[-1]
        if line.startswith("receipt.blobGasUsed"):
            out["blobgas"] = int(line.split()[-1])
        if line.startswith("slot2"):
            out["cds"] = int(line.split()[-1])
    return out


def contract_view_figure():
    b = read_basics()
    h = b["hash"]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.4)
    ax.axis("off")

    # blob を 64 x 64 のマス（1 マス = 32 バイト）で描く。先頭の 1 マスだけ使った
    gx, gy, cell = 0.3, 0.35, 0.05
    n = 64
    ax.add_patch(plt.Rectangle((gx, gy), n * cell, n * cell, fc=FILL, ec="#bdbdbd", lw=1))
    ax.add_patch(plt.Rectangle((gx, gy + (n - 1) * cell), 2 * cell, cell, fc=RED, ec=RED))
    ax.text(gx + n * cell / 2, gy + n * cell + 0.12, "blob: 4096 個 × 32 バイト = 131,072 バイト",
            ha="center", fontsize=10.5, color=INK)
    ax.annotate("左上の 2 マス（64 バイト）に\nデータの長さと\n\"hello\" の 5 バイト",
                (gx + 2 * cell, gy + (n - 0.5) * cell), (gx + 0.5, gy + 1.9),
                fontsize=9.5, color=RED, arrowprops=dict(arrowstyle="-", color=RED, lw=1))
    ax.text(gx + n * cell / 2, gy + 0.7, "残りは 0 でも\nblob gas は 131,072 を払う", ha="center",
            fontsize=10, color=SUB, linespacing=1.5)

    box(ax, 4.0, 3.1, 2.3, 0.8, "KZG commitment\n48 バイト", size=10)
    box(ax, 4.0, 1.75, 2.3, 0.8, "SHA-256 の先頭 1 バイトを\n0x01 に替える", size=9.5)
    box(ax, 4.0, 0.35, 2.3, 0.9, f"versioned hash\n{h[:10]}…{h[-6:]}", size=10, fc=PALE, ec="#9cabb5")
    arrow(ax, gx + n * cell, 3.5, 4.0, 3.5)
    arrow(ax, 5.15, 3.1, 5.15, 2.55)
    arrow(ax, 5.15, 1.75, 5.15, 1.25)

    ax.add_patch(FancyBboxPatch((7.0, 0.35), 2.8, 3.55, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=PALE, ec="#9cabb5", lw=1))
    ax.text(8.4, 3.6, "コントラクトの中", ha="center", fontsize=11, color=INK)
    box(ax, 7.2, 2.35, 2.4, 0.85, f"BLOBHASH(0)\n= {h[:10]}…", size=9.5)
    box(ax, 7.2, 1.35, 2.4, 0.75, f"CALLDATASIZE = {b['cds']}", size=9.5)
    box(ax, 7.2, 0.5, 2.4, 0.6, "blob の中身を読む命令は無い", size=9.5, fc=RED_PALE, ec=RED, color=RED)
    arrow(ax, 6.3, 0.8, 7.2, 2.6)
    save_plot(fig, "blob_contract_view.webp")


def utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.UTC)


def spike_figure(speed=1000, step_s=200, frame_ms=200, hold_ms=3500):
    """2024-03-27 の mainnet。ブロックごとの blob の数と、次のブロックの blob の単価。

    実時間の step_s 秒を 1 コマにし、1 コマを frame_ms ミリ秒で見せる（step_s / frame_ms * 1000 倍速）。
    """
    rows = json.load(open(OUT / "mainnet_2024-03-27_every_block.json"))
    t0 = rows[0]["timestamp"]
    mins = [(r["timestamp"] - t0) / 60 for r in rows]
    fees = [bf.blob_base_fee(r["excessBlobGas"], bf.CANCUN) for r in rows]
    blobs = [r["blobGasUsed"] // bf.GAS_PER_BLOB for r in rows]
    floor_r = max((r for r in rows if r["excessBlobGas"] == 0), key=lambda r: r["number"])
    peak_i = max(range(len(rows)), key=lambda i: fees[i])
    t_floor = (floor_r["timestamp"] - t0) / 60
    t_peak = mins[peak_i]
    t_end = mins[-1]
    assert abs(speed - step_s * 1000 / frame_ms) < 1e-9

    frames, durations = [], []
    k = 0
    while True:
        tcut = min(k * step_s / 60, t_end)
        idx = [i for i, m in enumerate(mins) if m <= tcut]
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True,
                                     gridspec_kw=dict(height_ratios=[3, 1.2], hspace=0.12))
        now = utc(t0 + tcut * 60)
        fig.suptitle(f"2024-03-27 {now:%H:%M} UTC（経過 {tcut:.0f} 分）　mainnet、実時間の {speed} 倍速で再生",
                     x=0.08, ha="left", fontsize=11.5, color=INK, y=0.97)
        a1.set_yscale("log")
        a1.set_ylim(0.5, 5e12)
        a1.set_xlim(0, t_end)
        a1.set_ylabel("blob gas 1 あたりの単価")
        a1.set_yticks([1, 1e3, 1e6, 1e9, 1e12])
        a1.set_yticklabels(["1 wei", "1,000 wei", "100 万 wei", "1 gwei", "1,000 gwei"])
        a1.grid(axis="y", color="#e6e6e6")
        a1.plot([mins[i] for i in idx], [fees[i] for i in idx], color=RED, lw=1.8)
        if idx:
            i = idx[-1]
            a1.plot([mins[i]], [fees[i]], "o", color=RED, ms=6)
            a1.text(mins[i] + 2, fees[i] * 3, f"{fees[i] / 1e9:,.3g} gwei" if fees[i] >= 1e6 else f"{fees[i]:,} wei",
                    fontsize=10.5, color=RED)
        if tcut >= t_floor:
            a1.axvline(t_floor, color=SUB, lw=0.8, ls=":")
            a1.text(t_floor - 1.5, 2e11, "16:12 まで 1 wei", ha="right", fontsize=9.5, color=SUB)
        if tcut >= t_peak:
            a1.text(t_peak - 2, fees[peak_i] * 2.2, "18:13 に 737 gwei", ha="right", fontsize=9.5, color=INK)
        a2.bar([mins[i] for i in idx], [blobs[i] for i in idx], width=0.18, color=ACCENT)
        a2.axhline(3, color=INK, lw=0.8, ls="--")
        a2.text(t_end + 1, 3, "target 3", ha="left", va="center", fontsize=9, color=INK)
        a2.set_ylim(0, 6.6)
        a2.set_yticks([0, 3, 6])
        a2.set_ylabel("blob の数")
        first = (30 - utc(t0).minute % 30) % 30 - utc(t0).second / 60   # 毎時 0 分と 30 分に目盛り
        ticks = [first + 30 * j for j in range(10) if first + 30 * j <= t_end]
        a2.set_xticks(ticks)
        a2.set_xticklabels([f"{utc(t0 + m * 60):%H:%M}" for m in ticks])
        a2.set_xlabel("時刻（UTC）")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, facecolor="#ffffff")
        plt.close(fig)
        frames.append(Image.open(buf).convert("RGB"))
        durations.append(frame_ms)
        if tcut >= t_end:
            break
        k += 1
    durations[-1] = hold_ms
    frames[0].save(HERE / "images" / "blob_fee_spike.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=70, method=6)


def reserve_figure():
    rows = json.load(open(OUT / "mainnet_2026-11_every_block.json"))
    t0 = rows[0]["timestamp"]
    mins = [(r["timestamp"] - t0) / 60 for r in rows]
    fees = [bf.blob_base_fee(r["excessBlobGas"], bf.BPO2) for r in rows]
    reserve = [bf.BLOB_BASE_COST * r["baseFeePerGas"] / bf.GAS_PER_BLOB for r in rows]
    blobs = [r["blobGasUsed"] // bf.GAS_PER_BLOB for r in rows]
    # 同じ使われ方を EIP-7918 なしの式に通した場合
    no7918, ex = [], rows[0]["excessBlobGas"]
    for r in rows:
        no7918.append(bf.blob_base_fee(ex, bf.BPO2))
        ex = bf.next_excess(ex, r["blobGasUsed"], r["baseFeePerGas"], bf.BPO2[:3] + (False,))

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True,
                                 gridspec_kw=dict(height_ratios=[3, 1.2], hspace=0.12))
    a1.set_yscale("log")
    a1.set_ylim(0.5, 3e8)
    a1.set_yticks([1, 1e3, 1e6, 1e8])
    a1.set_yticklabels(["1 wei", "1,000 wei", "100 万 wei", "1 億 wei"])
    a1.grid(axis="y", color="#e6e6e6")
    a1.set_ylabel("blob gas 1 あたりの単価")
    a1.plot(mins, reserve, color=SUB, lw=1.2, ls="--", label="下限: base fee × 8192 / 131072")
    a1.plot(mins, fees, color=RED, lw=1.8, label="実際の単価（ヘッダーから計算）")
    a1.plot(mins, no7918, color=ACCENT, lw=1.5, label="EIP-7918 なしの式に通した場合")
    a1.legend(loc="center right", fontsize=9.5, frameon=False)
    a1.set_title("2026-11-12 12:56〜13:56 UTC の mainnet（BPO2: target 14、max 21）", loc="left",
                 fontsize=11, color=INK)
    a2.bar(mins, blobs, width=0.15, color=ACCENT)
    a2.axhline(14, color=INK, lw=0.8, ls="--")
    a2.text(mins[-1] + 1, 14, "target 14", ha="left", va="center", fontsize=9, color=INK, bbox=dict(fc="#ffffff", ec="none", pad=1))
    a2.set_ylim(0, 22)
    a2.set_yticks([0, 7, 14, 21])
    a2.set_ylabel("blob の数")
    a2.set_xlabel("経過時間（分）")
    save_plot(fig, "blob_fee_reserve.webp")


def crossover_figure():
    rows = json.load(open(OUT / "mainnet_2026-11_every_block.json"))
    import statistics
    base = statistics.median(r["baseFeePerGas"] for r in rows)
    blob = statistics.median(bf.blob_base_fee(r["excessBlobGas"], bf.BPO2) for r in rows)
    gas = dict(tuple(map(int, l.split())) for l in (OUT / "calldata_gas.txt").read_text().splitlines()[1:])
    per_blob = 126945
    max_blobs = 6                                   # 1 トランザクションに添えられる blob（EIP-7594）
    x_end = per_blob * max_blobs                    # 761,670 バイト
    cd_end = (2**24 - 21000) // 40                  # 1 トランザクションの gas 上限 2^24（EIP-7825）に収まる calldata
    xs = sorted({max(1, int(10 ** (e / 40))) for e in range(0, 40 * 6 + 1) if 10 ** (e / 40) <= x_end} | {x_end})
    xs_cd = [n for n in xs if n < cd_end] + [cd_end]

    def cd(n):
        return (21000 + 40 * n) * base / 1e18

    def bl(n):
        return (21000 * base + math.ceil(n / per_blob) * bf.GAS_PER_BLOB * blob) / 1e18

    cross = next(n for n in range(1, 10000) if cd(n) > bl(n))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.plot(xs_cd, [cd(n) for n in xs_cd], color=INK, lw=1.8, label="calldata（21,000 + 40 × バイト数 gas）")
    ax.plot(xs, [bl(n) for n in xs], color=RED, lw=1.8, drawstyle="steps-post",
            label="blob（21,000 gas + blob の数 × 131,072 blob gas）")
    ax.plot(list(gas), [cd(n) for n in gas], "o", color=INK, ms=5, label="anvil で測った calldata の gasUsed")
    ax.axvline(cross, color=SUB, lw=0.8, ls=":")
    ax.text(cross * 1.15, cd(10) * 0.75, f"{cross} バイトで逆転", fontsize=10, color=SUB)
    ax.plot([cd_end], [cd(cd_end)], "x", color=INK, ms=7)
    ax.annotate(f"calldata は {cd_end:,} バイトで\n1 トランザクションの gas 上限", xy=(cd_end, cd(cd_end)),
                xytext=(0.9e5, 5e-3), fontsize=9.5, color=SUB, ha="right", va="center",
                arrowprops=dict(arrowstyle="-", color=SUB, lw=0.8))
    # 文字は blob 1 個の点線より左に置き、線で赤い階段の右端を指す（点線と文字を重ねない）
    ax.annotate(f"blob {max_blobs} 個で\n1 トランザクションの上限", xy=(x_end, bl(x_end)),
                xytext=(per_blob * 0.8, bl(10) * 2.6), fontsize=9.5, color=SUB, ha="right", va="center",
                arrowprops=dict(arrowstyle="-", color=SUB, lw=0.8))
    ax.axvline(per_blob, color=SUB, lw=0.8, ls=":")
    ax.text(per_blob * 0.8, bl(10) * 7, "blob 1 個に\n126,945 バイト", fontsize=9.5, color=SUB, ha="right")
    ax.set_xlabel("送るデータの大きさ（バイト）")
    ax.set_ylabel("手数料（ETH）")
    ax.set_xlim(1, x_end * 1.15)
    ax.set_xticks([1, 10, 100, 1000, 10000, 100000, x_end])
    ax.set_xticklabels(["1", "10", "100", "1,000", "1 万", "10 万", f"{x_end:,}"])
    ax.grid(color="#eeeeee")
    ax.legend(loc="upper left", fontsize=9.5, frameon=True, facecolor="#ffffff", edgecolor="none", framealpha=1)
    ax.set_title(f"2026-11-12 の中央値で計算: base fee {base / 1e9:.3f} gwei、blob gas の単価 {blob / 1e9:.4f} gwei",
                 loc="left", fontsize=10.5, color=INK)
    save_plot(fig, "blob_cost_crossover.webp")
    print("crossover bytes", cross, "base", base, "blob", blob)


if __name__ == "__main__":
    overview_figure()
    contract_view_figure()
    reserve_figure()
    crossover_figure()
    spike_figure()
