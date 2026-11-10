"""Generate the concept figure of the Ethereum hard fork note (standard library only).

Run: python3 figures.py  -> images/ethereum-hard-forks_concept.svg,
images/ethereum-hard-forks_opcodes.svg and images/ethereum-hard-forks_transfer.svg.
The last two read lab/output/summary.txt (written by lab/run.sh).
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GRAY_PALE = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

W, H = 960, 540
LEFT = 200                      # start of the first fork segment
SEG = 240                       # width of one fork segment
FORKS = ["Istanbul", "Berlin", "Cancun"]
# Row values per segment; True marks a value that changed at that fork.
ROWS = [
    ("SLOAD", [("800", False), ("2100 / 100", True), ("2100 / 100", False)]),
    ("SELFDESTRUCT", [("delete code", False), ("delete code", False), ("keep code", True)]),
]


def concept_figure():
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img"><title>'
        + escape("同じバイトコードのまま、フォークの境目で SLOAD のガスと SELFDESTRUCT の意味が変わる。"
                 "更新しなかったノードは古い規則で別の列を伸ばす")
        + "</title>",
        f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>",
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(x, y, w, h, fill, stroke, sw=2, rx=6):
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    # Fork names and the dashed boundaries where every node switches rules.
    for i, name in enumerate(FORKS):
        text(LEFT + SEG * i + SEG / 2, 52, name, 26)
    for i in range(1, len(FORKS)):
        x = LEFT + SEG * i
        p.append(f'<line x1="{x}" y1="70" x2="{x}" y2="515" stroke="{SUB}" '
                 f'stroke-width="2" stroke-dasharray="8 6"/>')

    # Row headers.
    text(16, 118, "chain", anchor="start", cls="sub")
    text(16, 339, "code", anchor="start", cls="sub")
    for r, (label, _) in enumerate(ROWS):
        text(16, 419 + r * 70, label, anchor="start", cls="sub")

    # Main chain: blocks that every upgraded node accepts.
    xs = [LEFT + 14 + 58 * k for k in range(12)]
    p.append(f'<line x1="{xs[0]}" y1="110" x2="{xs[-1] + 40}" y2="110" stroke="{BLUE}" stroke-width="3"/>')
    for x in xs:
        rect(x, 90, 40, 40, BLUE_PALE, BLUE)

    # Branch: nodes that kept the old rules at the Berlin boundary extend their own chain.
    bx = [LEFT + SEG + 30 + 58 * k for k in range(4)]
    split = xs[3] + 40
    p.append(f'<path d="M{split} 110 L{bx[0]} 215 L{bx[-1] + 40} 215" fill="none" '
             f'stroke="{OCHRE}" stroke-width="3"/>')
    for x in bx:
        rect(x, 195, 40, 40, OCHRE_PALE, OCHRE)
    text(bx[-1] + 60, 224, "old rules", anchor="start", cls="sub")

    # The deployed bytecode does not change across forks.
    rect(LEFT + 8, 310, SEG * 3 - 16, 46, GRAY_PALE, SUB, 1.5)
    text(LEFT + SEG * 1.5, 341, "same deployed bytecode")

    # What the same opcode costs or does in each segment.
    for r, (_, cells) in enumerate(ROWS):
        y = 388 + r * 70
        for i, (value, changed) in enumerate(cells):
            x = LEFT + SEG * i + 12
            if changed:
                rect(x, y, SEG - 24, 50, BLUE_PALE, BLUE, 2.5)
            else:
                rect(x, y, SEG - 24, 50, "#ffffff", SUB, 1.2)
            text(x + (SEG - 24) / 2, y + 33, value)

    p.append("</svg>")
    out = HERE / "images" / "ethereum-hard-forks_concept.svg"
    out.write_text("\n".join(p) + "\n", encoding="utf-8")


def summary_tables():
    """Split lab/output/summary.txt into {section title: [rows as lists of cells]}."""
    tables, key = {}, None
    for line in (HERE / "lab" / "output" / "summary.txt").read_text().splitlines():
        if line.startswith("== "):
            key = line.strip("= ")
            tables[key] = []
        elif key and "|" in line:
            tables[key].append([c.strip() for c in line.split("|")])
    return tables


def svg_start(w, h, title):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
        f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>",
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]


def opcodes_figure():
    """Which new opcodes run on each fork, and what SLOAD costs there."""
    t = summary_tables()
    probes = t["opcode probes (eth_call of init code)"]
    sload = {r[0]: r[1:] for r in t["SLOAD of the same slot twice in one call"][1:]}
    names = probes[0][1:]
    p = svg_start(W, H, "フォークごとに、新しい命令が動くかと、同じスロットを 2 回読む SLOAD のガス")

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    x0, cw, sw, top, rh = 150, 108, 104, 80, 50
    for j, name in enumerate(names):
        text(x0 + cw * j + cw / 2, top - 16, name, 24)
    sx = x0 + cw * len(names) + 16
    text(sx + sw, top - 48, "SLOAD gas", 24, cls="sub")
    text(sx + sw / 2, top - 16, "1st", 24)
    text(sx + sw * 1.5, top - 16, "2nd", 24)
    prev = None
    for i, row in enumerate(probes[1:]):
        fork, cells = row[0], row[1:]
        y = top + rh * i
        text(x0 - 16, y + 36, fork, 24, anchor="end")
        for j, cell in enumerate(cells):
            ok = cell.startswith("ok")
            fill, stroke = (BLUE_PALE, BLUE) if ok else (GRAY_PALE, "#ffffff")
            p.append(f'<rect x="{x0 + cw * j + 4}" y="{y + 4}" width="{cw - 8}" height="{rh - 8}" '
                     f'rx="5" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
            text(x0 + cw * j + cw / 2, y + 33, "ok" if ok else "error", 24, cls="" if ok else "sub")
        gas = sload[fork]
        for k, g in enumerate(gas):
            changed = prev is not None and g != prev[k]
            p.append(f'<rect x="{sx + sw * k + 4}" y="{y + 4}" width="{sw - 8}" height="{rh - 8}" rx="5" '
                     f'fill="{OCHRE_PALE if changed else "#ffffff"}" '
                     f'stroke="{OCHRE if changed else SUB}" stroke-width="{2 if changed else 1}"/>')
            text(sx + sw * k + sw / 2, y + 33, g, 24)
        prev = gas
    text(W / 2, top + rh * 8 + 42, "error = NotActivated　黄土の枠 = 前のフォークから変わった値", 24, cls="sub")
    p.append("</svg>")
    (HERE / "images" / "ethereum-hard-forks_opcodes.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def transfer_figure():
    """Gas that 3 SLOADs need in the receiver, against the 2300 gas that transfer() forwards."""
    t = summary_tables()
    sload = {r[0]: [int(v) for v in r[1:]] for r in t["SLOAD of the same slot twice in one call"][1:]}
    status = {r[0]: r[1:] for r in t["transfer(1 wei) to a receiver that reads 3 slots"][1:]}
    later = [f for f in sload if f not in ("petersburg", "istanbul")]
    assert len({tuple(sload[f]) for f in later}) == 1 and len({tuple(status[f]) for f in later}) == 1
    rows = [
        ("petersburg", 3 * sload["petersburg"][0], status["petersburg"][0]),
        ("istanbul", 3 * sload["istanbul"][0], status["istanbul"][0]),
        (f"{later[0]}–{later[-1]}", 3 * sload[later[0]][0], status[later[0]][0]),
        ("+ access list", 3 * sload[later[0]][1], status[later[0]][1]),
    ]
    p = svg_start(W, H, "受け取る側の SLOAD 3 回に要るガスと、transfer が渡す 2300 ガス")

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    x0, scale, top, rh = 230, 480 / 6300, 90, 92
    limit = x0 + 2300 * scale
    text(W / 2, 46, "gas for 3 SLOADs in the receiver", 24, cls="sub")
    for i, (label, gas, st) in enumerate(rows):
        y = top + rh * i
        over = gas > 2300
        text(x0 - 16, y + 44, label, 24, anchor="end")
        p.append(f'<rect x="{x0}" y="{y + 14}" width="{gas * scale:.1f}" height="44" rx="4" '
                 f'fill="{OCHRE_PALE if over else BLUE_PALE}" stroke="{OCHRE if over else BLUE}" stroke-width="2"/>')
        text(x0 + gas * scale + 12, y + 44, f"{gas:,}", 24, anchor="start")
        text(W - 20, y + 44, "success" if st == "1" else "failed", 24, anchor="end",
             cls="" if st == "1" else "sub")
    p.append(f'<line x1="{limit:.1f}" y1="{top - 6}" x2="{limit:.1f}" y2="{top + rh * 4}" '
             f'stroke="{INK}" stroke-width="2" stroke-dasharray="8 6"/>')
    text(limit, top + rh * 4 + 34, "2300 = gas that transfer() forwards", 24)
    p.append("</svg>")
    (HERE / "images" / "ethereum-hard-forks_transfer.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


if __name__ == "__main__":
    concept_figure()
    opcodes_figure()
    transfer_figure()
