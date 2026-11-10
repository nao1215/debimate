"""Generate the cover diagram of the oracle note.

concept_figure() draws, as a hand-written SVG (stdlib only), the market and
the reporters outside the chain boundary and the price feed and the
application inside it. The part outside (what the market was and what the
reporters observed) is trusted; inside, every node computes from the same
reported value.

Run: python3 content/notes/blockchain-systems/oracle/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("ink", INK), ("sub", SUB), ("accent", ACCENT), ("ochre", OCHRE)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle",
             rotate=None):
        r = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}"{r}>{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "チェーンの境界の外の市場と報告者、内側の価格フィードとアプリ")
    by, bh = 195, 100   # boxes

    # Chain boundary.
    f.box(470, 95, 465, 320, PALE, ACCENT, sw=3, rx=16)
    f.text(702, 140, "チェーンの中", 26, weight="normal")

    # Trusted part: market and reporters (a caution area, ochre).
    f.box(25, 95, 420, 320, OCHRE_PALE, OCHRE, sw=3, dash="10 7", rx=16)
    f.text(235, 140, "チェーンの外", 26, weight="normal")
    f.box(45, by, 140, bh, "#ffffff", SUB, sw=2.5)
    f.text(115, by + 44, "市場", 26, weight="normal")
    f.text(115, by + 78, "取引所", 24, SUB)
    for d in (16, 8):   # stacked boxes: several reporter nodes
        f.box(250 + d, by - d, 170, bh, "#ffffff", SUB, sw=2)
    f.box(250, by, 170, bh, "#ffffff", SUB, sw=2.5)
    f.text(335, by + 44, "報告者", 26, weight="normal")
    f.text(335, by + 78, "観測・署名", 24, SUB)
    f.text(235, 375, "ここは信頼する", 26, INK, "normal")

    # Inside the chain.
    f.box(510, by, 180, bh, "#ffffff", ACCENT, sw=2.5)
    f.text(600, by + 44, "価格フィード", 26, weight="normal")
    f.text(600, by + 78, "署名を検証", 24, SUB)
    f.box(745, by, 165, bh, "#ffffff", ACCENT, sw=2.5)
    f.text(827, by + 44, "アプリ", 26, weight="normal")
    f.text(827, by + 78, "価格を使う", 24, SUB)
    f.text(702, 375, "全ノードが同じ値で計算", 24, INK)

    # Flows.
    my = by + bh / 2
    f.line(187, my, 246, my, OCHRE, sw=5, arrow="ochre")
    f.line(422, my, 506, my, OCHRE, sw=5, arrow="ochre")
    f.line(692, my, 741, my, ACCENT, sw=5, arrow="accent")

    f.text(480, 478, "同じ値で計算しても、その値が市場と一致するとは限らない", 24, INK)
    f.save(HERE / "images" / "oracle_concept.svg")


def _plt(salt):
    """matplotlib with the site's monochrome settings (imported lazily)."""
    import sys
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(HERE / "lab"))
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": salt,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(HERE / "images" / name, metadata={"Date": None})


def deviation_heartbeat_figure():
    plt = _plt("oracle-deviation-heartbeat")
    from deviation_heartbeat import DEVIATION, feed, gap, market
    prices = market()
    t0, t1 = 5100, 6300
    t = [s / 60 for s in range(t0, t1)]
    fast, _, _ = feed(prices, 12)
    slow, _, _ = feed(prices, 60)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(7.2, 5.0), sharex=True)
    top.plot(t, prices[t0:t1], color=SUB, lw=2.0, label="market (simulated)")
    top.step(t, fast[t0:t1], where="post", color=ACCENT, lw=2.4,
             label="stored, 12 s delay")
    top.step(t, slow[t0:t1], where="post", color=RED, lw=2.4,
             label="stored, 60 s delay")
    top.set_ylabel("Price (USD)")
    top.legend(frameon=False, loc="lower left")
    bottom.plot(t, gap(prices, fast)[t0:t1], color=ACCENT, lw=2.2)
    bottom.plot(t, gap(prices, slow)[t0:t1], color=RED, lw=2.2)
    bottom.axhline(100 * DEVIATION, color=SUB, ls="--", lw=1.2)
    bottom.text(t[-1], 100 * DEVIATION + 0.3, "deviation threshold 0.5 %",
                color=SUB, ha="right")
    bottom.set_ylabel("Gap from market (%)")
    bottom.set_xlabel("Minutes")
    bottom.set_xlim(t[0], t[-1])
    for ax in (top, bottom):
        ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "oracle_deviation_heartbeat.svg")


def update_triggers_figure():
    """When a Data Feed updates (deviation or heartbeat) and how the app reads the age."""
    f = Svg(960, 540, "価格フィードが更新される 2 つの条件と、利用側が見る経過時間")
    # Legend.
    f.line(90, 50, 140, 50, SUB, sw=3)
    f.text(150, 58, "市場", 24, anchor="start")
    f.line(260, 50, 310, 50, ACCENT, sw=6)
    f.text(320, 58, "保存された価格", 24, anchor="start")
    market = [(80, 205), (150, 195), (220, 208), (290, 198), (360, 204), (430, 196),
              (500, 206), (560, 200), (600, 250), (640, 300), (700, 296), (780, 304),
              (900, 300)]
    pts = " ".join(f"{x},{y}" for x, y in market)
    f.parts.append(f'<polyline points="{pts}" fill="none" stroke="{SUB}" stroke-width="3"/>')
    f.parts.append(f'<polyline points="80,200 650,200 650,300 900,300" fill="none" '
                   f'stroke="{ACCENT}" stroke-width="6"/>')
    for x, y, label in ((330, 200, "heartbeat に達した"), (650, 300, "ずれが閾値を超えた")):
        f.parts.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{OCHRE_PALE}" '
                       f'stroke="{OCHRE}" stroke-width="4"/>')
    f.text(330, 160, "heartbeat に達した", 24)
    f.text(330, 245, "（値が同じでも更新）", 24, SUB)
    f.text(700, 160, "ずれが閾値を超えた", 24)
    f.text(650, 430, "updatedAt", 24)
    # Time axis and the age the application checks.
    f.line(80, 390, 905, 390, SUB, sw=3, arrow="sub")
    f.text(905, 375, "時間", 24, SUB, anchor="end")
    f.line(650, 380, 650, 400, INK, sw=3)
    f.line(880, 380, 880, 400, INK, sw=3)
    f.text(880, 430, "現在", 24)
    f.line(650, 445, 880, 445, OCHRE, sw=4)
    f.line(650, 435, 650, 455, OCHRE, sw=4)
    f.line(880, 435, 880, 455, OCHRE, sw=4)
    f.text(560, 452, "経過時間", 24, anchor="end")
    f.text(480, 510, "経過時間がアプリの許容時間以内かを利用側で判定する", 24, SUB)
    f.save(HERE / "images" / "oracle_update_triggers.svg")


if __name__ == "__main__":
    update_triggers_figure()
    concept_figure()
    deviation_heartbeat_figure()
