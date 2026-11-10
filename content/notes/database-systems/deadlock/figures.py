"""Generate the cover diagram of the deadlock note as a hand-written SVG.

Two transfers and two account records sit on the corners of a square.
A solid line means "holds the lock", a dashed arrow means "waits for the
lock"; each transfer's lines take its own colour (A blue, B ochre), and
red marks only the ring. On the left the two transfers take the records in opposite
order and the edges close into a ring; on the right they take them in the
same order and the ring is cut.

Run: python3 content/notes/database-systems/deadlock/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent

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
            '<defs>' + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("red", RED), ("blue", ACCENT), ("ochre", OCHRE),
                             ("sub", SUB))) + '</defs>',
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

    def line(self, x1, y1, x2, y2, color, sw=5, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def dot(self, cx, cy, r, color):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


BW, BH = 150, 80


# Each transfer has its own colour; its hold lines and wait arrows share it.
TX = {"A": (ACCENT, PALE, "blue"), "B": (OCHRE, OCHRE_PALE, "ochre")}


def node(f, cx, cy, label, tx):
    if tx:
        line, face, _ = TX[tx]
        f.box(cx - BW / 2, cy - BH / 2, BW, BH, face, line, sw=3, rx=40)
    else:
        f.box(cx - BW / 2, cy - BH / 2, BW, BH, FILL, SUB, sw=2.5, rx=6)
    f.text(cx, cy + 9, label, 26)


def hold(f, a, b, tx):
    (x1, y1), (x2, y2) = a, b
    c = TX[tx][0]
    if y1 == y2:
        f.line(min(x1, x2) + BW / 2, y1, max(x1, x2) - BW / 2, y1, c, sw=6)
    else:
        f.line(x1, min(y1, y2) + BH / 2, x1, max(y1, y2) - BH / 2, c, sw=6)


def wait(f, a, b, tx):
    (x1, y1), (x2, y2) = a, b
    c, m = TX[tx][0], TX[tx][2]
    if y1 == y2:
        s = 1 if x2 > x1 else -1
        f.line(x1 + s * BW / 2, y1, x2 - s * (BW / 2 + 8), y1, c, sw=5,
               arrow=m, dash="14 10")
    else:
        s = 1 if y2 > y1 else -1
        f.line(x1, y1 + s * BH / 2, x1, y2 - s * (BH / 2 + 8), c, sw=5,
               arrow=m, dash="14 10")


def panel(f, ox, title, same_order):
    a, r1, r2, b = (ox + 120, 180), (ox + 360, 180), (ox + 120, 370), (ox + 360, 370)
    f.text(ox + 240, 72, title, 30, weight="normal")
    hold(f, a, r1, "A")
    if same_order:
        hold(f, a, r2, "A")
        wait(f, b, r1, "B")
    else:
        wait(f, a, r2, "A")
        hold(f, b, r2, "B")
        wait(f, b, r1, "B")
    node(f, *a, "送金 A", "A")
    node(f, *b, "送金 B", "B")
    node(f, *r1, "口座 1", False)
    node(f, *r2, "口座 2", False)


def concept_figure():
    f = Svg(960, 540, "逆の順で取ると待ちが環になり、同じ順で取ると環が切れる")
    panel(f, 0, "逆の順で取る", same_order=False)
    # A circular arrow in the middle of the left square marks the ring.
    f.parts.append(
        '<path d="M240,230 A45,45 0 1 0 285,275" fill="none" '
        f'stroke="{RED}" stroke-width="4" marker-end="url(#arrow-red)"/>')
    f.text(240, 462, "待ちが環になる", 26, RED, weight="normal")
    f.line(480, 40, 480, 480, "#dddddd", sw=2)
    panel(f, 480, "同じ順で取る", same_order=True)
    f.text(720, 462, "環にならない", 26, INK, weight="normal")
    f.line(250, 515, 310, 515, SUB, sw=6)
    f.text(322, 523, "ロックを保持", 24, SUB, anchor="start")
    f.line(530, 515, 590, 515, SUB, sw=5, dash="14 10")
    f.text(602, 523, "解放を待つ", 24, SUB, anchor="start")
    f.save(HERE / "images" / "deadlock_concept.svg")


def rate_figure():
    """Deadlock rate by concurrency, from lab/deadlock_rate_output.txt (PostgreSQL measurement)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "deadlock",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = {}
    for line in (HERE / "lab" / "deadlock_rate_output.txt").read_text().splitlines():
        f = line.split()
        if len(f) == 6 and f[0].isdigit():
            rows.setdefault((int(f[0]), f[1]), []).append((int(f[2]), float(f[5])))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.0))
    for ax, n, top in zip(axes, (10, 100), (60, 0.6)):
        for order, color, mk, label in (("random", RED, "o", "arrival order"),
                                        ("ordered", ACCENT, "s", "id order")):
            xs, ys = zip(*rows[(n, order)])
            ax.plot(xs, ys, color=color, marker=mk, lw=2.4, ms=6, label=label)
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 2, 4, 8, 16, 32], ["1", "2", "4", "8", "16", "32"])
        ax.set_ylim(-top / 30, top)
        ax.set_title(f"{n} accounts", fontsize=11)
        ax.set_xlabel("Concurrent clients")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Aborted by deadlock (%)")
    axes[0].legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "deadlock_rate.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    rate_figure()
