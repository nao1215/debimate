"""Generate the wallet note's original explanatory SVGs (Python stdlib only).

Run: python3 content/notes/blockchain-systems/wallet/figures.py
Screenshots are quoted originals and are not processed by this script.
All key/seed labels are deliberately invalid placeholders, not test wallets.
"""


from html import escape


from pathlib import Path


from decimal import Decimal


OUT = Path(__file__).parent / "images"


class Figure:
    def __init__(self, width, height, title):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
                      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10" fill="none" stroke="#596b76" stroke-width="1.5"/></marker></defs>',
                      '<style>text{font-family:"Noto Sans CJK JP","Noto Sans JP",sans-serif;fill:#28343b} .small{fill:#555}</style>',
                      f'<rect width="{width}" height="{height}" fill="white"/>']

    def text(self, x, y, text, size=20, weight="normal", anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(text)}</text>')

    def rect(self, x, y, w, h, fill="#fff", dash=False):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#9cabb5" stroke-width="1.3"' + (' stroke-dasharray="6 5"' if dash else '') + '/>')

    def line(self, x1, y1, x2, y2, arrow=False, dash=False):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#596b76" stroke-width="1.5"' + (' marker-end="url(#arrow)"' if arrow else '') + (' stroke-dasharray="5 5"' if dash else '') + '/>')

    def save(self, name):
        (OUT / name).write_text("\n".join(self.parts + ['</svg>']) + "\n")


def local_transfer():
    # Render recorded balances, never substitute invented example values.
    source = OUT.parent / "lab" / "output"
    def balance(stage, chain, role):
        value = int((source / f"{stage}-{chain}-{role}.wei").read_text())
        return f"{Decimal(value) / Decimal(10**18):,f}"
    f = Figure(720, 390, "実測したローカル送金。チェーンAだけで残高が変化")
    f.text(20, 32, "チェーン A：1 ETH を送金", 25, "bold")
    f.text(20, 63, "開発用の残高。現実の価値はない", 18)
    for x, role, label in [(20, "sender", "送金者"), (385, "receiver", "受取人")]:
        f.rect(x, 82, 315, 149, "#eaf1f5")
        f.text(x+16, 114, label, 23, "bold")
        f.text(x+16, 151, balance("before", "a", role) + " ETH", 23)
        f.line(x+35, 160, x+35, 184, arrow=True)
        f.text(x+16, 215, balance("after", "a", role) + " ETH", 22)
    f.line(338, 149, 378, 149, arrow=True)
    f.text(20, 262, "送金者の減少 = 1 ETH ＋ 手数料 0.000021 ETH", 22)
    f.line(20, 285, 700, 285, dash=True)
    f.text(20, 320, "チェーン B：送金なし", 24, "bold")
    assert all(balance("before", "b", role) == balance("after", "b", role)
               for role in ("sender", "receiver"))
    f.text(20, 356, "同じアドレスでも、両者とも 10,000 ETH のまま", 22)
    f.save("local-transfer.svg")


def input_methods():
    f = Figure(400, 220, "GUI の入力欄。実際の製品画面ではない模式図")
    f.text(20, 32, "GUI：入力欄で指定", 22, "bold")
    f.text(20, 79, "送金先", 19)
    f.rect(112, 52, 266, 40, "#eaf1f5")
    f.text(126, 79, "受取人のアドレス", 18)
    f.text(20, 135, "数量", 19)
    f.rect(112, 108, 266, 40, "#eaf1f5")
    f.text(126, 135, "1 ETH", 19)
    f.rect(244, 166, 134, 36)
    f.text(260, 190, "内容を確認", 18)
    f.save("gui-input.svg")
    f = Figure(400, 220, "CLI の引数。実行用ではない模式図")
    f.text(20, 32, "CLI：コマンドで指定", 22, "bold")
    f.rect(20, 52, 358, 104, "#eaf1f5")
    f.text(34, 87, 'cast send "$receiver"', 21)
    f.text(58, 128, '--value 1ether …', 21)
    f.text(20, 184, "$receiver：受取人のアドレス", 18)
    f.text(20, 211, "1ether：送金する数量", 18)
    f.save("cli-input.svg")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    input_methods()
    local_transfer()
