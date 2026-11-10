"""Generate the figures of the Cross-Chain Bridge note.

concept_figure() and trust_figure() use the Python standard library only.
backing_figure() needs matplotlib and reads lab/bridge_sim_output.txt.

Run: python3 content/notes/blockchain-systems/cross-chain-bridge/figures.py
"""

import re
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
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
                for name, color in (("sub", SUB), ("accent", ACCENT), ("ochre", OCHRE)))
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




def concept_figure():
    f = Svg("source chain の金庫にロックした分だけ、destination chain で引換券を発行する。間で預け入れを確かめる役が要る")
    # Source chain (blue): the vault really holds the coins.
    f.box(24, 24, 300, 420, PALE, rx=16)
    f.text(174, 72, "source chain", 28)
    f.box(64, 130, 220, 200, "#ffffff", ACCENT, sw=3)
    f.text(174, 168, "金庫", 26)
    for i in range(5):
        f.circle(104 + i * 35, 230, 15, ACCENT)
    for i in range(5):
        f.circle(104 + i * 35, 278, 15, ACCENT)
    f.text(174, 380, "100 をロック", 26)

    # Destination chain (grey): wrapped coins are claims on the vault (dashed).
    f.box(636, 24, 300, 420, FILL, rx=16)
    f.text(786, 72, "destination chain", 28)
    f.box(676, 130, 220, 200, "#ffffff", SUB, sw=3)
    f.text(786, 168, "wrapped token", 26)
    for i in range(5):
        f.circle(716 + i * 35, 230, 15, "#ffffff", SUB, sw=2.5, dash="5 4")
    for i in range(5):
        f.circle(716 + i * 35, 278, 15, "#ffffff", SUB, sw=2.5, dash="5 4")
    f.text(786, 380, "100 を発行", 26)

    # The gap in the middle: someone has to vouch for the deposit (ochre).
    f.box(360, 170, 240, 120, OCHRE_PALE, OCHRE, sw=3)
    f.text(480, 220, "検証役", 26)
    f.text(480, 256, "預け入れは本当か", 22, SUB)
    f.line(290, 230, 352, 230, OCHRE, sw=4, arrow="ochre")
    f.line(606, 230, 668, 230, OCHRE, sw=4, arrow="ochre")
    f.text(480, 500, "発行した量が金庫の中身を超えると、引換券に裏付けが無くなる", 24, SUB)
    f.save(HERE / "images" / "bridge_concept.svg")


def trust_figure():
    """What the destination chain checks, per verification type."""
    f = Svg("destination chain が確かめる材料と、利用者が信頼する相手の 4 つのタイプ", height=600)
    f.text(330, 44, "確かめるもの", 22, SUB, anchor="start")
    f.text(660, 44, "信頼する相手", 22, SUB, anchor="start")
    rows = ["外部の署名者", "軽量クライアント", "異議の受付期間", "有効性の証明"]
    trusts = [("署名者の過半", "（例: 9 人中 5 人）"), ("source chain の合意", "と検証コードの実装"),
              ("期間内に異議を出す", "監視者が 1 人以上いる"), ("証明系と回路の実装", "")]
    for i, label in enumerate(rows):
        y = 70 + i * 130
        f.box(24, y, 912, 116, PALE, rx=12)
        f.text(44, y + 66, label, 24, anchor="start")
        cx = 360
        if i == 0:  # 9 signers, 5 signatures
            for k in range(9):
                f.circle(cx - 20 + k * 30, y + 58, 11, OCHRE if k < 5 else "#ffffff", OCHRE, sw=2.5)
        elif i == 1:  # header chain and a Merkle branch down to the event
            for k in range(4):
                f.box(cx - 30 + k * 64, y + 22, 44, 30, "#ffffff", ACCENT, sw=2.5, rx=4)
                if k:
                    f.line(cx - 30 + k * 64 - 18, y + 37, cx - 30 + k * 64 - 2, y + 37, ACCENT, sw=3)
            f.line(cx + 140, y + 54, cx + 140, y + 74, ACCENT, sw=3)
            f.line(cx + 140, y + 74, cx + 112, y + 92, ACCENT, sw=3)
            f.circle(cx + 108, y + 96, 7, ACCENT)
            f.text(cx - 30, y + 102, "ヘッダと経路", 20, SUB, anchor="start")
        elif i == 2:  # a timeline with a challenge window
            f.line(cx - 30, y + 58, cx + 230, y + 58, ACCENT, sw=3)
            f.box(cx + 10, y + 40, 170, 36, OCHRE_PALE, OCHRE, sw=2.5, rx=4)
            f.text(cx + 95, y + 66, "待つ", 20, SUB)
            f.circle(cx - 30, y + 58, 7, ACCENT)
            f.circle(cx + 230, y + 58, 7, ACCENT)
        else:  # one short proof
            f.box(cx - 30, y + 30, 120, 56, "#ffffff", ACCENT, sw=2.5, rx=6)
            f.text(cx + 30, y + 66, "proof", 22)
            f.line(cx + 96, y + 58, cx + 150, y + 58, ACCENT, sw=3, arrow="accent")
            f.text(cx + 160, y + 66, "検証", 22, anchor="start")
        a, b = trusts[i]
        f.text(660, y + (52 if b else 66), a, 24, anchor="start")
        if b:
            f.text(660, y + 86, b, 22, SUB, anchor="start")
    f.save(HERE / "images" / "bridge_trust.svg")


def backing_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "bridge-backing",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    text = (HERE / "lab" / "bridge_sim_output.txt").read_text()
    rows = re.findall(r"^(.+?)\s+locked=\s*(\d+) wrapped=\s*(\d+)$", text, re.M)
    labels = ["after deposits", "after a withdrawal", "after a forged release\n(5 of 9 keys stolen)"]
    locked = [int(r[1]) for r in rows]
    wrapped = [int(r[2]) for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    x = range(len(rows))
    ax.bar([i - 0.18 for i in x], locked, 0.36, color=ACCENT, label="coins locked in the vault")
    ax.bar([i + 0.18 for i in x], wrapped, 0.36, color="#ffffff", edgecolor=SUB,
           hatch="//", label="wrapped coins in circulation")
    for i, (l, w) in enumerate(zip(locked, wrapped)):
        ax.text(i - 0.18, l + 8, str(l), ha="center")
        ax.text(i + 0.18, w + 8, str(w), ha="center")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 520)
    ax.set_ylabel("coins")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(HERE / "images" / "bridge_backing.svg", metadata={"Date": None})


if __name__ == "__main__":
    concept_figure()
    trust_figure()
    backing_figure()
