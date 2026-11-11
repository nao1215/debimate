"""Generate the figures of the Bitcoin Merkle Tree weaknesses note.

Run: python3 figures.py  -> images/*.webp

Each figure is built as SVG text here (stdlib only), rendered by headless
Chrome at 2x and saved as WebP (Pillow). Only the WebP files are kept in
images/.

- concept_figure(): the two build rules and what each lets an attacker do.
- duplicate_figure(): CVE-2012-2459, 3 leaves and 4 leaves share a root.
- depth_figure(): the honest proof of T and the forged proof that is one level
  deeper, both ending at the same root.
- ambiguity_figure(): CVE-2017-12842, a 64-byte transaction reads both as a
  leaf and as an internal node.
"""

from html import escape
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED = "#7aa6c2", "#e15759"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def render(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        (HERE / "images").mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
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
        render("\n".join(self.parts + ["</svg>"]) + "\n", self.w, self.h, name)

GRAY = "#dddddd"


def concept_figure():
    """Two build rules, two weaknesses."""
    f = Svg(960, 540, "奇数の複製と、葉と内部ノードを区別しない計算が、それぞれ弱点になる")

    def node(x, y, w, s, fill=PALE, stroke=ACCENT, dash="", color=INK):
        f.box(x - w / 2, y - 22, w, 44, fill, stroke, dash=dash)
        if s:
            f.text(x, y + 8, s, 22, color)

    # Left: duplicating the odd node.
    f.box(20, 20, 450, 500, FILL, rx=16)
    f.text(245, 64, "規則 1：奇数なら最後を複製", 26)
    lx = [80, 185, 300, 405]
    mx = [(lx[0] + lx[1]) / 2, (lx[2] + lx[3]) / 2]
    for k, x in enumerate(mx):
        f.line(245, 150, x, 218, SUB, sw=2.5)
        for c in (2 * k, 2 * k + 1):
            f.line(x, 262, lx[c], 318, SUB, sw=2.5)
    node(245, 128, 110, "ルート")
    for x in mx:
        node(x, 240, 90, "")
    for k, x in enumerate(lx):
        dup = k == 3
        node(x, 340, 90, "Tx2" if dup else f"Tx{k}", "#ffffff" if dup else PALE,
             SUB if dup else ACCENT, "7 6" if dup else "", SUB if dup else INK)
    f.text(405, 394, "計算上の複製", 20, SUB)
    f.text(245, 446, "Tx2 を 2 回並べた 4 件と同じルート", 22, RED)
    f.text(245, 486, "→ 正当なブロックを拒ませる", 22)

    # Right: a 64-byte transaction read as an internal node.
    f.box(490, 20, 450, 500, FILL, rx=16)
    f.text(715, 64, "規則 2：葉も内部ノードも同じ計算", 26)
    f.line(715, 150, 610, 218, SUB, sw=2.5)
    f.line(715, 150, 800, 218, SUB, sw=2.5)
    node(715, 128, 110, "ルート")
    node(610, 240, 90, "")
    node(800, 240, 180, "T（64 バイト）", OCHRE_PALE, OCHRE)
    f.line(770, 262, 730, 318, OCHRE, sw=2.5, dash="7 6")
    f.line(830, 262, 865, 318, OCHRE, sw=2.5, dash="7 6")
    node(728, 340, 136, "左 32 バイト", "#ffffff", OCHRE, "7 6", SUB)
    node(870, 340, 120, "偽の取引", "#ffffff", OCHRE, "7 6")
    f.text(800, 394, "内部ノードと偽る", 20, SUB)
    f.text(715, 446, "ブロックに無い取引の証明が通る", 22, RED)
    f.text(715, 486, "→ 軽量クライアントを騙す", 22)
    f.save("bitcoin-merkle-tree-attacks_concept.webp")


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
        for x, s in zip(mx, ("Hash01", "Hash22")):
            f.box(x - 55, ys["mid"] - 25, 110, 50, fill, stroke)
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
    f.save("bitcoin-merkle-tree-attacks_duplicate.webp")


def depth_figure():
    """The forged proof is one level deeper than the honest proof of T."""
    f = Svg(960, 560, "T を葉とする正しい証明と、T を内部ノードとする 1 段深い偽の証明")
    rows = [150, 260, 370, 480]

    def chain(cx, head, leaf_label, depth4, px):
        f.text(cx, 56, head, 26)
        sx = px + 160
        levels = [("ルート", "", 0), ("計算値", "兄弟 B", 1), (leaf_label, "兄弟 A", 1)]
        if depth4:
            # The fake transaction is the right child; the first 32 bytes of T are the left.
            levels.append(("偽の取引", "左 32 バイト", -1))
        for k, (pl, sl, side) in enumerate(levels):
            y = rows[k]
            bx = sx if side > 0 else px - 160
            if k > 0:
                f.line(px, y - 26, px, rows[k - 1] + 26, ACCENT, sw=4)
                f.line(bx - 50 * side, y - 26, px + 20 * side, rows[k - 1] + 26, OCHRE, sw=2.5)
            dashed = k == 3
            f.box(px - 85, y - 26, 170, 52, "#ffffff" if dashed else PALE, ACCENT,
                  dash="7 6" if dashed else "")
            f.text(px, y + 9, pl, 22)
            if sl:
                f.box(bx - 70, y - 26, 140, 52, OCHRE_PALE, OCHRE)
                f.text(bx, y + 9, sl, 22)
        n = 3 if depth4 else 2
        f.text(cx, 540, f"証明のハッシュ {n} 個", 24, RED if depth4 else INK)

    chain(240, "正しい証明（T は葉）", "T の txid", False, 190)
    chain(720, "偽の証明（T を内部ノードに）", "T の txid", True, 700)
    f.line(480, 90, 480, 420, "#cccccc", sw=2, dash="6 6")
    f.save("bitcoin-merkle-tree-attacks_depth.webp")


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
    f.text(800, 395, "txid が一致", 24, SUB, anchor="end")

    f.text(480, 149, "=", 40)
    f.text(480, 200, "同じ値", 24, SUB)
    f.save("bitcoin-merkle-tree-attacks_64byte.webp")


if __name__ == "__main__":
    concept_figure()
    duplicate_figure()
    depth_figure()
    ambiguity_figure()
