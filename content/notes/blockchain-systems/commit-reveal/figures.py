"""Generate the figures of the commit-reveal note (hand-written SVG, standard library only).

python3 figures.py  ->  images/commit-reveal_frontrun.webp, images/commit-reveal_timeline.webp,
                        images/commit-reveal_randao.webp
（SVG を組み立て、Chrome の headless で 2 倍の解像度に描いて WebP にする）
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


def frontrun():
    """mempool で読んだ入札に、手数料を上乗せして割り込む（実験の block 2）。"""
    s = Svg("Alice の入札を mempool で読んだ Bob が、手数料を上乗せして先に処理される", 960, 400)
    s.rect(40, 70, 400, 260, NEUTRAL, "#cccccc", 1.5)
    s.text(240, 50, "mempool（誰でも中身を読める）", 24, cls="sub")
    s.rect(70, 100, 340, 66, BLUE_PALE, BLUE, 2)
    s.text(240, 142, "1. Alice：bid(50)、手数料 1 gwei", 22)
    s.line(240, 168, 240, 226, SUB, 2)
    s.text(255, 205, "Bob が中身を読む", 20, anchor="start", cls="sub")
    s.rect(70, 232, 340, 66, OCHRE_PALE, OCHRE, 2)
    s.text(240, 274, "2. Bob：bid(51)、手数料 3 gwei", 22)
    s.line(444, 200, 536, 200, SUB, 2)
    s.text(490, 186, "3. 並べる", 20, cls="sub")
    s.rect(540, 70, 390, 260, "#ffffff", INK, 2)
    s.text(735, 50, "ブロックを作る者が手数料の高い順に並べる", 20, cls="sub")
    s.rect(560, 100, 350, 66, OCHRE_PALE, OCHRE, 2)
    s.text(735, 142, "#0 Bob：bid(51) → 成功", 22)
    s.rect(560, 232, 350, 66, RED_PALE, RED, 2)
    s.text(735, 274, "#1 Alice：bid(50) → 取り消し", 22)
    s.text(480, 375, "後から送った Bob の入札が先に処理され、Alice は「too low」で負ける", 22)
    s.save("commit-reveal_frontrun.webp")


def timeline():
    """What is public and what stays private, before and after the commit deadline."""
    s = Svg("コミットの段では入札額のハッシュだけが公開され、締め切りの後のリビールの段で入札額と salt が公開されて照合される")
    left, mid, right = 150, 555, 935
    # 2 つの段の帯
    s.rect(left, 40, mid - left - 15, 410, BLUE_PALE, BLUE, rx=10)
    s.rect(mid + 15, 40, right - mid - 15, 410, OCHRE_PALE, OCHRE, rx=10)
    s.text((left + mid) / 2, 82, "コミットの段", 28)
    s.text((mid + right) / 2, 82, "リビールの段", 28)
    # 締め切り
    s.line(mid, 30, mid, 470, SUB, 2, arrow=False, dash=True)
    s.text(mid, 500, "締め切り", 24, cls="sub")
    # 行の名前
    s.text(75, 190, "公開", 26)
    s.text(75, 222, "誰でも見える", 24, cls="sub")
    s.text(75, 370, "手元", 26)
    s.text(75, 402, "本人だけ", 24, cls="sub")
    s.line(20, 290, right, 290, "#cccccc", 1.5, arrow=False)

    # コミットの段: 手元に値と salt、公開はハッシュだけ
    s.rect(200, 345, 300, 70, "#ffffff", INK)
    s.text(350, 377, "入札額 50 と salt", 26)
    s.text(350, 405, "（＋送り主のアドレス）", 18, cls="sub")
    s.line(350, 343, 350, 248)
    s.text(335, 335, "keccak256", 24, anchor="end", cls="sub")
    s.rect(200, 160, 300, 80, "#ffffff", BLUE, 3)
    s.text(350, 210, "0x66be…", 26)
    s.text(350, 140, "commit：32 バイトのハッシュ値", 24, cls="sub")

    # リビールの段: 値と salt を公開し、コントラクトが照合する
    s.rect(605, 152, 290, 56, "#ffffff", OCHRE, 3)
    s.text(750, 189, "入札額 50 と salt", 24)
    s.text(750, 140, "reveal：中身を明かす", 24, cls="sub")
    s.line(500, 380, 600, 200)
    s.text(585, 330, "明かす", 24, anchor="start", cls="sub")
    s.rect(605, 222, 290, 56, GREEN_PALE, GREEN, 2)
    s.text(750, 259, "コントラクトが照合", 24)
    # 時間の矢印
    s.line(left, 520, right, 520, SUB, 2)
    s.text(right - 4, 510, "時間", 24, anchor="end", cls="sub")
    s.save("commit-reveal_timeline.webp")


def randao():
    """The last proposer of an epoch can choose between two outcomes by withholding."""
    s = Svg("エポックの最後の提案者は、ブロックを出して値を混ぜるか、出さずに混ぜないかの 2 つの結果から選べる")
    xs = [120, 250, 380, 510]
    s.text(40, 70, "エポック（32 スロット）の終わり", 24, anchor="start", cls="sub")
    for i, x in enumerate(xs):
        last = i == len(xs) - 1
        fill, stroke = (OCHRE_PALE, OCHRE) if last else (BLUE_PALE, BLUE)
        s.rect(x - 50, 100, 100, 80, fill, stroke, 2)
        s.text(x, 150, ["…", "29", "30", "31"][i], 26)
        if i < len(xs) - 1:
            s.line(x + 52, 140, xs[i + 1] - 54, 140, SUB, 2)
    s.text(510, 220, "最後の提案者", 24)
    s.text(250, 220, "各提案者が値を混ぜる", 24, cls="sub")
    # 2 つの分岐
    s.line(562, 130, 680, 90)
    s.line(562, 150, 680, 260)
    s.rect(685, 50, 250, 90, BLUE_PALE, BLUE, 2)
    s.text(810, 88, "ブロックを出す", 24)
    s.text(810, 122, "→ 乱数 A", 26)
    s.rect(685, 215, 250, 90, OCHRE_PALE, OCHRE, 2)
    s.text(810, 253, "出さない", 24)
    s.text(810, 287, "→ 乱数 B", 26)
    # 説明
    s.rect(40, 360, 895, 140, NEUTRAL, "#cccccc", 1.5)
    s.text(487, 410, "自分の値は出す前から分かるので、A と B を先に計算できる", 26)
    s.text(487, 460, "有利な方を選べる代わりに、出さなければ報酬を失う", 24, cls="sub")
    s.save("commit-reveal_randao.webp")


if __name__ == "__main__":
    frontrun()
    timeline()
    randao()
