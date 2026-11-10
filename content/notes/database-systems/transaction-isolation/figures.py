"""Generate the cover diagram of the transaction isolation note as a hand-written SVG.

A grid with the four SQL standard isolation levels as rows and the three
read phenomena as columns. A cell is painted ochre when the standard does
not forbid the phenomenon at that level, so the painted area shrinks into
a staircase as the level goes up.

Run: python3 content/notes/database-systems/transaction-isolation/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
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

    def line(self, x1, y1, x2, y2, color, sw=5, arrow=False, dash=""):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def dot(self, cx, cy, r, color):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


LEVELS = ["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"]
PHENOMENA = [("dirty", "read"), ("nonrepeatable", "read"), ("phantom", "read")]
# Number of phenomena (counted from the right) the standard allows per level.
ALLOWED = [3, 2, 1, 0]


def concept_figure():
    f = Svg(960, 540, "SQL 標準の分離レベルと起き得る異常")
    x0, cw, y0, rh = 340, 200, 140, 78
    for j, (a, b) in enumerate(PHENOMENA):
        cx = x0 + cw * j + cw / 2
        f.text(cx, 72, a, 26, weight="normal")
        f.text(cx, 106, b, 26, weight="normal")
    for i, (level, n) in enumerate(zip(LEVELS, ALLOWED)):
        y = y0 + rh * i
        f.text(x0 - 20, y + rh / 2 + 9, level, 24, anchor="end")
        for j in range(3):
            x = x0 + cw * j
            bad = j >= 3 - n
            if bad:
                f.box(x + 5, y + 5, cw - 10, rh - 10, OCHRE_PALE, OCHRE, sw=3, rx=6)
            else:
                f.box(x + 4, y + 4, cw - 8, rh - 8, FILL, rx=6)
            f.text(x + cw / 2, y + rh / 2 + 9, "起き得る" if bad else "起きない",
                   24, INK if bad else SUB)
    f.text(480, 510, "塗った所は、標準がそのレベルで禁止していない異常", 24, SUB)
    f.save(HERE / "images" / "transaction-isolation_concept.svg")


def lost_update_figure():
    """Lost updates and retries by isolation level, from lab/lost_update_output.txt (PostgreSQL)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "transaction-isolation",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = {}
    for line in (HERE / "lab" / "lost_update_output.txt").read_text().splitlines():
        line = line.replace("read committed", "read_committed")
        f = line.split()
        if len(f) >= 7 and f[1].isdigit():
            c, orders, lost, retries = int(f[1]), int(f[2]), int(f[4]), int(f[6])
            key = f[0].replace("_", " ")
            rows.setdefault(key, []).append((c, 100 * lost / orders, retries / orders))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.0))
    for key, color, mk, label in (("read committed", RED, "o", "READ COMMITTED"),
                                  ("serializable", ACCENT, "s", "SERIALIZABLE")):
        cs = [r[0] for r in rows[key]]
        for ax, i in zip(axes, (1, 2)):
            ax.plot(cs, [r[i] for r in rows[key]], color=color, marker=mk, lw=2.4, ms=6,
                    label=label)
    for ax, ylabel in zip(axes, ("Lost updates (% of orders)", "Retries per order")):
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 2, 4, 8, 16, 32], ["1", "2", "4", "8", "16", "32"])
        ax.set_xlabel("Concurrent clients")
        ax.set_ylabel(ylabel)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylim(-3, 100)
    axes[1].legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "transaction-isolation_lost_update.svg", metadata={"Date": None})
    plt.close(fig)


def gap_lock_figure():
    """Record lock, gap lock and next-key lock on the keys of one index."""
    f = Svg(960, 540, "レコードのロック・gap lock・next-key lock が覆う索引の範囲")
    keys = [10, 20, 30, 40]
    kx = [330 + i * 140 for i in range(4)]  # left edge of each key box
    kw, kh = 70, 60
    f.text(kx[0] + (kx[-1] + kw - kx[0]) / 2, 62, "索引に並んだキー", 24, SUB)
    f.text(880, 62, "15 の挿入", 24, SUB)
    rows = [
        ("レコードのロック", True, False, "通る"),
        ("gap lock", False, True, "待つ"),
        ("next-key lock", True, True, "待つ"),
    ]
    for r, (label, rec, gap, insert) in enumerate(rows):
        y = 110 + r * 130
        f.text(40, y + 40, label, 24, anchor="start")
        f.line(kx[0] - 60, y + kh / 2, kx[-1] + kw + 4, y + kh / 2, "#c8c8c8", sw=2.5)
        if gap:
            f.box(kx[0] + kw + 6, y + 4, 140 - kw - 12, kh - 8, OCHRE_PALE, OCHRE, rx=6)
        for i, (x, k) in enumerate(zip(kx, keys)):
            on = rec and k == 20
            f.box(x, y, kw, kh, PALE if on else "#ffffff", ACCENT if on else SUB,
                  sw=2.5 if on else 2)
            f.text(x + kw / 2, y + 39, str(k), 24, INK if on else SUB)
        f.text(880, y + 40, insert, 24)
    f.text(480, 515, "15 は、キー 10 と 20 の間の隙間に入る", 24, SUB)
    f.save(HERE / "images" / "transaction-isolation_gap_lock.svg")


if __name__ == "__main__":
    concept_figure()
    lost_update_figure()
    gap_lock_figure()
