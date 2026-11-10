"""Hash Function ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/blockchain-systems/hash-function/figures.py

概念図 (hash_function_concept.svg) は標準ライブラリだけで SVG を手書きする。
"""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6, 4),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path)
    plt.close()
    print(f"wrote {path}")


# --- 図1: 出力のビット数 n と、総当たりに必要な試行回数 ---
# 原像・第二原像は 2^n 回、衝突は 2^(n/2) 回。本文の表と同じ式である。
n = np.arange(64, 513)

fig, ax = plt.subplots()
ax.plot(n, 2.0 ** n, color=COLOR_BLUE, linewidth=1.8, label="Preimage / second preimage: 2^n")
ax.plot(n, 2.0 ** (n / 2), color=COLOR_RED, linewidth=1.8, label="Collision: 2^(n/2)")
ax.set_yscale("log", base=2)

# SHA-256 (n = 256) の 2 点。本文の表の右列に当たる
ax.axvline(256, color=COLOR_GRAY, linestyle="--", linewidth=1)
ax.text(262, 2.0 ** 430, "SHA-256 (n = 256)", color=COLOR_GRAY, fontsize=9, ha="left", va="top")
for exp, color in ((256, COLOR_BLUE), (128, COLOR_RED)):
    ax.plot([256], [2.0 ** exp], marker="o", markersize=6, color=color)
    ax.annotate(
        f"2^{exp}",
        xy=(256, 2.0 ** exp),
        xytext=(268, 2.0 ** (exp - 40)),
        color=color,
        fontsize=9,
        va="center",
        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 0.8},
    )

# SHA-1 (n = 160) の衝突は、総当たりの 2^80 回より少ない計算で見付かった
ax.plot([160], [2.0 ** 80], marker="o", markersize=6, color=COLOR_GREEN)
ax.annotate(
    "SHA-1 (n = 160): 2^80 by brute force,\nbut a collision was found\nwith far fewer trials",
    xy=(160, 2.0 ** 76),
    xytext=(278, 2.0 ** 40),
    color=COLOR_GREEN,
    fontsize=9,
    ha="left",
    va="center",
    arrowprops={"arrowstyle": "->", "color": COLOR_GREEN, "linewidth": 1.0},
)

exps = (0, 128, 256, 384, 512)
ax.set_yticks([2.0 ** e for e in exps])
ax.set_yticklabels([f"2^{e}" for e in exps])
ax.set_ylim(2.0 ** 0, 2.0 ** 600)
ax.set_xlim(64, 512)
ax.set_xticks([64, 128, 160, 256, 384, 512])
ax.set_xlabel("Output length n (bits)")
ax.set_ylabel("Trials needed by brute force")
ax.legend(loc="upper left", fontsize=9)

save("hash_function_attack_cost.svg")


# --- 概念図: 大きさの違う入力が、どれも同じ大きさの 32 バイトに入る ---
# 標準ライブラリだけで SVG を手書きする。入力の正方形の面積は模式で、
# 1 文字 < 数 MB < 数 GB の順に大きくし、出力の箱は全て同じ大きさにする。
from html import escape

HERE = pathlib.Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '<marker id="arrowred" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def circle(self, cx, cy, r, fill, stroke, sw=3, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def box(self, x, y, w, h, fill, stroke, sw=3, rx=14):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=4):
        m = "arrowred" if color == RED else "arrow"
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{m})"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "大きさの違う入力が、どれも 32 バイトのハッシュ値になる")
    right = 370  # right edge of the input squares
    rows = [("1 文字", 14, 92), ("数 MB", 96, 200), ("数 GB", 236, 392)]

    f.box(465, 40, 140, 480, PALE, ACCENT, rx=14)
    f.text(535, 290, "SHA-256", 26, weight="normal")

    for label, side, cy in rows:
        x, y = right - side, cy - side / 2
        f.box(x, y, side, side, FILL, SUB, sw=2.5, rx=3 if side < 30 else 6)
        if side > 200:
            f.text(x + side / 2, cy + 9, label, 28)
        else:
            f.text(60, cy + 9, label, 28, anchor="start")
        f.arrow(right + 10, cy, 455, cy)
        f.arrow(615, cy, 682, cy)
        f.box(690, cy - 34, 200, 68, GREEN_PALE, GREEN, rx=8)
        f.text(790, cy + 9, "32 バイト", 26, INK, weight="normal")

    f.text(790, 495, "どれも同じ長さ", 26, SUB)
    f.text(60, 34, "入力の大きさは模式", 24, SUB, anchor="start")
    f.save(OUT / "hash_function_concept.svg")


concept_figure()
