"""SHA-256 - なぜ任意長のデータを固定長に変換できるのか の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/sha-256/figures.py
"""

import hashlib
import pathlib

import matplotlib

matplotlib.use("Agg")  # 表示せずファイルへ書く
import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6, 4),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(20260904)  # seed を固定して同じ図が出るようにする

PAIRS = 2000
MSG_BYTES = 32


def popcount(data: bytes) -> int:
    return sum(bin(b).count("1") for b in data)


def differing_bits(a: bytes, b: bytes) -> int:
    return popcount(bytes(x ^ y for x, y in zip(a, b)))


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path)
    plt.close()
    print(f"wrote {path}")


# --- 1 bit だけ違う入力の組で、ハッシュ値の異なる bit 数を数える ---
counts = []
for _ in range(PAIRS):
    msg = bytearray(rng.integers(0, 256, size=MSG_BYTES, dtype=np.uint8).tolist())
    flipped = bytearray(msg)
    pos = int(rng.integers(0, MSG_BYTES * 8))
    flipped[pos // 8] ^= 1 << (pos % 8)
    h1 = hashlib.sha256(bytes(msg)).digest()
    h2 = hashlib.sha256(bytes(flipped)).digest()
    counts.append(differing_bits(h1, h2))

counts = np.array(counts)
print(f"mean={counts.mean():.2f} min={counts.min()} max={counts.max()}")

bins = np.arange(counts.min() - 0.5, counts.max() + 1.5, 1)
plt.hist(counts, bins=bins, color=COLOR_BLUE, edgecolor="white", linewidth=0.4)
plt.axvline(128, color=COLOR_RED, linestyle="--", linewidth=1.5, zorder=5,
            label=f"128 = half of 256 output bits\n(measured mean {counts.mean():.1f})")
plt.xlabel("Differing bits between the two SHA-256 digests")
plt.ylabel(f"Input pairs (out of {PAIRS})")
plt.ylim(0, np.histogram(counts, bins=bins)[0].max() * 1.35)  # 凡例が棒に重ならない余白
plt.legend(loc="upper right", fontsize=9, framealpha=0.9)
plt.annotate(f"min {counts.min()}", xy=(counts.min(), 0), xytext=(counts.min(), 22),
             color=COLOR_GRAY, fontsize=9, ha="left")
plt.annotate(f"max {counts.max()}", xy=(counts.max(), 0), xytext=(counts.max(), 22),
             color=COLOR_GRAY, fontsize=9, ha="right")
save("hash_function_avalanche.svg")


# --- 冒頭の概念図（標準ライブラリだけで SVG を書く） ---
#
# 1 byte の note.txt と 64 MiB の disk.img を、512 bit のブロックの列として横に並べる。
# ブロックを何個読んでも、ブロックの間を渡る内部状態（256 bit）の箱は同じ大きさで、
# 最後の箱がそのままハッシュ値になる。padding（1 の bit・0 埋め・長さ）は赤で塗る。
# note.txt は 8 + 1 + 439 + 64 = 512 bit で 1 ブロック、disk.img は 2^29 bit が 512 で
# 割り切れるので、padding だけのブロックが 1 個増えて 1,048,577 ブロックになる。
from html import escape  # noqa: E402

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", COLOR_BLUE, COLOR_RED
FILL = "#f2f2f2"
OCHRE = "#d4a24c"  # padding（概念図だけ。グラフの色は変えない）
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
assert (64 * 2**20 * 8) % 512 == 0 and 8 + 1 + 64 <= 512


def concept_figure() -> None:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" '
        'viewBox="0 0 960 540" role="img"><title>ブロックの数と内部状態の大きさ</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
        '<rect width="960" height="540" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                     f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def rect(x, y, w, h, fill, stroke="none", sw=2.5, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" '
                     f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(x1, x2, y):
        parts.append(f'<line x1="{x1}" y1="{y}" x2="{x2 - 7}" y2="{y}" stroke="{SUB}" '
                     f'stroke-width="3"/>')
        parts.append(f'<path d="M{x2} {y} L{x2 - 10} {y - 6} L{x2 - 10} {y + 6} Z" fill="{SUB}"/>')

    S, BW, H, GAP = 56, 100, 56, 26  # state size, block width, height, gap with arrow
    END = 900                          # right edge of the final state

    def row(cy, items):
        """items: ("state",) / ("block", padding_fraction) / ("dots",), drawn right-aligned."""
        widths = [S if k[0] == "state" else BW for k in items]
        x = END - sum(widths) - GAP * (len(items) - 1)
        top = cy - H / 2
        for i, (item, w) in enumerate(zip(items, widths)):
            kind = item[0]
            if kind == "state":
                last = i == len(items) - 1
                rect(x, cy - S / 2, S, S, ACCENT, INK if last else "none", sw=3)
            elif kind == "dots":
                rect(x, top, w, H, "#ffffff", SUB, dash="6 6")
                text(x + w / 2, cy + 8, "…", 28, SUB)
            else:
                pad = item[1]
                rect(x, top, w, H, FILL, SUB)
                if pad:
                    pw = w if pad == 1 else min(w * pad, w - 8)  # 1 byte のデータも見える幅に残す
                    rect(x + w - pw, top, pw, H, OCHRE)
            if i < len(items) - 1:
                arrow(x + w + 4, x + w + GAP - 4, cy)
            x += w + GAP

    # Legend.
    for x, fill, label in [(60, FILL, "ブロック 512 bit"), (340, OCHRE, "padding"),
                           (560, ACCENT, "内部状態 256 bit")]:
        rect(x, 40, 34, 34, fill, SUB if fill == FILL else "none")
        text(x + 46, 66, label, 24, anchor="start")

    # note.txt: 8 bit of data, the rest of the only block is padding.
    y1, y2 = 190, 330
    text(60, y1 - 6, "1 byte", 28, weight="normal", anchor="start")
    text(60, y1 + 28, "note.txt", 24, SUB, anchor="start")
    row(y1, [("state",), ("block", 1 - 8 / 512), ("state",)])

    # disk.img: 1,048,576 full blocks, then one block of padding only.
    text(60, y2 - 6, "64 MiB", 28, weight="normal", anchor="start")
    text(60, y2 + 28, "disk.img", 24, SUB, anchor="start")
    row(y2, [("state",), ("block", 0), ("state",), ("dots",),
             ("state",), ("block", 1.0), ("state",)])
    text(220, y2 + 70, "データ 1,048,576 ブロック ＋ padding 1 ブロック", 24, SUB, anchor="start")

    text(END + 20, 490, "どちらも最後の 256 bit がハッシュ値", 26, anchor="end")
    parts.append(f'<line x1="{END - S / 2}" y1="{y2 + S / 2}" x2="{END - S / 2}" y2="{455}" '
                 f'stroke="{INK}" stroke-width="2"/>')

    path = OUT / "sha-256_concept.svg"
    path.write_text("\n".join(parts + ["</svg>"]) + "\n", encoding="utf-8")
    print(f"wrote {path}")


concept_figure()
