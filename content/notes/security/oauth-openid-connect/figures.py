"""Generate the cover diagram of the OAuth 2.0 / OIDC note as a hand-written SVG (stdlib only).

concept_figure(): where each token stops. The ID Token is addressed to the
client and stops inside it; the access token passes through the client to the
resource server. The bottom row repeats lab case (d): the quiz app carries
alice's tokens to the photo app, where the access token logs in and the
ID Token is rejected by aud.

Run: python3 content/notes/security/oauth-openid-connect/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE = "#d4a24c"
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
        mid = {RED: "arrowR", SUB: "arrowS", OCHRE: "arrowO"}.get(color, "arrowA")
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
        for i, c in (("arrowA", ACCENT), ("arrowR", RED), ("arrowS", SUB), ("arrowO", OCHRE))) + '</defs>')


def concept_figure():
    f = Svg(960, 540, "ID Token と access token の宛先")
    f.parts.insert(2, markers())

    # Top: authorization server, client (quiz app), resource server.
    f.box(20, 40, 170, 250, FILL, SUB, sw=3)
    f.text(105, 155, "authorization", 24)
    f.text(105, 187, "server", 24)
    f.box(290, 40, 330, 250, "#ffffff", ACCENT, sw=3, dash="10 7", rx=14)
    f.text(455, 80, "client（クイズアプリ）", 24, weight="normal")
    f.box(720, 40, 220, 250, PALE, ACCENT, sw=3)
    f.text(830, 155, "resource", 24)
    f.text(830, 187, "server", 24)

    # ID Token: addressed to the client, it stops inside the client.
    f.text(400, 138, "ID Token", 24)
    f.arrow(190, 160, 520, 160, ACCENT, sw=6)
    f.line(532, 136, 532, 184, ACCENT, sw=6)
    # access token: the client only carries it to the resource server.
    f.text(400, 238, "access token", 24)
    f.arrow(190, 260, 712, 260, OCHRE, sw=6)

    # Bottom: lab case (d), the quiz app takes alice's tokens to the photo app.
    f.text(20, 345, "クイズアプリが写真アプリに持ち込むと", 24, SUB, anchor="start")
    f.box(590, 370, 350, 150, FILL, SUB, sw=3)
    f.text(765, 404, "写真アプリ", 24, weight="normal")
    f.text(310, 450, "access token", 24, anchor="end")
    f.arrow(325, 442, 700, 442, OCHRE, sw=6)
    f.text(820, 450, "ログイン成功", 24, RED)
    f.text(310, 502, "ID Token", 24, anchor="end")
    f.arrow(325, 494, 560, 494, ACCENT, sw=6, dash="10 8")
    f.cross(588, 494, 14, SUB)
    f.text(780, 502, "aud で拒否", 24, SUB)

    f.save(HERE / "images" / "oauth-openid-connect_concept.svg")


if __name__ == "__main__":
    concept_figure()
