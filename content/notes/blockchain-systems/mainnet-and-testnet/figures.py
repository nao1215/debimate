"""Generate the figures of the mainnet-and-testnet note (standard library only).

concept_figure(): three chains that never touch.
ids_figure(): where chain ID and network ID live.
bech32_figure(): the parts of a bc1 address in three networks.
btc_networks_figure(): the five networks of Bitcoin Core 32.1 from
lab/output/btc_networks.txt. Magic bytes and ports differ for all five, while
the addresses of the same key collapse into fewer groups.

Each SVG is rendered by headless Chrome at 2x and saved as WebP (needs Pillow).

Run: python3 content/notes/blockchain-systems/mainnet-and-testnet/figures.py
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GRAY, GRAY_PALE = "#666666", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"


def save_webp(parts, w, h, name):
    """Render the SVG source with headless Chrome and write images/<name>.webp."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text("\n".join(parts) + "\n", encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


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
        ("メインネット", "chain ID 1", BLUE, BLUE_PALE, 250, 806),
        ("テストネット", "Sepolia、chain ID 11155111", OCHRE, OCHRE_PALE, 418, 590),
        ("ローカル", "Anvil、chain ID 31337", GRAY, GRAY_PALE, 754, None),
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
        if fork:
            text(mark - gap / 2, y + size + 44, "新しい規則", 24, anchor="middle")
        else:
            text(right, y + size + 44, "規則は起動時に選ぶ", 24, anchor="end")
    # time axis
    p.append(f'<line x1="250" y1="505" x2="{right}" y2="505" stroke="{SUB}" stroke-width="2"/>')
    p.append(f'<polygon points="{right},497 {right + 16},505 {right},513" fill="{SUB}"/>')
    text(240, 513, "時間", 24, anchor="end", cls="sub")
    p.append("</svg>")
    save_webp(p, w, h, "mainnet-and-testnet_concept.webp")


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
    cols = {"magic bytes": (175, 160), "ポート": (350, 110), "アドレス（古い形式）": (480, 170),
            "アドレス（bc1 の形式）": (670, 265)}
    for name, (x, cw) in cols.items():
        text(x + cw / 2, 52, name, 21, cls="sub")
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

    span("アドレス（古い形式）", 0, 0, "1BgGZ…", False)
    span("アドレス（古い形式）", 1, 4, "mrCDr…", True)
    span("アドレス（bc1 の形式）", 0, 0, "bc1qw508…", False)
    span("アドレス（bc1 の形式）", 1, 3, "tb1qw508…", True)
    span("アドレス（bc1 の形式）", 4, 4, "bcrt1qw508…", False)
    p.append("</svg>")
    save_webp(p, w, h, "mainnet-and-testnet_btc_networks.webp")


def svg_head(w, h, title):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
        f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} "
        f".mono{{font-family:{MONO}}}</style>",
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]


def put(p, x, y, s, size=22, anchor="middle", cls=""):
    c = f' class="{cls}"' if cls else ""
    p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="normal" '
             f'text-anchor="{anchor}"{c}>{escape(s)}</text>')


def box(p, x, y, w, h, fill, stroke, sw=2):
    p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
             f'stroke="{stroke}" stroke-width="{sw}"/>')


