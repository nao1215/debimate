"""Generate the SVG figures for the Byzantine Fault Tolerance note.

Run: python3 figures.py  (standard library only)
"""

import pathlib
from xml.sax.saxutils import escape

OUT = pathlib.Path(__file__).parent / "images"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
LIGHT = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def text(x, y, s, size=15, fill=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{fill}">{escape(s)}</text>')


def node(x, y, label, stroke=INK, dash=False, fill="#ffffff", r=24):
    d = ' stroke-dasharray="5 4"' if dash else ""
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="2"{d}/>' + text(x, y + 6, label, 17, stroke))


def arrow(x1, y1, x2, y2, color=INK, marker="a"):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="2" marker-end="url(#{marker})"/>')


def write_svg(name, width, height, body):
    OUT.mkdir(exist_ok=True)
    markers = "".join(
        f'<marker id="{mid}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
        for mid, color in (("a", INK), ("r", RED)))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" font-family="{FONT}">'
           f'<defs>{markers}</defs>'
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>{"".join(body)}</svg>\n')
    (OUT / name).write_text(svg, encoding="utf-8")
    print(f"wrote {OUT / name}")


def crash_vs_byzantine():
    """Left: A stops. Right: A tells B commit and C abort."""
    body = []
    for ox, title in ((0, "Crash fault（停止）"), (360, "Byzantine fault（二枚舌）")):
        body.append(f'<rect x="{ox + 10}" y="10" width="340" height="250" rx="3" '
                    f'fill="{LIGHT}" stroke="{SUB}" stroke-width="1"/>')
        body.append(text(ox + 180, 40, title, 18))
    # Crash: A is silent.
    body.append(node(90, 140, "A", SUB, dash=True))
    body.append(text(90, 195, "何も送らない", 15, SUB))
    body.append(node(270, 90, "B"))
    body.append(node(270, 190, "C"))
    body.append(text(180, 240, "B と C に届く値は食い違わない", 15, SUB))
    # Byzantine: A equivocates.
    body.append(node(450, 140, "A", RED))
    body.append(node(630, 90, "B"))
    body.append(node(630, 190, "C"))
    body.append(arrow(474, 130, 604, 98, RED, "r"))
    body.append(arrow(474, 150, 604, 182, RED, "r"))
    body.append(text(535, 100, "commit", 16, RED))
    body.append(text(535, 196, "abort", 16, RED))
    body.append(text(540, 240, "B と C は違う値を正しいと信じる", 15, SUB))
    write_svg("bft_crash_vs_byzantine.svg", 720, 270, body)


def quorum_overlap():
    """Two quorums of size n - f. Their overlap must keep an honest node."""
    body = []
    panels = (
        (0, "n = 3, f = 1, quorum = 2", ["B", "A", "C"], (0, 1), (1, 2),
         "重なりは嘘つきの A だけ"),
        (360, "n = 4, f = 1, quorum = 3", ["B", "A", "C", "D"], (0, 2), (1, 3),
         "重なりは 2 台。A が嘘つきでも C が残る"),
    )
    for ox, title, names, q1, q2, note in panels:
        body.append(f'<rect x="{ox + 10}" y="10" width="340" height="270" rx="3" '
                    f'fill="{LIGHT}" stroke="{SUB}" stroke-width="1"/>')
        body.append(text(ox + 180, 40, title, 18))
        gap = 280 / len(names)
        xs = [ox + 40 + gap * (i + 0.5) for i in range(len(names))]
        y = 150
        # Q1 above, Q2 below (solid / dashed brackets).
        for (lo, hi), label, by, dash in ((q1, "Q1", 95, ""), (q2, "Q2", 205, ' stroke-dasharray="6 4"')):
            x1, x2 = xs[lo] - 30, xs[hi] + 30
            tick = 10 if by < y else -10
            body.append(f'<path d="M{x1},{by + tick} L{x1},{by} L{x2},{by} L{x2},{by + tick}" '
                        f'fill="none" stroke="{ACCENT}" stroke-width="3"{dash}/>')
            body.append(text((x1 + x2) / 2, by - 8 if by < y else by + 22, label, 15, INK))
        for i, (x, name) in enumerate(zip(xs, names)):
            faulty = name == "A"
            body.append(node(x, y, name, RED if faulty else INK))
        body.append(text(ox + 180, 262, note, 15, SUB))
    write_svg("bft_quorum_overlap.svg", 720, 290, body)


if __name__ == "__main__":
    crash_vs_byzantine()
    quorum_overlap()
