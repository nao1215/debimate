"""Generate the cover diagram of the Ethereum account model note.

concept_figure() draws the world state as a table (address -> nonce, balance,
storageRoot, codeHash) as a hand-written SVG (stdlib only). It shows which
cells are empty for an EOA and which cells change when Alice sends Bob 1 ETH
with nonce 7.

Run: python3 content/notes/blockchain-systems/ethereum-account-model/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"


class Svg:
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
                for n, c in (("ink", INK), ("sub", SUB), ("accent", ACCENT), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle",
             rotate=None):
        r = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}"{r}>{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
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


COLS = [("アドレス", 170), ("nonce", 150), ("balance（ETH）", 250),
        ("storageRoot", 160), ("codeHash", 160)]
# (name, kind, cells); a cell is (text, style) with style in
# "plain" / "change" / "empty" / "code".
ROWS = [
    ("Alice", "EOA", [("7 → 8", "change"), ("5 → 4 − 手数料", "change"),
                      ("空", "empty"), ("空", "empty")]),
    ("Bob", "EOA", [("0", "plain"), ("2 → 3", "change"),
                    ("空", "empty"), ("空", "empty")]),
    ("トークン", "コントラクト", [("1", "plain"), ("0", "plain"),
                                 ("記憶領域", "code"), ("コード", "code")]),
]
STYLE = {
    "plain": ("#ffffff", SUB, INK, "normal"),
    "change": (ACCENT, ACCENT, INK, "normal"),
    "empty": (FILL, SUB, SUB, "normal"),
    "code": (OCHRE_PALE, OCHRE, INK, "normal"),
}


def concept_figure():
    f = Svg(960, 540, "Alice から Bob への送金で世界状態のどの欄が変わるか")
    f.text(480, 56, "Alice から Bob に 1 ETH を送る取引（nonce 7）", 28, weight="normal")
    x0, top, hh, rh = 35, 88, 52, 84
    xs = [x0]
    for _, w in COLS:
        xs.append(xs[-1] + w)
    for (name, w), x in zip(COLS, xs):
        f.text(x + w / 2, top + 35, name, 24, SUB)
    f.line(x0, top + hh, xs[-1], top + hh, SUB, sw=2)
    for i, (name, kind, cells) in enumerate(ROWS):
        y = top + hh + 10 + i * (rh + 10)
        f.text(x0 + 85, y + 36, name, 26, weight="normal")
        f.text(x0 + 85, y + 68, kind, 24, SUB)
        for (s, style), x, (_, w) in zip(cells, xs[1:], COLS[1:]):
            fill, stroke, color, weight = STYLE[style]
            f.box(x + 6, y, w - 12, rh, fill, stroke, sw=2.5, rx=8)
            f.text(x + w / 2, y + rh / 2 + 9, s, 24, color, weight)
    ly = 482
    for x, fill, stroke, label in ((60, ACCENT, ACCENT, "この取引で変わる欄"),
                                   (370, FILL, SUB, "EOA では空のまま"),
                                   (640, OCHRE_PALE, OCHRE, "コントラクトが使う")):
        f.box(x, ly - 22, 30, 30, fill, stroke, sw=2, rx=4)
        f.text(x + 44, ly, label, 24, INK, anchor="start")
    f.save(HERE / "images" / "ethereum-account-model_concept.svg")


def txpool_figure():
    """geth --dev: send nonce 2, 0, 1 and resend 0 from an account at nonce 0."""
    f = Svg(960, 540, "nonce 2・0・1 の順に送った取引が txpool とブロックに入る様子")
    left, col = 210, 185
    steps = [
        ("2 を送信", "0", ["2"], [], []),
        ("0 を送信", "1", ["2"], ["0"], []),
        ("1 を送信", "3", [], ["1", "2"], []),
        ("0 を再送", "3", [], [], ["0"]),
    ]
    rows = [(120, "アカウントの nonce"), (230, "queued（待ち）"), (370, "ブロック")]
    for y, label in rows:
        f.text(20, y + 9, label, 24, SUB, anchor="start")
    f.box(left - 10, 180, col * 3 + 4, 100, OCHRE_PALE, OCHRE, sw=2)
    f.box(left - 10, 320, col * 3 + 4, 100, FILL, SUB, sw=2)

    def chip(cx, cy, n, fill, stroke):
        f.box(cx - 32, cy - 30, 64, 60, fill, stroke, sw=2.5, rx=8)
        f.text(cx, cy + 9, n, 28)

    for i, (head, nonce, queued, mined, rejected) in enumerate(steps):
        cx = left + col * i + col / 2
        f.text(cx, 52, head, 26)
        f.text(cx, 129, nonce, 30)
        for k, n in enumerate(queued):
            chip(cx + (k - (len(queued) - 1) / 2) * 76, 230, n, "#ffffff", OCHRE)
        for k, n in enumerate(mined):
            chip(cx + (k - (len(mined) - 1) / 2) * 76, 370, n, PALE, ACCENT)
        for n in rejected:
            chip(cx, 300, n, "#ffffff", RED)
            f.line(cx + 44, 278, cx + 76, 310, RED, sw=4)
            f.line(cx + 76, 278, cx + 44, 310, RED, sw=4)
            f.text(cx, 370, "拒否", 24, SUB)
        if i:
            f.line(left + col * i, 40, left + col * i, 420, "#d6d6d6", sw=2)
    f.text(480, 480, "1 が届くと、待っていた 2 も続けてブロックに入る", 24, SUB)
    f.text(480, 516, "再送した 0 は nonce too low（次の番号は 3）", 24, SUB)
    f.save(HERE / "images" / "ethereum-account-model_txpool.svg")


if __name__ == "__main__":
    concept_figure()
    txpool_figure()
