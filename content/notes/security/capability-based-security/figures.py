"""Generate the SVG figures for the Capability-based Security note.

    python3 figures.py

Writes images/acl_vs_capability.svg. No third-party packages are needed.
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
    out = [text(x0, 26, title, size=16, anchor="start", weight="bold"),
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


def main():
    out = Path(__file__).with_name("images")
    out.mkdir(exist_ok=True)
    (out / "acl_vs_capability.svg").write_text(acl_vs_capability(), encoding="utf-8")


if __name__ == "__main__":
    main()
