"""Generate the cover diagram of the transactional outbox note (stdlib only).

Left: a dual write. Only the DB write is inside the transaction, so the send
to the broker falls outside it (ochre, with a red cross). Right: the order row and the outbox row
are written in one transaction; the relay and the broker stay outside and send
the outbox row after the commit.

The second figure (order) draws the PostgreSQL 17 run described in the note:
the row of order A gets id 1 but commits 3 seconds later than the row of order B (id 2).

Run: python3 content/notes/distributed-systems/transactional-outbox/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


class Svg:
    def __init__(self, width, height, title, defs=""):
        markers = "".join(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for name, color in (("sub", SUB), ("accent", ACCENT), ("ochre", OCHRE)))
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<defs>{markers}{defs}</defs>',
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

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def cross(self, cx, cy, r, color, sw=5):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)

    def raw(self, s):
        self.parts.append(s)

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "二重書き込みと Transactional Outbox の違い")
    # Left: dual write.
    f.text(240, 46, "二重書き込み", 28, weight="normal")
    f.box(130, 74, 220, 60, PALE, ACCENT)
    f.text(240, 113, "アプリケーション", 24)
    f.box(20, 168, 230, 244, "none", ACCENT, sw=3, dash="10 7", rx=14)
    f.text(135, 398, "トランザクション", 24, SUB)
    f.box(42, 190, 186, 170, FILL, SUB)
    f.text(80, 226, "DB", 24, SUB)
    f.box(70, 272, 130, 74, PALE, ACCENT)
    f.text(135, 318, "注文", 26)
    f.line(160, 136, 152, 268, ACCENT, arrow="accent")
    f.box(290, 264, 160, 82, FILL, SUB)
    f.text(370, 314, "ブローカー", 24)
    f.line(310, 136, 362, 258, OCHRE, sw=5, arrow="ochre", dash="12 8")
    f.cross(337, 197, 12, RED, sw=6)
    f.text(240, 456, "送信だけが", 26, INK, weight="normal")
    f.text(240, 492, "トランザクションの外", 26, INK, weight="normal")

    f.line(480, 30, 480, 510, "#dddddd", sw=2)

    # Right: transactional outbox.
    f.text(730, 46, "Transactional Outbox", 28, weight="normal")
    f.box(620, 74, 220, 60, PALE, ACCENT)
    f.text(730, 113, "アプリケーション", 24)
    f.box(508, 168, 436, 224, "none", ACCENT, sw=3, dash="10 7", rx=14)
    f.text(650, 378, "1 つのトランザクション", 24, SUB)
    f.box(528, 184, 396, 160, FILL, SUB)
    f.text(566, 270, "DB", 24, SUB)
    f.box(610, 222, 140, 80, PALE, ACCENT)
    f.text(680, 271, "注文", 26)
    f.box(772, 222, 136, 80, PALE, ACCENT)
    f.text(840, 271, "outbox", 26)
    f.line(680, 136, 680, 218, ACCENT, arrow="accent")
    f.line(780, 136, 830, 218, ACCENT, arrow="accent")
    f.box(780, 410, 120, 66, FILL, SUB)
    f.text(840, 452, "relay", 24)
    f.box(560, 410, 160, 66, FILL, SUB)
    f.text(640, 452, "ブローカー", 24)
    f.line(840, 304, 840, 404, SUB, arrow="sub")
    f.line(778, 443, 726, 443, SUB, arrow="sub")
    f.text(726, 518, "commit の後で relay が送る", 24, SUB)
    f.save(HERE / "images" / "transactional-outbox_concept.svg")



def order_figure():
    """id order and commit order differ, so a relay reading by id sends B before A."""
    f = Svg(960, 540, "先に採番された A の行が、commit の遅れで B の後に発行される")
    x0, sec = 250, 160          # x of t = 0 and pixels per second
    lanes = {"tx A": 120, "tx B": 240, "relay": 390}
    for name, y in lanes.items():
        f.text(30, y + 8, name, 26, anchor="start")
        f.line(x0 - 20, y, 930, y, "#dddddd", sw=1.5)
    # tx A: INSERT id 1 at once, commit after 3 s.
    f.box(x0, 96, 3 * sec, 48, OCHRE_PALE, OCHRE, sw=2)
    f.text(x0 + 12, 128, "INSERT id 1", 24, anchor="start")
    f.text(x0 + 3 * sec + 12, 128, "COMMIT", 24, anchor="start")
    f.line(x0, 172, x0 + 3 * sec, 172, SUB, sw=1.5)
    f.text(x0 + 12, 198, "commit delayed 3 s", 22, SUB, anchor="start")
    # tx B: INSERT id 2 and commit soon after.
    bx = x0 + 0.3 * sec
    f.box(bx, 216, 0.5 * sec, 48, PALE, ACCENT, sw=2)
    f.text(bx - 8, 252, "INSERT id 2", 24, anchor="end")
    f.text(bx + 0.5 * sec + 12, 252, "COMMIT", 24, anchor="start")
    # relay reads twice: right after B commits, and after A commits.
    for t_read, sent in ((1.6, "sends 2 (B)"), (3.94, "sends 1 (A)")):
        x = x0 + t_read * sec
        f.line(x, 90, x, 360, SUB, sw=2, dash="6 6")
        f.box(x - 70, 366, 140, 48, FILL, SUB, sw=2)
        f.text(x, 398, "read", 24)
        f.text(x, 452, sent, 24)
    f.text(480, 515, "unsent rows are read in id order", 22, SUB)
    f.save(HERE / "images" / "transactional-outbox_order.svg")


if __name__ == "__main__":
    concept_figure()
    order_figure()
