"""Generate the figures of the upgradeable-proxy note (standard library only).

Run: python3 figures.py -> images/upgradeable-proxy_concept.svg, upgradeable-proxy_layout.svg
and upgradeable-proxy_slot_space.svg. The layout figure reads lab/output/summary.txt and the
slot figure uses the Keccak-256 of lab/slots.py.
"""

import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """The proxy keeps the address and the data; only the code pointer moves."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("プロキシが storage と実装のアドレスを持ち、DELEGATECALL で実装 V2 のコードを使う")}'
        '</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def arrow(x1, y1, x2, y2, color=INK, width=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                 f'stroke-width="{width}"{d}/>')
        # Arrow head pointing right (all arrows in this figure go left to right).
        p.append(f'<polygon points="{x2 + 16},{y2} {x2 - 2},{y2 - 11} {x2 - 2},{y2 + 11}" '
                 f'fill="{color}"/>')

    # Callers: they always send to the same proxy address.
    text(62, 120, "利用者", 26)
    for i in range(3):
        p.append(f'<circle cx="62" cy="{180 + i * 70}" r="22" fill="{FILL}" '
                 f'stroke="{INK}" stroke-width="2"/>')
    arrow(92, 250, 128, 250)

    # Proxy: fixed address, holds every value.
    p.append(f'<rect x="150" y="40" width="420" height="460" rx="14" fill="#ffffff" '
             f'stroke="{INK}" stroke-width="2.5"/>')
    text(360, 86, "プロキシ（アドレスは不変）", 26, weight="normal")
    text(360, 124, "storage はすべてここ", 24, cls="sub")
    rows = [("slot 0", "owner", FILL, SUB), ("slot 1", "balance", FILL, SUB),
            ("0xae0e…", "名前空間", FILL, SUB),
            ("0x3608…", "実装のアドレス", OCHRE_PALE, OCHRE)]
    for i, (slot, label, fill, stroke) in enumerate(rows):
        y = 150 + i * 82
        p.append(f'<rect x="172" y="{y}" width="376" height="64" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2"/>')
        text(190, y + 41, slot, 24, "start", cls="sub")
        text(532, y + 41, label, 24, "end")
    pointer_y = 150 + 3 * 82 + 32

    # Implementations: code only. V1 is no longer referenced.
    p.append(f'<rect x="700" y="60" width="230" height="150" rx="12" fill="#ffffff" '
             f'stroke="{SUB}" stroke-width="2" stroke-dasharray="8 6"/>')
    text(815, 120, "実装 V1", 28, cls="sub")
    text(815, 162, "差し替え前", 24, cls="sub")
    p.append(f'<rect x="700" y="300" width="230" height="150" rx="12" fill="{BLUE_PALE}" '
             f'stroke="{BLUE}" stroke-width="3"/>')
    text(815, 360, "実装 V2", 28, weight="normal")
    text(815, 402, "今のコード", 24)

    # Pointer: dashed to the old one, solid DELEGATECALL to the current one.
    p.append(f'<path d="M 548 {pointer_y} C 630 {pointer_y}, 620 140, 698 140" fill="none" '
             f'stroke="{SUB}" stroke-width="2" stroke-dasharray="8 6"/>')
    arrow(548, pointer_y + 8, 680, 380, BLUE, 5)
    text(815, 490, "DELEGATECALL で実行", 24, cls="sub")
    (HERE / "images" / "upgradeable-proxy_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")



def svg_open(w, h, title):
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(x, y, w, h, fill, stroke, sw=2):
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')

    def line(x1, y1, x2, y2, color=SUB, width=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{d}/>')

    return p, text, rect, line


def layout_figure():
    """The same three slots read by V1 and by V2Bad, which added `fee` at the top."""
    out = (HERE / "lab" / "output" / "summary.txt").read_text()
    fee = int(out.split("fee()=")[1].split()[0])
    owner = out.split("slot 0=0x")[1].split()[0][-40:]
    balance = int(out.split("slot 1=0x")[1].split()[0], 16)
    short = f"0x{owner[:4]}…{owner[-4:]}"
    rows = [
        ("slot 0", short, f"owner = {short}", f"fee = {fee / 10 ** 47:.2f} × 10^47"),
        ("slot 1", f"0x…{balance:x}", f"balance = {balance}", f"owner = 0x…00{balance:x}"),
        ("slot 2", "0", "(unused)", "balance = 0"),
    ]
    p, text, rect, line = svg_open(960, 540, "同じ 3 つの slot を、V1 と先頭に fee を足した V2Bad が別の意味で読む")
    text(160, 70, "V1 reads", cls="sub")
    text(480, 70, "proxy storage", cls="sub")
    text(810, 70, "V2Bad reads", cls="sub")
    for i, (slot, value, v1, v2) in enumerate(rows):
        y = 110 + 120 * i
        rect(375, y, 210, 76, "#f2f2f2", SUB, 1.5)
        text(480, y + 32, slot, 22, cls="sub")
        text(480, y + 62, value, 24)
        rect(10, y + 8, 300, 60, BLUE_PALE, BLUE)
        text(160, y + 46, v1, 24)
        rect(680, y + 8, 270, 60, OCHRE_PALE, OCHRE)
        text(815, y + 46, v2, 24)
        line(310, y + 38, 375, y + 38, BLUE, 2.5)
        line(585, y + 38, 680, y + 38, OCHRE, 2.5)
    text(480, 500, "upgrade changes only the code; the values in the slots stay", 24, cls="sub")
    p.append("</svg>")
    (HERE / "images" / "upgradeable-proxy_layout.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def slot_space_figure():
    """Where Solidity puts variables, where hashes land, and the ERC-1967 slot next to its hash."""
    sys.path.insert(0, str(HERE / "lab"))
    from slots import erc1967, keccak256  # noqa: E402

    label = "eip1967.proxy.implementation"
    hashed = keccak256(label.encode()).hex()
    slot = erc1967(label)[2:]
    assert int(hashed, 16) - 1 == int(slot, 16)
    p, text, rect, line = svg_open(960, 540, "slot の空間で、変数は小さい番号に集まり、ERC-1967 の slot はハッシュから 1 を引いた場所にある")
    x0, x1, y = 60, 900, 150
    rect(x0, y - 18, x1 - x0, 36, "#f2f2f2", SUB, 1.5)
    text(x0, y - 34, "0", 22, anchor="start", cls="sub")
    text(x1, y - 34, "2^256 − 1", 22, anchor="end", cls="sub")
    rect(x0 + 2, y - 16, 16, 32, BLUE_PALE, BLUE, 2)
    text(x0, y + 56, "slot 0, 1, 2 …", 24, anchor="start")
    text(x0, y + 86, "state variables", 22, anchor="start", cls="sub")
    for f in (0.48, 0.63, 0.77, 0.9):
        x = x0 + (x1 - x0) * f
        line(x, y - 16, x, y + 16, SUB, 2)
    text(x0 + (x1 - x0) * 0.6, y - 64, "keccak256(key, slot)", 24)
    text(x0 + (x1 - x0) * 0.6, y - 34, "mapping values: preimage known", 22, cls="sub")
    xs = x0 + (x1 - x0) * int(slot[:2], 16) / 256
    line(xs, y - 18, xs, y + 18, OCHRE, 4)
    # Zoom into the two neighbouring slots.
    zx, zy, zw = 200, 290, 700
    line(xs, y + 18, zx, zy, OCHRE, 1.5, "6 5")
    line(xs, y + 18, zx + zw, zy, OCHRE, 1.5, "6 5")
    rect(zx, zy, zw, 84, "#ffffff", SUB, 1.5)
    text(zx + 20, zy + 34, f"0x{hashed[:4]}…{hashed[-4:]}", 24, anchor="start")
    text(zx + 210, zy + 34, "keccak256(\"eip1967.proxy.implementation\")", 22, anchor="start")
    text(zx + 210, zy + 66, "preimage known: the string", 22, anchor="start", cls="sub")
    rect(zx, zy + 100, zw, 84, OCHRE_PALE, OCHRE, 2)
    text(zx + 20, zy + 134, f"0x{slot[:4]}…{slot[-4:]}", 24, anchor="start")
    text(zx + 210, zy + 134, "the hash − 1 = ERC-1967 implementation slot", 22, anchor="start")
    text(zx + 210, zy + 166, "no known preimage", 22, anchor="start", cls="sub")
    p.append("</svg>")
    (HERE / "images" / "upgradeable-proxy_slot_space.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


if __name__ == "__main__":
    concept_figure()
    layout_figure()
    slot_space_figure()
