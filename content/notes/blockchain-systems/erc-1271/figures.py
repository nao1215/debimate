"""Generate the figures of the ERC-1271 note.

Run: python3 figures.py  -> images/*.webp
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
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
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>{escape(s)}</text>')

    def box(self, x, y, bw, bh, stroke, fill, sw=2.5, rx=8, dash=False):
        d = ' stroke-dasharray="7 5"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, arrow=True, dash=False):
        m = ' marker-end="url(#arr)"' if arrow else ""
        d = ' stroke-dasharray="6 5"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="2"{m}{d}/>')

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


def address_figure():
    """Why ecrecover never returns a contract account's address."""
    s = Svg("EOA のアドレスは公開鍵から決まるので ecrecover で復元できる。コントラクトのアカウントのアドレスはデプロイの方法から決まるので、ecrecover は所有者の EOA のアドレスしか返さない")
    # EOA lane.
    s.box(30, 40, 900, 200, OCHRE, OCHRE_PALE)
    s.text(55, 82, "EOA", 26, anchor="start")
    s.text(55, 140, "秘密鍵 → 公開鍵 → アドレス", 24, anchor="start")
    s.text(55, 196, "ecrecover(digest, 署名) → 公開鍵 → 同じアドレス", 24, anchor="start")
    s.text(905, 196, "一致", 24, anchor="end")
    # Contract account lane.
    s.box(30, 290, 900, 200, BLUE, BLUE_PALE)
    s.text(55, 332, "コントラクトのアカウント", 26, anchor="start")
    s.text(55, 390, "デプロイした側のアドレスと nonce など → アドレス", 24, anchor="start")
    s.text(55, 446, "ecrecover(digest, 署名) → 所有者の EOA のアドレス", 24, anchor="start")
    s.box(838, 418, 70, 40, RED, RED_PALE, sw=2, rx=6)
    s.text(873, 446, "≠", 26, fill=RED)
    s.text(480, 528, "公開鍵から決まらないアドレスは、どんな署名からも復元されない", 22, cls="sub")
    s.save("erc-1271_address.webp")


def branch_figure():
    """How a verifier branches between ecrecover and isValidSignature."""
    s = Svg("署名者のアドレスにコードが無ければ ecrecover、あればアカウントの isValidSignature に問い合わせる")
    s.box(30, 200, 250, 140, SUB, GRAY_PALE)
    s.text(155, 255, "署名者のアドレスに", 24)
    s.text(155, 298, "コードがあるか", 24)

    s.line(280, 240, 330, 130)
    s.text(310, 165, "無い", 24, anchor="end", cls="sub")
    s.box(340, 50, 590, 160, OCHRE, OCHRE_PALE)
    s.text(365, 92, "EOA（コードが無い）", 26, anchor="start")
    s.text(365, 138, "ecrecover(digest, sig)", 26, anchor="start", cls="mono")
    s.text(365, 182, "== 署名者のアドレス ?", 26, anchor="start")

    s.line(280, 300, 330, 410)
    s.text(305, 395, "ある", 24, anchor="end", cls="sub")
    s.box(340, 330, 590, 160, BLUE, BLUE_PALE)
    s.text(365, 372, "コントラクト・委任した EOA（ERC-1271）", 24, anchor="start")
    s.text(365, 418, "signer.isValidSignature(digest, sig)", 24, anchor="start", cls="mono")
    s.text(365, 462, "== 0x1626ba7e ?", 26, anchor="start", cls="mono")

    s.save("erc-1271_branch.webp")


