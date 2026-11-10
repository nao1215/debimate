"""Generate the figures of the query plan cache note.

concept_figure() draws the cover diagram as a hand-written SVG (stdlib only):
the statement is parsed once at PREPARE, executions 1-5 build a custom plan
each time, and from execution 6 one saved generic plan is reused.

times_figure() plots Execution Time of executions 1, 6 and 7 from the three
saved runs (lab/output.txt, output-2.txt, output-3.txt). Executions 2-5 run
without EXPLAIN ANALYZE, so they have no measured time and are not plotted.

Run: python3 content/notes/database-systems/query-plan-cache/figures.py
"""

import re
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """Minimal hand-written SVG canvas (stdlib only)."""

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
                for n, c in (("red", RED), ("sub", SUB), ("accent", ACCENT)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=8):
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
    f = Svg(960, 540, "PREPARE した文の解析と計画を、実行の何回目に行うか")
    rows = {"解析": 140, "計画": 268, "実行": 390}
    for name, cy in rows.items():
        f.text(24, cy + 9, name, 26, anchor="start")
    # Parse once at PREPARE.
    f.box(92, rows["解析"] - 32, 124, 64, PALE, ACCENT, sw=3)
    f.text(154, rows["解析"] + 9, "PREPARE", 24)

    xs = [270 + i * 80 for i in range(7)]
    cut = (xs[4] + xs[5]) / 2
    # Executions 1-5: a custom plan built each time with the value.
    for x in xs[:5]:
        f.box(x - 32, rows["計画"] - 32, 64, 64, PALE, ACCENT, sw=3)
    f.text((xs[0] + xs[4]) / 2, rows["計画"] - 50, "値ごとに作る", 24, SUB)
    # From execution 6: one saved generic plan reused.
    f.box(cut + 10, rows["計画"] - 32, 930 - cut - 10, 64, OCHRE_PALE, OCHRE, sw=3)
    f.text((cut + 930) / 2, rows["計画"] + 9, "保存した計画", 24)
    f.text((cut + 930) / 2, rows["計画"] - 50, "使い回す", 24, SUB)
    for i, x in enumerate(xs, start=1):
        f.parts.append(f'<circle cx="{x}" cy="{rows["実行"]}" r="28" fill="#ffffff" '
                       f'stroke="{SUB}" stroke-width="2.5"/>')
        f.text(x, rows["実行"] + 9, str(i), 26)
    f.text(xs[-1] + 74, rows["実行"] + 9, "…", 26, SUB)
    f.line(cut, 92, cut, 430, INK, sw=3, dash="8 7")
    f.text(cut, 72, "6 回目で切り替わる", 26, INK)
    f.text(510, 490, "EXECUTE の回数（generic plan の方が安く見積もられた場合）", 24, SUB)
    f.save(HERE / "images" / "query-plan-cache_concept.svg")


RUNS = ["output.txt", "output-2.txt", "output-3.txt"]


def load(name):
    text = (HERE / "lab" / name).read_text(encoding="utf-8")
    times = {}
    for n in (1, 6, 7):
        block = re.search(rf"--- {n} 回目\n.*?Execution Time: ([\d.]+) ms", text, re.S)
        times[n] = float(block.group(1))
    return times


