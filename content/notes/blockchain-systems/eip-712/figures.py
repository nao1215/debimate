"""Generate the figures of the EIP-712 note.

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


def concept_figure():
    """The signed digest = 0x1901 | domain separator | hashStruct(message)."""
    s = Svg("署名する 32 バイトは 0x1901、domain separator、メッセージのハッシュを繋いだもののハッシュ")
    # keccak256 is taken over the whole row: 2 + 32 + 32 = 66 bytes.
    s.raw(f'<path d="M40,84 V70 H920 V84" fill="none" stroke="{SUB}" stroke-width="2"/>')
    s.text(480, 52, "この列全体の keccak256 ＝ 鍵が署名する 32 バイト", 26)

    y0, bh = 92, 96
    s.box(40, y0, 90, bh, SUB, GRAY_PALE)
    s.text(85, y0 + 58, "1901", 26, cls="mono")
    s.box(130, y0, 390, bh, OCHRE, OCHRE_PALE)
    s.text(325, y0 + 44, "domain separator", 28)
    s.text(325, y0 + 78, "署名の領域（どこ向けか）", 22, cls="sub")
    s.box(520, y0, 400, bh, BLUE, BLUE_PALE)
    s.text(720, y0 + 44, "hashStruct(message)", 28)
    s.text(720, y0 + 78, "メッセージのハッシュ（中身）", 22, cls="sub")

    top = 238
    s.box(150, top, 350, 220, OCHRE, "#ffffff", sw=2)
    for i, f in enumerate(["name", "version", "chainId", "verifyingContract"]):
        s.text(176, top + 44 + 48 * i, f, 26, anchor="start", cls="mono")
    s.line(325, y0 + bh, 325, top - 4)
    # One changed field: the same signature no longer matches.
    s.box(410, top + 115, 76, 40, RED, RED_PALE, sw=2, rx=6)
    s.text(448, top + 144, "≠", 28, fill=RED)

    s.box(530, top, 390, 220, BLUE, "#ffffff", sw=2)
    s.text(556, top + 44, "型の名前と項目名", 24, anchor="start")
    s.text(556, top + 80, "Permit(address owner,…)", 24, anchor="start", cls="sub mono")
    for i, f in enumerate(["owner / spender", "value / nonce / deadline"]):
        s.text(556, top + 140 + 46 * i, f, 24, anchor="start", cls="mono")
    s.line(720, y0 + bh, 720, top - 4)

    s.text(480, 510, "chainId やコントラクトが違う → 別の 32 バイト → 署名が通らない", 24, cls="sub")
    s.save("eip-712_concept.webp")


def prefix_figure():
    """The first byte of what gets signed: transactions vs EIP-191 data."""
    s = Svg("署名するバイト列の先頭 1 バイト。型付きトランザクションは 0x01〜0x04、旧来のトランザクションは 0xc0 以上、EIP-191 は 0x19", h=400)
    x0, x1, y = 60, 900, 190

    def xpos(b):
        return x0 + (x1 - x0) * b / 256

    s.text(480, 50, "署名するバイト列の先頭 1 バイト（0x00〜0xff）", 26)
    s.box(x0, y, x1 - x0, 50, GRAY, GRAY_PALE, sw=2, rx=4)
    # Typed transactions 0x01..0x04 (blue), EIP-191 0x19 (ochre), legacy RLP list 0xc0..0xff (blue).
    s.box(xpos(1), y, xpos(5) - xpos(1), 50, BLUE, BLUE_PALE, sw=2, rx=2)
    s.box(xpos(0x19), y, xpos(0x1a) - xpos(0x19) + 4, 50, OCHRE, OCHRE_PALE, sw=2, rx=2)
    s.box(xpos(0xc0), y, x1 - xpos(0xc0), 50, BLUE, BLUE_PALE, sw=2, rx=2)
    for b, label in [(0, "0x00"), (0x80, "0x80"), (0xc0, "0xc0"), (0x100, "0xff")]:
        s.text(xpos(b), y + 80, label, 22, cls="sub mono")

    s.line(xpos(3), y - 70, xpos(3), y - 6)
    s.text(xpos(3) - 10, y - 82, "型付きトランザクションの種類 0x01〜0x04", 22, anchor="start")
    s.line(xpos(0x19) + 2, y + 110, xpos(0x19) + 2, y + 56)
    s.text(xpos(0x19) - 10, y + 140, "0x19：EIP-191（personal_sign・EIP-712）", 22, anchor="start", fill="#8a6418")
    s.text(x1, y - 22, "旧来のトランザクション（RLP のリスト）", 22, anchor="end")
    s.text(480, 380, "トランザクションと EIP-191 のデータは、先頭の 1 バイトで重ならない", 22, cls="sub")
    s.save("eip-712_prefix.webp")


def replay_figure():
    """One permit signature handed to three tokens (experiment 2 of lab/run.py)."""
    s = Svg("同じ permit の署名を 3 つのトークンに渡すと、ドメインが違う 2 つでは別人のアドレスが復元される")
    s.box(30, 200, 230, 140, BLUE, BLUE_PALE)
    s.text(145, 255, "1 つの署名", 28)
    s.text(145, 298, "owner 0x7099…", 24, cls="sub mono")

    rows = [
        (40, BLUE, BLUE_PALE, "chain ID 31337 のトークン", "署名したドメイン", "0x7099…（owner）を復元"),
        (200, GRAY, GRAY_PALE, "chain ID 31338 の同じアドレス", "chainId が違う", "0x099c… を復元"),
        (360, GRAY, GRAY_PALE, "chain ID 31337 の別のトークン", "verifyingContract が違う", "0x0eEA… を復元"),
    ]
    for y, st, fi, name, why, rec in rows:
        s.line(260, 270, 340, y + 70)
        s.box(345, y, 440, 140, st, fi)
        s.text(370, y + 42, name, 26, anchor="start")
        s.text(370, y + 80, why, 24, anchor="start", cls="sub")
        s.text(370, y + 118, rec, 24, anchor="start")
    s.text(865, 100, "署名者", 24)
    s.text(865, 134, "＝ owner", 24)
    s.raw(f'<path d="M795,250 H812 V450 H795" fill="none" stroke="{SUB}" stroke-width="2"/>')
    s.box(822, 318, 120, 64, RED, RED_PALE, sw=2, rx=6)
    s.text(882, 360, "revert", 26)
    s.text(480, 528, "owner と違う：同じ署名が別人の署名として読まれる", 24, cls="sub")
    s.save("eip-712_replay.webp")


def scam_figure():
    """A drainer Permit: the domain is genuine, the spender and amount are the attacker's."""
    s = Svg("詐欺の Permit。ドメインは本物のトークンのままで、spender・value・deadline が攻撃者の都合に差し替わっている。サイトの URL は署名に入らない", h=510)
    # The phishing site on the left.
    s.box(30, 150, 230, 180, GRAY, GRAY_PALE, dash=True)
    s.text(145, 210, "詐欺サイト", 26)
    s.text(145, 248, "URL は画面に出ても", 20, cls="sub")
    s.text(145, 278, "署名には入らない", 20, cls="sub")
    s.line(260, 240, 330, 240)

    # The wallet's signing screen.
    s.box(340, 20, 590, 435, SUB, "#ffffff", sw=2)
    s.text(365, 62, "署名するメッセージの項目（Permit の例）", 24, anchor="start", cls="sub")
    rows = [
        ("verifyingContract", "本物のトークン", False),
        ("chainId", "操作するつもりのチェーン", False),
        ("spender", "攻撃者のアドレス", True),
        ("value", "最大値（無制限）", True),
        ("deadline", "遠い将来", True),
    ]
    for i, (k, v, bad) in enumerate(rows):
        y = 90 + 70 * i
        s.box(360, y, 550, 56, RED if bad else OCHRE, RED_PALE if bad else OCHRE_PALE, sw=2, rx=6)
        s.text(380, y + 37, k, 22, anchor="start", cls="mono")
        s.text(890, y + 37, v, 22, anchor="end", fill=RED if bad else None)
    s.text(635, 492, "黄土色：本物のまま　赤：差し替えられた項目", 20, cls="sub")
    s.save("eip-712_scam.webp")


def signature_figure():
    """A 65-byte signature split into r, s and v (as sliced in lab/run.py)."""
    s = Svg("65 バイトの署名は、r（32 バイト）、s（32 バイト）、v（1 バイト）の順に並ぶ", h=300)
    y = 90
    for x, w, name, sub, st, fi in [(40, 400, "r", "32 バイト", BLUE, BLUE_PALE),
                                    (440, 400, "s", "32 バイト", BLUE, BLUE_PALE),
                                    (840, 80, "v", "1 バイト", OCHRE, OCHRE_PALE)]:
        s.box(x, y, w, 80, st, fi, sw=2, rx=4)
        s.text(x + w / 2, y + 50, name, 28, cls="mono")
        s.text(x + w / 2, y + 118, sub, 22, cls="sub")
    s.text(480, 50, "65 バイトの署名", 24)
    s.text(480, 268, "v は、署名から求まる公開鍵の 2 つの候補のどちらかを選ぶ", 22, cls="sub")
    s.save("eip-712_sig.webp")


if __name__ == "__main__":
    concept_figure()
    prefix_figure()
    replay_figure()
    scam_figure()
    signature_figure()
