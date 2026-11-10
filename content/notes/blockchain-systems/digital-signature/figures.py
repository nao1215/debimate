"""Generate the cover diagram of the Digital Signature note as a hand-written SVG.

Containment: the private key (ochre) stays inside the signer's frame. Only the
message, the signature and the public key (blue) straddle the gap between
the signer's frame and the verifier's frame, and the verifier uses only
these three.

Run: python3 content/notes/blockchain-systems/digital-signature/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
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
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '<marker id="arrowred" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def circle(self, cx, cy, r, fill, stroke, sw=3, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def box(self, x, y, w, h, fill, stroke, sw=3, rx=14):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=4):
        m = "arrowred" if color == RED else "arrow"
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{m})"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "秘密鍵は署名する側の枠を出ず、枠を越えるのは公開してよい 3 つだけ")

    # Two frames: the signer and the verifier.
    f.box(30, 30, 450, 440, "none", SUB, sw=3, rx=18)
    f.box(520, 30, 410, 440, "none", SUB, sw=3, rx=18)
    f.text(200, 78, "署名する側", 28, weight="normal")
    f.text(800, 78, "検証する側", 28, weight="normal")

    # The private key lives inside the signer's frame only.
    f.box(60, 225, 190, 74, OCHRE, OCHRE, rx=12)
    f.text(155, 272, "秘密鍵", 28, INK, weight="normal")
    f.text(155, 340, "枠の外に出ない", 24, INK)

    # The three public items straddle both frames.
    pills = [("メッセージ", 110), ("署名", 225), ("公開鍵", 380)]
    for name, y in pills:
        f.box(390, y, 220, 74, PALE, ACCENT, sw=3, rx=37)
        f.text(500, y + 47, name, 28)
    f.arrow(250, 262, 382, 262)                  # private key -> signature
    f.arrow(230, 299, 384, 400)                  # key pair -> public key
    f.arrow(440, 184, 440, 217)                  # message -> signature

    # The verifier uses only the three public items.
    f.box(700, 200, 200, 124, FILL, SUB, rx=12)
    f.text(800, 252, "検証", 28, weight="normal")
    f.text(800, 292, "合格 / 不合格", 24, SUB)
    for _, y in pills:
        f.arrow(618, y + 37, 692, 262 + (y + 37 - 262) * 0.3)

    f.text(480, 515, "枠を越えるのは公開してよい 3 つだけ", 26, SUB)
    f.save(HERE / "images" / "digital-signature_concept.svg")


def nonce_reuse_figure():
    f = Svg(960, 540, "同じ nonce で作った 2 つの署名から秘密鍵が求まる")
    f.text(480, 56, "同じ nonce k を 2 回使った 2 つの署名", 28)
    # Two signatures share r (ochre) because k was reused.
    for i, y in enumerate((110, 290)):
        n = "₁₂"[i]
        f.box(40, y, 330, 140, PALE, ACCENT, rx=14)
        f.text(205, y + 44, f"署名 {i + 1}", 26)
        f.box(70, y + 66, 110, 52, OCHRE_PALE, OCHRE, rx=10)
        f.text(125, y + 101, "r", 26)
        f.text(270, y + 101, f"s{n}（z{n} に対して）", 24)
    f.text(205, 480, "r は k だけで決まるので重なる", 24, SUB)
    # Solve k, then d.
    f.box(430, 150, 480, 100, FILL, SUB, rx=12)
    f.text(670, 192, "k = (z₁ − z₂) / (s₁ − s₂)", 26)
    f.text(670, 228, "公開された値だけで計算できる", 24, SUB)
    f.box(430, 320, 480, 100, RED_PALE, RED, rx=12)
    f.text(670, 362, "秘密鍵 d = (s₁·k − z₁) / r", 26)
    f.text(670, 398, "誰でも正当な署名を作れる", 24, SUB)
    f.arrow(376, 180, 422, 195)
    f.arrow(376, 360, 422, 215)
    f.arrow(670, 256, 670, 312)
    f.text(670, 480, "計算は全て曲線の位数 n を法とする", 24, SUB)
    f.save(HERE / "images" / "digital-signature_nonce_reuse.svg")


def sighash_figure():
    f = Svg(960, 540, "sighash type で署名の範囲に入る入力と出力が変わる")
    panels = [(20, "通常の指定（ALL）", False), (500, "ALL | ANYONECANPAY", True)]
    for x0, title, narrow in panels:
        f.box(x0, 30, 440, 420, "none", SUB, sw=3, rx=18)
        f.text(x0 + 220, 76, title, 26)
        f.text(x0 + 110, 124, "入力", 24, SUB)
        f.text(x0 + 330, 124, "出力", 24, SUB)
        inputs = [("自分の入力", True), ("他の入力", not narrow), ("他の入力", not narrow)]
        for j, (name, covered) in enumerate(inputs):
            y = 150 + j * 92
            if covered:
                f.box(x0 + 25, y, 170, 70, PALE, ACCENT, rx=12)
                f.text(x0 + 110, y + 45, name, 24)
            else:
                f.parts.append(
                    f'<rect x="{x0 + 25}" y="{y}" width="170" height="70" rx="12" '
                    f'fill="{FILL}" stroke="{SUB}" stroke-width="3" stroke-dasharray="8 6"/>')
                f.text(x0 + 110, y + 45, "後から足せる", 24, SUB)
        for j in range(2):
            y = 196 + j * 92
            f.box(x0 + 245, y, 170, 70, PALE, ACCENT, rx=12)
            f.text(x0 + 330, y + 45, f"出力 {j + 1}", 24)
    f.box(270, 478, 34, 34, PALE, ACCENT, rx=6)
    f.text(316, 504, "署名の範囲（書き換えると検証が落ちる）", 24, anchor="start")
    f.save(HERE / "images" / "digital-signature_sighash.svg")


if __name__ == "__main__":
    concept_figure()
    nonce_reuse_figure()
    sighash_figure()
