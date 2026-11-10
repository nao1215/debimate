"""Generate the figures of the ERC-721 note (Python standard library only).

concept_figure(): the NFT contract on the chain holds tokenId -> owner and
returns tokenURI as a string; the JSON and the image it points to live on a
server outside the chain. The owners are those at the end of lab/run.py.

approval_figure(): approve covers one tokenId, setApprovalForAll covers every
NFT of the owner in the contract, including one received later (token #5 of
the lab).

metadata_figure(): experiment 4 of lab/run.py. The JSON of token #2 changes
three times while ownerOf(2) stays bob: a server-side edit (block 24, no
transaction), setBaseURI (block 25, no event), and a deletion (HTTP 404).
Values are copied from lab/output/summary.txt.

Run: python3 content/notes/blockchain-systems/erc-721/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GRAY_PALE = "#f2f2f2"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle", weight="normal"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(self, x1, y1, x2, y2, sw=3.5):
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#arrow)"/>')

    def save(self, name):
        path = HERE / "images" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "NFT コントラクトが持つのは tokenId と所有者の対応と URI の文字列で、"
                      "JSON と画像はチェーンの外のサーバーにある")
    # On the chain: the contract.
    f.box(25, 25, 470, 490, BLUE_PALE, BLUE, sw=3, rx=16)
    f.text(260, 70, "NFT コントラクト（チェーン上）", 26, weight="normal")
    f.text(130, 122, "tokenId", 24, SUB)
    f.text(345, 122, "ownerOf", 24, SUB)
    rows = [("#1", "Counter"), ("#2", "bob"), ("#3", "carol"), ("#4", "bob")]
    for i, (token, owner) in enumerate(rows):
        y = 138 + i * 62
        focus = token == "#2"
        f.box(55, y, 410, 52, "#ffffff", INK if focus else SUB, sw=3 if focus else 1.8, rx=8)
        f.text(130, y + 35, token, 24, weight="normal")
        f.text(345, y + 35, owner, 24)
    f.box(55, 400, 410, 92, "#ffffff", INK, sw=3, rx=8)
    f.text(260, 436, "tokenURI(2) が返す文字列", 24, SUB)
    f.text(260, 474, "https://…/2.json", 24)

    # Outside the chain: the server.
    f.box(560, 25, 375, 490, OCHRE_PALE, OCHRE, sw=3, dash="12 8", rx=16)
    f.text(747, 70, "チェーンの外（サーバー）", 26, weight="normal")
    f.box(590, 110, 315, 150, "#ffffff", INK, sw=2.5, rx=8)
    f.text(747, 146, "2.json", 24, weight="normal")
    f.text(612, 190, '"name": "#2"', 24, anchor="start")
    f.text(612, 232, '"image": "…png"', 24, anchor="start")
    f.box(660, 315, 175, 130, GRAY_PALE, SUB, sw=2.5, rx=8)
    f.parts.append(f'<polyline points="680,425 725,365 760,405 785,380 815,425" fill="none" '
                   f'stroke="{SUB}" stroke-width="3" stroke-linejoin="round"/>')
    f.parts.append(f'<circle cx="790" cy="345" r="12" fill="none" stroke="{SUB}" stroke-width="3"/>')
    f.text(747, 488, "画像", 24)

    f.arrow(465, 446, 584, 200)
    f.arrow(747, 262, 747, 309)
    f.save("erc-721_concept.svg")


def approval_figure():
    f = Svg(960, 410, "approve は 1 つの tokenId、setApprovalForAll は後から受け取る分も含めた全部")

    def tile(x, y, label, state):
        fill, stroke, sw, dash = {
            "held": ("#ffffff", SUB, 2, ""),
            "picked": (BLUE_PALE, BLUE, 4, ""),
            "later": ("#ffffff", SUB, 2, "8 6"),
        }[state]
        f.box(x, y, 96, 76, fill, stroke, sw=sw, dash=dash, rx=8)
        f.text(x + 48, y + 48, label, 26, SUB if state == "later" else INK)

    # Row 1: approve covers one tokenId.
    f.text(30, 40, "approve(carol, 3)", 26, anchor="start", weight="normal")
    f.text(30, 106, "alice の NFT", 24, SUB, anchor="start")
    for i, token in enumerate((2, 3, 4)):
        tile(245 + i * 120, 60, f"#{token}", "picked" if token == 3 else "held")
    f.text(640, 106, "carol は #3 だけ", 24, anchor="start")

    f.parts.append(f'<line x1="25" y1="168" x2="935" y2="168" stroke="{SUB}" '
                   'stroke-width="1.5" stroke-dasharray="4 4"/>')

    # Row 2: setApprovalForAll covers every NFT of alice in this contract.
    f.text(30, 212, "setApprovalForAll(bob, true)", 26, anchor="start", weight="normal")
    f.box(225, 232, 380, 120, OCHRE_PALE, OCHRE, sw=3.5, rx=14)
    f.text(30, 300, "alice の NFT", 24, SUB, anchor="start")
    tile(245, 254, "#2", "held")
    tile(365, 254, "#4", "held")
    tile(490, 254, "#5", "later")
    f.text(538, 388, "後で受け取る", 24, SUB)
    f.text(640, 285, "bob は全部を動かせる", 24, anchor="start")
    f.text(640, 323, "取り消すまで続く", 24, anchor="start")
    f.save("erc-721_approval.svg")


def metadata_figure():
    f = Svg(960, 540, "所有者が bob のまま、tokenId #2 の JSON は 3 回変わる")
    RED, RED_PALE = "#e15759", "#fbe3e3"
    stages = [
        ("最初", "24", "v1/2.json", "blue.svg", "ok"),
        ("サーバーで書き換え", "24", "v1/2.json", "red.svg", "ok"),
        ("setBaseURI(v2)", "25", "v2/2.json", "green.svg", "ok"),
        ("サーバーで削除", "25", "v2/2.json", "HTTP 404", "gone"),
    ]
    # The chain: one band, the owner never changes.
    f.box(25, 70, 910, 120, BLUE_PALE, BLUE, sw=3, rx=14)
    f.text(45, 108, "チェーン上の ownerOf(2)", 24, SUB, anchor="start")
    f.box(25, 250, 910, 270, OCHRE_PALE, OCHRE, sw=3, dash="12 8", rx=14)
    f.text(45, 288, "サーバーが返す JSON", 24, SUB, anchor="start")
    for i, (label, block, path, image, state) in enumerate(stages):
        cx = 140 + i * 227
        f.text(cx, 45, label, 24)
        f.text(cx, 150, "bob", 26)
        f.text(cx, 180, f"block {block}", 24, SUB)
        if state == "gone":
            f.box(cx - 95, 310, 190, 180, RED_PALE, RED, sw=3, rx=10)
        else:
            f.box(cx - 95, 310, 190, 180, "#ffffff", INK, sw=2, rx=10)
        f.text(cx, 352, path, 24, SUB)
        if state == "gone":
            f.text(cx, 425, image, 26)
        else:
            f.text(cx, 405, "image", 24, SUB)
            f.text(cx, 445, image, 26)
    # What moved the chain between the stages.
    for i, (s, color) in enumerate([("取引なし", SUB), ("取引 1 件", INK), ("取引なし", SUB)]):
        x = 140 + i * 227 + 113
        f.text(x, 230, s, 24, color)
    f.save("erc-721_metadata.svg")


if __name__ == "__main__":
    concept_figure()
    approval_figure()
    metadata_figure()
