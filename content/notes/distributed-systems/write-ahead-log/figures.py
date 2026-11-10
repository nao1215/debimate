"""Generate the cover diagram of the WAL note as a hand-written SVG.

concept_figure() draws one server's log as a tape split into segments,
using the example in the note: a snapshot covers index 200, so the
low-water mark L is 201, the high-water mark H is 240 and the log end T is
250. Segments 1 and 2 may be deleted, 201..240 is committed, and 241..250
must not be shown to clients. Widths are not to scale.

fsync_figure() plots lab/fsyncbench_output.txt (a measurement, so it reads
the saved output instead of measuring again): records per second against the
batch size per Sync, and the latency when one record arrives every 1 ms.

Run: python3 content/notes/distributed-systems/write-ahead-log/figures.py
"""

from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("WAL のセグメントと、低位・高位ウォーターマークとログ末尾の位置")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} '
        f'.red{{fill:{RED}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(x, y, w_, h_, fill, stroke, sw, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{h_}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    ty, th = 196, 100  # the tape
    xs = [40, 230, 420, 690, 860, 920]  # seg1 | seg2 | 201-240 | 241-250 | unused

    # Segments 1 and 2: covered by the snapshot, may be deleted.
    for i, (a, b) in enumerate(((xs[0], xs[1]), (xs[1], xs[2])), start=1):
        rect(a, ty, b - a, th, FILL, SUB, 2, "9 6")
        text((a + b) / 2, ty + 42, f"segment {i}", 24, cls="sub")
        text((a + b) / 2, ty + 78, f"{(i - 1) * 100 + 1}〜{i * 100}", 24, cls="sub")
    # Segment 3, being written: committed part, uncommitted part, unused tail.
    rect(xs[2], ty, xs[3] - xs[2], th, GREEN_PALE, GREEN, 3)
    text((xs[2] + xs[3]) / 2, ty + 42, "segment 3", 24)
    text((xs[2] + xs[3]) / 2, ty + 78, "201〜240", 24)
    rect(xs[3], ty, xs[4] - xs[3], th, OCHRE_PALE, OCHRE, 4)
    text((xs[3] + xs[4]) / 2, ty + 62, "241〜250", 24, weight="normal")
    rect(xs[4], ty, xs[5] - xs[4], th, "#ffffff", SUB, 1.5, "4 5")

    # The three positions.
    for x, name, val in ((xs[2], "低位", "L = 201"), (xs[3], "高位", "H = 240"),
                         (xs[4], "末尾", "T = 250")):
        p.append(f'<line x1="{x}" y1="{ty - 40}" x2="{x}" y2="{ty + th + 14}" '
                 f'stroke="{INK}" stroke-width="5" stroke-linecap="round"/>')
        text(x, ty - 90, name, 26, weight="normal")
        text(x, ty - 54, val, 24)

    # What each range means.
    yb = ty + th + 64
    text((xs[0] + xs[2]) / 2, yb, "削除して良い", 26, weight="normal", cls="sub")
    text((xs[0] + xs[2]) / 2, yb + 38, "スナップショットに反映済み", 24, cls="sub")
    text((xs[2] + xs[3]) / 2, yb, "確定済み", 26, weight="normal")
    text((xs[3] + xs[4]) / 2, yb, "見せない", 26, weight="normal")
    text((xs[3] + xs[4]) / 2, yb + 38, "未確定", 24, cls="sub")

    # Direction of appends.
    ya = 490
    p.append(f'<line x1="{xs[0]}" y1="{ya}" x2="{xs[5] - 10}" y2="{ya}" stroke="{SUB}" '
             'stroke-width="2"/>')
    p.append(f'<polygon points="{xs[5]},{ya} {xs[5] - 16},{ya - 8} {xs[5] - 16},{ya + 8}" '
             f'fill="{SUB}"/>')
    text(xs[5], ya + 34, "追記する向き", 24, "end", cls="sub")

    (HERE / "images").mkdir(exist_ok=True)
    (HERE / "images" / "write-ahead-log_concept.svg").write_text(
        "\n".join(p + ["</svg>"]) + "\n", encoding="utf-8")


def read_bench():
    """Return the rows of part 1 and part 2 of lab/fsyncbench_output.txt."""
    part, rows = None, {1: [], 2: []}
    for line in (HERE / "lab" / "fsyncbench_output.txt").read_text().splitlines():
        if line.startswith("[part "):
            part = int(line[6])
        elif part and line.strip() and line.split()[0].isdigit():
            rows[part].append([float(x) for x in line.split()])
    return rows[1], rows[2]


