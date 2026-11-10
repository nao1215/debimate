"""Generate the cover figure of the Bitcoin Merkle Tree note (Python stdlib only).

concept_figure() draws a phone that keeps only block headers on the left and
the Merkle tree of an 8-transaction block on the right. To show that Tx2 is in
the block, only the sibling hashes on the path (ochre) are sent; the phone
computes the path nodes (accent) up to the root in one of its headers, and the
other hashes (gray) are never sent.

Run: python3 content/notes/blockchain-systems/bitcoin-merkle-tree/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED = "#7aa6c2", "#e15759"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("sub", SUB), ("red", RED), ("accent", ACCENT)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=3, arrow="", dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def raw(self, s):
        self.parts.append(s)

    def save(self, name):
        (HERE / "images").mkdir(exist_ok=True)
        (HERE / "images" / name).write_text(
            "\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")

GRAY = "#dddddd"


def concept_figure():
    f = Svg(960, 540, "ヘッダだけを持つ端末が、少数の兄弟ハッシュで包含を確かめる")

    # Left: the phone keeps only the chain of 80-byte headers.
    f.text(135, 62, "携帯端末", 26, weight="normal")
    f.box(50, 84, 170, 380, FILL, SUB, sw=2.5, rx=24)
    strip_top, sh, sg = 112, 36, 12
    mine = 3
    for k in range(6):
        y = strip_top + k * (sh + sg)
        hit = k == mine
        f.box(70, y, 130, sh, ACCENT if hit else PALE, ACCENT, sw=2, rx=4)
        if hit:
            f.text(135, y + 27, "root", 24)
    f.text(135, 440, "ヘッダだけ", 24, SUB)

    # Right: the full block on another participant, as a Merkle tree.
    f.text(615, 62, "ブロック全体を持つ参加者", 26, weight="normal")
    f.box(290, 84, 650, 380, "#ffffff", SUB, sw=2.5, rx=16)
    ys = [404, 316, 228, 140]
    xs = [[330 + i * 80 for i in range(8)]]
    while len(xs[-1]) > 1:
        prev = xs[-1]
        xs.append([(prev[i] + prev[i + 1]) / 2 for i in range(0, len(prev), 2)])
    target = 2
    path = [target >> lv for lv in range(4)]
    for lv in range(1, 4):
        for i, x in enumerate(xs[lv]):
            for c in (2 * i, 2 * i + 1):
                on = path[lv] == i and path[lv - 1] == c
                f.line(x, ys[lv] + 20, xs[lv - 1][c], ys[lv - 1] - 20,
                       ACCENT if on else "#c8c8c8", sw=5 if on else 3)
    for lv in range(4):
        for i, x in enumerate(xs[lv]):
            if path[lv] == i:
                fill = ACCENT
            elif lv < 3 and path[lv] ^ 1 == i:
                fill = OCHRE
            else:
                fill = GRAY
            w = 92 if lv == 3 else 56
            f.box(x - w / 2, ys[lv] - 20, w, 40, fill, rx=6, sw=0)
    f.text(xs[0][target], ys[0] + 9, "Tx2", 24)
    f.text(xs[3][0], ys[3] + 9, "root", 24)

    # The root of the tree is the root in one of the phone's headers.
    y = strip_top + mine * (sh + sg) + sh / 2
    f.raw(f'<path d="M{xs[3][0] - 50},{ys[3]} C 420,{ys[3]} 330,{y} 206,{y}" '
          f'fill="none" stroke="{ACCENT}" stroke-width="4" '
          f'stroke-dasharray="8 7" marker-end="url(#arrow-accent)"/>')

    legend = [(OCHRE, "証明として渡る"), (ACCENT, "端末が計算"), (GRAY, "渡らない")]
    x = 56
    for color, label in legend:
        f.box(x, 494, 30, 30, color, rx=4, sw=0)
        f.text(x + 42, 518, label, 24, anchor="start")
        x += 60 + 26 * len(label) + 40
    f.save("bitcoin-merkle-tree_concept.svg")


def duplicate_figure():
    """CVE-2012-2459: duplicating the odd node makes 3 and 4 leaves share a root."""
    f = Svg(960, 540, "3 件の正当なブロックと Tx2 を 2 回並べた 4 件のブロックが同じルートになる")
    ys = {"leaf": 390, "mid": 270, "root": 150}

    def tree(dx, fill, stroke, labels, dup):
        lx = [dx + 60 + i * 100 for i in range(4)]
        mx = [(lx[0] + lx[1]) / 2, (lx[2] + lx[3]) / 2]
        rx = (mx[0] + mx[1]) / 2
        for i, x in enumerate(mx):
            for c in (2 * i, 2 * i + 1):
                f.line(x, ys["mid"] + 25, lx[c], ys["leaf"] - 25, SUB, sw=2.5)
            f.line(rx, ys["root"] + 25, x, ys["mid"] - 25, SUB, sw=2.5)
        for i, x in enumerate(lx):
            dashed = dup and i == 3
            f.box(x - 45, ys["leaf"] - 25, 90, 50, "#ffffff" if dashed else fill,
                  SUB if dashed else stroke, dash="7 6" if dashed else "")
            f.text(x, ys["leaf"] + 9, labels[i], 24, SUB if dashed else INK)
        for x, s in zip(mx, ("H01", "H22")):
            f.box(x - 45, ys["mid"] - 25, 90, 50, fill, stroke)
            f.text(x, ys["mid"] + 9, s, 24)
        f.box(rx - 60, ys["root"] - 25, 120, 50, fill, stroke)
        f.text(rx, ys["root"] + 9, "ルート", 24)
        return lx, rx

    f.text(250, 70, "正当なブロック（3 件）", 26)
    lx, _ = tree(0, PALE, ACCENT, ["Tx0", "Tx1", "Tx2", "Tx2"], True)
    f.text(lx[3], 450, "計算上の複製", 24, SUB)

    f.text(710, 70, "無効なブロック（4 件）", 26)
    rx_leaf, _ = tree(460, OCHRE_PALE, OCHRE, ["Tx0", "Tx1", "Tx2", "Tx2"], False)
    f.text(480, ys["root"] + 12, "=", 40)
    f.text(480, ys["root"] + 52, "同じ値", 24, SUB)

    # Bitcoin Core's fix: a pair of equal hashes marks the block as mutated.
    f.box(rx_leaf[2] - 52, ys["leaf"] - 36, 204, 72, "none", RED, sw=3, dash="8 6")
    f.text((rx_leaf[2] + rx_leaf[3]) / 2, 466, "組の 2 つが同じ", 24)
    f.text((rx_leaf[2] + rx_leaf[3]) / 2, 500, "→ 棄却", 24, RED)
    f.save("bitcoin-merkle-tree_duplicate.svg")


def ambiguity_figure():
    """A 64-byte transaction reads both as a leaf and as an internal node."""
    f = Svg(960, 540, "64 バイトの取引は葉としても内部ノードとしても読める")

    def panel(cx, head, fill, stroke, top):
        f.text(cx, 62, head, 26)
        f.box(cx - 170, 110, 340, 60, fill, stroke)
        f.text(cx, 149, top, 24)
        f.line(cx, 250, cx, 178, SUB, sw=2.5, arrow="sub")
        f.text(cx + 14, 222, "二重 SHA-256", 24, SUB, anchor="start")
        f.box(cx - 190, 260, 380, 70, fill, stroke)

    panel(240, "葉として読む", PALE, ACCENT, "txid")
    f.text(240, 304, "取引 T（64 バイト）", 24)
    f.text(240, 380, "ブロックに入った本物の取引", 24, SUB)

    panel(720, "内部ノードとして読む", OCHRE_PALE, OCHRE, "内部ノードのハッシュ")
    f.line(720, 260, 720, 330, OCHRE, sw=2.5)
    f.text(625, 304, "左 32 バイト", 24)
    f.text(815, 304, "右 32 バイト", 24)
    f.box(715, 430, 200, 60, "#ffffff", OCHRE, dash="8 6")
    f.text(815, 469, "偽の取引", 24)
    f.line(815, 428, 815, 338, OCHRE, sw=2.5, arrow="sub")
    f.text(800, 395, "ハッシュが一致", 24, SUB, anchor="end")

    f.text(480, 149, "=", 40)
    f.text(480, 200, "同じ値", 24, SUB)
    f.save("bitcoin-merkle-tree_64byte.svg")


if __name__ == "__main__":
    concept_figure()
    duplicate_figure()
    ambiguity_figure()
