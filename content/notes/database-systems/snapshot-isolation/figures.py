"""Generate the cover diagram of the snapshot isolation note as a hand-written SVG.

Time runs from left to right. The two middle lanes are the records x and y,
each split into the version every transaction can read (50) and the version
written later. T1 and T2 read both records at their own Start-Timestamp
(vertical lines) and see 50. T1 writes x and T2 writes y; the writes do not
overlap, so first-committer-wins lets both commit (write skew).

Run: python3 content/notes/database-systems/snapshot-isolation/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent

INK, SUB, ACCENT = "#1f1f1f", "#666666", "#7aa6c2"
RED = "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>' + ''.join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("blue", ACCENT), ("ochre", OCHRE))) + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}"{o} stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=5, arrow=False, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def dot(self, cx, cy, r, color):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


L, R = 130, 900          # time axis
S1, C1 = 200, 540        # T1: Start-Timestamp and commit
S2, C2 = 280, 740        # T2: Start-Timestamp and commit
XY, YY, LH = 150, 235, 60  # lanes of record x and record y


# The 50 version is shared by both; the -50 version takes the writer's color.
def lane(f, y, name, commit, fill, stroke):
    f.text(L - 40, y + LH / 2 + 10, name, 30, weight="normal")
    f.box(L, y, commit - L, LH, FILL, SUB, sw=2.5, rx=4)
    f.text((L + commit) / 2 + 40, y + LH / 2 + 9, "50", 26)
    f.box(commit, y, R - commit, LH, fill, stroke, sw=2.5, rx=4)
    f.text((commit + R) / 2, y + LH / 2 + 9, "-50", 26)


def band(f, y, start, commit, name, fill, stroke):
    f.box(start, y, commit - start, 50, fill, stroke, sw=2.5, rx=8)
    f.text(start + 40, y + 34, name, 26, weight="normal")


def concept_figure():
    f = Svg(960, 540, "write skew: 同じ時点を読み、別々のレコードを書く 2 本")
    f.text(R, 75, "時間 →", 24, SUB, anchor="end")
    lane(f, XY, "x", C1, PALE, ACCENT)
    lane(f, YY, "y", C2, OCHRE_PALE, OCHRE)
    band(f, 40, S1, C1, "T1", PALE, ACCENT)
    band(f, 355, S2, C2, "T2", OCHRE_PALE, OCHRE)
    # Start-Timestamp: each transaction reads both records at this point.
    f.line(S1, 90, S1, YY + LH, ACCENT, sw=4, dash="8 7")
    f.line(S2, 355, S2, XY, OCHRE, sw=4, dash="8 7")
    for x, c in ((S1, ACCENT), (S2, OCHRE)):
        for y in (XY, YY):
            f.dot(x, y + LH / 2, 9, c)
    # Writes at commit: T1 -> x, T2 -> y. Different records, no overlap.
    f.line(C1, 90, C1, XY - 6, ACCENT, sw=6, arrow="blue")
    f.line(C2, 355, C2, YY + LH + 6, OCHRE, sw=6, arrow="ochre")
    f.text(480, 458, "縦線の時点で読むので、どちらも x = 50、y = 50 を見る", 24, SUB)
    # Only the verdict "-100" is red; the rest of the sentence stays black.
    f.parts.append(
        '<text x="480" y="506" font-size="26" font-weight="normal" text-anchor="middle" '
        f'style="fill:{INK}">書くレコードが違うので両方確定し、合計は '
        f'<tspan style="fill:{RED}">-100</tspan></text>')
    f.save(HERE / "images" / "snapshot-isolation_concept.svg")


if __name__ == "__main__":
    concept_figure()
