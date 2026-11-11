"""Generate the figures of the ERC-721 note (Python standard library only).

concept_figure(): the NFT contract on the chain holds tokenId -> owner and
returns tokenURI as a string; the JSON and the image it points to live on a
server outside the chain. The owners are illustrative.

log_figure(): the Transfer log of ERC-20 and ERC-721 side by side. topic0 is
the same hash; ERC-721 puts tokenId in topic3 and leaves the data empty,
ERC-20 puts the amount in the data (lab output: topics=4 data=0x).

lab_figure(): the cast of lab/run.py. Four default Anvil accounts (EOA),
the StudyNFT contract, the two recipients (Counter without NFT code and
StudyReceiver whose withdraw only keeper can call), and the loopback HTTP
server for the metadata JSON.

stuck_figure(): experiment 2 of lab/run.py. After transferFrom #1 to Counter,
alice's transferFrom(Counter, alice, 1) is rejected (not authorized) and
Counter has no code that calls the NFT contract, so nobody can move #1.

approval_figure(): approve covers one tokenId, setApprovalForAll covers every
NFT of the owner in the contract, including one received later (token #5 of
the lab).

metadata_figure(): experiment 4 of lab/run.py. The JSON of token #2 changes
three times while ownerOf(2) stays bob: a server-side edit (block 24, no
transaction), setBaseURI (block 25, no event), and a deletion (HTTP 404).
Values are copied from lab/output/summary.txt.

Run: python3 content/notes/blockchain-systems/erc-721/figures.py  -> images/*.webp
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GRAY_PALE = "#f2f2f2"


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
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
        """Build the SVG, render it with headless Chrome and write images/<name> as WebP."""
        (HERE / "images").mkdir(exist_ok=True)
        svg_text = "\n".join(self.parts + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def concept_figure():
    f = Svg(960, 540, "NFT コントラクトが持つのは tokenId と所有者の対応と URI の文字列で、"
                      "JSON と画像はチェーンの外のサーバーにある")
    # On the chain: the contract.
    f.box(25, 25, 470, 490, BLUE_PALE, BLUE, sw=3, rx=16)
    f.text(260, 70, "NFT コントラクト（チェーン上）", 26, weight="normal")
    f.text(130, 122, "tokenId", 24, SUB)
    f.text(345, 122, "所有者（ownerOf）", 24, SUB)
    rows = [("#1", "alice"), ("#2", "bob"), ("#3", "carol"), ("#4", "bob")]
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
    f.text(612, 232, '"image": "…/blue.svg"', 24, anchor="start")
    f.box(660, 315, 175, 130, GRAY_PALE, SUB, sw=2.5, rx=8)
    f.parts.append(f'<polyline points="680,425 725,365 760,405 785,380 815,425" fill="none" '
                   f'stroke="{SUB}" stroke-width="3" stroke-linejoin="round"/>')
    f.parts.append(f'<circle cx="790" cy="345" r="12" fill="none" stroke="{SUB}" stroke-width="3"/>')
    f.text(747, 488, "画像", 24)

    f.arrow(465, 446, 584, 200)
    f.arrow(747, 262, 747, 309)
    f.save("erc-721_concept.webp")


def log_figure():
    f = Svg(960, 380, "ERC-20 と ERC-721 の Transfer のログ: topic0 は同じで、tokenId は topics、数量はデータ欄")
    f.box(185, 20, 590, 50, BLUE_PALE, BLUE, sw=2, rx=8)
    f.text(480, 54, "topics（検索用の欄）", 22, SUB)
    f.box(790, 20, 150, 50, GRAY_PALE, SUB, sw=2, rx=8)
    f.text(865, 54, "データ欄", 22, SUB)
    cols = [("topic0", 185, 170), ("topic1", 365, 130), ("topic2", 505, 130), ("topic3", 645, 130)]
    for name, x, w in cols:
        f.text(x + w / 2, 105, name, 20, SUB)
    rows = [("ERC-20", ["0xddf252ad…", "from", "to", None], "数量"),
            ("ERC-721", ["0xddf252ad…", "from", "to", "tokenId"], "空（0x）")]
    for r, (label, tops, data) in enumerate(rows):
        y = 125 + r * 110
        f.text(30, y + 55, label, 24, anchor="start")
        for (name, x, w), v in zip(cols, tops):
            if v is None:
                f.box(x, y, w, 85, "#ffffff", SUB, sw=2, dash="8 6", rx=8)
                f.text(x + w / 2, y + 53, "なし", 22, SUB)
            else:
                same = v.startswith("0x")
                f.box(x, y, w, 85, OCHRE_PALE if same else "#ffffff", OCHRE if same else INK,
                      sw=3 if same else 2, rx=8)
                f.text(x + w / 2, y + 53, v, 22)
        f.box(790, y, 150, 85, "#ffffff", INK, sw=2, rx=8)
        f.text(865, y + 53, data, 22)
    f.text(270, 350, "同じ値（イベントの名前と引数の型のハッシュ）", 20, SUB, anchor="start")
    f.save("erc-721_log.webp")


def lab_figure():
    f = Svg(960, 500, "実験の登場人物: 4 つのテスト用アカウント、StudyNFT、2 つの宛先のコントラクト、JSON のサーバー")
    f.box(25, 25, 910, 350, BLUE_PALE, BLUE, sw=3, rx=16)
    f.text(45, 62, "ローカルのチェーン（Anvil）", 22, SUB, anchor="start")
    for i, (name, role) in enumerate([("alice", "発行者・最初の所有者"), ("bob", "全部の許可を受ける"),
                                      ("carol", "1 つの許可を受ける"), ("keeper", "withdraw を呼べる")]):
        x = 50 + i * 222
        f.box(x, 82, 200, 86, "#ffffff", SUB, sw=2, rx=8)
        f.text(x + 100, 118, name, 24)
        f.text(x + 100, 152, role, 18, SUB)
    f.text(480, 196, "EOA（テスト用アカウント）", 20, SUB)
    f.box(50, 222, 300, 110, "#ffffff", INK, sw=3, rx=10)
    f.text(200, 266, "StudyNFT", 26)
    f.text(200, 304, "学習用の ERC-721", 20, SUB)
    f.box(380, 222, 260, 110, GRAY_PALE, SUB, sw=2.5, rx=10)
    f.text(510, 266, "Counter", 24)
    f.text(510, 304, "NFT を扱うコードが無い", 20, SUB)
    f.box(660, 222, 250, 110, "#ffffff", SUB, sw=2.5, rx=10)
    f.text(785, 266, "StudyReceiver", 24)
    f.text(785, 304, "受け取り・withdraw", 20, SUB)
    f.text(645, 360, "宛先のコントラクト", 20, SUB)
    f.box(260, 410, 440, 70, OCHRE_PALE, OCHRE, sw=3, dash="12 8", rx=12)
    f.text(480, 453, "127.0.0.1 の HTTP サーバー（JSON）", 22)
    f.arrow(200, 334, 300, 406)
    f.text(150, 400, "tokenURI の指す先", 18, SUB)
    f.save("erc-721_lab.webp")


def stuck_figure():
    f = Svg(960, 470, "コントラクトが所有者になった NFT は、そのコードが呼ばない限り誰も動かせない")
    RED = "#c0392b"
    f.box(25, 30, 300, 120, "#ffffff", INK, sw=2.5, rx=10)
    f.text(175, 80, "alice", 26)
    f.text(175, 120, "EOA・秘密鍵で取引を送る", 21, SUB)
    f.box(635, 30, 300, 120, GRAY_PALE, SUB, sw=2.5, rx=10)
    f.text(785, 80, "Counter（コントラクト）", 22)
    f.text(785, 120, "コード: increment() だけ", 21, SUB)
    f.box(290, 300, 380, 140, BLUE_PALE, BLUE, sw=3, rx=14)
    f.text(480, 345, "NFT コントラクト", 24, SUB)
    f.text(480, 400, "#1 の所有者 = Counter", 26)
    f.arrow(175, 152, 380, 294)
    f.text(480, 200, "transferFrom(Counter, alice, 1)", 21)
    f.text(480, 236, "呼び出し元が所有者でないので拒否", 21, RED)
    f.parts.append(f'<circle cx="262" cy="212" r="20" fill="#ffffff" stroke="{RED}" stroke-width="3"/>')
    f.text(262, 221, "×", 26, RED)
    f.parts.append(f'<line x1="785" y1="152" x2="580" y2="294" stroke="{SUB}" stroke-width="3" '
                   'stroke-dasharray="10 8"/>')
    f.text(712, 262, "呼び出すコードが無い", 21, SUB, anchor="start")
    f.save("erc-721_stuck.webp")


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
    f.save("erc-721_approval.webp")


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
        f.text(cx, 180, f"ブロック {block}", 24, SUB)
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
    for i, (s, color) in enumerate([("取引なし", SUB), ("取引 1 件・イベントなし", INK), ("取引なし", SUB)]):
        x = 140 + i * 227 + 113
        f.text(x, 230, s, 24, color)
    f.save("erc-721_metadata.webp")


if __name__ == "__main__":
    concept_figure()
    log_figure()
    lab_figure()
    stuck_figure()
    approval_figure()
    metadata_figure()
