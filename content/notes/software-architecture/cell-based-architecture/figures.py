"""Cell-based Architecture ノートの図を生成する。

再生成:
    uv run --with matplotlib python content/notes/software-architecture/cell-based-architecture/figures.py
"""

import pathlib
from math import comb

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6.4, 4),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "cell-based-architecture",
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)

# ワーカー 100 台。1 人の顧客が使う台数 k を変える。
N = 100
ks = list(range(1, 11))
cell_full = [k / N for k in ks]  # 通常の cell: 毒入り顧客と同じ cell の顧客が全滅
shuffle_full = [1 / comb(N, k) for k in ks]  # 組が完全に重なる顧客だけが全滅
# k = 1 では一部だけ止まる顧客がいないので、対数軸に載せない。
shuffle_part = [1 - comb(N - k, k) / comb(N, k) - 1 / comb(N, k) if k > 1 else float("nan")
                for k in ks]

fig, ax = plt.subplots()
ax.semilogy(ks, cell_full, marker="s", markersize=4, color=COLOR_GRAY,
            label="Cell: fully down")
ax.semilogy(ks, shuffle_full, marker="o", markersize=4, color=COLOR_RED,
            label="Shuffle sharding: fully down")
ax.semilogy(ks, shuffle_part, marker="^", markersize=4, color=COLOR_BLUE,
            linestyle="--", label="Shuffle sharding: partly down")
ax.set_xlabel("Workers per customer (k), out of 100")
ax.set_ylabel("Share of other customers")
ax.set_xticks(ks)
ax.set_ylim(1e-14, 1.5)
ax.legend(loc="lower left", fontsize=9, frameon=False)
plt.savefig(OUT / "cell_shuffle_overlap.svg")
plt.close()
print("wrote", OUT / "cell_shuffle_overlap.svg")


# --- 冒頭の図: 機能で分けるか、顧客で分けるか ---
from matplotlib.patches import FancyBboxPatch, Rectangle

FUNCS = ["Orders", "Payments", "Search"]
GROUPS = ["A-D", "E-H", "I-L"]
COLOR_TEXT = "#1f1f1f"
COLOR_FILL = "#f2f2f2"


def grid(ax, title, by_row):
    ax.set_xlim(-1.5, 3.05)
    ax.set_ylim(-0.95, 3.45)
    ax.axis("off")
    ax.set_title(title, fontsize=13, color=COLOR_TEXT)
    for r, func in enumerate(FUNCS):
        y = 2 - r
        ax.text(-0.15, y + 0.4, func, ha="right", va="center", fontsize=12, color=COLOR_GRAY)
        for c in range(len(GROUPS)):
            ax.add_patch(Rectangle((c + 0.1, y + 0.1), 0.8, 0.6, facecolor=COLOR_FILL,
                                   edgecolor=COLOR_GRAY, linewidth=0.6))
    for c, group in enumerate(GROUPS):
        ax.text(c + 0.5, -0.3, group, ha="center", va="center", fontsize=12, color=COLOR_GRAY)
    ax.text(1.5, -0.7, "customers", ha="center", va="center", fontsize=12, color=COLOR_GRAY)
    for i in range(3):
        if by_row:  # 1 つのサービスが全顧客を処理する
            box = (0.02, 2 - i + 0.02, 2.96, 0.76)
        else:  # 1 つの cell が一部の顧客の全機能を処理する
            box = (i + 0.02, 0.02, 0.96, 2.76)
            ax.text(i + 0.5, 3.1, f"cell {i + 1}", ha="center", va="center",
                    fontsize=12, color=COLOR_TEXT)
        ax.add_patch(FancyBboxPatch(box[:2], box[2], box[3], boxstyle="round,pad=0,rounding_size=0.06",
                                    fill=False, edgecolor=COLOR_BLUE, linewidth=2.5))


fig, (left, right) = plt.subplots(1, 2, figsize=(8, 3.3))
grid(left, "Microservices: split by function", by_row=True)
grid(right, "Cells: split by customer", by_row=False)
fig.subplots_adjust(wspace=0.05)
plt.savefig(OUT / "cell_split_axis.svg")
plt.close()
print("wrote", OUT / "cell_split_axis.svg")


# cell を 10 個から 11 個に増やした時、行き先が変わる顧客（標準ライブラリの SVG）。
# 顧客 ID は "customer-<番号>" の sha256。剰余と、仮想ノード 100 個ずつのハッシュリングを比べる。
def reroute_figure():
    import bisect
    import hashlib
    from html import escape

    def h(s):
        return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")

    def ring(n_cells, vnodes=100):
        points = sorted((h(f"cell-{c}-vnode-{v}"), c) for c in range(n_cells) for v in range(vnodes))
        keys = [p for p, _ in points]
        return lambda x: points[bisect.bisect(keys, x) % len(points)][1]

    ids = [h(f"customer-{i}") for i in range(10_000)]
    ring10, ring11 = ring(10), ring(11)
    moved = {
        "modulo": [x % 10 != x % 11 for x in ids],
        "ring": [ring10(x) != ring11(x) for x in ids],
    }
    blue, blue_pale, ochre, ochre_pale = COLOR_BLUE, "#eaf1f5", "#d4a24c", "#f8eed8"
    font = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
    w, hgt = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{hgt}" viewBox="0 0 {w} {hgt}" '
        f'role="img"><title>{escape("cell を 10 個から 11 個に増やした時に行き先が変わる顧客")}</title>',
        f"<style>text{{font-family:{font};fill:#1f1f1f}} .sub{{fill:{COLOR_GRAY}}}</style>",
        f'<rect width="{w}" height="{hgt}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="middle"{c}>{escape(s)}</text>')

    for j, (key, title) in enumerate((("modulo", "hash(id) % N"), ("ring", "consistent hashing"))):
        x0 = 52 + 470 * j
        text(x0 + 198, 46, title, 26)
        for i in range(110):
            x, y = x0 + 36 * (i % 11), 72 + 36 * (i // 11)
            fill, stroke = (ochre_pale, ochre) if moved[key][i] else (blue_pale, blue)
            p.append(f'<rect x="{x}" y="{y}" width="30" height="30" rx="4" fill="{fill}" '
                     f'stroke="{stroke}" stroke-width="1.5"/>')
        share = sum(moved[key]) / len(ids)
        text(x0 + 198, 474, f"moved: {share:.0%} of 10,000 customers", 24)
    text(480, 522, "10 → 11 cells.  ochre = goes to another cell,  blue = stays", 22, "sub")
    p.append("</svg>")
    (OUT / "cell_reroute.svg").write_text("\n".join(p) + "\n", encoding="utf-8")
    print("wrote", OUT / "cell_reroute.svg")


reroute_figure()
