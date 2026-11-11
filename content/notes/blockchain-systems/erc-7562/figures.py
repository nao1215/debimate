"""Generate the figures of the ERC-7562 note.

Run: python3 figures.py  -> images/*.webp

Each figure is built as SVG text here, rendered by headless Chrome at 2x and
saved as WebP (Pillow). Only the WebP files are kept in images/. The numbers
of erc-7562_paid.webp come from lab/output/summary.txt.
"""

from html import escape
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, NEUTRAL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"


def render(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """Small helper for the figures below (text 22px or larger)."""

    def __init__(self, title, w=960, h=540):
        self.w, self.h = w, h
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                          f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", rx=10, sw=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, arrow=True, sw=2.5):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" '
                          f'stroke-width="{sw}"{m}/>')

    def arrow(self, x1, y1, x2, y2):
        self.line(x1, y1, x2, y2)

    def cross(self, x, y, r=18):
        self.parts.append(f'<g stroke="{RED}" stroke-width="7" stroke-linecap="round">'
                          f'<line x1="{x - r}" y1="{y - r}" x2="{x + r}" y2="{y + r}"/>'
                          f'<line x1="{x - r}" y1="{y + r}" x2="{x + r}" y2="{y - r}"/></g>')

    def save(self, name):
        render("\n".join(self.parts + ["</svg>"]) + "\n", self.w, self.h, name)


def flow_figure():
    """Cover: the bundler simulates one UserOperation three times, then pays on chain."""
    f = Svg("送り主の UserOperation を Bundler が手元で 3 回検証し、handleOps を自分の EOA から送る。"
            "チェーンの上の EntryPoint で検証が失敗すると、手数料は Bundler が払う", 1220, 520)
    # Sender.
    f.box(20, 170, 150, 150, NEUTRAL, SUB)
    f.text(95, 235, "送り主", 24)
    f.text(95, 272, "UserOperation", 20, SUB)
    f.arrow(172, 245, 206, 245)
    # Off-chain: three simulations inside the bundler.
    f.box(210, 90, 616, 330, "#ffffff", BLUE, rx=16, sw=2.5, dash="9 6")
    f.text(518, 130, "Bundler の手元（シミュレーション）", 24)
    steps = [("① 受け取った時", "1 件だけ", "規則に合うか"),
             ("② バンドルの前", "1 件ずつ", "状態の変化"),
             ("③ 送る直前", "バンドル全体", "組み合わせ")]
    for i, (head, sub, what) in enumerate(steps):
        x = 230 + i * 200
        f.box(x, 165, 176, 160, BLUE_PALE, BLUE)
        f.text(x + 88, 210, head, 22)
        f.text(x + 88, 252, sub, 22, SUB)
        f.text(x + 88, 300, what, 22, SUB)
        if i < 2:
            f.arrow(x + 178, 245, x + 198, 245)
    f.text(518, 385, "ERC-7562 の規則で、ここの結果をチェーンでも保つ", 22, SUB)
    # On chain.
    f.arrow(828, 245, 916, 245)
    f.text(874, 282, "handleOps", 16, SUB)
    f.box(920, 120, 278, 250, OCHRE_PALE, OCHRE, rx=14)
    f.text(1059, 162, "チェーンの EntryPoint", 22)
    f.box(956, 190, 206, 62, "#ffffff", OCHRE)
    f.text(1059, 230, "検証", 24)
    f.arrow(1059, 254, 1059, 280)
    f.box(956, 284, 206, 62, "#ffffff", OCHRE)
    f.text(1059, 324, "実行", 24)
    f.text(1059, 430, "ここで検証が失敗すると", 22, SUB)
    f.text(1059, 462, "手数料は Bundler が払う", 22, SUB)
    f.save("erc-7562_flow.webp")


