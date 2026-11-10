"""Generate the cover diagram of the Parse, Don't Validate note as a hand-written SVG.

concept_figure() draws types as sets: the large region is every string and
the small region inside it is Email. parse moves a checked value into the
Email region; validate returns true but leaves the value in the string
region. The later processing lives inside the Email region.

Run: python3 content/notes/software-architecture/parse-dont-validate/figures.py
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
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
            '<marker id="arrowa" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker></defs>',
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

    def line(self, x1, y1, x2, y2, color=INK, sw=4, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def db(self, cx, top, w, h, fill, stroke):
        rx, ry = w / 2, 10
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def dot(f, cx, cy, fill, stroke, r=13):
    f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
                   f'stroke="{stroke}" stroke-width="3"/>')


def concept_figure():
    f = Svg(960, 540, "parse は値を Email の領域に移し、validate は string の領域に残す")

    # Every string.
    f.box(20, 30, 920, 480, FILL, SUB, sw=2.5, rx=28)
    f.text(50, 78, "string", 30, INK, "normal", "start")
    for x, y, s in ((90, 470, '""'), (300, 470, '"abc"'), (300, 130, '"x@"')):
        dot(f, x, y - 8, "#ffffff", SUB, r=8)
        f.text(x + 18, y, s, 24, SUB, anchor="start")

    # Email: a smaller region inside string.
    f.box(500, 100, 410, 380, PALE, ACCENT, sw=3.5, rx=24)
    f.text(530, 146, "Email", 30, INK, "normal", "start")
    f.box(580, 330, 300, 100, "#ffffff", INK, sw=3, rx=14)
    f.text(730, 390, "後段の処理", 26, weight="normal")

    # The input.
    dot(f, 110, 250, "#ffffff", INK)
    f.text(110, 216, '"a@b.jp"', 24)

    # parse: the value moves into the Email region.
    f.parts.append(
        f'<path d="M128,250 C260,250 420,220 610,222" fill="none" stroke="{ACCENT}" '
        'stroke-width="5" stroke-linecap="round" marker-end="url(#arrowa)"/>')
    f.text(330, 216, "parse", 26, INK, "normal")
    dot(f, 630, 222, ACCENT, INK)
    f.text(730, 230, "a@b.jp", 24, anchor="middle")
    f.line(630, 238, 630, 322, INK, 4, arrow=True)

    # validate: true, but the value stays a string.
    f.line(118, 266, 176, 344, OCHRE, 4, arrow=True)
    f.text(162, 306, "validate", 26, INK, "normal", "start")
    dot(f, 190, 362, OCHRE_PALE, OCHRE)
    f.text(214, 370, "true でも string のまま", 24, INK, anchor="start")

    f.save(HERE / "images" / "parse-dont-validate_concept.svg")


def couchdb_figure():
    """CVE-2017-12635: one user document with two roles keys, read two ways.
    The JSON is shortened (password and other fields omitted)."""
    f = Svg(960, 540, "重複した roles を、検査関数と本体が別々に読む")
    mono = "font-family:'DejaVu Sans Mono',monospace"

    def code(x, y, s):
        f.parts.append(f'<text x="{x}" y="{y}" font-size="26" style="{mono};fill:{INK}">'
                       f'{escape(s)}</text>')

    f.text(40, 50, "_users の文書（抜粋）", 24, SUB, anchor="start")
    f.box(40, 70, 440, 290, "#ffffff", SUB, sw=2.5)
    f.box(56, 182, 408, 56, OCHRE_PALE, OCHRE, sw=2, rx=6)
    f.box(56, 252, 408, 56, PALE, ACCENT, sw=2, rx=6)
    code(64, 116, "{")
    code(84, 160, '"name": "oper",')
    code(84, 220, '"roles": ["_admin"],')
    code(84, 290, '"roles": []')
    code(64, 340, "}")

    # Who reads which key.
    f.line(472, 280, 560, 280, ACCENT, sw=4)
    f.box(570, 236, 360, 92, PALE, ACCENT)
    f.text(750, 274, "検査関数（JavaScript）", 24)
    f.text(750, 310, "後の roles だけを見て通す", 24, SUB)
    f.line(472, 210, 560, 120, OCHRE, sw=4)
    f.box(570, 72, 360, 92, OCHRE_PALE, OCHRE)
    f.text(750, 110, "本体（Erlang）", 24)
    f.text(750, 146, "前の roles で権限を判定", 24, SUB)

    f.box(40, 420, 890, 76, "#ffffff", SUB, sw=2)
    f.text(485, 468, "検査を通った同じ文書で、管理者の役割を得られる", 26)
    f.save(HERE / "images" / "parse-dont-validate_couchdb.svg")


if __name__ == "__main__":
    concept_figure()
    couchdb_figure()
