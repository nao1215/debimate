"""Generate the figures of the upgradeable-proxy note.

Run: python3 figures.py  -> images/*.webp
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
The layout figure reads lab/output/summary.txt and the slot map uses lab/slots.py.
"""

import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GRAY, GRAY_PALE = "#9a9a9a", "#f2f2f2"
RED, RED_PALE = "#e15759", "#fbe3e3"
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
            f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            f'<marker id="arrb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
            f'<marker id="arrr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>'
            '</defs>',
        ]

    def text(self, x, y, s, size=22, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>{escape(s)}</text>')

    def box(self, x, y, bw, bh, stroke, fill, sw=2, rx=8, dash=False):
        d = ' stroke-dasharray="8 6"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=SUB, width=2, arrow="", dash=False):
        m = f' marker-end="url(#{arrow})"' if arrow else ""
        d = ' stroke-dasharray="6 5"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{width}"{m}{d}/>')

    def raw(self, s):
        self.p.append(s)

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
    """The proxy keeps the address and the data; only the code pointer moves."""
    s = Svg("利用者はプロキシだけを呼ぶ。データはプロキシにあり、実装のアドレスだけを差し替える")
    s.text(70, 130, "利用者", 24)
    for i in range(3):
        s.raw(f'<circle cx="70" cy="{180 + i * 70}" r="22" fill="{GRAY_PALE}" stroke="{SUB}" stroke-width="2"/>')
    s.line(100, 250, 146, 250, arrow="arr", width=2.5)

    s.box(150, 40, 420, 460, INK, "#ffffff", sw=2.5, rx=14)
    s.text(360, 86, "プロキシ（アドレスは変わらない）", 24)
    s.text(360, 122, "データ（storage）はすべてここ", 20, cls="sub")
    rows = [("owner（所有者）", GRAY_PALE, SUB), ("balance（残高）", GRAY_PALE, SUB),
            ("…", GRAY_PALE, SUB), ("実装のアドレス", OCHRE_PALE, OCHRE)]
    for i, (label, fill, stroke) in enumerate(rows):
        y = 150 + i * 82
        s.box(172, y, 376, 64, stroke, fill)
        s.text(360, y + 41, label, 22)
    py = 150 + 3 * 82 + 32

    s.box(700, 60, 230, 150, SUB, "#ffffff", dash=True, rx=12)
    s.text(815, 122, "実装 V1", 26, cls="sub")
    s.text(815, 160, "差し替え前のコード", 20, cls="sub")
    s.box(700, 300, 230, 150, BLUE, BLUE_PALE, sw=3, rx=12)
    s.text(815, 362, "実装 V2", 26)
    s.text(815, 400, "今のコード", 20)

    s.raw(f'<path d="M 548 {py} C 630 {py}, 620 140, 698 140" fill="none" stroke="{SUB}" '
          'stroke-width="2" stroke-dasharray="8 6"/>')
    s.line(548, py + 8, 696, 380, BLUE, 4, arrow="arrb")
    s.text(815, 488, "DELEGATECALL で", 20, cls="sub")
    s.text(815, 516, "V2 のコードを借りる", 20, cls="sub")
    s.save("upgradeable-proxy_concept.webp")