def concept_figure():
    """Validation reads only what the simulation can pin; the environment is fenced off."""
    f = Svg("検証は自分の storage と関連する slot だけを読み、時刻や他のコントラクトの storage は柵の外に置く",
            960, 540)
    f.text(150, 100, "ブロックまでに変わる値", 24, SUB)
    env = [("TIMESTAMP", 150), ("NUMBER", 250), ("関連しない storage", 350)]
    for label, y in env:
        f.box(40, y, 220, 64, OCHRE_PALE, OCHRE)
        f.text(150, y + 42, label, 25 if len(label) < 10 else 22)
    fx, fy = 306, 282
    for _, y in env:
        f.line(260, y + 32, fx - 20, fy + (y - 250) * 0.25, arrow=False, sw=2)
    f.cross(fx, fy)
    f.box(340, 70, 300, 400, BLUE_PALE, BLUE, rx=16, sw=3)
    f.text(490, 118, "検証", 30)
    f.text(490, 152, "ERC-7562 の規則（原則）", 22, SUB)
    f.box(370, 190, 240, 76, "#ffffff", BLUE)
    f.text(490, 237, "自分の storage", 25)
    f.box(370, 296, 240, 76, "#ffffff", BLUE)
    f.text(490, 330, "自分に関連する", 23)
    f.text(490, 360, "他の slot", 23)
    f.text(490, 412, "書き換えの影響は", 22, SUB)
    f.text(490, 444, "そのアカウントだけ", 22, SUB)
    f.arrow(640, 270, 694, 270)
    f.box(700, 170, 230, 200, NEUTRAL, SUB, rx=12, dash="8 6")
    f.text(815, 255, "実行", 30)
    f.text(815, 300, "任意のコード", 24, SUB)
    f.save("erc-7562_concept.webp")


def paid_figure():
    """Stage 3 of lab/output/summary.txt: who paid for the invalidated bundle."""
    import re
    out = (HERE / "lab" / "output" / "summary.txt").read_text(encoding="utf-8")
    attacker = int(re.search(r"attacker paid\s*: (\d+) gwei", out).group(1))
    bundler = int(re.search(r"bundler paid\s*: (\d+) gwei", out).group(1))
    accounts = int(re.search(r"10 GateAccounts\s*: (\d+) gwei", out).group(1))
    rows = [("Bundler", bundler, BLUE_PALE, BLUE),
            ("攻撃者", attacker, OCHRE_PALE, OCHRE),
            ("10 個の GateAccount", accounts, NEUTRAL, SUB)]
    f = Svg("Gate を閉じた攻撃者より、revert したバンドルを送った Bundler が多く払った")
    f.text(480, 70, "無効になったバンドル 1 件で払った額（gwei）", 26)
    x0, wmax, top = 300, 520, 130
    for i, (label, v, fill, stroke) in enumerate(rows):
        y = top + i * 120
        f.text(x0 - 20, y + 50, label, 24, anchor="end")
        w = wmax * v / bundler
        if w:
            f.box(x0, y + 15, w, 56, fill, stroke, rx=4)
        else:
            f.parts.append(f'<line x1="{x0}" y1="{y + 10}" x2="{x0}" y2="{y + 76}" '
                           f'stroke="{SUB}" stroke-width="2.5"/>')
        f.text(x0 + w + 16, y + 52, f"{v:,}", 24, anchor="start")
    f.text(480, 510, "同じブロックで Gate.close() を先に割り込ませた実験", 24, SUB)
    f.save("erc-7562_paid.webp")


def roles_figure():
    """ERC-4337 roles and who pays: the bundler pays gas, EntryPoint refunds only validated ops."""
    f = Svg("利用者が UserOperation を Bundler に送り、Bundler が handleOps を EntryPoint に送る。"
            "EntryPoint はアカウントの validateUserOp を呼び、通った分だけ deposit から Bundler に払い戻す", 1000, 470)
    boxes = [(20, "利用者", "UserOperation を作る", NEUTRAL, SUB),
             (270, "Bundler", "自分の EOA で送る", BLUE_PALE, BLUE),
             (520, "EntryPoint", "コントラクト", OCHRE_PALE, OCHRE),
             (770, "スマートアカウント", "validateUserOp", OCHRE_PALE, OCHRE)]
    for x, head, sub, fill, stroke in boxes:
        f.box(x, 150, 190, 120, fill, stroke)
        f.text(x + 95, 202, head, 20 if len(head) > 8 else 24)
        f.text(x + 95, 240, sub, 18, SUB)
    f.arrow(212, 210, 266, 210)
    f.text(240, 135, "UserOperation", 17, SUB)
    f.arrow(462, 190, 516, 190)
    f.text(490, 112, "handleOps", 17, SUB)
    f.text(490, 136, "ガス代は Bundler", 17, SUB)
    f.arrow(712, 210, 766, 210)
    f.text(740, 135, "検証→実行", 17, SUB)
    # Refund arrow from EntryPoint back to the bundler.
    f.parts.append(f'<path d="M615 272 C 615 360, 365 360, 365 276" fill="none" stroke="{OCHRE}" '
                   f'stroke-width="3" stroke-dasharray="8 6" marker-end="url(#arrow)"/>')
    f.text(490, 385, "アカウントか Paymaster の deposit から払い戻す（検証を通った分だけ）", 21)
    f.text(500, 430, "チェーンの外: 利用者・Bundler　　チェーンの上: EntryPoint・アカウント", 20, SUB)
    f.save("erc-7562_roles.webp")


