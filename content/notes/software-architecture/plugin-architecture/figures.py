"""Generate the cover diagram of the Plugin Architecture note as a hand-written SVG.

concept_figure() puts the two ways of adding a destination side by side.
Left: every destination is an `if` inside the core, so the core box grows
with each new one (the new one in blue, the growth in ochre). Right: the core keeps its size and
the destinations plug into the sockets on its edge (the boundary); the new
destination (blue) is added outside the core.

callcost_figure() plots lab/callcost_output.txt (the Go benchmark in
lab/callcost/) as the time of one Export call, in-process and out-of-process.

Run: python3 content/notes/software-architecture/plugin-architecture/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE = "#d4a24c"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
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

    def line(self, x1, y1, x2, y2, color=INK, sw=4, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def db(self, cx, top, w, h, fill, stroke):
        rx, ry = w / 2, 10
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


DESTS = ["ES", "S3", "stdout"]


def concept_figure():
    f = Svg(960, 540, "if を足す形ではコアが伸び、境界で受ける形では拡張だけが増える")
    f.line(470, 30, 470, 510, "#dddddd", 2)

    # Left: destinations are branches inside the core.
    f.text(240, 52, "コアに if を足す形", 28, weight="normal")
    f.box(100, 80, 280, 430, "#ffffff", INK, sw=3, rx=16)
    f.text(240, 120, "コア", 26, weight="normal")
    for i, name in enumerate(DESTS):
        y = 142 + i * 82
        f.box(125, y, 230, 64, FILL, SUB, sw=2, rx=8)
        f.text(240, y + 41, f"if {name}", 26)
    y = 142 + 3 * 82
    f.box(125, y, 230, 64, PALE, ACCENT, sw=3.5, rx=8)
    f.text(240, y + 41, "if 新しい宛先", 26)
    # The core grows with each destination.
    f.line(404, 92, 404, 498, OCHRE, 4)
    f.line(394, 92, 414, 92, OCHRE, 4)
    f.line(394, 498, 414, 498, OCHRE, 4)
    f.parts.append(
        f'<text x="438" y="295" font-size="24" text-anchor="middle" '
        f'writing-mode="tb" style="fill:{SUB}">'
        '宛先ごとに伸びる</text>')

    # Right: destinations plug into the boundary on the edge of the core.
    f.text(712, 52, "境界で受ける形", 28, weight="normal")
    cx, cy, cw, ch = 505, 160, 170, 260
    f.box(cx, cy, cw, ch, "#ffffff", INK, sw=3, rx=16)
    f.text(cx + cw / 2 - 10, cy + ch / 2 + 9, "コア", 26, weight="normal")
    f.text(cx + cw, cy - 18, "境界", 24, INK, "normal")
    for i in range(4):
        sy = cy + 20 + i * 60
        # Socket on the edge of the core.
        f.box(cx + cw - 14, sy, 28, 40, FILL, SUB, sw=3, rx=4)
        if i < 3:
            f.line(cx + cw + 14, sy + 20, 740, sy + 20, SUB, 4)
            f.box(740, sy - 2, 190, 44, FILL, SUB, sw=3, rx=8)
            f.text(835, sy + 29, f"{DESTS[i]} 拡張", 24)
        else:
            f.box(760, sy - 2, 170, 44, PALE, ACCENT, sw=3.5, rx=8)
            f.text(845, sy + 29, "新しい宛先", 24)
            f.line(758, sy + 20, cx + cw + 22, sy + 20, ACCENT, 4)
            f.parts.append(
                f'<polygon points="{cx + cw + 16},{sy + 20} {cx + cw + 34},{sy + 10} '
                f'{cx + cw + 34},{sy + 30}" fill="{ACCENT}"/>')
    f.text(712, 470, "コアの大きさは変わらない", 24, SUB)

    f.save(HERE / "images" / "plugin-architecture_concept.svg")


def callcost_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "plugin-architecture",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = []
    for line in (HERE / "lab" / "callcost_output.txt").read_text().splitlines():
        parts = line.split()
        if parts and parts[0].isdigit():
            rows.append([float(v) for v in parts])
    labels = {16: "16 B", 1024: "1 KiB", 65536: "64 KiB"}
    series = [("in-process", 1, ACCENT),
              ("pipe (child process)", 2, SUB),
              ("net/rpc (Unix socket)", 3, RED)]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    width = 0.26
    for j, (name, col, color) in enumerate(series):
        xs = [i + (j - 1) * width for i in range(len(rows))]
        ys = [r[col] for r in rows]
        ax.bar(xs, ys, width, color=color, label=name)
        for x, y in zip(xs, ys):
            text = f"{y:.1f} ns" if y < 100 else f"{y / 1000:.0f} µs"
            ax.text(x, y * 1.25, text, ha="center", va="bottom", fontsize=10)
    ax.set_yscale("log")
    ax.set_ylim(0.5, 3e5)
    ax.set_xticks(range(len(rows)), [labels[int(r[0])] for r in rows])
    ax.set_xlabel("Payload per call")
    ax.set_ylabel("Time per call (ns, log scale)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False,
              fontsize=10, ncols=3)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "plugin-architecture_call_cost.svg",
                metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    callcost_figure()