def times_figure():
    with plt.rc_context({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "query-plan-cache",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    }):
        fig, ax = plt.subplots(figsize=(7.2, 3.8))
        ax.axvspan(1.5, 5.5, color=FILL, zorder=0)
        ax.text(3.5, 100, "executions 2-5:\ncustom plan,\nnot timed", ha="center",
                va="center", color=SUB, fontsize=9.5)
        ax.axvline(5.5, color=RED, lw=1.4, ls="--")
        ax.text(1, 100, "custom\nplan", ha="center", va="center", color=SUB,
                fontsize=9.5)
        ax.text(5.6, 192, "generic plan from the 6th", color=RED, fontsize=9.5,
                va="top")
        markers = ["o", "s", "^"]
        for i, (name, mk) in enumerate(zip(RUNS, markers), start=1):
            t = load(name)
            ax.plot([1], [t[1]], marker=mk, color=ACCENT, ms=8, ls="none")
            ax.plot([6, 7], [t[6], t[7]], marker=mk, color=RED, ms=8, lw=2.0)
            ax.plot([], [], marker=mk, color=SUB, ls="none", ms=8,
                    label=f"experiment {i}")
        ax.set_xlim(0.5, 7.5)
        ax.set_ylim(0, 200)
        ax.set_xticks(range(1, 8))
        ax.set_xlabel("Execution of q(1) (n-th EXECUTE)")
        ax.set_ylabel("Execution Time (ms)")
        ax.legend(loc="upper left", frameon=False, fontsize=9.5)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(HERE / "images" / "query-plan-cache_times.svg",
                    metadata={"Date": None})
        plt.close(fig)


def invalidation_figure():
    f = Svg(960, 540, "保存した計画を捨てる合図が出る変更と、出ない変更")
    cols = [(40, "DDL・search_path", "行数が変わる ANALYZE", "pg_class などを更新"),
            (500, "値の分布だけが変わる", "ANALYZE", "pg_statistic を更新")]
    for i, (x, a, b, c) in enumerate(cols):
        cx = x + 210
        f.box(x, 40, 420, 104, FILL, SUB)
        f.text(cx, 84, a, 26)
        f.text(cx, 122, b, 26)
        f.line(cx, 146, cx, 206, SUB, arrow="sub")
        f.box(x + 40, 212, 340, 70, FILL, SUB)
        f.text(cx, 256, c, 26)
        if i == 0:
            f.line(cx, 284, cx, 392, ACCENT, arrow="accent")
            f.text(cx + 16, 346, "無効化の通知", 24, SUB, anchor="start")
            f.box(x + 40, 400, 340, 96, PALE, ACCENT, sw=3)
            f.text(cx, 440, "次の実行の前に", 24, SUB)
            f.text(cx, 476, "計画を作り直す", 26)
        else:
            f.line(cx, 284, cx, 340, SUB, dash="6 8")
            f.text(cx + 16, 346, "通知なし", 24, SUB, anchor="start")
            f.box(x + 40, 400, 340, 96, OCHRE_PALE, OCHRE, sw=3)
            f.text(cx, 440, "古い計画のまま", 26)
            f.text(cx, 476, "rows=3891 の見積もり", 24, SUB)
    f.save(HERE / "images" / "query-plan-cache_invalidation.svg")


def pgbouncer_figure():
    f = Svg(960, 540, "PgBouncer の transaction mode とプリペアドステートメント")
    panels = [(0, "1.21 より前", False),
              (270, "1.21 以降（max_prepared_statements が 0 以外）", True)]
    for top, label, tracked in panels:
        f.text(40, top + 40, label, 26, anchor="start")
        for j, (tx, conn) in enumerate((("tx 1: Parse s1", "接続 A に s1"),
                                         ("tx 2: Execute s1", "接続 B"))):
            y = top + 70 + j * 90
            f.box(40, y, 300, 60, FILL, SUB)
            f.text(190, y + 39, tx, 24)
            f.line(344, y + 30, 426, y + 30, SUB, arrow="sub")
            f.box(432, y, 220, 60, PALE, ACCENT)
            f.text(542, y + 39, conn, 24)
        y = top + 160
        f.line(656, y + 30, 698, y + 30, SUB, arrow="sub")
        if tracked:
            f.box(704, y, 226, 60, PALE, ACCENT, sw=3)
            f.text(817, y + 39, "s1 を作って実行", 24)
        else:
            f.box(704, y, 226, 60, "#fbe3e3", RED, sw=3)
            f.text(817, y + 39, "s1 が無く失敗", 24)
    f.line(40, 262, 920, 262, "#cccccc", sw=2)
    f.save(HERE / "images" / "query-plan-cache_pgbouncer.svg")


if __name__ == "__main__":
    concept_figure()
    times_figure()
    invalidation_figure()
    pgbouncer_figure()