def one_write_figure():
    """One write invalidates many ops when they share a slot, one op when slots are per account."""
    f = Svg("全員が同じスイッチを読むと 1 回の書き換えで 10 件が無効になる。"
            "各自の slot だけを読むと 1 回の書き換えで無効になるのは 1 件", 1000, 470)
    f.text(250, 50, "全員が同じ slot を読む", 24)
    f.text(750, 50, "各自の slot だけを読む", 24)
    f.parts.append(f'<line x1="500" y1="30" x2="500" y2="440" stroke="#d0d0d0" stroke-width="2"/>')
    # Left: one shared switch.
    f.box(170, 90, 160, 60, OCHRE_PALE, OCHRE)
    f.text(250, 128, "Gate.isOpen", 22)
    f.cross(360, 120, 14)
    f.text(410, 128, "1 回", 20, SUB)
    for i in range(10):
        x = 30 + i * 45
        f.line(250, 152, x + 18, 228, arrow=False, sw=1.5)
        f.box(x, 230, 36, 60, "#ffffff", RED, rx=6)
    f.text(250, 340, "10 件が無効", 24)
    f.text(250, 380, "1 回の書き換えで全員を止められる", 20, SUB)
    # Right: each account reads its own slot.
    for i in range(10):
        x = 530 + i * 45
        f.box(x, 100, 36, 40, OCHRE_PALE, OCHRE, rx=4)
        f.line(x + 18, 142, x + 18, 228, arrow=False, sw=1.5)
        f.box(x, 230, 36, 60, "#ffffff", RED if i == 0 else BLUE, rx=6)
    f.cross(548, 120, 12)
    f.text(548, 92, "1 回", 18, SUB)
    f.text(750, 340, "1 件だけ無効", 24)
    f.text(750, 380, "全員を止めるには件数分の書き換えが要る", 20, SUB)
    f.text(500, 450, "□ は UserOperation（赤は無効になったもの）", 18, SUB)
    f.save("erc-7562_one_write.webp")


def attacks_figure():
    """Where each of the three mass-invalidation methods is caught."""
    f = Svg("大量無効化の 3 つの方法と、見つかる場所。1 つ目は 2 回目の検証、2 つ目は 3 回目の検証で見つかる。"
            "3 つ目は 3 回目の後、ブロックの中で割り込む", 1000, 430)
    steps = [(30, "① 受け取った時"), (250, "② バンドルの前"), (470, "③ 送る直前"), (720, "ブロックの中")]
    for x, label in steps:
        w = 250 if x == 720 else 190
        fill, stroke = (OCHRE_PALE, OCHRE) if x == 720 else (BLUE_PALE, BLUE)
        f.box(x, 70, w, 70, fill, stroke)
        f.text(x + w / 2, 113, label, 22)
    for x in (222, 442, 662):
        f.arrow(x, 105, x + 24 if x != 662 else 716, 105)
    rows = [(200, "方法 1: 後で失敗する", 345),
            (270, "方法 2: 一緒だと失敗する", 565),
            (340, "方法 3: 前に割り込む", 845)]
    for y, label, xc in rows:
        f.text(20, y + 8, label, 21, anchor="start")
        f.line(290, y, xc - 24, y, arrow=False, sw=2)
        if xc == 845:
            f.cross(xc, y, 12)
            f.text(xc, y + 45, "検証の後なので見つからない", 19, RED)
        else:
            f.parts.append(f'<circle cx="{xc}" cy="{y}" r="16" fill="none" stroke="{BLUE}" stroke-width="4"/>')
            f.text(xc + 30, y + 8, "ここで見つかる", 20, SUB, anchor="start")
    f.save("erc-7562_attacks.webp")


