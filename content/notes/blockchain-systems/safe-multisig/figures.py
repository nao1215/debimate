"""Generate the figures of the Safe note.

Each figure is built as SVG here, rendered by headless Chrome at 2x and saved
as WebP (Pillow). images/ keeps only the WebP files.

1. safe_overview.webp: owners sign off-chain, any EOA sends execTransaction to
   the Safe proxy (owners, threshold, nonce, assets), the proxy runs the
   singleton's code with delegatecall, and the code checks the signatures
   before calling the destination. The destination sees the proxy as the sender.
2. safe_operation.webp: operation 0 (call) runs the destination's code on its
   own storage; operation 1 (delegatecall) runs it on the proxy's storage, so
   the destination's code can overwrite the implementation address.

Run: python3 content/notes/blockchain-systems/safe-multisig/figures.py
(needs google-chrome and Pillow)
"""

from html import escape
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_F = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_F = "#d4a24c", "#f8eed8"
GRAY_F = "#f2f2f2"


class Svg:
    def __init__(self, width, height, title):
        self.size = (width, height)
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" '
            f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                          f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, x, y, r, fill, stroke):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=3, arrow=True, dash=""):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                          f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, path):
        """Render the SVG with headless Chrome at 2x and save it as WebP."""
        path.parent.mkdir(exist_ok=True)
        w, h = self.size
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={w},{h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(path, "WEBP", quality=90, method=6)


def overview_figure():
    s = Svg(960, 530, "所有者がチェーンの外で署名し、誰かの EOA が execTransaction を送る。"
                      "プロキシは実装のコードを delegatecall で動かし、署名を数えてから宛先を呼ぶ")
    # Owners (off-chain signing).
    s.box(24, 30, 140, 300, "#ffffff", SUB, sw=2, dash="8 6")
    s.text(94, 66, "所有者", 26)
    for i, (y, name) in enumerate(((120, "A"), (200, "B"), (280, "C"))):
        s.circle(94, y, 28, OCHRE_F if i < 2 else "#ffffff", OCHRE if i < 2 else SUB)
        s.text(94, y + 9, name, 26)
    s.text(94, 368, "チェーンの外で", 22, color=SUB)
    s.text(94, 398, "ハッシュに署名", 22, color=SUB)
    # Relayer EOA.
    s.box(262, 150, 170, 100, GRAY_F, SUB, sw=2)
    s.text(347, 192, "送信する EOA", 24)
    s.text(347, 228, "手数料を払う", 22, color=SUB)
    s.line(168, 200, 256, 200)
    s.text(212, 184, "署名 2 個", 20, color=SUB)
    # Proxy: storage (settings) and the ETH balance of the account.
    s.box(590, 20, 340, 300, BLUE_F, BLUE)
    s.text(760, 58, "Safe のプロキシ", 28)
    s.box(604, 72, 312, 188, "#ffffff", BLUE, sw=1.5, dash="6 5", rx=8)
    s.text(616, 98, "storage", 20, color=SUB, anchor="start")
    for i, row in enumerate(("所有者 A・B・C", "必要数（threshold）2", "nonce（通し番号）", "実装のアドレス")):
        s.text(760, 132 + i * 36, row, 22)
    s.box(604, 270, 312, 40, GRAY_F, SUB, sw=1.5, rx=6)
    s.text(760, 298, "ETH の残高", 22)
    s.line(436, 200, 582, 200)
    s.text(509, 184, "execTransaction", 19, color=SUB)
    # Implementation (code only).
    s.box(590, 390, 340, 120, "#ffffff", BLUE, dash="8 6")
    s.text(760, 428, "実装（singleton）", 28)
    s.text(760, 464, "署名を数える（checkNSignatures）", 20, color=SUB)
    s.text(760, 494, "取引を実行する（コードだけ）", 20, color=SUB)
    s.line(760, 322, 760, 382, dash="6 6")
    s.text(775, 356, "delegatecall", 22, color=SUB, anchor="start")
    # Destination: the sender seen by the destination is the proxy.
    s.box(262, 410, 170, 80, "#ffffff", SUB, sw=2)
    s.text(347, 458, "宛先", 24)
    s.line(586, 310, 438, 420)
    s.text(500, 296, "送金・呼び出し", 20, color=SUB, anchor="end")
    s.text(500, 322, "（送り主はプロキシ）", 20, color=SUB, anchor="end")
    s.save(HERE / "images" / "safe_overview.webp")


def operation_figure():
    """operation 0 runs the destination's code on its own storage;
    operation 1 runs it on the proxy's storage, so it can overwrite the implementation address."""
    s = Svg(960, 470, "operation = 0 は宛先の storage で動き、operation = 1 はプロキシの storage で動く")
    s.line(480, 30, 480, 440, "#d9d9d9", 2, arrow=False)
    for cx, title, op, dash, note1, note2 in (
            (240, "operation = 0（call）", "call", "", "宛先のコードは", "宛先の storage を使う"),
            (720, "operation = 1（delegatecall）", "delegatecall", "6 6", "宛先のコードが", "プロキシの storage を書き換えられる")):
        s.text(cx, 50, title, 26)
        s.box(cx - 190, 80, 380, 130, BLUE_F, BLUE)
        s.text(cx, 116, "Safe のプロキシ（storage）", 22)
        s.box(cx - 160, 136, 320, 36, "#ffffff", BLUE, sw=1.5, rx=6)
        s.text(cx, 162, "実装のアドレス", 22)
        s.box(cx - 150, 290, 300, 90, "#ffffff", SUB, sw=2)
        s.text(cx, 330, "宛先のコントラクト", 22)
        s.text(cx, 362, "（攻撃者が用意できる）" if op == "delegatecall" else "（自分の storage を持つ）", 20, color=SUB)
        s.line(cx, 212, cx, 284, dash=dash)
        s.text(cx + 12, 254, op, 20, color=SUB, anchor="start")
        s.text(cx, 412, note1, 20, color=SUB)
        s.text(cx, 440, note2, 20, color=SUB)
    # the dangerous write: from the destination back to the implementation address
    s.parts.append('<path d="M840 290 C 900 250, 900 190, 884 160" fill="none" stroke="#e15759" '
                   'stroke-width="3" marker-end="url(#arrow)"/>')
    s.text(886, 228, "上書き", 20, color="#e15759", anchor="end")
    s.save(HERE / "images" / "safe_operation.webp")


if __name__ == "__main__":
    overview_figure()
    operation_figure()
