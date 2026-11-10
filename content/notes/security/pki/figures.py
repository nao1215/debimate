"""Generate the cover diagram of the PKI note as a hand-written SVG (stdlib only).

concept_figure(): the trust store on the device holds only the Root CA; the
intermediate and the server certificate come from the server and are tied to
it by signatures. Ochre marks the name, period and purpose checks; red marks
only the point where using the leaf as a CA is rejected.

Run: python3 content/notes/security/pki/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")

    def arrow(self, x1, y1, x2, y2, color, sw=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        mid = {RED: "arrowR", SUB: "arrowS"}.get(color, "arrowA")
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d} marker-end="url(#{mid})"/>')

    def cross(self, cx, cy, r, color, sw=6):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)


def markers():
    return ('<defs>' + ''.join(
        f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" '
        f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
        for i, c in (("arrowA", ACCENT), ("arrowR", RED), ("arrowS", SUB))) + '</defs>')


def concept_figure():
    f = Svg(960, 540, "trust store から証明書をたどる検証と、拒否される箇所")
    f.parts.insert(2, markers())
    top, h = 170, 200

    # Left: the trust store on the device holds only the Root CA.
    f.box(20, top, 250, h, "none", ACCENT, sw=3, dash="10 7", rx=14)
    f.text(145, top - 16, "trust store（端末）", 24, SUB)
    f.box(50, 230, 190, 84, PALE, ACCENT, sw=3)
    f.text(145, 281, "Root CA", 26, weight="normal")

    # Right: the server sends the intermediate and its own certificate.
    f.box(310, top, 630, h, FILL, "none", sw=0, rx=14)
    f.text(332, top + h - 20, "サーバーが送る", 24, SUB, anchor="start")
    f.box(340, 230, 210, 84, "#ffffff", ACCENT, sw=3)
    f.text(445, 281, "Intermediate", 26)
    f.box(660, 210, 260, 124, "#ffffff", ACCENT, sw=3)
    f.text(790, 260, "example.test", 26, weight="normal")
    f.text(790, 300, "サーバー証明書", 24, SUB)

    f.arrow(240, 272, 334, 272, ACCENT, sw=5)
    f.text(287, 258, "署名", 24, SUB)
    f.arrow(550, 272, 654, 272, ACCENT, sw=5)
    f.text(602, 258, "署名", 24, SUB)

    # Up: using the leaf as a CA is rejected (CA:FALSE).
    f.box(660, 30, 260, 70, "#ffffff", SUB, sw=3, dash="8 6")
    f.text(790, 74, "evil.example.test", 24)
    f.arrow(790, 208, 790, 108, SUB, sw=5, dash="10 8")
    f.cross(790, 140, 15, RED)
    f.text(640, 150, "CA ではない", 24, RED, anchor="end")

    # Down: checks against the name, the period and the purpose.
    for i, label in enumerate(("名前", "期限", "用途")):
        x = 666 + i * 88
        f.box(x, 410, 76, 52, OCHRE_PALE, OCHRE, sw=3)
        f.text(x + 38, 445, label, 24)
        f.line(x + 38, 334, x + 38, 408, OCHRE, sw=3, dash="4 6")
    f.text(640, 445, "外れたら拒否", 24, SUB, anchor="end")

    f.save(HERE / "images" / "pki_concept.svg")


def name_constraints_figure():
    """permitted;DNS:example.test on the intermediate, as in the OpenSSL check."""
    f = Svg(960, 540, "nameConstraints で、Intermediate CA が発行できる名前の範囲を絞る")
    f.parts.append(markers())
    f.box(380, 24, 200, 64, PALE, ACCENT)
    f.text(480, 65, "Root CA", 26)
    f.arrow(480, 92, 480, 132, SUB)
    f.box(300, 138, 360, 92, PALE, ACCENT)
    f.text(480, 176, "Intermediate CA", 26)
    f.text(480, 212, "permitted;DNS:example.test", 24, SUB)

    # The permitted name space.
    f.box(40, 290, 520, 220, FILL, SUB, sw=2.5, dash="10 7", rx=16)
    f.text(64, 330, "example.test の下", 24, SUB, anchor="start")
    f.box(110, 380, 360, 76, "#ffffff", ACCENT)
    f.text(290, 427, "www.example.test", 26)
    f.box(620, 380, 300, 76, "#ffffff", SUB)
    f.text(770, 427, "www.other.test", 26)
    f.cross(905, 372, 16, RED)
    f.text(770, 492, "error 47 で拒否", 24, SUB)
    f.arrow(420, 236, 300, 372, SUB)
    f.arrow(560, 236, 740, 372, SUB)
    f.save(HERE / "images" / "pki_name_constraints.svg")


def lifecycle_figure():
    """Where ACME, CT and revocation sit in the life of one certificate."""
    f = Svg(960, 540, "1 枚の証明書の発行から有効期限までと、ACME・CT・失効の位置")
    x0, x_rev, x1 = 90, 560, 870
    y, h = 220, 70
    f.box(x0, y, x_rev - x0, h, PALE, ACCENT, rx=8)
    f.text((x0 + x_rev) / 2, y + 45, "有効", 26)
    f.box(x_rev, y, x1 - x_rev, h, OCHRE_PALE, OCHRE, rx=8)
    f.text((x_rev + x1) / 2, y + 45, "期限は残るが失効済み", 24)

    # Above the bar.
    f.line(x0, 120, x0, y - 4, SUB, sw=2.5)
    f.text(x0 - 10, 72, "発行", 26, anchor="start")
    f.text(x0 - 10, 106, "ACME で自動化", 24, SUB, anchor="start")
    f.line(430, 150, 430, y - 4, SUB, sw=2.5)
    f.text(430, 106, "鍵の漏洩や", 24)
    f.text(430, 138, "誤発行が分かる", 24)
    f.line(x1, 120, x1, y - 4, SUB, sw=2.5)
    f.text(x1 + 10, 106, "有効期限", 26, anchor="end")

    # Below the bar.
    f.line(x0, y + h + 4, x0, 360, SUB, sw=2.5)
    f.text(x0 - 10, 392, "発行時に CT ログへ記録（SCT）", 24, anchor="start")
    f.text(x0 - 10, 424, "誤発行を第三者が観測できる", 24, SUB, anchor="start")
    f.line(x_rev, y + h + 4, x_rev, 360, SUB, sw=2.5)
    f.text(x_rev + 20, 392, "失効（CRL / OCSP）", 24, anchor="start")
    f.text(x_rev + 20, 424, "取れない時に止めるかは", 24, SUB, anchor="start")
    f.text(x_rev + 20, 456, "クライアント次第", 24, SUB, anchor="start")
    f.text(480, 520, "時間 →", 24, SUB)
    f.save(HERE / "images" / "pki_lifecycle.svg")


if __name__ == "__main__":
    concept_figure()
    name_constraints_figure()
    lifecycle_figure()
