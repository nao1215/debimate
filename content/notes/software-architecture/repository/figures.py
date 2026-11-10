"""Generate the cover figure of the Repository note (Python stdlib only).

concept_figure() draws the three layers as nested rings: the domain layer in
the centre, the application layer around it and the infrastructure layer on
the outside. The Repository interface sits in the domain layer, and every
dependency arrow points inward (the SQL implementation satisfies the
interface). The Order aggregate is drawn as one block, and the same block
travels between the implementation and the DB.

lost_update_figure() plots lab/lost_update_output.txt (lab/lost_update.py):
lines lost without the version check and conflicts retried with it.

Run: python3 content/notes/software-architecture/repository/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE, WHITE = "#f2f2f2", "#eaf1f5", "#ffffff"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MARKERS = {"ink": SUB, "accent": ACCENT, "red": RED}


class Svg:
    def __init__(self, width, height, title):
        defs = "".join(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for name, color in MARKERS.items())
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<defs>{defs}</defs>',
            f'<rect width="{width}" height="{height}" fill="{WHITE}"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def ellipse(self, cx, cy, rx, ry, fill, stroke, sw=2.5):
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow="", dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, color, sw=4, arrow="", dash="", fill="none"):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"{da}{m}/>')

    def cross(self, cx, cy, r, color, sw=6):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)

    def db(self, cx, top, w, h, label):
        rx, ry = w / 2, 14
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{FILL}" stroke="{SUB}" stroke-width="2.5"/>')
        self.ellipse(cx, top, rx, ry, FILL, SUB)
        self.text(cx, top + h / 2 + 18, label)

    def save(self, name):
        out = HERE / "images"
        out.mkdir(exist_ok=True)
        (out / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n",
                                encoding="utf-8")


def aggregate(f, x, y, scale=1.0, label=True):
    """Order root with two lines, drawn as one framed block."""
    w, h = 120 * scale, 96 * scale
    f.box(x, y, w, h, WHITE, ACCENT, sw=3, rx=8)
    f.box(x + 12 * scale, y + 12 * scale, w - 24 * scale, 26 * scale,
          ACCENT, ACCENT, sw=0, rx=4)
    for i in range(2):
        f.box(x + 12 * scale + i * 52 * scale, y + 50 * scale, 44 * scale,
              32 * scale, FILL, SUB, sw=1.5, rx=4)
    if label:
        f.text(x + w / 2, y + h + 30, "Order 集約", 24)


def concept_figure():
    f = Svg(960, 540, "Repository の置き場所と依存の向き")
    cx, cy = 360, 278
    f.ellipse(cx, cy, 356, 252, FILL, SUB)
    f.ellipse(cx, cy, 222, 182, WHITE, SUB)
    f.ellipse(cx, cy, 176, 112, PALE, ACCENT, sw=3)
    f.text(cx, 72, "インフラストラクチャ", 24, SUB)
    f.text(cx, 132, "アプリケーション", 24, SUB)
    f.text(cx, 202, "ドメイン", 26, weight="normal")

    # Domain layer: the aggregate and the Repository interface.
    aggregate(f, 216, 222)
    f.box(370, 250, 156, 58, WHITE, ACCENT, sw=3)
    f.text(448, 288, "Repository", 24)

    # Application layer: the use case depends inward.
    f.box(270, 402, 180, 48, WHITE, SUB, sw=2.5)
    f.text(360, 434, "ユースケース", 24)
    f.line(400, 400, 430, 318, ACCENT, 4, arrow="accent")
    f.line(320, 400, 296, 356, ACCENT, 4, arrow="accent")

    # Infrastructure layer: the SQL implementation satisfies the interface.
    f.box(596, 250, 112, 58, OCHRE_PALE, OCHRE, sw=3)
    f.text(652, 288, "SQL 実装", 24)
    f.line(592, 279, 538, 279, ACCENT, 4, arrow="accent", dash="9 7")

    # The aggregate goes to and comes back from the DB as one block.
    f.db(870, 214, 120, 120, "DB")
    f.line(714, 242, 798, 242, SUB, 3, arrow="ink")
    f.line(798, 316, 714, 316, SUB, 3, arrow="ink")
    aggregate(f, 726, 255, scale=0.5, label=False)
    f.text(870, 396, "集約ごと", 24, SUB)
    f.text(870, 428, "保存・復元", 24, SUB)

    f.save("repository_concept.svg")


def lost_update_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "repository",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = []
    for line in (HERE / "lab" / "lost_update_output.txt").read_text().splitlines():
        parts = line.replace("|", " ").split()
        if parts and parts[0].isdigit():
            rows.append([int(v) for v in parts])
    k = [r[0] for r in rows]
    added = [r[1] for r in rows]
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.8))
    left.plot(k, [100 * r[2] / a for r, a in zip(rows, added)], color=RED, lw=2.4,
              marker="o", label="no version check")
    left.plot(k, [100 * r[3] / a for r, a in zip(rows, added)], color=ACCENT, lw=2.4,
              marker="s", label="version check + retry")
    left.set_ylabel("Added lines lost (%)")
    left.set_ylim(-3, 100)
    left.legend(loc="upper left", frameon=False, fontsize=10)
    right.plot(k, [r[4] / a for r, a in zip(rows, added)], color=ACCENT, lw=2.4,
               marker="s")
    right.set_ylabel("Conflicts retried per line")
    right.set_ylim(0, 1.2)
    for ax in (left, right):
        ax.set_xlabel("Workers saving the same order")
        ax.set_xticks(k)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e6e6e6", lw=0.8)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "repository_lost_update.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    lost_update_figure()
