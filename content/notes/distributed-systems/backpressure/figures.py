"""Backpressure ノートの図を生成する。

実行: uv run --with matplotlib python figures.py
lab/results.json（lab/queue_experiment.py の出力）と lab/retry_output.txt
（lab/retry_amplification.py の出力）を読み、images/ に SVG を書く。
冒頭の概念図（images/backpressure_concept.svg）は標準ライブラリだけで書く。
"""
import json
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).parent
TEXT = "#1f1f1f"
SUB = "#666666"
STYLE = {
    "unbounded": dict(color="#e15759", linestyle="-", label="unbounded"),
    "block": dict(color="#7aa6c2", linestyle="-", label="bounded: block"),
    "reject": dict(color=SUB, linestyle="--", label="bounded: reject"),
}

plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": TEXT,
    "xtick.color": SUB, "ytick.color": SUB, "svg.fonttype": "path",
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.hashsalt": "backpressure", "figure.facecolor": "#ffffff",
})


def queue_experiment():
    data = json.loads((ROOT / "lab" / "results.json").read_text())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))
    for mode, st in STYLE.items():
        t, q = zip(*data[mode]["samples"])
        ax1.plot(t, q, linewidth=2, **st)
        t, w = zip(*data[mode]["waits"])
        ax2.plot(t, w, linewidth=2, **st)
    ax1.set_title("Queue length", color=TEXT, loc="left")
    ax1.set_xlabel("elapsed time (s)")
    ax1.set_ylabel("items in queue")
    ax2.set_title("Waiting time in queue", color=TEXT, loc="left")
    ax2.set_xlabel("elapsed time when dequeued (s)")
    ax2.set_ylabel("wait (s)")
    for ax in (ax1, ax2):
        ax.grid(axis="y", color="#eeeeee")
        ax.set_xlim(0, 4)
        ax.set_ylim(bottom=0)
    ax1.legend(frameon=False, loc="upper left", labelcolor=TEXT)
    fig.text(0.01, 0.01, "arrival 200/s, service 100/s, bounded queue maxsize=50",
             color=SUB, fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(ROOT / "images" / "queue_growth.svg", facecolor="white",
                metadata={"Date": None})
    plt.close(fig)



def retry_figure():
    rows = [line.split() for line in
            (ROOT / "lab" / "retry_output.txt").read_text().splitlines()[1:]]
    layers = [int(r[0]) for r in rows]
    series = [
        (1, "retry=1 at every layer", dict(color=SUB, linestyle=":")),
        (2, "retry=2 at every layer", dict(color=SUB, linestyle="--")),
        (3, "retry=3 at every layer", dict(color="#e15759", linestyle="-")),
        (4, "retry=3 at one layer only", dict(color="#7aa6c2", linestyle="--")),
        (5, "retry budget 10%", dict(color="#7aa6c2", linestyle="-")),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for col, label, st in series:
        ys = [float(r[col]) for r in rows]
        ax.plot(layers, ys, linewidth=2.4, marker="o", markersize=5,
                label=label, **st)
        ax.annotate(f"{ys[-1]:g}x", (layers[-1], ys[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=10,
                    color=st["color"])
    ax.set_yscale("log")
    ax.set_xticks(layers)
    ax.set_xlim(0.8, 5.6)
    ax.set_yticks([1, 10, 100, 1000], ["1", "10", "100", "1000"])
    ax.minorticks_off()
    ax.set_xlabel("layers (L)")
    ax.set_ylabel("attempts at the bottom layer\nper user operation")
    ax.grid(axis="y", color="#eeeeee", which="major")
    ax.legend(frameon=False, loc="upper left", labelcolor=TEXT, fontsize=10)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "backpressure_retry.svg", facecolor="white",
                metadata={"Date": None})
    plt.close(fig)


FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, ACCENT, RED = TEXT, "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


class Svg:
    def __init__(self, width, height, title, defs=""):
        markers = "".join(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for name, color in (("sub", SUB), ("accent", ACCENT), ("red", RED)))
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<defs>{markers}{defs}</defs>',
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

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def cross(self, cx, cy, r, color, sw=5):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)

    def raw(self, s):
        self.parts.append(s)

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def flow(f, x0, x1, y, t, color):
    """Block arrow whose thickness t stands for the rate."""
    head = 24
    f.raw(f'<path d="M{x0},{y - t / 2} H{x1 - head} V{y - t / 2 - 10} '
          f'L{x1},{y} L{x1 - head},{y + t / 2 + 10} V{y + t / 2} H{x0} z" '
          f'fill="{color}"/>')


def tank_row(f, y0, bounded):
    top, bottom = y0 + 56, y0 + 216
    left, right = 380, 560
    f.text(936, y0 + 34, "上限あり（バックプレッシャー）" if bounded else "上限なし",
           26, weight="normal", anchor="end")
    mid = (top + bottom) / 2
    f.box(24, mid - 40, 160, 80, FILL, SUB)
    f.text(104, mid + 8, "Producer", 24)
    f.box(752, bottom - 68, 184, 80, FILL, SUB)
    f.text(844, bottom - 20, "Consumer", 24)
    level = top + 56 if bounded else top + 12
    fill, edge = (PALE, ACCENT) if bounded else (OCHRE_PALE, OCHRE)
    f.raw(f'<rect x="{left}" y="{level}" width="{right - left}" '
          f'height="{bottom - level}" fill="{fill}"/>')
    f.line(left, level, right, level, edge, sw=4)
    f.raw(f'<path d="M{left},{top - 8} V{bottom} H{right} V{top - 8}" fill="none" '
          f'stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
    t_in = 18 if bounded else 36
    flow(f, 186, left - 4, top + 50, t_in, SUB)
    f.text(282, top + 50 + t_in / 2 + 36, "100 件/秒" if bounded else "200 件/秒", 24)
    flow(f, right + 4, 748, bottom - 28, 18, SUB)
    f.text(656, bottom - 56, "100 件/秒", 24)
    if bounded:
        f.line(left - 16, level, right + 16, level, INK, sw=3, dash="10 6")
        f.text(470, level - 12, "上限", 24, weight="normal")
        f.line(left - 8, top + 4, 196, top + 4, ACCENT, sw=5, arrow="accent",
               dash="12 8")
        f.text(282, top - 12, "待って", 24, INK, weight="normal")
        f.text(470, bottom + 32, "満杯を上流に伝え、流入を処理に合わせる",
               24, INK)
    else:
        f.line(470, top + 40, 470, top - 34, RED, sw=5, arrow="red")
        f.text(470, bottom + 32, "差の 100 件/秒が溜まり続ける", 24, INK,
               weight="normal")


def concept_figure():
    f = Svg(960, 540, "上限なしのキューとバックプレッシャー")
    tank_row(f, 0, bounded=False)
    tank_row(f, 272, bounded=True)
    f.save(ROOT / "images" / "backpressure_concept.svg")



def stack(f, x, y, n, fill, edge):
    """n small cells piled up from y (bottom) upwards: items waiting at that side."""
    for k in range(n):
        f.box(x, y - 22 * (k + 1), 56, 18, fill, edge, sw=1.5, rx=3)


def flow_control_figure():
    """Push, Pull and Credit-based: who decides how much is sent, and where items wait."""
    f = Svg(960, 540, "Push・Pull・Credit-based で、送る量を決める側と、溢れた分が待つ場所")
    rows = [
        ("Push", "Producer decides"),
        ("Pull", "Consumer fetches"),
        ("Credit-based", "Consumer grants n"),
    ]
    for i, (name, who) in enumerate(rows):
        y = 20 + 175 * i
        mid = y + 80
        f.text(20, mid - 6, name, 26, anchor="start")
        f.text(20, mid + 26, who, 22, SUB, anchor="start")
        f.box(310, mid - 34, 140, 68, FILL, SUB)
        f.text(380, mid + 8, "Producer", 24)
        f.box(770, mid - 34, 150, 68, FILL, SUB)
        f.text(845, mid + 8, "Consumer", 24)
        if name == "Push":
            for k, dy in enumerate((-22, 0, 22)):
                f.line(454, mid + dy, 690, mid + dy, SUB, sw=3, arrow="sub")
            stack(f, 700, mid + 66, 6, OCHRE_PALE, OCHRE)
            f.text(572, mid + 62, "data as fast as made", 22, SUB)
        elif name == "Pull":
            f.line(766, mid - 18, 456, mid - 18, ACCENT, sw=3, arrow="accent", dash="10 6")
            f.text(610, mid - 30, "fetch", 22, SUB)
            f.line(454, mid + 18, 762, mid + 18, SUB, sw=3, arrow="sub")
            f.text(610, mid + 50, "only what was fetched", 22, SUB)
        else:
            f.line(766, mid - 18, 456, mid - 18, ACCENT, sw=3, arrow="accent", dash="10 6")
            f.text(610, mid - 30, "request(n)", 22, SUB)
            f.line(454, mid + 18, 762, mid + 18, SUB, sw=3, arrow="sub")
            f.text(610, mid + 50, "at most n items", 22, SUB)
            stack(f, 238, mid + 44, 4, OCHRE_PALE, OCHRE)
    f.save(ROOT / "images" / "backpressure_flow_control.svg")


if __name__ == "__main__":
    queue_experiment()
    retry_figure()
    concept_figure()
    flow_control_figure()
