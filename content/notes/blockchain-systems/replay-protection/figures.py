"""Generate the figures of the replay-protection note (hand-written SVG, standard library + Pillow).

python3 figures.py  ->  images/replay-protection_fork.webp, images/replay-protection_voucher.webp,
                        images/replay-protection_timeline.webp, images/replay-protection_recover.webp
（SVG を組み立て、Chrome の headless で 2 倍の解像度に描いて WebP にする。数値は lab/output/output.txt の結果）
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
NEUTRAL = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, title, w=960, h=540):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/>'
            '</marker></defs>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                      f'{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, dash=False, rx=8):
        d = ' stroke-dasharray="7 5"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=2, arrow=True, dash=False):
        m = ' marker-end="url(#ar)"' if arrow else ""
        d = ' stroke-dasharray="8 6"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{sw}"{m}{d}/>')

    def save(self, name):
        (HERE / "images").mkdir(exist_ok=True)
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)



def fork():
    """One chain splits into A and B. The old-format transaction lands on both, the EIP-155 one only on A."""
    s = Svg("分岐の前の共通のブロックの列が、chain A（31337）と chain B（31338）の 2 本に分かれる。"
            "chain ID を含めない署名のトランザクションは両方のブロックに入り、chain ID 31337 を含めたトランザクションは A だけに入って B では外される", h=470)
    s.p.append('<g transform="translate(0,-75)">')
    bw, bh = 92, 76
    # 分岐の前の共通の列
    for i, x in enumerate((40, 160, 280)):
        s.rect(x, 232, bw, bh, NEUTRAL, SUB)
        if i:
            s.line(x - 28, 270, x - 2, 270, SUB, 2)
    s.text(206, 350, "分岐の前は残高も nonce も共通", 22, cls="sub")
    # 分かれた 2 本
    rows = {"A": 120, "B": 344}
    for name, y in rows.items():
        s.p.append(f'<path d="M372,270 C410,270 410,{y + bh / 2} 448,{y + bh / 2}" fill="none" '
                   f'stroke="{SUB}" stroke-width="2" marker-end="url(#ar)"/>')
        s.rect(450, y, 250, bh, "#ffffff", SUB)
    # 取り込まれたトランザクションの印
    def mark(x, y, fill, stroke, label):
        s.rect(x, y, 100, 52, fill, stroke, rx=6)
        s.text(x + 50, y + 35, label, 22)
    yA, yB = rows["A"] + 12, rows["B"] + 12
    mark(464, yA, OCHRE_PALE, OCHRE, "古い形式")
    mark(586, yA, BLUE_PALE, BLUE, "EIP-155")
    mark(464, yB, OCHRE_PALE, OCHRE, "古い形式")
    s.rect(586, yB, 100, 52, "#ffffff", RED, rx=6, dash=True)
    s.text(636, yB + 37, "×", 30)
    s.text(730, rows["A"] + 34, "チェーン A", 26, anchor="start")
    s.text(730, rows["A"] + 64, "chain ID 31337", 22, anchor="start", cls="sub")
    s.text(730, rows["B"] + 34, "チェーン B", 26, anchor="start")
    s.text(730, rows["B"] + 64, "chain ID 31338", 22, anchor="start", cls="sub")
    s.text(636, rows["B"] + 112, "外される", 22)
    # 凡例
    s.rect(60, 470, 26, 26, OCHRE_PALE, OCHRE, rx=4)
    s.text(96, 491, "chain ID なしの署名", 22, anchor="start")
    s.rect(500, 470, 26, 26, BLUE_PALE, BLUE, rx=4)
    s.text(536, 491, "chain ID 31337 入りの署名", 22, anchor="start")
    s.p.append("</g>")
    s.save("replay-protection_fork.webp")


def voucher():
    """Where one EIP-712 voucher signature passes, for three ways of building the domain."""
    s = Svg("1 つの引換券の署名を 4 か所に出した結果。domain に chainId と verifyingContract を入れない mode 0 は、"
            "分岐した B と 2 個目のコントラクトでも通る。デプロイ時に固定した mode 1 は B で通り、2 個目では署名が不一致。"
            "検証のたびに計算する mode 2 は両方とも署名が不一致。同じ場所への 2 回目は、3 つとも使用済みで拒否",
            h=560)
    cols = ["署名した先", "分岐した B", "A の 2 個目", "同じ先に 2 回目"]
    subs = ["A の 1 個目", "同じアドレス", "別のアドレス", "A の 1 個目"]
    rows = [("mode 0", "chainId も", "verifyingContract も無し", ["通る", "通る", "通る", "使用済み"]),
            ("mode 1", "両方あり", "デプロイ時に固定", ["通る", "通る", "署名が不一致", "使用済み"]),
            ("mode 2", "両方あり", "検証のたびに計算", ["通る", "署名が不一致", "署名が不一致", "使用済み"])]
    x0, cw, y0, rh = 276, 164, 130, 118
    for j, (c, sub) in enumerate(zip(cols, subs)):
        cx = x0 + j * cw + cw / 2
        s.text(cx, 72, c, 22)
        s.text(cx, 102, sub, 20, cls="sub")
    for i, (name, l1, l2, cells) in enumerate(rows):
        y = y0 + i * rh
        s.text(20, y + 42, name, 26, anchor="start")
        s.text(20, y + 72, l1, 20, anchor="start", cls="sub")
        s.text(20, y + 98, l2, 20, anchor="start", cls="sub")
        for j, cell in enumerate(cells):
            x = x0 + j * cw + 6
            if cell == "通る" and j == 0:
                fill, stroke = BLUE_PALE, BLUE
            elif cell == "通る":
                fill, stroke = OCHRE_PALE, OCHRE
            else:
                fill, stroke = NEUTRAL, "#bdbdbd"
            s.rect(x, y + 8, cw - 12, rh - 16, fill, stroke)
            s.text(x + (cw - 12) / 2, y + rh / 2 + 8, cell, 22, cls="" if cell == "通る" else "sub")
    s.rect(290, 510, 24, 24, BLUE_PALE, BLUE, rx=4)
    s.text(322, 530, "意図した支払い", 20, anchor="start")
    s.rect(500, 510, 24, 24, OCHRE_PALE, OCHRE, rx=4)
    s.text(532, 530, "同じ署名の使い回しが通った", 20, anchor="start")
    s.save("replay-protection_voucher.webp")


def timeline():
    """2016-07 the DAO fork splits ETH and ETC; old transactions replay on both until each side adopts EIP-155."""
    s = Svg("2016 年 7 月のブロック 1,920,000 で ETH と ETC に分かれ、同じトランザクションが両方で通る期間が続いた。"
            "ETH は 2016 年 11 月の Spurious Dragon で EIP-155 を入れ、ETC は 2017 年 1 月の Die Hard で chain ID 61 を採用した。"
            "chain ID を含めない形式は、その後も両方で有効", h=490)
    y_eth, y_etc, y_c = 140, 300, 220
    x_fork, x_end = 250, 920
    s.line(40, y_c, x_fork, y_c, SUB, 4, arrow=False)
    s.text(60, y_c - 18, "分岐の前", 20, anchor="start", cls="sub")
    for y in (y_eth, y_etc):
        s.p.append(f'<path d="M{x_fork},{y_c} C{x_fork + 40},{y_c} {x_fork + 40},{y} {x_fork + 80},{y}" '
                   f'fill="none" stroke="{SUB}" stroke-width="4"/>')
        s.line(x_fork + 80, y, x_end, y, SUB, 4, arrow=False)
    s.text(x_end, y_eth - 16, "ETH", 24, anchor="end")
    s.text(x_end, y_etc + 34, "ETC", 24, anchor="end")
    s.text(x_fork - 14, y_c + 40, "2016-07", 20, anchor="end", cls="sub")
    s.text(x_fork - 14, y_c + 66, "ブロック 1,920,000", 20, anchor="end", cls="sub")
    s.p.append(f'<circle cx="{x_fork}" cy="{y_c}" r="9" fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
    # 両方で通る期間（ETH 側は EIP-155 まで、ETC 側は Die Hard まで）
    x_eth155, x_etc155 = 560, 760
    s.rect(x_fork + 84, y_eth - 16, x_eth155 - x_fork - 84, 32, OCHRE_PALE, OCHRE, rx=4)
    s.rect(x_fork + 84, y_etc - 16, x_etc155 - x_fork - 84, 32, OCHRE_PALE, OCHRE, rx=4)
    s.text((x_fork + 84 + x_eth155) / 2, y_eth + 7, "ETC でも通る", 18)
    s.text((x_fork + 84 + x_etc155) / 2, y_etc + 7, "ETH でも通る", 18)
    for x, y, d, l1, l2 in ((x_eth155, y_eth, -1, "2016-11 Spurious Dragon", "EIP-155（chain ID 1）"),
                            (x_etc155, y_etc, 1, "2017-01 Die Hard", "EIP-155（chain ID 61）")):
        s.p.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="3"/>')
        ty = y - 72 if d < 0 else y + 50
        s.text(x, ty, l1, 20)
        s.text(x, ty + 26, l2, 20, cls="sub")
    s.text(480, 446, "黄土の帯: 片方のチェーン向けのトランザクションが、もう片方でも通った期間（それぞれが EIP-155 を入れるまで）", 17, cls="sub")
    s.text(480, 472, "chain ID を含めない形式で署名したトランザクションは、その後も両方で有効", 17, cls="sub")
    s.save("replay-protection_timeline.webp")


def recover():
    """Rewriting v changes the chain ID that is hashed, so a different sender is recovered."""
    s = Svg("ノードは v から chain ID を読み、9 項目をハッシュして署名から送り主を復元する。"
            "v を 62710 から 62712 に書き換えると chain ID が 31338 になり、ハッシュが変わって、"
            "残高の無い別のアドレス 0x7d0a… が復元される", h=400)
    def row(y, v, chain, who, sub, fill, stroke):
        s.rect(30, y, 240, 80, NEUTRAL, SUB)
        s.text(150, y + 34, "署名の v", 20)
        s.text(150, y + 62, v, 18, cls="sub")
        s.line(270, y + 40, 302, y + 40)
        s.rect(304, y, 316, 80, "#ffffff", SUB)
        s.text(462, y + 34, "9 項目をハッシュする", 20)
        s.text(462, y + 62, f"nonce … data, chainId {chain}, 0, 0", 18, cls="sub")
        s.line(620, y + 40, 654, y + 40)
        s.rect(656, y, 274, 80, fill, stroke)
        s.text(793, y + 34, who, 20)
        s.text(793, y + 62, sub, 18, cls="sub")
    s.text(30, 50, "同じ r, s で送り主を復元する", 22, anchor="start")
    row(80, "62710 = 31337×2+35+1", "31337", "Alice 0x691f…", "署名した本人", BLUE_PALE, BLUE)
    row(250, "62712 に書き換え", "31338", "別のアドレス 0x7d0a…", "残高が無く、残高不足で拒否", RED_PALE, RED)
    s.text(462, 200, "↓ chain ID が変わると、ハッシュも変わる", 20, cls="sub")
    s.save("replay-protection_recover.webp")


if __name__ == "__main__":
    fork()
    voucher()
    timeline()
    recover()