def fsync_figure():
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "write-ahead-log",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    back, rate = read_bench()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.2, 4.0))
    ax.plot([r[0] for r in back], [r[1] for r in back], color=ACCENT,
            marker="o", lw=2.4, ms=6)
    ax.set_yscale("log")
    ax.set_ylim(1e3, 5e5)
    ax.set_ylabel("Records per second")
    ax.set_title("Back to back", fontsize=11, color=SUB)
    bx.plot([r[0] for r in rate], [r[1] for r in rate], color=ACCENT,
            marker="o", lw=2.4, ms=6, label="p50")
    bx.plot([r[0] for r in rate], [r[2] for r in rate], color=RED,
            marker="s", lw=2.4, ms=6, ls="--", label="p99")
    bx.set_yscale("log")
    bx.set_yticks([1, 2, 5, 10, 20, 50, 100], ["1", "2", "5", "10", "20", "50", "100"])
    bx.set_ylim(1, 100)
    bx.set_ylabel("Latency until durable (ms)")
    bx.set_title("1 record arrives every 1 ms", fontsize=11, color=SUB)
    bx.legend(frameon=False, loc="upper left")
    for a in (ax, bx):
        a.set_xscale("log", base=2)
        ticks = [1, 4, 16, 64, 256] if a is ax else [1, 4, 16, 64]
        a.set_xticks(ticks, [str(t) for t in ticks])
        a.set_xlabel("Records per Sync")
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "write-ahead-log_fsync_batch.svg",
                metadata={"Date": None})


class Canvas:
    """Small hand-written SVG canvas for the explanatory figures."""

    def __init__(self, title, w=960, h=540):
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                      f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(self, x1, y1, x2, y2):
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" '
                      'stroke-width="4" stroke-linecap="round" marker-end="url(#arr)"/>')

    def save(self, name):
        (HERE / "images" / name).write_text("\n".join(self.p + ["</svg>"]) + "\n",
                                            encoding="utf-8")


def fsync_retry_figure():
    """fsync failure: retrying (before 2019) versus stopping and replaying WAL."""
    c = Canvas("fsync の失敗を再試行した場合と、止めて WAL から再生する場合")
    rows = [(40, "再試行（2019 年 2 月より前）",
             [("fsync", "失敗", FILL, SUB), ("OS が", "データを捨てる", FILL, SUB),
              ("fsync", "成功", FILL, SUB), ("書けたと", "扱う", "#fbe3e3", RED)]),
            (290, "停止（11.2 など以降）",
             [("fsync", "失敗", FILL, SUB), ("サーバーを", "止める", FILL, SUB),
              ("再起動", "", FILL, SUB), ("WAL から", "再生する", PALE, ACCENT)])]
    for top, label, steps in rows:
        c.text(40, top + 34, label, 26, anchor="start")
        for i, (a, b, fill, stroke) in enumerate(steps):
            x = 40 + i * 230
            c.box(x, top + 64, 190, 120, fill, stroke, sw=3 if stroke != SUB else 2.5)
            if b:
                c.text(x + 95, top + 116, a, 26)
                c.text(x + 95, top + 154, b, 26)
            else:
                c.text(x + 95, top + 134, a, 26)
            if i < 3:
                c.arrow(x + 194, top + 124, x + 226, top + 124)
    c.p.append(f'<line x1="40" y1="262" x2="920" y2="262" stroke="#cccccc" stroke-width="2"/>')
    c.save("write-ahead-log_fsync_retry.svg")


def leader_change_figure():
    """Entries after the high-water mark survive only if the new Leader has them."""
    c = Canvas("Leader の交代で、高位ウォーターマークより後ろのエントリがどうなるか")
    cell, x0 = 104, 300
    idx = [40, 41, 42, 43, 44, 45]
    rows = [(70, "旧 Leader", 6), (210, "新 Leader", 4)]
    for y, name, n in rows:
        c.text(40, y + (52 if n == 6 else 34), name, 26, anchor="start")
        for i in range(n):
            v = idx[i]
            if v <= 42:
                fill, stroke = FILL, SUB
            elif v == 43:
                fill, stroke = PALE, ACCENT
            else:
                fill, stroke = OCHRE_PALE, OCHRE
            c.box(x0 + i * cell, y, cell - 12, 76, fill, stroke)
            c.text(x0 + i * cell + (cell - 12) / 2, y + 48, str(v), 26)
    c.text(40, 278, "（元 Follower 1）", 24, SUB, anchor="start")
    hx = x0 + 3 * cell - 6
    c.p.append(f'<line x1="{hx}" y1="40" x2="{hx}" y2="320" stroke="{INK}" '
               'stroke-width="5" stroke-linecap="round"/>')
    c.text(hx, 30, "H = 42", 24)
    c.box(40, 380, 420, 120, PALE, ACCENT, sw=3)
    c.text(250, 430, "43 は新 Leader にある", 26)
    c.text(250, 470, "後から確定する", 24, SUB)
    c.box(500, 380, 420, 120, OCHRE_PALE, OCHRE, sw=3)
    c.text(710, 430, "44・45 は新 Leader に無い", 26)
    c.text(710, 470, "上書きされて消える", 24, SUB)
    c.save("write-ahead-log_leader_change.svg")


if __name__ == "__main__":
    concept_figure()
    fsync_figure()
    fsync_retry_figure()
    leader_change_figure()
