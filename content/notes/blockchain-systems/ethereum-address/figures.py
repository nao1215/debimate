"""Generate the figures of the ethereum-address note (standard library only).

Run: python3 figures.py  -> images/ethereum-address_concept.svg,
     images/ethereum-address_redeploy.svg
"""
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """Inputs of the three rules go into keccak256; the chain ID does not."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("3 つの規則の材料が keccak256 に入り、chain ID は入らない。同じアドレスでもチェーンごとに中身が違う")}'
        '</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                 f'{escape(s)}</text>')

    def box(x, y, bw, bh, fill, stroke, label=None, dash=False, rx=6, size=24):
        d = ' stroke-dasharray="7 5"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2"{d}/>')
        if label:
            text(x + bw / 2, y + bh / 2 + 9, label, size)

    def arrow(x1, y1, x2, y2, color=INK, width=3, dash=False):
        d = ' stroke-dasharray="7 6"' if dash else ""
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                 f'stroke-width="{width}"{d}/>')
        if not dash:
            p.append(f'<polygon points="{x2 + 12},{y2} {x2},{y2 - 8} {x2},{y2 + 8}" fill="{color}"/>')

    # Three byte strips: segment widths follow the role, not the exact byte count.
    rows = [
        ("EOA", 60, [("公開鍵 64B", 370, BLUE_PALE)]),
        ("CREATE", 175, [("送り手", 200, BLUE_PALE), ("nonce", 170, OCHRE_PALE)]),
        ("CREATE2", 290, [("ff", 44, FILL), ("送り手", 96, BLUE_PALE),
                          ("salt", 76, OCHRE_PALE), ("H(init)", 154, OCHRE_PALE)]),
    ]
    for name, top, segs in rows:
        text(30, top - 10, name, 24, "start", "sub")
        x = 30
        for label, sw, fill in segs:
            stroke = OCHRE if fill == OCHRE_PALE else (BLUE if fill == BLUE_PALE else SUB)
            box(x, top, sw, 56, fill, stroke, label, rx=2)
            x += sw
        arrow(x + 6, top + 28, 430, top + 28)

    # keccak256 takes all three; the last 20 bytes become the address.
    box(444, 60, 130, 286, "#ffffff", INK, rx=10)
    text(509, 196, "keccak", 26)
    text(509, 228, "256", 26)
    arrow(578, 95, 606, 95)
    box(620, 60, 310, 70, BLUE_PALE, BLUE, "アドレス（下位 20B）")

    # Same address, different content per chain.
    for i, (chain, fill, stroke, label, dash) in enumerate([
        ("チェーン A", BLUE_PALE, BLUE, "コード X", False),
        ("チェーン B", "#ffffff", OCHRE, "空 / 別のコード", True),
    ]):
        x = 620 + i * 160
        p.append(f'<line x1="{x + 75}" y1="130" x2="{x + 75}" y2="176" stroke="{SUB}" stroke-width="2"/>')
        box(x, 176, 150, 170, "#ffffff", SUB, rx=8)
        text(x + 75, 212, chain, 24, cls="sub")
        box(x + 12, 236, 126, 92, fill if not dash else OCHRE_PALE, stroke, None, dash=dash)
        if dash:
            text(x + 75, 276, "空 /", 24)
            text(x + 75, 308, "別のコード", 24)
        else:
            text(x + 75, 291, label, 24)

    # The chain ID goes into the signature, never into keccak256 above.
    box(30, 430, 170, 60, OCHRE_PALE, OCHRE, "chain ID")
    arrow(200, 460, 296, 460)
    box(310, 430, 120, 60, FILL, SUB, "署名")
    text(470, 470, "に入る", 24, "start", "sub")
    arrow(160, 430, 470, 352, SUB, 2, dash=True)
    cx, cy = 330, 387
    p.append(f'<line x1="{cx - 14}" y1="{cy - 14}" x2="{cx + 14}" y2="{cy + 14}" stroke="{RED}" stroke-width="5"/>')
    p.append(f'<line x1="{cx - 14}" y1="{cy + 14}" x2="{cx + 14}" y2="{cy - 14}" stroke="{RED}" stroke-width="5"/>')
    text(370, 400, "アドレスには入らない", 24, "start", "sub")
    (HERE / "images" / "ethereum-address_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def redeploy_figure():
    """What sits at the first target address after each step, Shanghai vs Cancun."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("Shanghai では同じアドレスに V2 が置かれ、Cancun 以降は V1 が残る")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                 f'{escape(s)}</text>')

    def box(x, y, bw, bh, fill, stroke, dash=False):
        d = ' stroke-dasharray="7 5"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2"{d}/>')

    def arrow(x1, y, x2):
        p.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{INK}" stroke-width="3"/>')
        p.append(f'<polygon points="{x2 + 12},{y} {x2},{y - 8} {x2},{y + 8}" fill="{INK}"/>')

    cols = [(230, "1〜2 作る"), (480, "3 消す"), (730, "4〜5 作り直す")]
    cw, ch = 200, 110
    for x, label in cols:
        text(x + cw / 2, 50, label, 24, cls="sub")
    text(30, 92, "0xCB8956e6… にあるコード", 24, "start", "sub")

    rows = [
        (120, "Shanghai", [("V1", "version 1", BLUE_PALE, BLUE, False),
                            ("空", "0 bytes", "#ffffff", SUB, True),
                            ("V2", "version 2", OCHRE_PALE, OCHRE, False)]),
        (300, "Cancun 以降", [("V1", "version 1", BLUE_PALE, BLUE, False),
                              ("V1 のまま", "218 bytes", BLUE_PALE, BLUE, False),
                              ("V1 のまま", "version 1", BLUE_PALE, BLUE, False)]),
    ]
    for top, name, cells in rows:
        text(30, top + ch / 2 + 9, name, 26, "start")
        for i, ((x, _), (main, sub, fill, stroke, dash)) in enumerate(zip(cols, cells)):
            box(x, top, cw, ch, fill, stroke, dash)
            text(x + cw / 2, top + 48, main, 26)
            text(x + cw / 2, top + 84, sub, 24, cls="sub")
            if i < 2:
                arrow(x + cw + 6, top + ch / 2, cols[i + 1][0] - 18)

    # Cancun: the Deployer cannot be created again, V2 lands elsewhere.
    cx, cy = 632, 452
    p.append(f'<line x1="{cx - 12}" y1="{cy - 12}" x2="{cx + 12}" y2="{cy + 12}" stroke="{RED}" stroke-width="5"/>')
    p.append(f'<line x1="{cx - 12}" y1="{cy + 12}" x2="{cx + 12}" y2="{cy - 12}" stroke="{RED}" stroke-width="5"/>')
    text(930, 461, "Deployer を作り直せない", 24, "end", "sub")
    text(930, 500, "V2 は 0x673a327D… へ", 24, "end", "sub")
    (HERE / "images" / "ethereum-address_redeploy.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


if __name__ == "__main__":
    concept_figure()
    redeploy_figure()
