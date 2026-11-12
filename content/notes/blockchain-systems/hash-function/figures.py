"""Hash Function ノートの図を作る。

    python3 figures.py   # -> images/*.webp

数値の図は lab/output/（lab/run.sh の出力）を読む。仕組みの図は
matplotlib の箱と矢印で描く。どれも PNG（dpi 200、白背景）から WebP にする。

- tries_figure(): keccak256 の先頭 n ビットが一致するまでの試行回数。表紙
- collide32_figure(): 32 ビットでどれでもよい 2 つが一致するまでの回数、200 回の分布
- poly_figure(): Poly Network の名前と、狙った関数の keccak256
- padding_figure(): Keccak-256 と SHA3-256 の最後のブロック
- length_extension_figure(): sha256(秘密 || 本文) の値から計算を続ける
"""

import csv
import io
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#4f7fa0", "#c8423f", "#fbe3e3"
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP",
    "font.size": 11,
    "axes.edgecolor": SUB,
    "axes.labelcolor": INK,
    "xtick.color": SUB,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
MONO = "DejaVu Sans Mono"


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(buf).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def measured():
    d = defaultdict(list)
    with open(OUT / "measure.tsv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            d[(r["kind"], int(r["n"]))].append(int(r["tries"]))
    return d


def poly_tries():
    text = (OUT / "poly.txt").read_text(encoding="utf-8")
    m = re.search(r"tries=(\d+) seconds=([\d.]+) threads=(\d+)", text)
    return int(m.group(1)), float(m.group(2)), int(m.group(3))


def jp(n):
    """1,121,318,094 -> 約 11 億 の形"""
    if n >= 10**8:
        return f"約 {n / 10**8:.0f} 億"
    if n >= 10**4:
        return f"約 {n / 10**4:.0f} 万"
    return f"{n:,}"


def tries_figure():
    d = measured()
    poly, sec, threads = poly_tries()
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    xs = list(range(8, 33))
    ax.plot(xs, [2**n for n in xs], color=RED, lw=1.2, ls="--", label="決まった値に当てる: 理論の平均 $2^n$")
    ax.plot(xs, [math.sqrt(math.pi / 2 * 2**n) for n in xs], color=ACCENT, lw=1.2, ls="--",
            label="どれでもよい 2 つ: 理論の平均 約 $1.25 \\times 2^{n/2}$")
    tn = sorted(n for k, n in d if k == "target")
    cn = sorted(n for k, n in d if k == "collide")
    ax.plot(tn, [statistics.mean(d[("target", n)]) for n in tn], "o", color=RED, ms=7,
            label="決まった値に当てる: 実測の平均")
    ax.plot(cn, [statistics.mean(d[("collide", n)]) for n in cn], "o", color=ACCENT, ms=7,
            label="どれでもよい 2 つ: 実測の平均（各 200 回）")
    ax.plot([32], [poly], "*", color=RED, ms=17, mec=INK, mew=0.6)
    ax.annotate(f"Poly Network で攻撃者が使った名前 f1121318093\nf0 から数えて {poly:,} 回目\n"
                f"手元の {threads} スレッドで {sec:.0f} 秒",
                xy=(32, poly), xytext=(21.6, 6e10), fontsize=10, color=INK,
                arrowprops=dict(arrowstyle="->", color=SUB, lw=0.8))
    c32 = statistics.mean(d[("collide", 32)])
    ax.annotate(f"関数セレクターの 32 ビットで\n平均 {c32:,.0f} 回", xy=(32, c32), xytext=(25.3, 5e2),
                fontsize=10, color=INK, arrowprops=dict(arrowstyle="->", color=SUB, lw=0.8))
    ax.set_yscale("log")
    ax.set_xticks([8, 12, 16, 20, 24, 28, 32])
    ax.set_xlabel("比べる先頭のビット数 n")
    ax.set_ylabel("一致するまでの試行回数")
    ax.set_title("keccak256 の先頭 n ビットが一致するまでの試行回数（実測）", fontsize=12, loc="left", color=INK)
    ax.grid(True, which="major", alpha=0.3, lw=0.5)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.set_ylim(5, 2e12)
    save(fig, "tries.webp")


def collide32_figure():
    v = measured()[("collide", 32)]
    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    ax.hist([x / 1000 for x in v], bins=25, color=PALE, edgecolor=ACCENT, lw=0.8)
    m = statistics.mean(v)
    ax.axvline(m / 1000, color=ACCENT, lw=1.4)
    top = ax.get_ylim()[1]
    ax.set_ylim(0, top * 1.15)
    ax.text(m / 1000 + 2, top * 1.07, f"平均 {m:,.0f} 回", color=INK, fontsize=10)
    ax.set_xlabel("一致するまでの試行回数（千回）")
    ax.set_ylabel("200 回のうちの回数")
    ax.set_title(f"32 ビットでどれでもよい 2 つが一致するまで（200 回、最小 {min(v):,} 回・最大 {max(v):,} 回）",
                 fontsize=11, loc="left", color=INK)
    save(fig, "collide32.webp")


def box(ax, x, y, w, h, text, fc=FILL, ec=SUB, size=10, family=None, color=INK, ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=ec, lw=0.9))
    tx = x + w / 2 if ha == "center" else x + 0.15
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=size, color=color,
            family=family or plt.rcParams["font.family"])


def arrow(ax, x0, y0, x1, y1, color=SUB):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12, color=color, lw=1.0))


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-0.1, w)
    ax.set_ylim(-0.15, h)
    ax.axis("off")
    return fig, ax