def ids_figure():
    """chain ID sits inside the signed transaction; network ID in the Status message between nodes."""
    w, h = 960, 430
    p = svg_head(w, h, "chain ID は署名したトランザクションの中に、network ID はノード同士が接続時に送る Status の中にある")
    # Left: a signed transaction.
    put(p, 240, 44, "署名済みのトランザクション（EIP-1559）", 20)
    box(p, 40, 64, 380, 290, GRAY_PALE, SUB)
    fields = ["chainId", "nonce", "宛先・金額", "手数料・gas", "data"]
    for i, f in enumerate(fields):
        y = 82 + i * 44
        hl = f == "chainId"
        box(p, 64, y, 230, 36, OCHRE_PALE if hl else "#ffffff", OCHRE if hl else SUB, 2.5 if hl else 1.5)
        put(p, 179, y + 26, f, 21, cls="mono" if f in ("chainId", "nonce", "data") else "")
    p.append(f'<path d="M306 82 h14 v214 h-14" fill="none" stroke="{BLUE}" stroke-width="2.5"/>')
    put(p, 372, 186, "署名の", 20, cls="sub")
    put(p, 372, 212, "対象", 20, cls="sub")
    box(p, 64, 304, 334, 36, BLUE_PALE, BLUE)
    put(p, 231, 330, "署名（v, r, s）", 21)
    put(p, 240, 396, "書き換えると、送り主が別のアドレスになる", 19, cls="sub")
    # Right: two nodes exchanging Status.
    put(p, 715, 44, "ノード同士の接続（Status メッセージ）", 24)
    for x in (520, 820):
        box(p, x, 150, 100, 70, GRAY_PALE, SUB)
        put(p, x + 50, 194, "ノード", 22)
    p.append(f'<line x1="626" y1="185" x2="814" y2="185" stroke="{SUB}" stroke-width="2.5"/>')
    p.append(f'<polygon points="626,185 638,178 638,192" fill="{SUB}"/>')
    p.append(f'<polygon points="814,185 802,178 802,192" fill="{SUB}"/>')
    box(p, 560, 240, 310, 124, "#ffffff", SUB, 1.5)
    for i, (f, hl) in enumerate([("networkId", True), ("genesis のハッシュ", False), ("forkId", False)]):
        y = 254 + i * 34
        box(p, 574, y, 282, 28, OCHRE_PALE if hl else "#ffffff", OCHRE if hl else SUB, 2.5 if hl else 1)
        put(p, 715, y + 21, f, 19, cls="mono" if f != "genesis のハッシュ" else "")
    p.append(f'<line x1="715" y1="189" x2="715" y2="238" stroke="{SUB}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    put(p, 715, 396, "接続した直後に互いに送る", 19, cls="sub")
    p.append("</svg>")
    save_webp(p, w, h, "mainnet-and-testnet_ids.webp")


def bech32_figure():
    """The same key in three networks: HRP and checksum change, the data part stays."""
    w, h = 960, 380
    p = svg_head(w, h, "bc1 の形式のアドレスは、HRP と末尾の検査用の 6 文字だけがネットワークで変わる")
    rows = [("メインネット", "bc", "v8f3t4"), ("テストネット", "tb", "xpjzsx"), ("regtest", "bcrt", "ygt080")]
    data = "qw508d6qejxtdg4y5r3zarvary0c5xw7k"
    fs, cw = 22, 13.3  # monospace font size and its character width
    x0 = 190
    spans = [(4 * cw + 14, OCHRE_PALE, OCHRE), (cw + 12, "#ffffff", SUB),
             (len(data) * cw + 14, GRAY_PALE, SUB), (6 * cw + 14, OCHRE_PALE, OCHRE)]
    xs, x = [], x0
    for sw, _, _ in spans:
        xs.append(x)
        x += sw + 6
    heads = ["HRP", "区切り", "公開鍵から作る部分（同じ）", "検査用"]
    for i, (sw, _, _) in enumerate(spans):
        put(p, xs[i] + sw / 2, 52 if i != 1 else 84, heads[i], 19, cls="sub")
    for r, (name, hrp, chk) in enumerate(rows):
        y = 100 + r * 80
        put(p, 30, y + 36, name, 22, anchor="start")
        for i, (sw, fill, stroke) in enumerate(spans):
            box(p, xs[i], y, sw, 52, fill, stroke, 2 if stroke != SUB or i == 2 else 1.5)
            put(p, xs[i] + sw / 2, y + 34, [hrp, "1", data, chk][i], fs, cls="mono")
    put(p, w / 2, 360, "黄土色はネットワークで変わる部分。検査用の文字は HRP を含めて計算する", 19, cls="sub")
    p.append("</svg>")
    save_webp(p, w, h, "mainnet-and-testnet_bech32.webp")


if __name__ == "__main__":
    concept_figure()
    btc_networks_figure()
    ids_figure()
    bech32_figure()
