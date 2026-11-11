"""Generate the figures of the Bridge incidents note.

Run: python3 figures.py  -> images/*.webp

Each figure is built as SVG text here (stdlib only), rendered by headless
Chrome at 2x and saved as WebP (Pillow). Only the WebP files are kept in
images/.

- concept_figure(): the four incidents as four holes in the part that checks
  deposits, between the vault and the wrapped tokens.
- ronin_figure(): the timeline of how the fifth signature was obtained.
- wormhole_figure(): a real Instructions sysvar and a fake account look the
  same to a program that does not check the account address.
- bsc_figure(): the two BNB chains, the relayer and the forged proof.
- iavl_figure(): an honest proof path and a forged one whose unused right
  child holds a fake leaf, both ending at the same root.
"""

from html import escape
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#7aa6c2", "#e15759", "#fbe3e3"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"


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
            f'<style>text{{font-family:{FONT};fill:{INK}}} .mono{{font-family:{MONO}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("sub", SUB), ("red", RED), ("accent", ACCENT), ("ochre", OCHRE)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c} '
            f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=3, arrow="", dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, name):
        render("\n".join(self.parts + ["</svg>"]) + "\n", self.w, self.h, name)


def concept_figure():
    """Vault - checking part with four holes - wrapped tokens."""
    f = Svg(960, 500, "4 件の事故が破った場所。どれも金庫ではなく、間の確かめる部分")
    # source chain vault
    f.box(24, 60, 210, 330, PALE, rx=14)
    f.text(129, 104, "source chain", 22, SUB)
    f.box(54, 140, 150, 150, "#ffffff", ACCENT, sw=3)
    f.text(129, 176, "金庫", 24)
    for r in range(2):
        for c in range(3):
            f.circle(89 + c * 40, 222 + r * 40, 14, ACCENT)
    f.text(129, 340, "壊れていない", 20, SUB)
    # destination chain wrapped tokens
    f.box(726, 60, 210, 330, FILL, rx=14)
    f.text(831, 104, "destination chain", 22, SUB)
    f.box(756, 140, 150, 150, "#ffffff", SUB, sw=3)
    f.text(831, 176, "引換券", 24)
    for r in range(2):
        for c in range(3):
            f.circle(791 + c * 40, 222 + r * 40, 14, "#ffffff", SUB, dash="5 4")
    f.text(831, 340, "壊れていない", 20, SUB)
    # the checking part in the middle with four holes
    f.box(270, 40, 420, 380, OCHRE_PALE, OCHRE, sw=3, rx=14)
    f.text(480, 80, "確かめる部分", 24)
    holes = [("Ronin", "署名者の鍵と代行の許可"), ("Wormhole", "署名を確かめるコード"),
             ("Nomad", "確認済みの初期値"), ("BSC Token Hub", "Merkle proof を確かめるコード")]
    for i, (name, what) in enumerate(holes):
        y = 104 + i * 76
        f.box(296, y, 368, 62, "#ffffff", RED, sw=2.5, dash="7 5")
        f.text(316, y + 27, name, 20, INK, anchor="start")
        f.text(316, y + 52, what, 20, SUB, anchor="start")
    f.line(236, 230, 262, 230, OCHRE, sw=4, arrow="ochre")
    f.line(698, 230, 720, 230, OCHRE, sw=4, arrow="ochre")
    f.text(480, 470, "偽の預け入れ・焼却が、間の穴を通って本物として扱われた", 22, SUB)
    f.save("bridge-incidents_concept.webp")


def ronin_figure():
    """Timeline: permission granted, left in place, used by the attacker."""
    f = Svg(960, 330, "Ronin で 5 本目の署名が得られるまでの経緯")
    y = 150
    f.line(40, y, 920, y, SUB, sw=3)
    # the permission that was never revoked (ochre band)
    f.box(110, y - 18, 640, 36, OCHRE_PALE, OCHRE, sw=2, rx=6)
    f.text(505, y + 7, "代行の許可が取り消されないまま残る", 20, INK)
    events = [
        (110, "2021 年 11 月", "Axie DAO が", "署名の代行を許可"),
        (260, "2021 年 12 月", "代行は終わる", "（許可は残る）"),
        (750, "2022 年 3 月 23 日", "鍵 4 本＋代行の経路", "で偽の払い出し"),
        (850, "3 月 29 日", "利用者が払い出せず", "発覚"),
    ]
    for i, (x, date, a, b) in enumerate(events):
        attack = i == 2
        f.circle(x, y, 9, RED if attack else ACCENT)
        up = i % 2 == 0
        ty = 60 if up else 214
        f.text(x, ty, date, 20, SUB)
        f.text(x, ty + 30, a, 20, INK)
        f.text(x, ty + 58, b, 20, INK)
    f.text(800, y + 34, "6 日後", 18, SUB)
    f.save("bridge-incidents_ronin.webp")


