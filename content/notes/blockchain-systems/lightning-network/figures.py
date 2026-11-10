"""Lightning Network ノートの図を生成する。

lab/simulate.py が書いた lab/result.json を読んでプロットする。
concept_figure() は冒頭の概念図を標準ライブラリだけで SVG に手書きする。
容量が一定のチャネルを 1 本の棒にし、Alice と Bob の分割点だけが更新ごとに動き、
チェーンに載るのは開設と閉鎖の 2 回だけであることを示す。
cltv_figure() は中継の 2 区間の HTLC の期限の差を、liquidity_figure() は
本文の例のチャネルで向きごとに送れる上限を、同じく SVG に手書きする。

再生成:
    python3 content/notes/blockchain-systems/lightning-network/lab/simulate.py
    uv run --with matplotlib python content/notes/blockchain-systems/lightning-network/figures.py
"""

import json
import pathlib
from html import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_BLUE = "#7aa6c2"
COLOR_GRAY = "#666666"
COLOR_TEXT = "#1f1f1f"

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
    "svg.hashsalt": "lightning-network",
})

HERE = pathlib.Path(__file__).parent
OUT = HERE / "images"
OUT.mkdir(exist_ok=True)


def payment_success() -> None:
    data = json.loads((HERE / "lab" / "result.json").read_text())
    amounts = data["amounts"]
    styles = {
        "1": dict(color=COLOR_GRAY, marker="o", linestyle="-"),
        "2": dict(color=COLOR_GRAY, marker="s", linestyle=":"),
        "4": dict(color=COLOR_BLUE, marker="^", linestyle=":"),
        "8": dict(color=COLOR_BLUE, marker="D", linestyle="-"),
    }
    fig, ax = plt.subplots()
    for k, rates in data["success"].items():
        label = "single path" if k == "1" else f"split into {k} parts"
        ax.plot(amounts, [r * 100 for r in rates], label=label, **styles[k])
    ax.plot(amounts, [r * 100 for r in data["bound"]], color=COLOR_TEXT,
            linestyle="--", linewidth=1, label="endpoint balance bound")
    ax.set_xscale("log")
    ax.set_xlabel("Payment amount (sat)")
    ax.set_ylabel("Success rate (%)")
    ax.set_ylim(-3, 103)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.savefig(OUT / "lightning_payment_success.svg", metadata={"Date": None})
    plt.close(fig)
    print("wrote", OUT / "lightning_payment_success.svg")


# ---- 冒頭の概念図（標準ライブラリだけで書く SVG） ----
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """A tiny hand-written SVG builder (960x540, white background)."""

    def __init__(self, title, width=960, height=540):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
                for name, color in (("sub", SUB), ("accent", ACCENT), ("red", RED), ("ochre", OCHRE)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}"{o} stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5, dash="", opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{o} '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, stroke, sw=4, fill="none"):
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


# (段階名, Alice の取り分の割合, チェーンに載るか)。割合は形を見せるための値。
STEPS = [
    ("開設", 1.00, True),
    ("更新 1", 0.86, False),
    ("更新 2", 0.74, False),
    ("…", None, False),
    ("更新 n", 0.46, False),
    ("閉鎖", 0.46, True),
]


def concept_figure() -> None:
    f = Svg("容量が一定のチャネルで分割点だけが動き、チェーンには開設と閉鎖だけが載る")
    lane, x0, width, bar_h = 196, 280, 640, 44
    f.text(lane, 60, "チェーン", 26, weight="normal")
    f.text(x0 + width / 2, 60, "チャネル（容量は一定）", 26, weight="normal")
    f.line(lane, 84, lane, 508, SUB, sw=3, dash="4 9")
    for i, (name, share, on_chain) in enumerate(STEPS):
        cy = 120 + i * 76
        f.text(52, cy + 9, name, 26, anchor="start")
        if share is None:
            continue
        if on_chain:
            f.circle(lane, cy, 17, GREEN)
            f.line(lane + 20, cy, x0 - 6, cy, GREEN, sw=4)
        split = x0 + width * share
        f.box(x0, cy - bar_h / 2, width, bar_h, OCHRE_PALE, rx=6)
        f.box(x0, cy - bar_h / 2, split - x0, bar_h, ACCENT, rx=6)
        f.box(x0, cy - bar_h / 2, width, bar_h, "none",
              GREEN if on_chain else SUB, sw=3 if on_chain else 2, rx=6)
        if share < 1:
            f.line(split, cy - bar_h / 2 - 8, split, cy + bar_h / 2 + 8, INK, sw=4)
            f.text(x0 + width - 16, cy + 9, "Bob", 24, anchor="end")
        f.text(x0 + 16, cy + 9, "Alice", 24, anchor="start")
    f.save(OUT / "lightning-network_concept.svg")


