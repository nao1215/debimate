"""Generate the figures of the ethereum-address note.

Run: python3 figures.py  -> images/*.webp
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
The values in the lab figure come from lab/output/summary.txt.
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"


class Svg:
    def __init__(self, title, w=960, h=540):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} .mono{{font-family:{MONO}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs>'
            f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
            f'<marker id="arrs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '</defs>',
        ]

    def text(self, x, y, s, size=22, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def lines(self, x, cy, rows, size=22, anchor="middle", cls="", gap=1.35):
        """Several lines centred vertically on cy."""
        top = cy - (len(rows) - 1) * size * gap / 2 + size * 0.36
        for i, s in enumerate(rows):
            self.text(x, top + i * size * gap, s, size, anchor, cls)

    def box(self, x, y, bw, bh, stroke, fill, rx=8, dash=False, sw=2):
        d = ' stroke-dasharray="8 6"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, width=2.5, arrow="arr", dash=False):
        m = f' marker-end="url(#{arrow})"' if arrow else ""
        d = ' stroke-dasharray="7 6"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{width}"{m}{d}/>')

    def cross(self, cx, cy, r=13):
        for a, b in ((-r, r), (r, -r)):
            self.p.append(f'<line x1="{cx - r}" y1="{cy + a}" x2="{cx + r}" y2="{cy + b}" '
                          f'stroke="{RED}" stroke-width="5"/>')

    def save(self, name):
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def concept_figure():
    """Inputs of the three rules go into keccak256; the chain ID does not."""
    s = Svg("3 つの規則の材料が keccak256 に入り、chain ID は入らない。同じアドレスでもチェーンごとに中身が違う")
    # Byte strips: segment widths follow the role, not the exact byte count.
    rows = [
        ("EOA", 60, [(["公開鍵（64 バイト）"], 370, BLUE_PALE)]),
        ("CREATE", 175, [(["送り手"], 200, BLUE_PALE), (["nonce"], 170, OCHRE_PALE)]),
        ("CREATE2", 290, [(["ff"], 44, FILL), (["送り手"], 96, BLUE_PALE),
                          (["salt"], 76, OCHRE_PALE), (["initcode の", "ハッシュ"], 154, OCHRE_PALE)]),
    ]
    for name, top, segs in rows:
        s.text(30, top - 10, name, 24, "start", "sub")
        x = 30
        for label, sw, fill in segs:
            stroke = OCHRE if fill == OCHRE_PALE else (BLUE if fill == BLUE_PALE else SUB)
            s.box(x, top, sw, 56, stroke, fill, rx=2)
            s.lines(x + sw / 2, top + 28, label, 22 if len(label) == 1 else 19, gap=1.15)
            x += sw
        s.line(x + 6, top + 28, 440, top + 28)

    s.box(444, 60, 130, 286, INK, "#ffffff", rx=10)
    s.lines(509, 203, ["keccak", "256"], 26)
    s.line(578, 95, 616, 95)
    s.box(620, 60, 310, 70, BLUE, BLUE_PALE)
    s.text(775, 103, "アドレス（下位 20 バイト）", 22)

    for i, (chain, fill, stroke, label, dash) in enumerate([
        ("チェーン A", BLUE_PALE, BLUE, ["コード X"], False),
        ("チェーン B", OCHRE_PALE, OCHRE, ["空 /", "別のコード"], True),
    ]):
        x = 620 + i * 160
        s.line(x + 75, 130, x + 75, 176, SUB, 2, arrow="")
        s.box(x, 176, 150, 170, SUB, "#ffffff")
        s.text(x + 75, 212, chain, 22, cls="sub")
        s.box(x + 12, 236, 126, 92, stroke, fill, dash=dash)
        s.lines(x + 75, 282, label, 22)

    s.box(30, 430, 170, 60, OCHRE, OCHRE_PALE)
    s.text(115, 469, "chain ID", 24)
    s.line(200, 460, 306, 460)
    s.text(253, 448, "入る", 18, cls="sub")
    s.box(310, 430, 170, 60, SUB, FILL)
    s.text(395, 469, "取引の署名", 24)
    s.line(160, 430, 470, 352, SUB, 2, arrow="", dash=True)
    s.cross(330, 387)
    s.text(370, 400, "アドレスの材料には入らない", 22, "start", "sub")
    s.save("ethereum-address_concept.webp")


def ddproxy_figure():
    """One signed transaction without a chain ID puts the factory at one address on every chain."""
    s = Svg("chain ID の無い 1 件の取引を各チェーンに流すと、ファクトリも CREATE2 の作成先も同じアドレスになる")
    s.box(30, 190, 230, 170, OCHRE, OCHRE_PALE, rx=10)
    s.lines(145, 275, ["署名済みの取引 1 件", "chain ID なし（v=27）", "送り手の秘密鍵は", "誰も知らない"], 19)
    s.text(470, 34, "送り手の nonce 0 で作る", 22, cls="sub")
    s.text(795, 34, "同じ salt・initcode で作る", 22, cls="sub")
    lanes = [(84, "Ethereum"), (228, "チェーン X"), (372, "チェーン Y")]
    for y, name in lanes:
        s.line(262, 275, 336, y + 45, SUB, 2, arrow="arrs")
        s.text(345, y - 6, name, 20, "start", "sub")
        s.box(340, y, 260, 90, BLUE, BLUE_PALE)
        s.text(470, y + 38, "ファクトリ", 22)
        s.text(470, y + 70, "0x4e59b448…", 20, cls="mono")
        s.line(604, y + 45, 656, y + 45)
        s.box(660, y, 270, 90, BLUE, BLUE_PALE)
        s.text(795, y + 38, "CREATE2 の作成先", 22)
        s.text(795, y + 70, "どのチェーンでも同じ", 20, cls="sub")
    s.text(480, 515, "送り手・nonce が同じなので CREATE の式でも同じアドレスになる", 20, cls="sub")
    s.save("ethereum-address_ddproxy.webp")


def lab_figure():
    """What the local experiment put at each address on chains A, B and C."""
    s = Svg("チェーン A と C は同じ位置にファクトリと Child が並び、B は nonce 0 に V2 が入ってずれる")
    cols = [(40, "チェーン A（31337）", False), (340, "チェーン B（31338）", True), (640, "チェーン C（31339）", False)]
    cw = 280
    for x, name, shifted in cols:
        s.text(x + cw / 2, 36, name, 22)
        s.box(x, 56, cw, 56, BLUE, BLUE_PALE)
        s.text(x + cw / 2, 92, "EOA 0xf39Fd6e5…", 20, cls="mono")
        # nonce 0
        s.text(x + 8, 146, "nonce 0 の作成先 0x5FbDB231…", 17, "start", "sub")
        if shifted:
            s.box(x, 156, cw, 64, OCHRE, OCHRE_PALE)
            s.text(x + cw / 2, 196, "V2（別のコード）", 22)
            s.text(x + 8, 250, "nonce 1 の作成先 0xe7f1725E…", 17, "start", "sub")
            s.box(x, 260, cw, 64, OCHRE, OCHRE_PALE)
            s.text(x + cw / 2, 300, "ファクトリ", 22)
            fy = 324
        else:
            s.box(x, 156, cw, 64, BLUE, BLUE_PALE)
            s.text(x + cw / 2, 196, "ファクトリ", 22)
            fy = 220
        s.line(x + cw / 2, fy + 4, x + cw / 2, 396, SUB, 2, arrow="arrs")
        s.text(x + cw / 2 + 10, (fy + 400) / 2 + 8, "CREATE2", 18, "start", "sub")
        fill, stroke = (OCHRE_PALE, OCHRE) if shifted else (BLUE_PALE, BLUE)
        s.box(x, 400, cw, 80, stroke, fill)
        s.text(x + cw / 2, 432, "Child（salt=0, v=1）", 20)
        s.text(x + cw / 2, 464, "0xbE75Bf11…" if shifted else "0x66fAc1bd…", 20, cls="mono")
    s.text(480, 520, "青は 3 つのチェーンで同じアドレス、黄土色はずれたアドレス", 20, cls="sub")
    s.save("ethereum-address_lab.webp")


def wintermute_figure():
    """Ethereum and OP Mainnet: the 2019 factory transaction is replayed, then nonces are burned."""
    s = Svg("Ethereum の ProxyFactory を作った取引が OP Mainnet で再生され、nonce を進めた攻撃者が同じアドレスに Safe を作る")
    s.text(30, 44, "Ethereum", 24, "start")
    s.text(30, 300, "OP Mainnet", 24, "start")
    s.line(30, 60, 930, 60, SUB, 1.5, arrow="")
    s.line(30, 316, 930, 316, SUB, 1.5, arrow="")
    # Ethereum lane
    s.box(30, 84, 260, 110, BLUE, BLUE_PALE)
    s.lines(160, 139, ["2019 年", "ProxyFactory を作る", "（chain ID なしの署名）"], 19)
    s.line(294, 139, 386, 139)
    s.box(390, 84, 330, 110, BLUE, BLUE_PALE)
    s.lines(555, 139, ["2020 年 11 月", "ProxyFactory の CREATE で", "Wintermute の Safe 0x4f3a…"], 19)
    # OP lane, in time order
    s.box(30, 350, 190, 120, OCHRE, OCHRE_PALE, dash=True)
    s.lines(125, 410, ["2022 年 5 月", "0x4f3a… へ", "2,000 万 OP", "（まだ何も無い）"], 18)
    s.line(224, 410, 246, 410)
    s.box(250, 350, 210, 120, OCHRE, OCHRE_PALE)
    s.lines(355, 410, ["6 月 5 日", "ProxyFactory が", "同じアドレスにできる"], 18)
    s.line(464, 410, 486, 410)
    s.box(490, 350, 220, 120, OCHRE, OCHRE_PALE)
    s.lines(600, 410, ["攻撃者の Safe を", "作り続けて nonce を", "2020 年と同じ値へ"], 18)
    s.line(714, 410, 736, 410)
    s.box(740, 350, 190, 120, RED, "#fbe3e3", sw=2.5)
    s.lines(835, 410, ["0x4f3a… に", "攻撃者の Safe"], 20)
    # replay and the shared address
    s.line(200, 198, 340, 344, SUB, 2, arrow="arrs", dash=True)
    s.text(285, 250, "同じ取引を再生", 20, "start", "sub")
    s.line(720, 170, 820, 344, SUB, 2, arrow="arrs", dash=True)
    s.text(782, 250, "同じアドレス", 20, "start", "sub")
    s.text(480, 516, "どちらのアドレスも ProxyFactory のアドレスと nonce で決まる", 20, cls="sub")
    s.save("ethereum-address_wintermute.webp")


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    concept_figure()
    ddproxy_figure()
    lab_figure()
    wintermute_figure()