def wormhole_figure():
    """A real sysvar and a fake account read the same way."""
    f = Svg(960, 430, "渡されたアカウントが本物の sysvar かを確かめなかった")
    rows = [("正しい呼び出し", "本物の Instructions sysvar", "ランタイムが作る", ACCENT, PALE, ""),
            ("攻撃", "偽のアカウント", "攻撃者が作る", RED, RED_PALE, "7 5")]
    for i, (label, acct, who, stroke, fill, dash) in enumerate(rows):
        y = 40 + i * 190
        f.text(30, y + 30, label, 22, SUB, anchor="start")
        f.box(30, y + 46, 330, 130, fill, stroke, sw=2.5, dash=dash)
        f.text(195, y + 82, acct, 22)
        f.text(195, y + 114, who, 20, SUB)
        f.text(195, y + 154, "命令の一覧: 署名の検証の命令あり", 18, INK)
        f.line(370, y + 100, 520, y + 100, SUB, sw=3, arrow="sub")
        f.text(445, y + 88, "渡す", 20, SUB)
        f.box(530, y + 46, 400, 130, "#ffffff", SUB, sw=2.5)
        f.text(730, y + 86, "Wormhole のプログラム", 22)
        f.text(730, y + 122, "アドレスを確かめずに読む", 20, SUB)
        f.text(730, y + 150, "→ 署名は検証済みと判断", 20, SUB)
    f.save("bridge-incidents_wormhole.webp")


def iavl_figure():
    """Honest path vs. forged path with an unused right child."""
    f = Svg(960, 500, "root の計算に使われない右の子に、偽の葉のハッシュを入れた")

    def panel(dx, title, forged):
        f.text(dx + 220, 34, title, 22, SUB)
        # root
        f.box(dx + 160, 56, 120, 50, "#ffffff", ACCENT, sw=3)
        f.text(dx + 220, 89, "root", 22, cls="mono")
        f.text(dx + 290, 89, "記録された root と一致", 15, SUB, anchor="start")
        f.line(dx + 220, 150, dx + 220, 112, ACCENT, sw=3, arrow="accent")
        # path element: left = sibling hash, right field
        f.box(dx + 40, 150, 360, 150, PALE, ACCENT, sw=2.5)
        f.text(dx + 220, 176, "経路の要素", 20, SUB)
        f.box(dx + 64, 190, 140, 56, "#ffffff", ACCENT, sw=2.5)
        f.text(dx + 134, 216, "左の子", 20)
        f.text(dx + 134, 238, "兄弟のハッシュ", 16, SUB)
        if forged:
            f.box(dx + 236, 190, 140, 56, RED_PALE, RED, sw=2.5, dash="7 5")
            f.text(dx + 306, 216, "右の子", 20)
            f.text(dx + 306, 238, "偽の葉のハッシュ", 16, SUB)
            f.text(dx + 150, 282, "計算は 左の子＋葉の値", 16, INK)
        else:
            f.box(dx + 236, 190, 140, 56, "#ffffff", SUB, sw=2, dash="4 4")
            f.text(dx + 306, 224, "右の子: 空", 18, SUB)
            f.text(dx + 150, 282, "計算は 左の子＋葉の値", 16, INK)
        # the real leaf feeds the computation
        f.box(dx + 70, 340, 140, 50, "#ffffff", ACCENT, sw=2.5)
        f.text(dx + 140, 372, "本物の葉", 20)
        f.line(dx + 140, 340, dx + 140, 306, ACCENT, sw=3, arrow="accent")
        if forged:
            f.box(dx + 250, 340, 140, 50, RED_PALE, RED, sw=2.5, dash="7 5")
            f.text(dx + 320, 372, "偽の葉", 20)
            f.line(dx + 320, 340, dx + 320, 252, RED, sw=2.5, arrow="red", dash="5 4")
            f.text(dx + 220, 424, "確認 1: 本物の葉から root が一致（右の子は無視）", 17, INK)
            f.text(dx + 220, 452, "確認 2: 偽の葉のハッシュ ＝ 右の子", 18, INK)
            f.text(dx + 220, 480, "→ 偽の葉も木の中にあると判定", 18, SUB)
        else:
            f.text(dx + 220, 430, "葉の値と兄弟のハッシュから", 20, INK)
            f.text(dx + 220, 460, "計算した値が root と一致する", 20, INK)

    panel(0, "正しい証明", False)
    f.line(480, 60, 480, 440, "#dddddd", sw=2)
    panel(500, "攻撃の証明", True)
    f.save("bridge-incidents_iavl.webp")


def bsc_figure():
    """Beacon Chain -> relayer -> BSC Token Hub; the forged proof minted BNB twice."""
    f = Svg(960, 360, "BNB Beacon Chain から BSC への bridge と、偽の proof による発行")
    f.box(24, 40, 270, 240, PALE, rx=14)
    f.text(159, 80, "BNB Beacon Chain", 22)
    f.text(159, 110, "source chain", 18, SUB)
    f.box(54, 140, 210, 100, "#ffffff", ACCENT, sw=2.5)
    f.text(159, 180, "ヘッダの root", 20)
    f.text(159, 212, "（預け入れは無い）", 18, SUB)
    f.box(666, 40, 270, 240, FILL, rx=14)
    f.text(801, 80, "BNB Smart Chain", 22)
    f.text(801, 110, "destination chain", 18, SUB)
    f.box(696, 140, 210, 100, "#ffffff", SUB, sw=2.5)
    f.text(801, 180, "BSC Token Hub", 20)
    f.text(801, 212, "proof を確かめて発行", 18, SUB)
    f.box(340, 120, 280, 140, RED_PALE, RED, sw=2.5, dash="7 5")
    f.text(480, 160, "攻撃者（relayer に登録）", 20)
    f.text(480, 196, "偽の Merkle proof", 20)
    f.text(480, 230, "を 2 回提出", 20)
    f.line(628, 190, 688, 190, RED, sw=3, arrow="red")
    f.text(480, 320, "1,000,000 BNB の発行が 2 回通った", 22, INK)
    f.save("bridge-incidents_bsc.webp")


if __name__ == "__main__":
    concept_figure()
    ronin_figure()
    wormhole_figure()
    bsc_figure()
    iavl_figure()
