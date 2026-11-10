"""Materialized View ノートの図を生成する。

再生成:
    uv run --with matplotlib python content/notes/database-systems/materialized-view/figures.py

数値は lab/output.txt の (c-1)・(c-2) の実測値（psql の \\timing）。
読み手の開始時刻は、lab/run.sh が出力した「refresh の開始から約 N ms 後」の値
（docker exec の起動時間を含む概算）。
"""

import pathlib
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"
COLOR_TEXT = "#1f1f1f"

plt.rcParams.update({
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.hashsalt": "materialized-view",
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)

# (label, refresh duration [s], reader start [s], reader duration [s])
RUNS = [
    ("REFRESH", 2.961600, 0.154, 2.824188),
    ("REFRESH CONCURRENTLY", 2.663952, 0.154, 0.001077),
]


def refresh_timeline() -> None:
    fig, axes = plt.subplots(2, 1, figsize=(6.5, 3.6), sharex=True)
    for ax, (label, refresh, start, reader) in zip(axes, RUNS):
        ax.barh(1, refresh, left=0, height=0.5, color=COLOR_GRAY, alpha=0.35,
                edgecolor=COLOR_GRAY)
        ax.text(0.03, 1, f"{label}  {refresh * 1000:.0f} ms", va="center",
                fontsize=10, color=COLOR_TEXT)
        if reader > 0.01:
            ax.barh(0, reader, left=start, height=0.5, color=COLOR_RED,
                    alpha=0.8, edgecolor=COLOR_RED, hatch="//")
            ax.text(start + reader + 0.04, 0,
                    f"SELECT waits {reader * 1000:.0f} ms", va="center",
                    fontsize=10, color=COLOR_TEXT)
        else:
            ax.plot([start], [0], marker="o", color=COLOR_BLUE,
                    markersize=8)
            ax.text(start + 0.06, 0,
                    f"SELECT returns in {reader * 1000:.1f} ms (old rows)",
                    va="center", fontsize=10, color=COLOR_TEXT)
        ax.set_yticks([0, 1], ["reader", "refresher"])
        ax.set_ylim(-0.6, 1.6)
        ax.set_xlim(0, 4.2)
        ax.grid(axis="x", alpha=0.3, linewidth=0.5)
    axes[-1].set_xlabel("seconds since refresh started")
    fig.tight_layout()
    path = OUT / "refresh_timeline.svg"
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path}")


def lab_query_times():
    """lab/output.txt の (a) から、元の表と daily_sales の時間を 3 回ずつ読む。"""
    text = (pathlib.Path(__file__).parent / "lab" / "output.txt").read_text(encoding="utf-8")
    block = text.split("== (a)", 1)[1].split("== 表の大きさ", 1)[0]
    times = [float(t) for t in re.findall(r"Time: ([\d.]+) ms", block)]
    assert len(times) == 6, times
    return times[0::2], times[1::2]  # run.sh は元の表と view を交互に測る


def query_times() -> None:
    base, view = lab_query_times()
    with plt.rc_context({
        "font.size": 10, "axes.edgecolor": COLOR_GRAY, "axes.labelcolor": COLOR_TEXT,
        "xtick.color": COLOR_TEXT, "ytick.color": COLOR_TEXT, "text.color": COLOR_TEXT,
        "svg.fonttype": "path", "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    }):
        fig, ax = plt.subplots(figsize=(7.2, 2.8))
        rows = [("orders (5 million rows)", base, COLOR_RED),
                ("daily_sales (365 rows)", view, COLOR_BLUE)]
        for y, (label, ts, color) in zip([1, 0], rows):
            mean = sum(ts) / len(ts)
            ax.barh(y, mean, color=color, height=0.55)
            ax.plot(ts, [y] * len(ts), "o", color=COLOR_TEXT, ms=4)
            ax.text(max(ts) * 1.3, y, f"{min(ts):,.2f} - {max(ts):,.2f} ms"
                    if mean < 10 else f"{min(ts):,.0f} - {max(ts):,.0f} ms",
                    va="center", fontsize=10)
        ax.set_yticks([1, 0], [r[0] for r in rows], fontsize=10)
        ax.set_xscale("log")
        ax.set_xlim(0.1, 20000)
        ax.set_ylim(-0.6, 1.6)
        ax.set_xlabel("Time to sum March sales (ms, log scale, 3 runs each)")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        path = OUT / "materialized-view_query_times.svg"
        fig.savefig(path, metadata={"Date": None})
        plt.close(fig)
        print(f"wrote {path}")



def refresh_methods() -> None:
    """3 つの REFRESH を、元の表から読む量・view に書く量・読み手で並べる（標準ライブラリの SVG）。"""
    from html import escape

    ink, sub, blue, blue_pale = COLOR_TEXT, COLOR_GRAY, COLOR_BLUE, "#eaf1f5"
    ochre, ochre_pale, gray_pale = "#d4a24c", "#f8eed8", "#f2f2f2"
    font = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img"><title>{escape("3 つの REFRESH の、元の表から読む量、view に書く量、実行中の読み手")}</title>',
        f"<style>text{{font-family:{font};fill:{ink}}} .sub{{fill:{sub}}}</style>",
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def bar(x, y, frac, fill, stroke):
        p.append(f'<rect x="{x}" y="{y}" width="220" height="40" rx="4" fill="#ffffff" '
                 f'stroke="{sub}" stroke-width="1" stroke-dasharray="4 4"/>')
        p.append(f'<rect x="{x}" y="{y}" width="{220 * frac:.0f}" height="40" rx="4" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2"/>')

    # (name, example, read fraction, read label, write fraction, write label, reader, reader style)
    rows = [
        ("full", "REFRESH", 1.0, "all rows", 1.0, "replace all", "wait", "ochre"),
        ("incremental", "Oracle fast, pg_ivm", 0.12, "changes only", 0.12, "affected rows", "by product", "gray"),
        ("concurrent", "CONCURRENTLY", 1.0, "all rows", 0.12, "changed rows", "not blocked", "blue"),
    ]
    text(400, 62, "reads from orders", cls="sub")
    text(660, 62, "writes to the view", cls="sub")
    text(870, 62, "readers", cls="sub")
    for i, (name, example, rf, rl, wf, wl, reader, style) in enumerate(rows):
        y = 100 + 140 * i
        text(20, y + 34, name, 26, anchor="start")
        text(20, y + 70, example, 22, anchor="start", cls="sub")
        bar(290, y + 8, rf, blue_pale, blue)
        text(400, y + 88, rl, 22, cls="sub")
        bar(550, y + 8, wf, blue_pale, blue)
        text(660, y + 88, wl, 22, cls="sub")
        fill, stroke = {"ochre": (ochre_pale, ochre), "gray": (gray_pale, sub), "blue": (blue_pale, blue)}[style]
        p.append(f'<rect x="{800}" y="{y + 4}" width="140" height="48" rx="6" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2"/>')
        text(870, y + 37, reader, 22)
    text(480, 515, "readers = SELECT on the view during REFRESH in PostgreSQL 17", 22, cls="sub")
    p.append("</svg>")
    (OUT / "refresh_methods.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


if __name__ == "__main__":
    refresh_timeline()
    query_times()
    refresh_methods()