def reuse_figure():
    """A login signature for account A is accepted by account B of the same owner (experiment 5)."""
    s = Svg("アカウント A のログインのための署名を、同じ所有者のアカウント B も有効と返す。文言にアカウントのアドレスが無いと、B としてもログインできてしまう")
    s.box(30, 170, 270, 200, OCHRE, OCHRE_PALE)
    s.text(165, 222, "所有者の EOA", 26)
    s.text(165, 266, "ログインの文言に", 22, cls="sub")
    s.text(165, 296, "1 回署名", 22, cls="sub")
    s.text(165, 334, "（アカウントのアドレス無し）", 20, cls="sub")
    rows = [(50, BLUE, BLUE_PALE, "StudyAccount A", "ログインしようとしたアカウント", "A としてログイン"),
            (300, RED, RED_PALE, "StudyAccount B", "所有者が同じ別のアカウント", "B としてもログインできてしまう")]
    for y, st, fi, name, why, res in rows:
        s.line(300, 270, 380, y + 85)
        s.box(385, y, 545, 180, st, fi)
        s.text(410, y + 44, name, 26, anchor="start")
        s.text(410, y + 82, why, 22, anchor="start", cls="sub")
        s.text(410, y + 122, "isValidSignature → 0x1626ba7e", 22, anchor="start", cls="mono")
        s.text(410, y + 160, res, 22, anchor="start", fill=RED if st == RED else None)
    s.text(480, 525, "isValidSignature は所有者だけを見て、どのアカウント向けかは見ない", 22, cls="sub")
    s.save("erc-1271_reuse.webp")


def erc6492_figure():
    """ERC-6492 wrapped signature and the steps of an off-chain verifier."""
    s = Svg("ERC-6492 の署名は、ファクトリ・呼び出しデータ・元の署名を abi.encode し、末尾に 0x6492…6492 を付けたもの。検証する側は 1 回の eth_call でデプロイを模擬してから isValidSignature を呼ぶ")
    s.text(480, 44, "ERC-6492 の署名", 24, cls="sub")
    s.box(30, 64, 640, 110, BLUE, BLUE_PALE)
    s.text(350, 104, "abi.encode(", 22, cls="mono")
    s.text(350, 144, "factory, factoryCalldata, 元の署名)", 22)
    s.box(670, 64, 260, 110, OCHRE, OCHRE_PALE)
    s.text(800, 104, "0x6492…6492", 22, cls="mono")
    s.text(800, 144, "末尾の 32 バイト", 22, cls="sub")

    s.text(480, 240, "検証する側（1 回の eth_call の中）", 24, cls="sub")
    steps = [(30, "1. 末尾を見て", "6492 の形と判断"), (340, "2. ファクトリを呼び", "デプロイを模擬"),
             (650, "3. isValidSignature", "を元の署名で呼ぶ")]
    for x, a, b in steps:
        s.box(x, 270, 280, 120, SUB, GRAY_PALE)
        s.text(x + 140, 318, a, 22)
        s.text(x + 140, 356, b, 22, cls="sub")
    s.line(310, 330, 336, 330)
    s.line(620, 330, 646, 330)
    s.text(480, 460, "eth_call はトランザクションを送らないので、チェーンの状態は変わらない", 22, cls="sub")
    s.save("erc-1271_6492.webp")


def rehash_figure():
    """Defensive rehash: mixing the account address makes the digest differ per account."""
    s = Svg("アカウントのアドレスを混ぜてハッシュし直すと、A 向けの署名は B では別のハッシュになり、通らない", h=420)
    s.box(30, 150, 240, 120, OCHRE, OCHRE_PALE)
    s.text(150, 200, "所有者の EOA", 24)
    s.text(150, 238, "A 向けに署名", 22, cls="sub")
    rows = [(40, BLUE, BLUE_PALE, "アカウント A（アドレスを混ぜる版）", "keccak256(A のアドレス ‖ hash)", "署名したハッシュと一致"),
            (240, GRAY, GRAY_PALE, "アカウント B（アドレスを混ぜる版）", "keccak256(B のアドレス ‖ hash)", "別のハッシュ → 無効")]
    for y, st, fi, name, calc, res in rows:
        s.line(270, 210, 350, y + 70)
        s.box(355, y, 575, 140, st, fi)
        s.text(380, y + 40, name, 24, anchor="start")
        s.text(380, y + 80, calc, 22, anchor="start")
        s.text(380, y + 118, res, 22, anchor="start", cls="sub")
    s.text(480, 410, "式は考え方の例（ERC-7739 の正確な形ではない）", 20, cls="sub")
    s.save("erc-1271_rehash.webp")


if __name__ == "__main__":
    address_figure()
    branch_figure()
    reuse_figure()
    erc6492_figure()
    rehash_figure()
