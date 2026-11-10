"""Generate the cover diagram of the leader-and-followers note as a hand-written SVG.

concept_figure() draws the log of each node as a row of boxes aligned by
index, so the same position holds the same entry on every node. The number
and the colour of a box is the term in which the entry was made. Entries up
to index 6 are on a majority (Leader and Follower 1 of three nodes) and are
committed; the green line is the commit index. Leader's entries 7 and 8 are
not committed yet (dashed). Follower 2 lags behind.

election_figure() plots lab/election.py (about 20 s): the distribution of
the time to elect a new leader and the split-vote rate for each spread of the
randomized election timeout, in the shape of Figure 16 of the Raft paper.

Run: python3 content/notes/distributed-systems/leader-and-followers/figures.py
"""

import sys
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
import election  # noqa: E402
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

TERMS = [1, 1, 1, 2, 2, 2, 2, 2]  # term of the entry at index 1..8 (Leader's log)
COMMIT = 6
X0, COL, BOX, BH = 236, 86, 74, 62


def concept_figure():
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("Leader が決めた順序で各ノードのログが同じ位置に並び、過半数に届いた所まで確定する")}'
        '</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} '
        f'.red{{fill:{RED}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def entry(x, y, term, committed):
        if committed:
            fill, stroke, dash = (FILL, SUB, "") if term == 1 else (ACCENT, ACCENT, "")
        else:
            fill, stroke, dash = OCHRE_PALE, OCHRE, ' stroke-dasharray="8 6"'
        p.append(f'<rect x="{x}" y="{y}" width="{BOX}" height="{BH}" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="3"{dash}/>')
        text(x + BOX / 2, y + BH / 2 + 10, str(term), 28,
             cls="" if committed else "sub")

    def col_x(i):
        return X0 + (i - 1) * COL

    # Index header.
    yh = 118
    text(30, yh, "index", 24, "start", cls="sub")
    for i in range(1, len(TERMS) + 1):
        text(col_x(i) + BOX / 2, yh, str(i), 24, cls="sub")

    rows = [("Leader", 8), ("Follower 1", 6), ("Follower 2", 4)]
    for r, (name, length) in enumerate(rows):
        y = 140 + r * 92
        text(30, y + BH / 2 + 10, name, 28, "start", "normal")
        for i in range(1, length + 1):
            entry(col_x(i), y, TERMS[i - 1], i <= COMMIT)
        if length < COMMIT:
            text(col_x(length + 1) + 6, y + BH / 2 + 9, "遅れている", 24, "start",
                 cls="sub")

    # Commit index.
    xc = col_x(COMMIT) + BOX + (COL - BOX) / 2
    p.append(f'<line x1="{xc}" y1="84" x2="{xc}" y2="{140 + 2 * 92 + BH + 14}" '
             f'stroke="{GREEN}" stroke-width="6" stroke-linecap="round"/>')
    text(xc - 12, 66, "確定（commit index）", 24, "end", "normal")
    text(xc + 12, 66, "未確定", 24, "start", cls="sub")

    # Legend: colour is the term, dashed is not committed.
    yl = 450
    items = [((FILL, SUB, ""), "任期 1"), ((ACCENT, ACCENT, ""), "任期 2"),
             ((OCHRE_PALE, OCHRE, ' stroke-dasharray="8 6"'), "未確定")]
    x = 236
    for (fill, stroke, dash), label in items:
        p.append(f'<rect x="{x}" y="{yl}" width="44" height="36" rx="6" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="3"{dash}/>')
        text(x + 56, yl + 27, label, 24, "start")
        x += 210
    text(30, yl + 27, "箱の色", 24, "start", cls="sub")

    (HERE / "images").mkdir(exist_ok=True)
    (HERE / "images" / "leader-and-followers_concept.svg").write_text(
        "\n".join(p + ["</svg>"]) + "\n", encoding="utf-8")


def election_figure():
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "leader-and-followers",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    styles = {0: (SUB, ":"), 5: (RED, "-"), 25: (ACCENT, "--"),
              150: (INK, "-")}
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.2, 4.0),
                                 gridspec_kw={"width_ratios": [1.6, 1]})
    split = []
    for spread in election.SPREADS:
        res = election.run(spread)
        split.append(100 * (1 - sum(r is not None and r[1] == 1 for r in res)
                            / len(res)))
        if spread not in styles:
            continue
        times = sorted(r[0] for r in res if r is not None)
        ys = [100 * (i + 1) / len(res) for i in range(len(times))]
        color, ls = styles[spread]
        ax.step(times, ys, where="post", color=color, ls=ls, lw=2.2,
                label=f"{election.BASE:g}-{election.BASE + spread:g} ms")
    ax.set_xscale("log")
    ax.set_xlim(100, 10000)
    ax.set_ylim(0, 102)
    ax.set_xlabel("Time to elect a leader (ms)")
    ax.set_ylabel("Trials with a leader (%)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=10)
    labels = [f"{election.BASE + s:g}" for s in election.SPREADS]
    bx.bar(range(len(split)), split, color=ACCENT, width=0.65)
    bx.set_xticks(range(len(split)), labels, rotation=45)
    bx.set_xlabel("Max timeout (ms), min 150")
    bx.set_ylabel("Split vote in 1st term (%)")
    bx.set_ylim(0, 100)
    for a in (ax, bx):
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "leader-and-followers_election_timeout.svg",
                metadata={"Date": None})


def overwrite_figure():
    """Raft paper Figure 8: an old-term entry on a majority is still overwritten."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("過半数に届いた過去の任期のエントリが、後の Leader に上書きされる")}'
        '</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, color=INK, anchor="middle"):
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                 f'style="fill:{color}">{escape(s)}</text>')

    def cell(x, y, term):
        if term is None:
            p.append(f'<rect x="{x}" y="{y}" width="96" height="54" rx="8" fill="#ffffff" '
                     f'stroke="{SUB}" stroke-width="2" stroke-dasharray="6 6"/>')
            text(x + 48, y + 36, "-", 24, SUB)
            return
        fill, stroke = (PALE, ACCENT) if term == 2 else (OCHRE_PALE, OCHRE)
        p.append(f'<rect x="{x}" y="{y}" width="96" height="54" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2.5"/>')
        text(x + 48, y + 36, str(term), 24)

    stages = [
        ("段階 1", "A が B に配る", [2, 2, None, None, None]),
        ("段階 2", "E が自分に書く", [2, 2, None, None, 3]),
        ("段階 3", "A が C に配る", [2, 2, 2, None, 3]),
        ("段階 4", "E が上書き", [3, 3, 3, 3, 3]),
    ]
    for k, (head, desc, terms) in enumerate(stages):
        ox = 14 + k * 236
        text(ox + 110, 40, head, 24, SUB)
        text(ox + 110, 74, desc, 24)
        for i, (node, term) in enumerate(zip("ABCDE", terms)):
            y = 98 + i * 72
            text(ox + 44, y + 36, node, 24, SUB)
            cell(ox + 76, y, term)
        if k < 3:
            p.append(f'<line x1="{ox + 226}" y1="96" x2="{ox + 226}" y2="452" '
                     f'stroke="#d8d8d8" stroke-width="2"/>')
    text(14 + 236, 500, "数字はエントリの任期", 24, SUB)
    text(14 + 2 * 236 + 110, 500, "過半数に届く", 24, SUB)
    text(14 + 3 * 236 + 110, 500, "任期 2 が消える", 24, RED)
    (HERE / "images" / "leader-and-followers_overwrite.svg").write_text(
        "\n".join(p + ["</svg>"]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    concept_figure()
    election_figure()
    overwrite_figure()
