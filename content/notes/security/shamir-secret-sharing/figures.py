"""Shamir's Secret Sharing - 閾値以上の Share が揃った時だけ Secret を復元する の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/shamir-secret-sharing/figures.py
"""

import pathlib

import matplotlib
matplotlib.use("Agg")  # 表示せずファイルへ書く
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
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "shamir-secret-sharing",  # 要素の id を固定する
    # 2 枚を横に並べた幅の広い図なので、本文の幅（720px）に縮めても 12px 以上になる大きさにする。
    "font.size": 13,
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path, metadata={"Date": None})  # 日付を入れず、再生成で差分を出さない
    plt.close()
    print(f"wrote {path}")


# --- 図1: 実数上の模式図。2 点では q(0) が定まらず、3 点で 1 本に定まる ---
#
# 通す点は (1, 2) と (2, 4)。q(0) = c を決めると、q(x) = c + (2 - 3c/2)x + (c/2)x^2
# が一意に決まる。c を変えても 2 点は必ず通るので、2 点からは c を絞れない。
def through_two_points(c: float, x: np.ndarray) -> np.ndarray:
    a2 = c / 2.0
    a1 = 2.0 - 1.5 * c
    return c + a1 * x + a2 * x**2


x = np.linspace(-0.05, 3.2, 400)
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)

left, right = axes
for c, color in [(-1.0, COLOR_BLUE), (1.0, COLOR_RED), (3.0, COLOR_GREEN)]:
    left.plot(x, through_two_points(c, x), color=color, linewidth=1.8,
              label=f"q(0) = {c:.0f}")
    left.plot([0], [c], marker="o", markersize=6, color=color)
left.plot([1, 2], [2, 4], linestyle="none", marker="o", markersize=7,
          color=COLOR_GRAY, zorder=5)
for px, py, name in [(1, 2, "Share 1"), (2, 4, "Share 2")]:
    left.annotate(name, (px, py), textcoords="offset points", xytext=(6, -14),
                  fontsize=12, color=COLOR_GRAY)
left.axvline(0, color=COLOR_GRAY, linestyle="--", linewidth=1)
left.set_title("2 shares (k-1): q(0) is not determined", fontsize=13)
left.set_xlabel("x")
left.set_ylabel("q(x)")
left.legend(loc="upper left", frameon=False, fontsize=12)

# 3 点 (1, 2), (2, 4), (3, 7) を通る 2 次式は q(x) = 1 + 0.5x + 0.5x^2 だけ
true_poly = 1.0 + 0.5 * x + 0.5 * x**2
right.plot(x, true_poly, color=COLOR_BLUE, linewidth=1.8)
right.plot([1, 2, 3], [2, 4, 7], linestyle="none", marker="o", markersize=7,
           color=COLOR_GRAY, zorder=5)
for px, py, name in [(1, 2, "Share 1"), (2, 4, "Share 2"), (3, 7, "Share 3")]:
    right.annotate(name, (px, py), textcoords="offset points", xytext=(6, -14),
                   fontsize=12, color=COLOR_GRAY)
right.plot([0], [1], marker="o", markersize=6, color=COLOR_RED)
right.annotate("Secret = q(0) = 1", (0, 1), textcoords="offset points",
               xytext=(8, -18), fontsize=12, color=COLOR_RED)
right.axvline(0, color=COLOR_GRAY, linestyle="--", linewidth=1)
right.set_title("3 shares (k): one quadratic, one q(0)", fontsize=13)
right.set_xlabel("x")
save("sss_polynomial_intuition.svg")


# --- 図2: mod 13 で、集めた Share の個数ごとに残る Secret 候補の数 ---
#
# q(x) = a0 + a1x + a2x^2 mod 13 を全て（13^3 通り）作り、手元の Share と
# 一致する物だけを a0 ごとに数える。本文と同じ (1, 9)、(2, 7)、(3, 11) を使う。
P = 13
ALL_SHARES = [(1, 9), (2, 7), (3, 11)]


def count_candidates(shares) -> np.ndarray:
    counts = np.zeros(P, dtype=int)
    for a0 in range(P):
        for a1 in range(P):
            for a2 in range(P):
                if all((a0 + a1 * sx + a2 * sx * sx) % P == sy for sx, sy in shares):
                    counts[a0] += 1
    return counts


two = count_candidates(ALL_SHARES[:2])
three = count_candidates(ALL_SHARES)