def associated_figure():
    """Solidity puts balanceOf[A] at keccak(A || p): an associated slot of A inside the token contract."""
    f = Svg("トークンのコントラクトの storage。slot p は mapping 自体、keccak(A||p) は A の残高で A に関連する slot、"
            "keccak(B||p) は B の残高で A には関連しない", 1000, 420)
    f.text(500, 50, "トークンのコントラクトの storage（mapping balanceOf の slot 番号を p とする）", 22)
    rows = [("keccak(A || p)", "balanceOf[A]", "A に関連する slot", BLUE_PALE, BLUE, INK),
            ("keccak(B || p)", "balanceOf[B]", "A には関連しない", NEUTRAL, SUB, SUB),
            ("p 以外の固定の番号", "totalSupply など", "A には関連しない", NEUTRAL, SUB, SUB)]
    f.text(200, 105, "slot の番号", 20, SUB)
    f.text(470, 105, "値", 20, SUB)
    for i, (slot, val, note, fill, stroke, color) in enumerate(rows):
        y = 125 + i * 80
        f.box(80, y, 240, 60, fill, stroke, rx=6)
        f.text(200, y + 38, slot, 22)
        f.box(350, y, 240, 60, "#ffffff", stroke, rx=6)
        f.text(470, y + 38, val, 22)
        f.text(620, y + 38, note, 22, color, anchor="start")
    f.text(500, 400, "A の検証は、他人のコントラクトの中でも A に関連する slot なら読める", 21, SUB)
    f.save("erc-7562_associated.webp")


def entities_figure():
    """A UserOperation names up to four entities; staked ones get wider storage and are tracked."""
    f = Svg("UserOperation に関わる主体は、送り主のアカウント、Factory、Paymaster、Aggregator。"
            "stake した主体は EntryPoint に ETH を 1 日以上ロックし、広い storage を読める代わりに reputation で見張られる",
            1000, 460)
    f.box(30, 150, 220, 160, NEUTRAL, SUB)
    f.text(140, 215, "UserOperation", 22)
    f.text(140, 255, "に関わる主体", 20, SUB)
    ents = [("送り主のアカウント", "検証する本人"), ("Factory", "アカウントを作る"),
            ("Paymaster", "手数料を肩代わり"), ("Aggregator", "署名をまとめて検証")]
    for i, (head, sub) in enumerate(ents):
        y = 40 + i * 100
        f.box(330, y, 260, 80, BLUE_PALE, BLUE)
        f.text(460, y + 34, head, 22)
        f.text(460, y + 64, sub, 18, SUB)
        f.line(252, 230, 326, y + 40, sw=2)
    f.box(680, 120, 290, 220, OCHRE_PALE, OCHRE, rx=14)
    f.text(825, 165, "stake した場合", 24)
    f.text(825, 210, "EntryPoint に ETH を預け", 20, SUB)
    f.text(825, 240, "1 日以上ロック", 20, SUB)
    f.text(825, 295, "広い storage を読める", 20)
    f.arrow(594, 230, 676, 230)
    f.text(825, 390, "失敗の多さ（reputation）は", 19, SUB)
    f.text(825, 418, "stake の有無に関わらず数える", 19, SUB)
    f.save("erc-7562_entities.webp")


def tracer_figure():
    """How a bundler checks the rules: trace the validation, then match the trace against the rules."""
    f = Svg("Bundler は debug_traceCall と erc7562Tracer で検証を実行し、使った命令・触れた slot・keccak の入力を集め、"
            "ERC7562Parser で規則と照合して受け付けるか決める", 1000, 380)
    f.box(20, 120, 220, 120, NEUTRAL, SUB)
    f.text(130, 172, "UserOperation", 22)
    f.text(130, 208, "の検証", 20, SUB)
    f.arrow(242, 180, 286, 180)
    f.box(290, 100, 240, 160, BLUE_PALE, BLUE)
    f.text(410, 150, "debug_traceCall", 22)
    f.text(410, 185, "erc7562Tracer", 20, SUB)
    f.text(410, 225, "ノードが記録", 20, SUB)
    f.arrow(532, 180, 576, 180)
    f.box(580, 80, 200, 200, "#ffffff", BLUE)
    for i, t in enumerate(["使った命令", "触れた slot", "keccak の入力"]):
        f.text(680, 135 + i * 50, t, 21)
    f.arrow(782, 180, 826, 180)
    f.box(830, 105, 150, 150, OCHRE_PALE, OCHRE)
    f.text(905, 150, "規則と照合", 21)
    f.text(905, 185, "ERC7562Parser", 16, SUB)
    f.text(905, 225, "受け付けか拒否", 17, SUB)
    f.text(410, 320, "eth_call だけでは成否と戻り値しか分からない", 20, SUB)
    f.save("erc-7562_tracer.webp")


if __name__ == "__main__":
    roles_figure()
    flow_figure()
    one_write_figure()
    attacks_figure()
    associated_figure()
    entities_figure()
    tracer_figure()
    concept_figure()
    paid_figure()
