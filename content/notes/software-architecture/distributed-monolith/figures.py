"""Generate the figure of the distributed monolith note from lab/output.txt.

The numbers are read from the saved output of lab/chain.py (a measurement on
127.0.0.1), so this script does not rerun the one-minute experiment.
The right panel adds the theoretical curve 0.99 ** n for n synchronous calls.

concept_figure() draws the cover diagram as a hand-written SVG (stdlib only):
independent services with their own DB on the left, and services tied into
one change unit by a synchronous chain and a shared DB on the right.

Run: python3 content/notes/software-architecture/distributed-monolith/figures.py
"""

import re
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "distributed-monolith",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})

# Japanese labels in output.txt -> English labels in the figure, in order.
CASES = [
    "all up, serial",
    "all up, parallel",
    "payment hangs, serial",
    "shipping hangs, serial",
    "shipping hangs,\nshipping queued",
]
TIMEOUT_MS = 500
FAIL_RATE = 0.01


def load():
    text = (HERE / "lab" / "output.txt").read_text(encoding="utf-8")
    rows = re.findall(r"成功\s+(\d+)/(\d+)\s+中央値\s+([\d.]+) ms", text)
    measured = float(re.search(r"注文の成功率 ([\d.]+)%", text).group(1))
    assert len(rows) == len(CASES), rows
    return [(int(ok), int(n), float(ms)) for ok, n, ms in rows], measured


def chain_figure():
    rows, measured = load()
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(8.2, 4.2), gridspec_kw={"width_ratios": [1.35, 1]})

    y = range(len(rows))[::-1]
    colors = [ACCENT if ok == n else RED for ok, n, _ in rows]
    left.barh(list(y), [ms for _, _, ms in rows], color=colors, height=0.6)
    for yi, (ok, n, ms) in zip(y, rows):
        left.text(ms + 12, yi, f"{ms:.0f} ms  ({ok}/{n} ok)", va="center",
                  fontsize=10, zorder=3,
                  bbox={"fc": "#ffffff", "ec": "none", "pad": 1})
    left.axvline(TIMEOUT_MS, color=SUB, lw=1.2, ls="--", zorder=0)
    left.text(TIMEOUT_MS, len(rows) - 0.45, "timeout 0.5 s", ha="center",
              color=SUB, fontsize=10, bbox={"fc": "#ffffff", "ec": "none", "pad": 1})
    left.set_yticks(list(y), CASES, fontsize=10)
    left.set_xlim(0, 950)
    left.set_ylim(-0.6, len(rows) - 0.2)
    left.set_xlabel("Median order latency (ms)")

    stages = list(range(1, 11))
    theory = [100 * (1 - FAIL_RATE) ** k for k in stages]
    right.plot(stages, theory, color=INK, lw=2.0, marker="o", ms=4,
               label="theory 0.99^n")
    right.plot([3], [measured], "o", color=RED, ms=9,
               label=f"measured n=3: {measured:.2f}%")
    right.set_xlabel("Synchronous calls in a row (n)")
    right.set_ylabel("Order success rate (%)")
    right.set_xticks([1, 3, 5, 7, 9])
    right.set_ylim(89, 100.5)
    right.legend(loc="lower left", frameon=False, fontsize=10)

    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    (HERE / "images").mkdir(exist_ok=True)
    fig.savefig(HERE / "images" / "distributed-monolith_chain.svg")


FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{OCHRE}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="middle" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=5, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def db(self, cx, top, w, h, label):
        rx, ry = w / 2, 14
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{FILL}" stroke="{SUB}" stroke-width="2.5"/>')
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" '
            f'fill="{FILL}" stroke="{SUB}" stroke-width="2.5"/>')
        self.text(cx, top + h / 2 + 18, label)

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


SERVICES = ["注文", "在庫", "決済"]


