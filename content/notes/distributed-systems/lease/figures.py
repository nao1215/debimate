"""Generate the cover diagram of the lease note as a hand-written SVG.

concept_figure() puts Node A, the storage and Node B on one time axis.
A holds the lease with fencing token 33, stops in a GC, and its lease
expires. B gets the next lease with token 34 and writes. A's delayed write
with token 33 reaches the storage last and is rejected, the same order as
lab/run.py replays. The time scale is illustrative, not measured.

Run: python3 content/notes/distributed-systems/lease/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

X0, X1, T_MAX = 180, 930, 20


def tx(t):
    return X0 + (X1 - X0) * t / T_MAX


def concept_figure():
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("失効に気付かない Node A の遅れた書き込みを、ストレージが token の大小で拒否する")}'
        '</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} '
        f'.red{{fill:{RED}}}</style>',
        '<defs>'
        + "".join(
            f'<marker id="{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" '
            f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for name, c in (("a-ink", INK), ("a-sub", SUB), ("a-accent", ACCENT), ("a-ochre", OCHRE)))
        + '</defs>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(x, y, w_, h_, fill, stroke="none", sw=0, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{h_}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(x, y1, y2, color, marker):
        p.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" '
                 f'stroke-width="5" marker-end="url(#{marker})"/>')

    # Node A: lease band on top, GC pause below.
    ya = 70
    text(20, ya + 62, "Node A", 28, "start", "normal")
    rect(tx(0), ya, tx(10) - tx(0), 50, PALE, ACCENT, 3)
    text((tx(0) + tx(10)) / 2, ya + 34, "lease（token 33）", 24)
    text(tx(10) + 10, ya + 34, "失効", 24, "start", cls="sub")
    p.append(f'<line x1="{tx(10)}" y1="{ya - 6}" x2="{tx(10)}" y2="{ya + 120}" '
             f'stroke="{SUB}" stroke-width="2" stroke-dasharray="6 5"/>')
    rect(tx(3), ya + 64, tx(15) - tx(3), 50, FILL, SUB, 1.5)
    text((tx(3) + tx(15)) / 2, ya + 98, "GC で停止（期限切れに気付かない）", 24, cls="sub")

    # Storage: the latest token it has accepted.
    ys = 262
    text(20, ys + 48, "ストレージ", 28, "start", "normal")
    rect(tx(0), ys, tx(20) - tx(0), 76, "#ffffff", SUB, 2)
    for t in (2, 14):
        p.append(f'<line x1="{tx(t)}" y1="{ys}" x2="{tx(t)}" y2="{ys + 76}" '
                 f'stroke="{SUB}" stroke-width="1.5"/>')
    text((tx(2) + tx(14)) / 2, ys + 47, "最新の token 33", 24)
    text((tx(14) + tx(20)) / 2, ys + 47, "最新の token 34", 24)

    # Node B: the next lease, after the gap.
    yb = 410
    text(20, yb + 34, "Node B", 28, "start", "normal")
    rect(tx(12), yb, tx(20) - tx(12), 50, OCHRE_PALE, OCHRE, 3)
    text((tx(12) + tx(20)) / 2, yb + 34, "lease（token 34）", 24)

    # Writes.
    arrow(tx(1.5), ya + 52, ys - 4, ACCENT, "a-accent")
    text(tx(1.5) + 12, ys - 18, "33 受理", 24, "start")
    arrow(tx(13.5), yb - 2, ys + 80, OCHRE, "a-ochre")
    text(tx(13.5) - 12, yb - 24, "34 受理", 24, "end")
    xr = tx(16.5)
    p.append(f'<line x1="{xr}" y1="{ya + 116}" x2="{xr}" y2="{ys - 30}" stroke="{RED}" '
             'stroke-width="5"/>')
    p.append(f'<path d="M{xr - 15},{ys - 36} l30,30 M{xr + 15},{ys - 36} l-30,30" '
             f'stroke="{RED}" stroke-width="7" stroke-linecap="round"/>')
    text(xr + 26, ys - 12, "33 を拒否", 24, "start", "normal", "red")

    # Time axis.
    yt = 500
    p.append(f'<line x1="{X0}" y1="{yt}" x2="{X1}" y2="{yt}" stroke="{SUB}" '
             'stroke-width="2" marker-end="url(#a-sub)"/>')
    text(X0, yt + 32, "時間", 24, "start", cls="sub")

    (HERE / "images").mkdir(exist_ok=True)
    (HERE / "images" / "lease_concept.svg").write_text(
        "\n".join(p + ["</svg>"]) + "\n", encoding="utf-8")


def margin_figure():
    """Holder counts from the request, Grantor from the reply, and both add a
    margin for the clock-rate drift. The scale is illustrative, not measured."""
    w, h = 960, 540
    x0, unit = 220, 54
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("Holder は早めに手放し、Grantor は遅めに次の相手へ貸す")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
        '<defs><marker id="m-sub" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" '
        f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def X(t):
        return x0 + t * unit

    def text(x, y, s, size=24, anchor="middle", color=INK):
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                 f'style="fill:{color}">{escape(s)}</text>')

    def rect(x, y, w_, h_, fill, stroke="none", sw=0, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{h_}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    # The blank between the Holder letting go and the next grant.
    rect(X(9), 60, X(12) - X(9), 300, FILL, rx=0)
    text((X(9) + X(12)) / 2, 400, "空白", 26)
    text((X(9) + X(12)) / 2, 432, "誰も持たない", 24, color=SUB)

    # Grantor: counts from the reply (t = 1), lends again only after a margin.
    yg = 100
    text(30, yg + 34, "Grantor", 28, "start")
    rect(X(1), yg, X(11) - X(1), 50, OCHRE_PALE, OCHRE, 2.5)
    text((X(1) + X(11)) / 2, yg + 34, "応答から数えて貸す", 24)
    text(X(11), yg + 84, "期限", 24, color=SUB)
    rect(X(11), yg, X(12) - X(11), 50, "#ffffff", OCHRE, 2.5, "7 5")
    text(X(12), yg - 14, "次に貸す", 24, color=SUB)

    # Holder: counts from the request (t = 0), lets go a margin earlier.
    yh = 250
    text(30, yh + 34, "Holder", 28, "start")
    rect(X(0), yh, X(9) - X(0), 50, PALE, ACCENT, 2.5)
    text((X(0) + X(9)) / 2, yh + 34, "要求から数えて使う", 24)
    text(X(10), yh + 84, "期限", 24, color=SUB)
    rect(X(9), yh, X(10) - X(9), 50, "#ffffff", ACCENT, 2.5, "7 5")
    text(X(9), yh - 14, "手放す", 24, color=SUB)

    # Request and reply.
    p.append(f'<line x1="{X(0)}" y1="{yh}" x2="{X(1)}" y2="{yg + 56}" stroke="{SUB}" '
             f'stroke-width="3" marker-end="url(#m-sub)"/>')
    text(X(0), yh + 82, "要求", 24, color=SUB)

    # Legend for the dashed part.
    rect(220, 470, 44, 30, "#ffffff", SUB, 2.5, "7 5", rx=4)
    text(276, 494, "時計のずれに見込むマージン", 24, "start", SUB)
    p.append("</svg>")
    (HERE / "images" / "lease_margin.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


if __name__ == "__main__":
    concept_figure()
    margin_figure()