def poly_figure():
    from importlib import util
    spec = util.spec_from_file_location("keccak", HERE / "lab" / "keccak.py")
    k = util.module_from_spec(spec)
    spec.loader.exec_module(k)
    a = k.keccak256(b"putCurEpochConPubKeyBytes(bytes)").hex()
    b = k.keccak256(b"f1121318093(bytes,bytes,uint64)").hex()
    fig, ax = canvas(9.4, 3.6)
    ax.text(0.1, 3.35, "狙われた関数", fontsize=10, color=SUB)
    box(ax, 0.1, 2.35, 3.4, 0.75, "putCurEpochConPubKeyBytes(bytes)", family=MONO, size=9)
    ax.text(0.1, 1.55, "攻撃者が送った名前 ＋ 固定された引数の型", fontsize=10, color=SUB)
    box(ax, 0.1, 0.55, 3.4, 0.75, "f1121318093(bytes,bytes,uint64)", fc=RED_PALE, ec=RED, family=MONO, size=9)
    for y, h in [(2.72, a), (0.92, b)]:
        arrow(ax, 3.6, y, 4.3, y)
        ax.text(3.95, y + 0.12, "keccak256", ha="center", fontsize=8, color=SUB, family=MONO)
        ax.add_patch(FancyBboxPatch((4.4, y - 0.37), 4.9, 0.75, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc="#ffffff", ec=SUB, lw=0.9))
        ax.text(4.55, y, h[:8], fontsize=9.5, color=RED, family=MONO, va="center")
        ax.text(4.55 + 0.76, y, h[8:40] + "…", fontsize=9.5, color=SUB, family=MONO, va="center")
    ax.add_patch(FancyBboxPatch((4.47, 0.4), 0.8, 2.75, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="none", ec=RED, lw=1.2, ls="--"))
    ax.text(5.4, 1.82, "先頭 4 バイトだけを比べるので、同じ関数として呼ばれる\n残りの 28 バイトは全く違う",
            fontsize=10, color=INK, va="center")
    save(fig, "poly.webp")


def padding_figure():
    fig, ax = canvas(10.0, 3.3)
    ax.text(0.1, 3.05, "空の入力を 1 ブロック（136 バイト）に詰めた形", fontsize=10, color=SUB)
    rows = [(2.0, "01", "Keccak-256（Ethereum の keccak256）", "c5d24601…85a470"),
            (0.6, "06", "SHA3-256（FIPS 202、hashlib.sha3_256）", "a7ffc6f8…f8434a")]
    for y, b, name, out in rows:
        ax.text(0.1, y + 0.78, name, fontsize=10, color=INK)
        box(ax, 0.1, y, 0.9, 0.6, b, fc=RED_PALE, ec=RED, family=MONO, size=11)
        box(ax, 1.0, y, 3.6, 0.6, "00 00 … 00（134 バイト）", size=9, color=SUB)
        box(ax, 4.6, y, 0.9, 0.6, "80", family=MONO, size=11)
        arrow(ax, 5.65, y + 0.3, 6.45, y + 0.3)
        ax.text(6.05, y + 0.42, "Keccak-f", ha="center", fontsize=8, color=SUB, family=MONO)
        box(ax, 6.55, y, 3.3, 0.6, out, fc="#ffffff", family=MONO, size=10)
    ax.text(0.15, 0.2, "違いは赤い 1 バイトだけ。出力は全く別の値になる", fontsize=10, color=INK)
    save(fig, "padding.webp")


def length_extension_figure():
    fig, ax = canvas(10.4, 4.2)
    # 上の段: サーバーが作った値
    ax.text(0.1, 3.9, "サーバー: sha256(秘密 ‖ 本文) を値として渡す", fontsize=10, color=SUB)
    box(ax, 0.1, 2.85, 1.6, 0.7, "秘密\n16 バイト", fc="#dddddd", size=9)
    box(ax, 1.7, 2.85, 2.0, 0.7, "本文\n19 バイト", size=9)
    box(ax, 3.7, 2.85, 1.5, 0.7, "パディング\n29 バイト", size=9, color=SUB)
    arrow(ax, 5.3, 3.2, 6.1, 3.2)
    ax.text(5.7, 3.33, "圧縮", ha="center", fontsize=8.5, color=SUB)
    box(ax, 6.2, 2.85, 4.0, 0.7, "値 = 内部状態\nc253f0e1…（攻撃者にも見える）", fc=PALE, ec=ACCENT, size=9)
    # 下の段: 攻撃者
    ax.text(0.1, 2.15, "攻撃者: 秘密を知らずに、値から計算を続ける", fontsize=10, color=SUB)
    box(ax, 0.1, 1.1, 5.1, 0.7, "（秘密 ‖ 本文 ‖ パディング）は計算済みとして飛ばす", size=9, color=SUB)
    box(ax, 6.2, 1.1, 1.9, 0.7, "追記\n15 バイト", fc=RED_PALE, ec=RED, size=9)
    box(ax, 8.1, 1.1, 2.1, 0.7, "パディング\n49 バイト", size=9, color=SUB)
    arrow(ax, 7.2, 2.8, 7.2, 1.85, color=ACCENT)
    ax.text(7.3, 2.3, "初期値にする", fontsize=8.5, color=ACCENT)
    arrow(ax, 9.15, 1.05, 9.15, 0.55)
    box(ax, 5.2, 0.0, 5.0, 0.5, "新しい値 d273494c… = sha256(秘密 ‖ 本文 ‖ パディング ‖ 追記)", fc="#ffffff", ec=RED, size=9)
    save(fig, "length_extension.webp")


if __name__ == "__main__":
    tries_figure()
    collide32_figure()
    poly_figure()
    padding_figure()
    length_extension_figure()