def call_vs_delegate_figure():
    """CALL runs B's code on B's storage; DELEGATECALL runs B's code on A's storage."""
    s = Svg("CALL は呼び先の storage で、DELEGATECALL は呼び出し元の storage で呼び先のコードを動かす", h=500)
    for col, (title, delegate) in enumerate([("CALL", False), ("DELEGATECALL", True)]):
        ox = 20 + col * 470
        s.text(ox + 210, 46, title, 26, cls="mono")
        # Contract A (caller) and B (callee), each with code and storage.
        for j, name in enumerate(["A（呼び出し元）", "B（呼び先）"]):
            x = ox + j * 230
            s.box(x, 80, 190, 330, SUB, "#ffffff", rx=12)
            s.text(x + 95, 116, name, 20)
            s.box(x + 15, 140, 160, 100, SUB, GRAY_PALE)
            s.text(x + 95, 182, "コード", 20)
            s.text(x + 95, 214, "increment()" if j else "呼ぶ処理", 18, cls="mono" if j else "sub")
            used = (j == 0) if delegate else (j == 1)
            s.box(x + 15, 270, 160, 110, OCHRE if used else SUB, OCHRE_PALE if used else GRAY_PALE,
                  sw=3 if used else 1.5)
            s.text(x + 95, 312, "storage", 20)
            s.text(x + 95, 350, "count += 1" if used else "変わらない", 18, cls="" if used else "sub")
        # Call arrow A -> B
        s.line(ox + 190, 190, ox + 228, 190, arrow="arr", width=2.5)
        bx = ox + 230
        if delegate:
            # B's code acts on A's storage.
            s.raw(f'<path d="M {bx + 40} 240 C {bx + 30} 290, {ox + 215} 310, {ox + 178} 312" fill="none" '
                  f'stroke="{BLUE}" stroke-width="3.5" marker-end="url(#arrb)"/>')
        else:
            s.line(bx + 95, 240, bx + 95, 266, BLUE, 3.5, arrow="arrb")
        s.text(ox + 210, 450, "B のコードが B のデータを変える" if not delegate
               else "B のコードが A のデータを変える", 20, cls="sub")
    s.line(480, 60, 480, 470, GRAY, 1.5, dash=True)
    s.save("upgradeable-proxy_call_vs_delegate.webp")


def layout_figure():
    """The same three slots read by V1 and by V2Bad, which added `fee` at the top."""
    out = (HERE / "lab" / "output" / "summary.txt").read_text()
    fee = int(out.split("fee()=")[1].split()[0])
    owner = out.split("slot 0=0x")[1].split()[0][-40:]
    balance = int(out.split("slot 1=0x")[1].split()[0], 16)
    short = f"0x{owner[:4]}…{owner[-4:]}"
    rows = [
        ("slot 0", short, f"owner = {short}", f"fee = {fee / 10 ** 47:.2f} × 10^47"),
        ("slot 1", f"0x…{balance:x}", f"balance = {balance}", f"owner = 0x…00{balance:x}"),
        ("slot 2", "0", "（未使用）", "balance = 0"),
    ]
    s = Svg("同じ 3 つの slot を、V1 と先頭に fee を足した V2Bad が別の変数として読む")
    s.text(160, 70, "V1 の読み方", cls="sub")
    s.text(480, 70, "プロキシの storage", cls="sub")
    s.text(815, 70, "V2Bad の読み方", cls="sub")
    for i, (slot, value, v1, v2) in enumerate(rows):
        y = 110 + 120 * i
        s.box(375, y, 210, 76, SUB, GRAY_PALE, sw=1.5, rx=6)
        s.text(480, y + 32, slot, 20, cls="sub")
        s.text(480, y + 62, value, 22)
        s.box(10, y + 8, 300, 60, BLUE, BLUE_PALE, rx=6)
        s.text(160, y + 46, v1, 22)
        s.box(680, y + 8, 270, 60, OCHRE, OCHRE_PALE, rx=6)
        s.text(815, y + 46, v2, 22)
        s.line(310, y + 38, 375, y + 38, BLUE, 2.5)
        s.line(585, y + 38, 680, y + 38, OCHRE, 2.5)
    s.text(480, 500, "差し替えで変わるのはコードだけで、slot の値はそのまま", 22, cls="sub")
    s.save("upgradeable-proxy_layout.webp")


