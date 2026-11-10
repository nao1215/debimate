"""Generate the cover diagram of the transaction scope note as a hand-written SVG.

Time runs from left to right. The dashed frame is one transaction
(BEGIN to COMMIT), the blue band under it is the time the row lock is held,
and the ochre box is the wait for the payment API. In the wide scope (top) the
API wait sits inside the frame and stretches the lock; in the narrow scope
(bottom) the frame holds only the DB updates and the API is called after it.

Run: python3 content/notes/database-systems/transaction-scope/figures.py
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
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
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
        m = ' marker-end="url(#arrow)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def dot(self, cx, cy, r, color):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


STEP_H = 64


def step(f, x, w, y, label, external=False):
    if external:
        f.box(x, y, w, STEP_H, OCHRE_PALE, OCHRE, sw=2.5, rx=8)
        f.text(x + w / 2, y + STEP_H / 2 + 9, label, 24)
    else:
        f.box(x, y, w, STEP_H, PALE, ACCENT, sw=2.5, rx=8)
        f.text(x + w / 2, y + STEP_H / 2 + 9, label, 24)


def row(f, top, title, frame_end, lock_end):
    f.text(100, top + 62, title, 28, weight="normal")
    f.box(200, top, frame_end - 200, 104, "none", INK, sw=3, dash="10 7", rx=12)
    f.box(270, top + 122, lock_end - 270, 30, ACCENT, rx=4)


def concept_figure():
    f = Svg(960, 540, "トランザクションの範囲と行ロックを持つ時間")
    f.text(930, 40, "時間 →", 24, SUB, anchor="end")

    # Wide: the payment API wait is inside BEGIN..COMMIT.
    top = 70
    row(f, top, "広い範囲", 920, 920)
    step(f, 212, 120, top + 20, "引き当て")
    step(f, 344, 420, top + 20, "決済 API の応答待ち", external=True)
    step(f, 776, 132, top + 20, "注文作成")

    # Narrow: only the DB updates are inside; the API is called afterwards.
    top = 300
    row(f, top, "狭い範囲", 500, 500)
    step(f, 212, 120, top + 20, "引き当て")
    step(f, 344, 144, top + 20, "注文と依頼")
    step(f, 520, 400, top + 20, "決済 API の応答待ち", external=True)

    f.line(220, 510, 270, 510, INK, sw=3, dash="10 7")
    f.text(282, 518, "トランザクション", 24, SUB, anchor="start")
    f.box(540, 496, 50, 28, ACCENT, rx=4)
    f.text(602, 518, "行ロックを持つ時間", 24, SUB, anchor="start")
    f.save(HERE / "images" / "transaction-scope_concept.svg")


def lock_wait_figure():
    """The PostgreSQL 17.10 run in the note: A waits 5 s inside the transaction,
    B updates the same row 1 s after A and waits 4,006 ms for the row lock."""
    f = Svg(960, 540, "注文 A の応答待ちの間、注文 B がロック待ちで止まる時間")
    x0, sec = 180, 125

    def X(t):
        return x0 + t * sec

    # Order A: holds the row lock from its UPDATE to COMMIT.
    f.text(40, 132, "注文 A", 26, anchor="start")
    f.box(X(0), 92, 5 * sec, 64, PALE, ACCENT, sw=2.5, rx=8)
    f.text(X(2.5), 133, "決済の応答待ち（5 秒）", 24)
    f.text(X(0), 78, "UPDATE", 24, SUB)
    f.text(X(5), 78, "COMMIT", 24, SUB)
    f.box(X(0), 166, 5 * sec, 16, ACCENT, rx=4)
    f.text(X(5) + 14, 182, "行ロック", 24, SUB, anchor="start")

    # Order B: updates the same row one second later and waits for the lock.
    f.text(40, 322, "注文 B", 26, anchor="start")
    f.box(X(1), 282, 4 * sec, 64, OCHRE_PALE, OCHRE, sw=2.5, rx=8)
    f.text(X(3), 323, "ロック待ち 4,006 ms", 24)
    f.text(X(1), 268, "UPDATE", 24, SUB)
    f.dot(X(5), 314, 9, INK)
    f.text(X(5) + 18, 322, "更新が進む", 24, SUB, anchor="start")

    # pg_stat_activity three seconds after A's UPDATE.
    f.line(X(3), 200, X(3), 262, SUB, sw=3, dash="8 6")
    f.box(X(3) - 230, 372, 460, 76, "#ffffff", SUB, sw=2, rx=8)
    f.text(X(3), 402, "3 秒後: A は idle in transaction", 24)
    f.text(X(3), 436, "B は Lock で待つ", 24)
    f.line(X(3), 356, X(3), 370, SUB, sw=3, dash="8 6")

    # Time axis.
    f.line(X(0), 486, X(6), 486, SUB, sw=2)
    for t in range(7):
        f.line(X(t), 480, X(t), 492, SUB, sw=2)
        f.text(X(t), 522, f"{t} 秒", 24, SUB)
    f.save(HERE / "images" / "transaction-scope_lock_wait.svg")


if __name__ == "__main__":
    concept_figure()
    lock_wait_figure()