# BOLT 2 の値: 中継の差は迷うなら 34 ブロック以上、受取人の最小値の既定は 18。
DELTA, FINAL = 34, 18


def cltv_figure() -> None:
    f = Svg("下流の HTLC ほど期限が早く、その差が中継者の請求の時間になる")
    x0, per = 150, 13  # 1 ブロックあたりの幅
    end = FINAL + DELTA

    def x(b):
        return x0 + b * per

    # 中継者が上流を請求できる時間（待ちの領域）
    f.box(x(FINAL), 90, DELTA * per, 300, OCHRE_PALE, OCHRE, sw=2, dash="8 6", rx=4)
    f.text(x(FINAL) + DELTA * per / 2, 350, f"{DELTA} blocks", 26)
    f.text(x(FINAL) + DELTA * per / 2, 382, "for Bob to claim", 24, color=SUB)
    rows = [("Alice → Bob", end, 150), ("Bob → Carol", FINAL, 260)]
    for label, expiry, y in rows:
        f.text(30, y - 18, label, 26, anchor="start")
        f.box(x0, y, expiry * per, 40, PALE, ACCENT, rx=4)
        f.line(x(expiry), y - 8, x(expiry), y + 48, INK, sw=4)
    f.line(x0, 450, x(end) + 60, 450, SUB, sw=2.5, arrow="sub")
    for b, label in ((0, "N"), (FINAL, f"N+{FINAL}"), (end, f"N+{end}")):
        f.line(x(b), 442, x(b), 458, SUB, sw=2.5)
        f.text(x(b), 492, label, 24)
    f.text(x(end) + 60, 432, "block height", 24, color=SUB, anchor="end")
    f.save(OUT / "lightning-network_cltv.svg")


# 本文の例: 容量 1,000,000 sat、Alice 側 900,000 sat、Bob 側 100,000 sat。
CAPACITY, ALICE_SIDE = 1_000_000, 900_000


def liquidity_figure() -> None:
    f = Svg("片側の残高が、その向きに送れる上限になる")
    x0, width = 80, 800
    split = x0 + width * ALICE_SIDE / CAPACITY
    bob = CAPACITY - ALICE_SIDE
    f.text(480, 60, f"capacity {CAPACITY:,} sat", 28)
    f.box(x0, 100, split - x0, 70, PALE, ACCENT, rx=6)
    f.box(split, 100, x0 + width - split, 70, OCHRE_PALE, OCHRE, rx=6)
    f.text(x0 + 20, 145, f"Alice {ALICE_SIDE:,}", 26, anchor="start")
    f.text(x0 + width, 208, f"Bob {bob:,}", 26, anchor="end")
    # Alice から Bob へ: Alice の残高の分だけ
    f.line(x0, 300, split, 300, ACCENT, sw=6, arrow="accent")
    f.text(x0, 280, "Alice → Bob", 26, anchor="start")
    f.text(x0, 345, f"up to {ALICE_SIDE:,} sat", 24, color=SUB, anchor="start")
    # Bob から Alice へ: Bob の残高の分だけ
    f.line(x0 + width, 430, split, 430, OCHRE, sw=6, arrow="ochre")
    f.text(x0 + width, 410, "Bob → Alice", 26, anchor="end")
    f.text(x0 + width, 475, f"up to {bob:,} sat", 24, color=SUB, anchor="end")
    f.text(x0, 520, "fees and reserve are left out", 24, color=SUB, anchor="start")
    f.save(OUT / "lightning-network_liquidity.svg")


if __name__ == "__main__":
    payment_success()
    concept_figure()
    cltv_figure()
    liquidity_figure()