def slot_map_figure():
    """Where Solidity puts variables, and where ERC-1967 and ERC-7201 put their values."""
    sys.path.insert(0, str(HERE / "lab"))
    from slots import erc1967, erc7201  # noqa: E402

    impl = erc1967("eip1967.proxy.implementation")[2:]
    ns = erc7201("debimate.vault")[2:]
    s = Svg("storage の番号の空間で、Solidity の変数は 0 の近くに並び、ERC-1967 と ERC-7201 の場所は遠くにある", h=440)
    x0, x1, y = 60, 900, 200
    s.box(x0, y - 20, x1 - x0, 40, SUB, GRAY_PALE, sw=1.5, rx=6)
    s.text(x0, y + 54, "0", 20, anchor="start", cls="sub")
    s.text(x1, y + 54, "2^256 − 1", 20, anchor="end", cls="sub")

    # Solidity's sequential variables: right next to 0.
    s.box(x0 + 2, y - 18, 18, 36, BLUE, BLUE_PALE, rx=3)
    s.line(x0 + 11, y - 22, x0 + 11, y - 70, BLUE, 2)
    s.text(x0, y - 104, "宣言の順に並ぶ変数", 22, anchor="start")
    s.text(x0, y - 78, "slot 0, 1, 2 …", 20, anchor="start", cls="mono")

    def mark(hexval, color, title, sub, up):
        x = x0 + (x1 - x0) * int(hexval[:4], 16) / 65536
        s.line(x, y - 20, x, y + 20, color, 5)
        ty = y - 78 if up else y + 96
        s.line(x, y - 22 if up else y + 22, x, ty + (8 if up else -30), color, 2)
        s.text(x, ty - 26 if up else ty, title, 22)
        s.text(x, ty if up else ty + 28, sub, 20, cls="mono")

    mark(impl, OCHRE, "ERC-1967：実装のアドレス", f"0x{impl[:4]}…{impl[-4:]}", False)
    mark(ns, OCHRE, "ERC-7201：名前空間の起点", f"0x{ns[:4]}…{ns[-4:]}", True)
    # Inside the namespace, members still follow declaration order from the root.
    xn = x0 + (x1 - x0) * int(ns[:4], 16) / 65536
    s.text(xn, y + 100, "中のメンバーは起点から宣言の順に並ぶ", 20, cls="sub")
    s.text(xn, y + 126, "（起点に owner、次の slot に balance）", 20, cls="sub")
    s.text(480, 410, "ハッシュから決めた番号は、0 の近くの変数と重ならない", 22, cls="sub")
    s.save("upgradeable-proxy_slot_map.webp")


def initializer_figure():
    """constructor writes to the implementation; initialize via the proxy writes to the proxy."""
    s = Svg("constructor は実装の storage に書き、プロキシ経由の initialize はプロキシの storage に書く", h=500)
    s.text(470, 50, "実装の storage", 22, cls="sub")
    s.text(780, 50, "プロキシの storage", 22, cls="sub")
    rows = [
        ("① 実装をデプロイ", "constructor が動く",
         ("constructor の値", BLUE, BLUE_PALE), ("空のまま", SUB, GRAY_PALE)),
        ("② プロキシ経由で", "initialize(alice)",
         ("変わらない", SUB, GRAY_PALE), ("owner = alice", BLUE, BLUE_PALE)),
        ("③ 第三者が実装を直接", "initialize(mallory)",
         ("owner = mallory", RED, RED_PALE), ("owner = alice のまま", SUB, GRAY_PALE)),
    ]
    for i, (a, b, impl, proxy) in enumerate(rows):
        y = 80 + 130 * i
        s.text(20, y + 42, a, 22, anchor="start")
        s.text(20, y + 74, b, 20, anchor="start", cls="mono" if "(" in b else "sub")
        for x, (label, stroke, fill) in ((350, impl), (660, proxy)):
            s.box(x, y + 14, 240, 76, stroke, fill, sw=2.5 if stroke != SUB else 1.5)
            s.text(x + 120, y + 60, label, 22, fill=RED if stroke == RED else None)
    s.text(480, 482, "実装の storage は普段使われないが、初期化しないと誰でも所有者になれる", 20, cls="sub")
    s.save("upgradeable-proxy_initializer.webp")


if __name__ == "__main__":
    concept_figure()
    call_vs_delegate_figure()
    layout_figure()
    slot_map_figure()
    initializer_figure()
