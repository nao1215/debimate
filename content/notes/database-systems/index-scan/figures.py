"""Index Scan ノートの図を生成する。

lab/selectivity_pg_output.txt（PostgreSQL 17 での実測。lab/selectivity_pg.py の出力）から、
選択性ごとに seq scan と index scan が触ったページ数と時間を描く。

再生成:
    uv run --with matplotlib python content/notes/database-systems/index-scan/figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "index-scan",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def load():
    rows = {}
    for line in (HERE / "lab" / "selectivity_pg_output.txt").read_text().splitlines():
        f = line.split()
        if len(f) >= 6 and f[0].startswith("orders_") and f[1] in ("seq", "index"):
            rows.setdefault((f[0], f[1]), []).append((float(f[2]), int(f[4]), float(f[5])))
    return rows


def selectivity_figure():
    rows = load()
    series = [
        (("orders_random", "seq"), SUB, "--", "^", "Seq scan"),
        (("orders_sorted", "index"), ACCENT, "-", "s", "Index scan, rows in key order"),
        (("orders_random", "index"), RED, "-", "o", "Index scan, rows scattered"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.0))
    for col, (ax, ylabel) in enumerate(zip(axes, ("Pages touched", "Time (ms, warm cache)"))):
        for key, color, ls, mk, label in series:
            xs = [r[0] for r in rows[key]]
            ys = [r[1 + col] for r in rows[key]]
            ax.plot(xs, ys, color=color, ls=ls, marker=mk, lw=2.4, ms=5, label=label)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks([0.01, 0.1, 1, 10, 100], ["0.01", "0.1", "1", "10", "100"])
        ax.set_xlabel("Rows matched (%)")
        ax.set_ylabel(ylabel)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_yticks([10, 1_000, 100_000], ["10", "1k", "100k"])
    axes[1].set_yticks([0.1, 1, 10, 100], ["0.1", "1", "10", "100"])
    axes[0].legend(loc="upper left", frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "index-scan_selectivity.svg", metadata={"Date": None})
    plt.close(fig)


FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
PALE, FILL, OCHRE, OCHRE_PALE = "#eaf1f5", "#f2f2f2", "#d4a24c", "#f8eed8"


def pages_figure():
    """Pages touched by the same 100-row Index Scan (Buffers: shared read=4 / 103).

    One square is one page. The numbers are the EXPLAIN output in the note body.
    Hand-written SVG (stdlib only).
    """
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" '
        'viewBox="0 0 960 540" role="img"><title>同じ 100 件を返す Index Scan が触った'
        'ページの枚数</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
        '<rect width="960" height="540" fill="#ffffff"/>',
    ]

    def text(x, y, t, size=24, color=INK):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="middle" '
                     f'style="fill:{color}">{t}</text>')

    def grid(x0, y0, n, fill, stroke):
        cell, gap, cols = 28, 6, 11
        for i in range(n):
            x = x0 + (i % cols) * (cell + gap)
            y = y0 + (i // cols) * (cell + gap)
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    panels = [(40, "user_id の順に並んだ表", 4, PALE, ACCENT),
              (500, "ランダムに並んだ表", 103, OCHRE_PALE, OCHRE)]
    for x0, title, n, fill, stroke in panels:
        text(x0 + 210, 44, title, 26)
        parts.append(f'<rect x="{x0}" y="64" width="420" height="376" rx="12" '
                     f'fill="#ffffff" stroke="#d6d6d6" stroke-width="2"/>')
        grid(x0 + 23, 84, n, fill, stroke)
        text(x0 + 210, 480, f"{n} 枚", 28)
    text(480, 524, "1 マスが 1 ページ。どちらも返したのは同じ 100 件", 24, SUB)
    parts.append("</svg>")
    (HERE / "images" / "index-scan_pages.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    selectivity_figure()
    pages_figure()
