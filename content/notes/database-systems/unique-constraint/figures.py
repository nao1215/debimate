"""Generate the cover diagram of the unique constraint note as a hand-written SVG.

Two requests A and B register the same e-mail address. Each checks with
SELECT and then INSERTs. Without a unique constraint (top), A's INSERT lands
in the window between B's check and B's INSERT (ochre), and two rows remain.
With the constraint (bottom), B's INSERT waits for A's COMMIT and is
rejected, so one row remains.

The race figure plots lab/output.txt, measured by lab/run.sh on PostgreSQL 17.

Run: uv run --with matplotlib python content/notes/database-systems/unique-constraint/figures.py
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


BW, BH = 96, 50


def step(f, x, y, label, stroke=ACCENT, fill=PALE):
    f.box(x, y - BH / 2, BW, BH, fill, stroke, sw=2.5, rx=8)
    f.text(x + BW / 2, y + 9, label, 24)


def lanes(f, top, title):
    f.text(95, top + 76, title, 28, weight="normal")
    ya, yb = top + 40, top + 115
    for y, name in ((ya, "A"), (yb, "B")):
        f.text(212, y + 10, name, 28, weight="normal")
        f.line(240, y, 800, y, "#cccccc", sw=2)
    return ya, yb


def concept_figure():
    f = Svg(960, 540, "確認してから挿入する隙間と一意制約")
    f.text(930, 36, "時間 →", 24, SUB, anchor="end")

    # Without the constraint: A's INSERT falls into B's check-to-insert window.
    ya, yb = lanes(f, 50, "制約なし")
    f.box(386, ya - 40, 230, yb - ya + 80, OCHRE_PALE, OCHRE, sw=2.5, rx=8)
    step(f, 250, ya, "確認")
    step(f, 380 - 92, yb, "確認")
    step(f, 470, ya, "挿入")
    step(f, 620, yb, "挿入")
    f.text(880, (ya + yb) / 2 + 12, "2 件", 34, RED, weight="normal")

    f.line(30, 268, 930, 268, "#dddddd", sw=2)

    # With the constraint: B's INSERT waits for A's COMMIT and is rejected.
    ya, yb = lanes(f, 300, "制約あり")
    step(f, 250, ya, "確認")
    step(f, 288, yb, "確認")
    step(f, 470, ya, "挿入")
    step(f, 620, ya, "確定", GREEN, GREEN_PALE)
    step(f, 520, yb, "挿入")
    f.line(620, yb, 704, yb, OCHRE, sw=6, dash="10 8")
    f.text(662, yb - 14, "待つ", 24, SUB)
    f.line(718, yb - 16, 750, yb + 16, RED, sw=6)
    f.line(750, yb - 16, 718, yb + 16, RED, sw=6)
    f.text(880, (ya + yb) / 2 + 12, "1 件", 34, INK, weight="normal")

    f.box(250, 492, 40, 28, OCHRE_PALE, OCHRE, sw=2.5, rx=4)
    f.text(302, 515, "B が確認した後に A が挿入する隙間", 24, SUB, anchor="start")
    f.save(HERE / "images" / "unique-constraint_concept.svg")


def race_figure():
    """Rows per e-mail and 23505 errors per e-mail against concurrency (lab/output.txt)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "unique-constraint",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    lines = (HERE / "lab" / "output.txt").read_text().splitlines()
    keys = int(next(x for x in lines if x.startswith("keys=")).split()[0].split("=")[1])
    rows = {}
    for line in lines:
        f = line.split()
        if len(f) == 6 and f[2] in ("plain", "unique"):
            rows.setdefault((f[2], int(f[0])), []).append((float(f[3]), int(f[5]) / keys))
    clients = sorted({c for _, c in rows})

    def mean(table, i):
        return [sum(v[i] for v in rows[(table, c)]) / len(rows[(table, c)]) for c in clients]

    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.8))
    left.plot(clients, mean("plain", 0), color=RED, lw=2.4, marker="o", label="no UNIQUE")
    left.plot(clients, mean("unique", 0), color=ACCENT, lw=2.4, marker="s", label="UNIQUE")
    left.set_ylabel("Rows stored per e-mail")
    left.legend(frameon=False, loc="upper left", fontsize=10)
    right.plot(clients, mean("unique", 1), color=ACCENT, lw=2.4, marker="s")
    right.set_ylabel("23505 errors per e-mail (UNIQUE)")
    for ax in (left, right):
        ax.set_xscale("log", base=2)
        ax.set_xticks(clients, [str(c) for c in clients])
        ax.set_xlabel("Concurrent requests (same e-mail)")
        ax.set_ylim(0, 34 if ax is left else 17)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "unique-constraint_race.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    race_figure()