def concept_figure():
    f = Svg(960, 540, "独立したサービスと分散モノリスの違い")
    bw, bh, by = 108, 84, 150  # service boxes
    dtop, dh = 312, 66  # DB cylinders

    # Left: each service owns its DB and is its own deploy unit.
    f.text(240, 78, "独立したサービス", 30, weight="normal")
    for cx in (100, 240, 380):
        f.box(cx - 64, 118, 128, 300, "none", ACCENT, sw=3, dash="10 7", rx=14)
    for cx, name in zip((100, 240, 380), SERVICES):
        f.box(cx - bw / 2, by, bw, bh, PALE, ACCENT)
        f.text(cx, by + bh / 2 + 10, name, 28)
        f.line(cx, by + bh, cx, dtop - 14, SUB, sw=3)
        f.db(cx, dtop, 96, dh, "DB")
    f.text(240, 482, "1 つずつ変更できる", 26, SUB)

    f.line(480, 40, 480, 500, "#dddddd", sw=2)

    # Right: a sync chain and one shared DB bind all services together.
    xs = (580, 720, 860)
    f.text(720, 78, "分散モノリス", 30, weight="normal")
    f.box(510, 118, 420, 300, "none", OCHRE, sw=3, dash="10 7", rx=14)
    for cx, name in zip(xs, SERVICES):
        f.box(cx - bw / 2, by, bw, bh, PALE, ACCENT)
        f.text(cx, by + bh / 2 + 10, name, 28)
        f.line(cx, by + bh, cx, dtop - 16, OCHRE, sw=5)
    for a, b in zip(xs, xs[1:]):
        f.line(a + bw / 2 + 2, by + bh / 2, b - bw / 2 - 6, by + bh / 2, OCHRE,
               sw=5, arrow=True)
    f.db(720, dtop, 380, dh, "共有 DB")
    f.text(720, 482, "まとめて変更するしかない", 26, SUB)

    (HERE / "images").mkdir(exist_ok=True)
    f.save(HERE / "images" / "distributed-monolith_concept.svg")


def expand_contract_figure():
    """Three steps of changing the order API without a joint release.

    Ochre marks the old meaning of total and blue the new field, so the
    reader can follow each consumer moving from ochre to blue one at a time.
    """
    f = Svg(960, 540, "古い項目と新しい項目を並べて、呼ぶ側を 1 つずつ移す 3 段階")
    cols = (165, 480, 795)
    heads = ("1. 新しい項目を足す", "2. 1 つずつ移す", "3. 古い項目を消す")
    api = ((True, True), (True, True), (False, True))  # (old, new) returned
    users = (("旧", "旧", "旧"), ("新", "新", "旧"), ("新", "新", "新"))
    names = ("決済", "分析", "画面")
    for i, cx in enumerate(cols):
        f.text(cx, 62, heads[i], 26)
        f.box(cx - 140, 92, 280, 128, FILL, SUB, rx=12)
        f.text(cx, 128, "注文 API の応答", 24, SUB)
        old, nw = api[i]
        if old:
            f.box(cx - 128, 148, 124, 56, OCHRE_PALE, OCHRE, rx=8)
            f.text(cx - 66, 185, "total", 24)
        else:
            f.box(cx - 128, 148, 124, 56, "none", "#bbbbbb", dash="8 6", rx=8)
            f.text(cx - 66, 185, "削除", 24, SUB)
        if nw:
            f.box(cx + 4, 148, 124, 56, PALE, ACCENT, rx=8)
            f.text(cx + 66, 185, "新項目", 24)
        for j, name in enumerate(names):
            y = 262 + j * 70
            uses_new = users[i][j] == "新"
            f.box(cx - 100, y, 200, 54, PALE if uses_new else OCHRE_PALE,
                  ACCENT if uses_new else OCHRE, rx=8)
            f.text(cx, y + 36, f"{name}: {'新項目' if uses_new else 'total'}", 24)
    for a, b in zip(cols, cols[1:]):
        f.line(a + 150, 160, b - 158, 160, SUB, sw=3)
        f.parts.append(
            f'<path d="M{b - 158},152 L{b - 146},160 L{b - 158},168 z" fill="{SUB}"/>')
    f.text(480, 508, "どの時点でも、全員が読める項目が応答に残っている", 24, SUB)
    f.save(HERE / "images" / "distributed-monolith_expand_contract.svg")


if __name__ == "__main__":
    chain_figure()
    concept_figure()
    expand_contract_figure()