fig, axes = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
panels = [
    (axes[0], two, COLOR_BLUE, "2 shares (k-1): every q(0) keeps one polynomial"),
    (axes[1], three, COLOR_RED, "3 shares (k): only q(0) = 4 survives"),
]
for ax, counts, color, title in panels:
    ax.bar(range(P), counts, color=color, width=0.7)
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Candidate secret q(0) in GF(13)")
    ax.set_xticks(range(P))
    ax.tick_params(axis="x", labelsize=11.5)  # 10・11・12 の目盛りが重ならない大きさ
    ax.set_ylim(0, 1.35)
    ax.set_yticks([0, 1])
axes[0].set_ylabel("Polynomials that fit")
save("sss_candidates_mod13.svg")

# --- 図3: x = 13 は GF(13) の中では 0 と同じ（tss-lib などの x 座標の検査漏れ） ---
#
# 13 個の目盛りを円に並べ、x = 1, 2, ... と進んだ 13 が 0 の位置に戻ることを描く。
# 承認済みの配色で、Python 標準ライブラリだけで SVG を書く。
def x13_wraps_svg() -> str:
    import math

    w, h = 960, 540
    cx, cy, r = 260, 305, 170
    blue, blue_f = "#7aa6c2", "#eaf1f5"
    ochre = "#d4a24c"
    red, red_f = "#e15759", "#fbe3e3"
    ink, sub = "#1f1f1f", "#666666"
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        'font-family="sans-serif" font-weight="normal">',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{blue_f}" stroke="{blue}" stroke-width="3"/>',
    ]
    for v in range(13):
        a = -math.pi / 2 + 2 * math.pi * v / 13
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        tx, ty = cx + (r - 40) * math.cos(a), cy + (r - 40) * math.sin(a)
        if v == 0:
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="16" fill="{red_f}" stroke="{red}" stroke-width="3"/>')
        else:
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="{blue}"/>')
        out.append(f'<text x="{tx:.1f}" y="{ty + 9:.1f}" font-size="26" fill="{ink}" text-anchor="middle">{v}</text>')
    # 12 から 13（= 0）へ進む矢印
    a12 = -math.pi / 2 + 2 * math.pi * 12 / 13
    ro = r + 34
    x1, y1 = cx + ro * math.cos(a12), cy + ro * math.sin(a12)
    x2, y2 = cx + ro * math.cos(-math.pi / 2 - 0.08), cy + ro * math.sin(-math.pi / 2 - 0.08)
    out.append(
        f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{ochre}"/></marker></defs>'
    )
    out.append(
        f'<path d="M{x1:.1f},{y1:.1f} A{ro},{ro} 0 0 1 {x2:.1f},{y2:.1f}" fill="none" '
        f'stroke="{ochre}" stroke-width="4" marker-end="url(#ah)"/>'
    )
    out.append(f'<text x="{cx - 120}" y="{cy - r - 62}" font-size="24" fill="{sub}" text-anchor="middle">12 + 1 = 13</text>')
    out.append(f'<text x="{cx}" y="{cy + 10}" font-size="24" fill="{sub}" text-anchor="middle">x mod 13</text>')
    # 右の説明
    lx = 520
    rows = [
        (140, "ID chosen by a participant: x = 13", ink, 26),
        (185, "integer check: 13 ≠ 0 → accepted", sub, 24),
        (275, "inside GF(13): 13 = 0", ink, 26),
        (320, "share for x = 13 is q(0)", sub, 24),
    ]
    for y, s, c, fs in rows:
        out.append(f'<text x="{lx}" y="{y}" font-size="{fs}" fill="{c}">{s}</text>')
    out.append(f'<rect x="{lx - 10}" y="370" width="390" height="70" rx="8" fill="{red_f}" stroke="{red}" stroke-width="2"/>')
    out.append(f'<text x="{lx + 185}" y="415" font-size="26" fill="{ink}" text-anchor="middle">each dealer\'s secret leaks</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


(OUT / "sss_x13_wraps.svg").write_text(x13_wraps_svg(), encoding="utf-8")
print(f"wrote {OUT / 'sss_x13_wraps.svg'}")


if __name__ == "__main__":
    print("\n--- 本文で使っている値 ---")
    print(f"2 個の Share での候補ごとの多項式の数: {two.tolist()}")
    print(f"3 個の Share での候補ごとの多項式の数: {three.tolist()}")
