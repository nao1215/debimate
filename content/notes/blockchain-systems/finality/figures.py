"""Finality ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/blockchain-systems/finality/figures.py
"""

import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def attacker_success_probability(q: float, z: int) -> float:
    """Bitcoin 白書 (Nakamoto 2008) の AttackerSuccessProbability を写したもの。

    受け取り側が取引の後ろに z ブロック積むまで待った時点で、攻撃者がなお
    追い付く確率を返す。攻撃者の進捗は期待値 z*q/p の Poisson 分布と仮定する。
    """
    p = 1.0 - q
    lam = z * (q / p)
    total = 1.0
    for k in range(z + 1):
        poisson = math.exp(-lam)
        for i in range(1, k + 1):
            poisson *= lam / i
        total -= poisson * (1 - (q / p) ** (z - k))
    return total


# --- 図1: 後ろに積むブロック数 z と、攻撃の成功確率 ---
z_values = list(range(0, 26))
series = [
    (0.10, COLOR_BLUE),
    (0.30, COLOR_GREEN),
    (0.45, COLOR_RED),
]
for q, color in series:
    probs = [attacker_success_probability(q, z) for z in z_values]
    plt.semilogy(z_values, probs, marker="o", markersize=3, color=color, label=f"q = {q:.2f}")

plt.axhline(0.001, color=COLOR_GRAY, linestyle="--", linewidth=1)
plt.text(0.3, 0.0013, "0.1%", color=COLOR_GRAY, fontsize=9)
plt.xlabel("Blocks stacked after the transaction (z)")
plt.ylabel("Attack success probability")
plt.ylim(1e-8, 2)
plt.legend()
save("finality_success_rate.svg")


# --- 図2: 矛盾する 2 つの checkpoint への 2/3 は必ず 1/3 以上重なる（標準ライブラリで SVG を手書き）---
def overlap_figure() -> None:
    from html import escape

    ink, sub = "#1f1f1f", "#666666"
    blue, blue_pale = "#7aa6c2", "#eaf1f5"
    ochre, ochre_pale = "#d4a24c", "#f8eed8"
    red, red_pale = "#e15759", "#fbe3e3"
    font = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
    w, h = 960, 540
    x0, x1 = 120, 840  # 0 and 1 of the total stake
    third = (x1 - x0) / 3
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
        f'<title>{escape("矛盾する 2 つの checkpoint に 2/3 ずつ投票が集まると、1/3 以上のバリデータが両方に投票している")}</title>',
        f'<style>text{{font-family:{font};fill:{ink}}} .sub{{fill:{sub}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def bar(xa, xb, y, stroke, fill, label):
        p.append(f'<rect x="{xa}" y="{y}" width="{xb - xa}" height="70" rx="6" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2.5"/>')
        text((xa + xb) / 2, y + 45, label, 26)

    text(w / 2, 56, "all stake of the validators", 26, cls="sub")
    p.append(f'<rect x="{x0}" y="76" width="{x1 - x0}" height="16" fill="#f2f2f2" stroke="{sub}" stroke-width="1.5"/>')
    # The shared third: voted for both, so the votes themselves are the evidence.
    for x in (x0 + third, x0 + 2 * third):
        p.append(f'<line x1="{x}" y1="104" x2="{x}" y2="330" stroke="{sub}" stroke-width="2" stroke-dasharray="6 5"/>')
    bar(x0, x0 + 2 * third, 120, blue, blue_pale, "2/3 vote: checkpoint A")
    bar(x0 + third, x1, 220, ochre, ochre_pale, "2/3 vote: conflicting B")
    p.append(f'<path d="M{x0 + third},345 V360 H{x0 + 2 * third} V345" fill="none" stroke="{sub}" stroke-width="2"/>')
    text(w / 2, 400, "at least 1/3 voted for both", 26)
    p.append(f'<rect x="{w / 2 - 70}" y="420" width="140" height="56" rx="6" fill="{red_pale}" stroke="{red}" stroke-width="2"/>')
    text(w / 2, 458, "slashed", 26)

    for x, s in ((x0, "0"), (x0 + third, "1/3"), (x0 + 2 * third, "2/3"), (x1, "1")):
        text(x, 520, s, 24, cls="sub")
    path = OUT / "finality_overlap.svg"
    path.write_text("\n".join(p) + "\n</svg>\n", encoding="utf-8")
    print(f"wrote {path}")


overlap_figure()

# 本文と表の値が式と一致するかを、生成のたびに確かめる
if __name__ == "__main__":
    print("\n--- 本文で使っている値 ---")
    for z in (0, 5, 10):
        print(f"q=0.10 z={z}: {attacker_success_probability(0.10, z):.7f}")
    print("\n--- 表: 成功確率が 0.1% を下回る最小の z ---")
    for q in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45):
        z = 0
        while attacker_success_probability(q, z) >= 0.001:
            z += 1
        print(f"q={q:.2f}: z={z} (確認数 {z + 1})")
