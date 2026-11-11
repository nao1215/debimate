"""Generate the figures of the CometBFT note.

python3 figures.py   # concept, lock, stall, halt threshold + timeline from lab/timeline.csv

Needs google-chrome (headless, to render the SVG figures), matplotlib and Pillow.
Every figure is written to images/ as WebP.
"""

import csv
import io
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"

INK, SUB, NEUTRAL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=26, anchor="middle", cls="", weight="normal"):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                      f'font-weight="{weight}"{c}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2.5, dash=None, rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=SUB, sw=2.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                      f'stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke, sw=2.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" '
                      f'stroke-width="{sw}"{d}/>')

    def save(self, name):
        """Render the SVG with headless Chrome at 2x and store it as WebP."""
        self.p.append("</svg>")
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.p) + "\n", encoding="utf-8")
            subprocess.run(
                ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                 f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def gauge(s, x, y, w, share, label, h=34):
    """A vote bar: the filled share of the total weight against the 2/3 line."""
    s.rect(x, y, w, h, NEUTRAL, SUB, sw=2, rx=4)
    s.rect(x, y, w * share, h, OCHRE_PALE, OCHRE, sw=2, rx=4)
    tx = x + w * 2 / 3
    s.line(tx, y - 10, tx, y + h + 10, stroke=INK, sw=3)
    s.text(tx, y - 16, "2/3", 22)
    s.text(x + w * share / 2, y + 24, label, 20)


def concept_figure():
    """PoW branches and reorganizes; CometBFT commits with > 2/3 or waits at the next height."""
    s = Svg(960, 540, "PoW は分岐して長い方に揃うが、CometBFT は 2/3 を超える票で確定し、"
                      "届かなければ分岐せずに次の高さで待つ")
    s.line(480, 40, 480, 500, stroke="#d9d9d9", sw=2)

    # Left: PoW. A branch grows, the shorter tip is abandoned.
    s.text(240, 70, "PoW", 32)
    s.text(240, 108, "分岐し、長い方に揃う", 24, cls="sub")
    y, size = 300, 64
    xs = [40, 130, 220, 310]
    for i, x in enumerate(xs):
        s.rect(x, y, size, size, BLUE_PALE, BLUE)
        if i:
            s.line(xs[i - 1] + size, y + size / 2, x, y + size / 2)
    # abandoned branch from the 2nd block
    s.line(130 + size, y + 10, 220, 200 + size / 2, stroke=OCHRE, dash="7 6")
    s.rect(220, 200, size, size, OCHRE_PALE, OCHRE, dash="7 6")
    s.line(310 + size, y + size / 2, 400, y + size / 2)
    s.rect(400, y, size, size, BLUE_PALE, BLUE)
    s.text(252, 186, "捨てられる", 24, cls="sub")
    s.text(240, 430, "後から巻き戻り得る", 24)

    # Right: CometBFT. Committed blocks in one line, then rounds retry at the next height.
    s.text(720, 70, "CometBFT", 32)
    s.text(720, 108, "2/3 を超える票で確定、届かなければ止まる", 22, cls="sub")
    xs = [510, 600, 690]
    for i, x in enumerate(xs):
        s.rect(x, y, size, size, BLUE_PALE, BLUE, sw=3.5)
        if i:
            s.line(xs[i - 1] + size, y + size / 2, x, y + size / 2)
    # next height: proposed but not committed, the network waits instead of branching
    nx = 800
    s.line(690 + size, y + size / 2, nx, y + size / 2, dash="7 6")
    s.rect(nx, y, size, size, OCHRE_PALE, OCHRE, dash="7 6")
    s.text(nx + size / 2, y - 18, "次の高さ", 24, cls="sub")
    # vote gauge: 2 of 4 equal validators online, threshold > 2/3
    gx, gy, gw, gh = 530, 410, 380, 34
    s.rect(gx, gy, gw, gh, NEUTRAL, SUB, sw=2, rx=4)
    s.rect(gx, gy, gw * 0.5, gh, OCHRE_PALE, OCHRE, sw=2, rx=4)
    tx = gx + gw * 2 / 3
    s.line(tx, gy - 12, tx, gy + gh + 12, stroke=INK, sw=3)
    s.text(tx, gy - 20, "2/3", 24)
    s.text(gx + gw * 0.25, gy + 26, "4 台中 2 台", 22)
    s.text(720, 500, "止まるが、分岐しない", 26)
    s.line(nx + 84, y + 20, nx + 108, y + 44, stroke=RED, sw=4)
    s.line(nx + 108, y + 20, nx + 84, y + 44, stroke=RED, sw=4)
    s.save("cometbft_concept.webp")


def round_figure():
    """One round: propose, prevote, precommit, then commit or move to the next round.

    Redrawn in Japanese from docs/imgs/consensus_logic.png of CometBFT v0.38.x, with the
    case the official figure leaves out: when fewer than 2/3 of the votes (for anything)
    arrive, prevote/precommit wait timeouts never start and the step simply waits
    (enterPrevoteWait / enterPrecommitWait in consensus/state.go need HasTwoThirdsAny).
    """
    s = Svg(1120, 405, "1 つのラウンドは提案・prevote・precommit と進む。票が 2/3 分揃って"
                       "も確定しなければ次のラウンドへ、票が 2/3 分届かなければその段階で待つ")
    boxes = [
        ("propose（提案）", "提案者がブロック B を", "全員に送る"),
        ("prevote（1 段目）", "B を検証して支持する", "検証できなければ nil"),
        ("precommit（2 段目）", "prevote B が 2/3 超なら B", "揃わなければ nil"),
        ("確定", "precommit B が 2/3 超", "なら次の高さへ"),
    ]
    w, h, y, gap, x0 = 245, 130, 110, 36, 16
    for i, (head, l1, l2) in enumerate(boxes):
        x = x0 + i * (w + gap)
        s.rect(x, y, w, h, BLUE_PALE, BLUE, sw=3 if i == 3 else 2.5)
        s.text(x + w / 2, y + 38, head, 22)
        s.text(x + w / 2, y + 76, l1, 19, cls="sub")
        s.text(x + w / 2, y + 104, l2, 19, cls="sub")
        if i:
            ax = x - gap
            s.line(ax + 4, y + h / 2, x - 10, y + h / 2, stroke=SUB, sw=2.5)
            s.p.append(f'<polygon points="{x - 12},{y + h / 2 - 7} {x - 1},{y + h / 2} '
                       f'{x - 12},{y + h / 2 + 7}" fill="{SUB}"/>')
    # top: fewer than 2/3 of the votes arrive at all -> stay in prevote / precommit
    for i in (1, 2):
        cx = x0 + i * (w + gap) + w / 2
        s.p.append(f'<path d="M {cx + 50} {y} C {cx + 50} {y - 46}, {cx - 50} {y - 46}, '
                   f'{cx - 50} {y - 12}" fill="none" stroke="{OCHRE}" stroke-width="3"/>')
        s.p.append(f'<polygon points="{cx - 58},{y - 14} {cx - 50},{y - 1} {cx - 42},{y - 14}" '
                   f'fill="{OCHRE}"/>')
    mid = x0 + 1.5 * (w + gap) + w / 2
    s.text(mid, 32, "投票先を問わず、届いた票の合計が 2/3 以下", 22)
    s.text(mid, 60, "→ その段階で待ち続ける（ラウンドも進まない）", 22, cls="sub")
    # bottom: votes arrived but no block got 2/3 of precommits -> next round, new proposer
    bx = x0 + 2 * (w + gap) + w / 2
    ax = x0 + w / 2
    yb = y + h
    s.p.append(f'<polyline points="{bx},{yb} {bx},{yb + 70} {ax},{yb + 70} {ax},{yb + 12}" '
               f'fill="none" stroke="{BLUE}" stroke-width="3" stroke-dasharray="8 6"/>')
    s.p.append(f'<polygon points="{ax - 8},{yb + 14} {ax},{yb + 1} {ax + 8},{yb + 14}" fill="{BLUE}"/>')
    s.text((ax + bx) / 2, yb + 108, "票は 2/3 を超えて届いたが、同じブロックへの precommit が 2/3 に届かない", 21)
    s.text((ax + bx) / 2, yb + 140, "→ 待ち時間の後、同じ高さの次のラウンドへ（提案者が替わる）", 21, cls="sub")
    s.save("cometbft_round.webp")


def lock_figure():
    """The lock example: what each validator sends in round 0 and round 1 of height h."""
    s = Svg(1080, 560, "ロックした V1 が B′ を支持しないので、B′ への prevote は 2/3 に届かない")
    cols, cw, chh = (190, 480, 790), 270, 56
    heads = [("ラウンド 0 の prevote", "（提案者の V0 が B を提案）"), ("ラウンド 0 の precommit", ""),
             ("ラウンド 1 の prevote", "（提案者の V3 が B′ を提案）")]
    for x, (h1, h2) in zip(cols, heads):
        s.text(x + cw / 2, 44, h1, 22)
        if h2:
            s.text(x + cw / 2, 74, h2, 18, cls="sub")
    s.line(cols[2] - 10, 30, cols[2] - 10, 400, stroke="#d9d9d9", sw=2)
    blue, grey, ochre = (BLUE_PALE, BLUE, None), (NEUTRAL, SUB, None), (OCHRE_PALE, OCHRE, None)
    rows = [
        ("V0", [("B", *blue), ("B（B にロック）", *blue),
                ("高さ h を B で確定済み", NEUTRAL, SUB, "7 6")]),
        ("V1", [("B", *blue), ("B（B にロック）", *blue), ("B（ロックした B）", *blue)]),
        ("V2", [("nil（提案が届かない）", *grey), ("nil（中身が無い）", *grey), ("B′", *ochre)]),
        ("V3（嘘つき）", [("B", *blue), ("B を V0 にだけ送る", "#fbe9e9", RED, "7 6"),
                         ("B′", *ochre)]),
    ]
    for k, (name, cells) in enumerate(rows):
        y = 100 + k * 72
        s.text(16, y + 36, name, 22, anchor="start")
        for x, (label, fill, stroke, dash) in zip(cols, cells):
            s.rect(x, y, cw, chh, fill, stroke, dash=dash)
            s.text(x + cw / 2, y + 36, label, 20)
    s.text(cols[0] + cw / 2, 418, "B への prevote は 30", 19, cls="sub")
    s.text(cols[1] + cw / 2, 418, "V0 だけが precommit B 30 を見る", 19, cls="sub")
    gauge(s, cols[2], 470, cw, 0.5, "20 / 40")
    s.text(cols[2] - 24, 494, "B′ への prevote（V2・V3）", 20, anchor="end")
    s.text(cols[2] + cw / 2, 544, "27 に届かず、B′ は確定しない", 20, cls="sub")
    s.save("cometbft_lock.webp")


def stall_figure():
    """What the running nodes see while 2 of 4 are stopped, and during the 2|2 partition."""
    s = Svg(960, 460, "2 台を止めても、2 台ずつに分断しても、どの側も prevote が 2/3 に届かない")
    s.line(480, 30, 480, 380, stroke="#d9d9d9", sw=2)

    def node(x, y, name, alive):
        s.circle(x, y, 34, BLUE_PALE if alive else NEUTRAL, BLUE if alive else "#b3b3b3",
                 dash=None if alive else "6 5")
        s.text(x, y + 7, name, 20, cls="" if alive else "sub")
        if not alive:
            s.line(x + 20, y - 46, x + 40, y - 26, stroke=RED, sw=4)
            s.line(x + 40, y - 46, x + 20, y - 26, stroke=RED, sw=4)

    s.text(240, 54, "2 台を止めた区間", 26)
    for i, x in enumerate((90, 190, 290, 390)):
        node(x, 150, f"node{i}", i < 2)
    s.text(140, 222, "動いている 2 台", 20, cls="sub")
    gauge(s, 50, 290, 380, 0.5, "prevote 20 / 40")

    s.text(720, 54, "2 台ずつに分断した区間", 26)
    for i, x in enumerate((540, 630, 810, 900)):
        node(x, 150, f"node{i}", True)
    s.line(720, 100, 720, 200, stroke=RED, sw=3, dash="8 6")
    s.text(720, 228, "通信を切る", 20, cls="sub")
    gauge(s, 510, 290, 190, 0.5, "20 / 40")
    gauge(s, 740, 290, 190, 0.5, "20 / 40")
    s.text(240, 360, "node0・node1 に届いた prevote", 18, cls="sub")
    s.text(605, 360, "node0・node1 側", 18, cls="sub")
    s.text(835, 360, "node2・node3 側", 18, cls="sub")
    s.text(480, 430, "どの側も 2/3 に届かず、同じ高さで待ち続ける", 22, cls="sub")
    s.save("cometbft_stall.webp")


def halt_figure():
    """Share of voting power that cannot vote, against the 1/3 line (run 1 of lab/run.py)."""
    s = Svg(960, 540, "票が届かない重みが 1/3 未満なら確定が進み、1/3 以上なら全体が止まる")
    x0, x1 = 40, 920

    def X(v):
        return x0 + (x1 - x0) * v

    s.text(x0 - 20, 60, "各ノードに票が届かない重みの割合", 26, anchor="start", cls="sub")
    s.rect(X(0), 110, X(1 / 3) - X(0), 120, BLUE_PALE, BLUE, rx=0)
    s.rect(X(1 / 3), 110, X(1) - X(1 / 3), 120, OCHRE_PALE, OCHRE, rx=0)
    s.text((X(0) + X(1 / 3)) / 2, 182, "確定が進む", 28)
    s.text((X(1 / 3) + X(1)) / 2, 182, "全体が止まり、分岐しない", 28)
    s.line(X(1 / 3), 96, X(1 / 3), 290, stroke=INK, sw=3)
    s.text(X(1 / 3), 86, "1/3", 26)
    s.line(X(0), 270, X(1), 270, stroke=SUB, sw=2.5)
    for v, lab in [(0, "0"), (1 / 4, "1/4"), (1 / 2, "1/2"), (1, "1")]:
        s.text(X(v), 305, lab, 24, cls="sub")
    # phases of run 1: (share not voting, label, blocks committed / phase length)
    points = [(0, "4 台", "15 個 / 20 秒", "start"),
              (1 / 4, "node3 停止", "11 個 / 30 秒", "middle"),
              (1 / 2, "2 台停止", "0 個 / 45 秒", "middle"),
              (1 / 2, "2|2 に分断", "0 個 / 45 秒", "middle")]
    for i, (v, lab, blocks, anchor) in enumerate(points):
        x = X(v)
        if i < 3:
            s.p.append(f'<circle cx="{x}" cy="270" r="11" fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
        tx = x - 10 if anchor == "start" else x
        if i == 3:
            tx = X(0.75)
        s.text(tx if anchor == "middle" else x0 - 20, 350, lab, 26, anchor=anchor)
        s.text(tx if anchor == "middle" else x0 - 20, 390, blocks, 24, anchor=anchor, cls="sub")
    s.line(X(0.5) + 14, 278, X(0.75) - 70, 322, stroke=SUB, sw=2, dash="6 5")
    s.text(480, 470, "確定したブロックの数は、実験 1 回目の各区間", 24, cls="sub")
    s.save("cometbft_halt.webp")


def timeline_figure():
    """Committed height of the 4 nodes over time (run 1 of lab/run.py)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "cometbft",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    with open(HERE / "lab" / "timeline.csv") as f:
        rows = list(csv.DictReader(f))
    t = [float(r["t"]) for r in rows]
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    styles = [(BLUE, "-"), (BLUE, "--"), (OCHRE, "-"), (INK, "--")]
    for k, (color, ls) in enumerate(styles):
        # a stopped node has no sample: NaN breaks the line instead of bridging the gap
        ys = [int(r[f"h{k}"]) if r[f"h{k}"] else float("nan") for r in rows]
        ax.plot(t, ys, color=color, ls=ls, lw=1.2 if k == 3 else 1.8, label=f"node{k}",
                zorder=1 if k == 3 else 2)
    # phase boundaries
    bounds, names = [], []
    for ti, r in zip(t, rows):
        if not names or names[-1] != r["phase"]:
            bounds.append(ti)
            names.append(r["phase"])
    bounds.append(t[-1])
    short = {"all 4 up": "4 台", "node3 stopped": "3 台", "node2,3 stopped": "2 台",
             "node2,3 restarted": "再起動", "partition 0,1 | 2,3": "2|2 に分断",
             "partition healed": "通信を戻す"}
    top = max(int(r["h0"]) for r in rows if r["h0"])
    for i, name in enumerate(names):
        if name in ("node2,3 stopped", "partition 0,1 | 2,3"):
            ax.axvspan(bounds[i], bounds[i + 1], color=OCHRE_PALE, lw=0)
        ax.axvline(bounds[i], color="#d9d9d9", lw=1)
        ax.text((bounds[i] + bounds[i + 1]) / 2, top * 1.04, short.get(name, name),
                ha="center", fontsize=9, color=SUB)
    ax.set_xlabel("経過時間（秒）")
    ax.set_ylabel("確定済みの高さ")
    ax.set_ylim(0, top * 1.12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9, ncol=2)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    buf.seek(0)
    Image.open(buf).convert("RGB").save(IMAGES / "cometbft_timeline.webp", "WEBP",
                                        quality=90, method=6)


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    concept_figure()
    round_figure()
    lock_figure()
    stall_figure()
    halt_figure()
    if (HERE / "lab" / "timeline.csv").exists():
        timeline_figure()
