"""Generate the SVG figures for the Capability-based Security note.

    python3 figures.py

Writes images/acl_vs_capability.svg and images/capability-based-security_concept.svg.
No third-party packages are needed.

concept_figure() draws the access matrix of the "アクセス行列の行と列" section
(rows are subjects, columns are objects). The ochre band is one column, which
becomes the ACL of SYSX/BILL. The blue band is one row, which becomes the
capability list (C-list) of the compiler.
"""

from pathlib import Path
from xml.sax.saxutils import escape

INK, SUB, LINE, FILL, ACCENT, DANGER = "#1f1f1f", "#666666", "#bdbdbd", "#f2f2f2", "#7aa6c2", "#e15759"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

W, H = 460, 420
COL_W, BOX_W, BOX_H, STEP = 230, 196, 52, 92
TOP = 70  # y of the first box


def text(x, y, s, size=15, color=INK, anchor="middle", weight="normal"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
        f'font-weight="{weight}">{escape(s)}</text>'
    )


def box(x, y, title, sub, stroke=INK, fill="#ffffff"):
    return [
        f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="3" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>',
        text(x + BOX_W / 2, y + 22, title, size=15),
        text(x + BOX_W / 2, y + 42, sub, size=13, color=SUB),
    ]


def arrow(x, y1, y2, label, color=INK):
    return [
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 8}" stroke="{color}" stroke-width="1.6"/>',
        f'<path d="M{x} {y2} L{x - 5} {y2 - 9} L{x + 5} {y2 - 9} Z" fill="{color}"/>',
        text(x + 10, (y1 + y2) / 2 + 5, label, size=13, color=color if color != INK else SUB,
             anchor="start"),
    ]


def column(col, title, subtitle, boxes, labels):
    x0 = col * COL_W + (COL_W - BOX_W) / 2
    out = [text(x0, 26, title, size=16, anchor="start", weight="normal"),
           text(x0, 48, subtitle, size=13, color=SUB, anchor="start")]
    for i, spec in enumerate(boxes):
        out += box(x0, TOP + i * STEP, **spec)
    ax = x0 + 28
    for i, spec in enumerate(labels):
        out += arrow(ax, TOP + i * STEP + BOX_H, TOP + (i + 1) * STEP, **spec)
    return out


def acl_vs_capability():
    parts = [f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    parts += column(
        0, "ACL 型", "誰が頼んだかで判断する",
        [dict(title="利用者", sub="BILL には書けない"),
         dict(title="コンパイラ", sub="SYSX に書ける"),
         dict(title="OS", sub="主体の名前で ACL を引く", fill=FILL),
         dict(title="SYSX/BILL", sub="課金情報が消える", stroke=DANGER)],
        [dict(label="名前 SYSX/BILL"), dict(label="open(名前)"), dict(label="許可", color=DANGER)],
    )
    parts.append(f'<line x1="{COL_W}" y1="12" x2="{COL_W}" y2="{H - 12}" stroke="{LINE}" stroke-width="1"/>')
    parts += column(
        1, "capability 型", "何を持っているかで判断する",
        [dict(title="利用者", sub="自分で debug.txt を開く"),
         dict(title="コンパイラ", sub="STAT の fd は自前"),
         dict(title="OS", sub="fd が指す先に書く", fill=FILL),
         dict(title="debug.txt", sub="BILL の fd は誰も渡さない", stroke=ACCENT)],
        [dict(label="fd を渡す"), dict(label="write(fd)"), dict(label="書き込み", color=ACCENT)],
    )
    body = "\n  ".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'font-family="{FONT}">\n  {body}\n</svg>\n')


PALE = "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
SUBJECTS = ["alice", "コンパイラ"]
OBJECTS = ["debug.txt", "STAT", "BILL"]
CELLS = [["読み書き", "なし", "なし"],
         ["なし", "書き込み", "書き込み"]]


def concept_figure():
    cw, x0, rhx = 150, 40, 180            # column width, left edge, row header width
    y0, hh, rh = 116, 64, 86               # top, header height, row height
    xs = [x0 + rhx + i * cw for i in range(len(OBJECTS))]
    ys = [y0 + hh + i * rh for i in range(len(SUBJECTS))]
    right, bottom = xs[-1] + cw, ys[-1] + rh
    t = lambda *a, **k: text(*a, **k)  # noqa: E731

    parts = [f'<rect width="960" height="540" fill="#ffffff"/>']
    # Column band: the column of BILL is the ACL attached to BILL.
    bx = xs[-1]
    band = f'x="{bx}" y="{y0 - 8}" width="{cw}" height="{bottom - y0 + 70}" rx="10"'
    parts.append(f'<rect {band} fill="{OCHRE_PALE}" stroke="none"/>')
    # Row band: the row of the compiler is the C-list the compiler holds.
    ry = ys[-1]
    parts.append(f'<rect x="{x0 - 8}" y="{ry}" width="{right - x0 + 60}" height="{rh}" rx="10" '
                 f'fill="{PALE}" stroke="{ACCENT}" stroke-width="5"/>')
    # The outline of the column goes over the row so both cuts show at BILL.
    parts.append(f'<rect {band} fill="none" stroke="{OCHRE}" stroke-width="5"/>')

    # Grid lines of the matrix.
    for x in xs + [right]:
        parts.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{bottom}" stroke="{LINE}" stroke-width="2"/>')
    for y in [y0 + hh] + ys[1:] + [bottom]:
        parts.append(f'<line x1="{x0}" y1="{y}" x2="{right}" y2="{y}" stroke="{LINE}" stroke-width="2"/>')

    parts.append(t(x0, 58, "アクセス行列", size=28, anchor="start", weight="normal"))
    parts.append(t(x0 + 190, 58, "行は主体、列は対象", size=24, color=SUB, anchor="start"))
    parts.append(t(x0 + rhx / 2, y0 + 40, "主体＼対象", size=24, color=SUB))
    for x, name in zip(xs, OBJECTS):
        parts.append(t(x + cw / 2, y0 + 42, name, size=26, weight="normal"))
    for y, name, row in zip(ys, SUBJECTS, CELLS):
        parts.append(t(x0 + rhx / 2, y + rh / 2 + 9, name, size=26, weight="normal"))
        for x, cell in zip(xs, row):
            parts.append(t(x + cw / 2, y + rh / 2 + 9, cell, size=24,
                           color=SUB if cell == "なし" else INK))

    # Labels of the two cuts.
    parts.append(t(bx + cw / 2, bottom + 104, "列 = ACL", size=28, weight="normal"))
    parts.append(t(bx + cw / 2, bottom + 142, "対象が持つ", size=24, color=SUB))
    lx = right + 64
    parts.append(t(lx, ry + 38, "行 = capability", size=28, anchor="start", weight="normal"))
    parts.append(t(lx, ry + 74, "主体が持つ", size=24, color=SUB, anchor="start"))

    body = "\n  ".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" '
            f'font-family="{FONT}" role="img"><title>アクセス行列の列と行</title>\n  {body}\n</svg>\n')


def main():
    out = Path(__file__).with_name("images")
    out.mkdir(exist_ok=True)
    (out / "acl_vs_capability.svg").write_text(acl_vs_capability(), encoding="utf-8")
    (out / "capability-based-security_concept.svg").write_text(concept_figure(), encoding="utf-8")


if __name__ == "__main__":
    main()
