"""Generate the figures of the mainnet-and-testnet note (standard library only).

concept_figure(): three chains that never touch.
btc_networks_figure(): the five networks of Bitcoin Core 32.1 from
lab/output/btc_networks.txt. Magic bytes and ports differ for all five, while
the addresses of the same key collapse into fewer groups.

Run: python3 content/notes/blockchain-systems/mainnet-and-testnet/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GRAY, GRAY_PALE = "#666666", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """Three chains that never touch: started at different times, new rules on testnet first."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("メインネット・テストネット・ローカルのチェーンは別々の列で、新しい規則はテストネットで先に有効になる")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="start", cls="", weight="normal"):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    size, gap, right = 30, 12, 920
    # (title, chain ID, line, pale fill, x of first block, x of fork or None = rules from genesis)
    rows = [
        ("Mainnet", "chain ID 1", BLUE, BLUE_PALE, 250, 806),
        ("Testnet", "chain ID 11155111", OCHRE, OCHRE_PALE, 418, 590),
        ("Local", "chain ID 31337", GRAY, GRAY_PALE, 754, None),
    ]
    for i, (title, cid, line, pale, start, fork) in enumerate(rows):
        y = 70 + i * 150
        text(30, y + 22, title, 30, weight="normal")
        text(30, y + 58, cid, 24, cls="sub")
        x, first_new = start, None
        while x + size <= right:
            new = fork is None or x >= fork
            if new and first_new is None:
                first_new = x
            p.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" '
                     f'fill="{line if new else pale}" stroke="{line}" stroke-width="2"/>')
            if x + size + gap + size <= right:
                p.append(f'<line x1="{x + size}" y1="{y + size / 2}" x2="{x + size + gap}" '
                         f'y2="{y + size / 2}" stroke="{line}" stroke-width="2"/>')
            x += size + gap
        mark = first_new
        p.append(f'<line x1="{mark - gap / 2}" y1="{y - 12}" x2="{mark - gap / 2}" y2="{y + size + 12}" '
                 f'stroke="{INK}" stroke-width="2" stroke-dasharray="6 4"/>')
        text(mark - gap / 2, y + size + 44, "new rules" if fork else "rules: your choice", 24,
             anchor="middle" if fork else "start")
    # time axis
    p.append(f'<line x1="250" y1="505" x2="{right}" y2="505" stroke="{SUB}" stroke-width="2"/>')
    p.append(f'<polygon points="{right},497 {right + 16},505 {right},513" fill="{SUB}"/>')
    text(240, 513, "time", 24, anchor="end", cls="sub")
    p.append("</svg>")
    (HERE / "images" / "mainnet-and-testnet_concept.svg").write_text("\n".join(p) + "\n")


def btc_networks_figure():
    """Magic bytes and ports are unique per network; address prefixes are shared."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("magic bytes とポートは 5 つとも違い、同じ鍵のアドレスは 2〜3 通りにしか分かれない")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="normal" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def box(x, y, bw, bh, fill, stroke, label):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2.5"/>')
        text(x + bw / 2, y + bh / 2 + 9, label)

    # Values from lab/output/btc_networks.txt.
    nets = [("main", "f9beb4d9", "8333"), ("testnet3", "0b110907", "18333"),
            ("testnet4", "1c163f28", "48333"), ("signet", "0a03cf40", "38333"),
            ("regtest", "fabfb5da", "18444")]
    top, row, bh = 80, 90, 72
    cols = {"magic": (175, 160), "port": (350, 110), "pkh": (480, 170), "wpkh": (670, 265)}
    for name, (x, cw) in cols.items():
        text(x + cw / 2, 52, name, cls="sub")
    for i, (name, magic, port) in enumerate(nets):
        y = top + i * row
        text(30, y + bh / 2 + 9, name, 26, anchor="start")
        box(175, y, 160, bh, GRAY_PALE, SUB, magic)
        box(350, y, 110, bh, GRAY_PALE, SUB, port)

    def span(col, first, last, label, shared):
        x, cw = cols[col]
        y = top + first * row
        hh = (last - first) * row + bh
        box(x, y, cw, hh, OCHRE_PALE if shared else GRAY_PALE, OCHRE if shared else SUB, label)

    span("pkh", 0, 0, "1BgGZ…", False)
    span("pkh", 1, 4, "mrCDr…", True)
    span("wpkh", 0, 0, "bc1qw508…", False)
    span("wpkh", 1, 3, "tb1qw508…", True)
    span("wpkh", 4, 4, "bcrt1qw508…", False)
    p.append("</svg>")
    (HERE / "images" / "mainnet-and-testnet_btc_networks.svg").write_text("\n".join(p) + "\n")


if __name__ == "__main__":
    concept_figure()
    btc_networks_figure()
