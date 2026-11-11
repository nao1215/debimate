"""Generate the figures of the ERC-4337 note.

Run: python3 figures.py  -> images/*.webp

Each figure is built as SVG text here (stdlib only), rendered by headless
Chrome at 2x and saved as WebP (Pillow). Only the WebP files are kept in
images/. The numbers of the fees and gas figures come from
lab/output/summary.txt; this script reads the saved output and does not rerun
the experiment.

- concept_figure(): UserOperations travel off-chain to a bundler, and only the
  bundler's ordinary transaction (handleOps) reaches the unchanged protocol.
- loops_figure(): handleOps validates every UserOperation first, then executes.
- payflow_figure(): where the fee ETH comes from and goes to.
- fees_figure(): who paid each fee (section 3).
- gas_figure(): gas of each call frame (section 4).
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
GREEN, GREEN_F = "#8fae86", "#e9f1e6"
RED = "#e15759"
GRAY_F = "#f2f2f2"


def render(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        (HERE / "images").mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("ink", INK), ("sub", SUB), ("ochre", OCHRE), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, name):
        render("\n".join(self.parts + ["</svg>"]) + "\n", self.w, self.h, name)


def concept_figure():
    s = Svg(960, 540, "UserOperation はチェーンの外で Bundler に渡り、チェーンに載るのは Bundler の普通の取引 1 件だけ")
    # Off-chain layer: dashed outline, no fill.
    s.box(16, 16, 928, 248, "none", SUB, sw=2, dash="8 6")
    s.text(36, 54, "チェーンの外（UserOperation の mempool）", size=24, color=SUB, anchor="start")
    for i in range(3):  # stacked UserOperation cards
        s.box(52 + i * 14, 92 + i * 14, 236, 92, BLUE_F, BLUE)
    s.text(198, 152, "UserOperation", size=26)
    s.text(198, 186, "署名の形式は自由", size=22, color=SUB)
    s.line(320, 150, 430, 150, INK, arrow="ink")
    s.box(440, 96, 220, 108, OCHRE_F, OCHRE)
    s.text(550, 142, "Bundler", size=28)
    s.text(550, 180, "EOA・ガス代を払う", size=22, color=SUB)
    # On-chain layer: gray fill = the protocol, unchanged.
    s.box(16, 284, 928, 240, GRAY_F)
    s.text(36, 322, "チェーンの上（プロトコルは従来のまま）", size=24, color=SUB, anchor="start")
    s.line(500, 208, 500, 350, INK, arrow="ink")
    s.text(488, 244, "handleOps の取引", size=22, anchor="end")
    s.line(610, 350, 610, 214, OCHRE, dash="10 8", arrow="ochre")
    s.text(626, 244, "手数料を ETH で返す", size=22, anchor="start")
    s.box(36, 356, 600, 148, "#ffffff", INK, sw=2)
    s.text(70, 390, "EntryPoint", size=26, anchor="start")
    s.box(56, 408, 260, 80, BLUE_F, BLUE)
    s.text(186, 444, "1. 検証", size=26)
    s.text(186, 476, "使える処理に制限", size=22, color=SUB)
    s.line(324, 448, 354, 448, INK, arrow="ink")
    s.box(362, 408, 256, 80, GREEN_F, GREEN)
    s.text(490, 444, "2. 実行", size=26)
    s.text(490, 476, "任意のコード", size=22, color=SUB)
    s.box(676, 346, 248, 70, BLUE_F, BLUE)
    s.text(800, 390, "スマートアカウント", size=24)
    s.box(676, 434, 248, 70, BLUE_F, BLUE, dash="8 6")
    s.text(800, 466, "Paymaster", size=24)
    s.text(800, 494, "（使う場合）", size=20, color=SUB)
    s.line(636, 380, 668, 380, INK, arrow="ink")
    s.line(636, 468, 668, 468, INK, arrow="ink")
    s.save("erc-4337_concept.webp")


def loops_figure():
    s = Svg(960, 580, "handleOps は全ての UserOperation を先に検証し、その後で実行する")
    s.text(480, 42, "EntryPoint の handleOps（Bundler が送る 1 件の取引）", size=26)
    s.text(480, 80, "検証は全て、どの実行よりも前に終わる（実行で他の検証の結果が変わらない）", size=20, color=SUB)
    y0 = 110
    cols = [(20, BLUE_F, BLUE, "1 回目のループ：検証", "アカウントの作成・署名の確認・前払い"),
            (540, GREEN_F, GREEN, "2 回目のループ：実行", "callData（させたい操作）を実行")]
    for x, face, edge, head, sub in cols:
        s.box(x, y0, 400, 290, "#ffffff", edge, sw=2.5, rx=14)
        s.text(x + 200, y0 + 42, head, size=26)
        s.text(x + 200, y0 + 76, sub, size=19, color=SUB)
        for i in range(3):
            s.box(x + 40, y0 + 100 + i * 60, 320, 46, face, edge, rx=8)
            s.text(x + 200, y0 + 131 + i * 60, f"UserOperation {i + 1}", size=22)
    s.line(428, y0 + 145, 530, y0 + 145, INK, sw=3, arrow="ink")
    s.text(480, y0 + 184, "全て", size=20, color=SUB)
    s.text(480, y0 + 210, "通ったら", size=20, color=SUB)
    # Validation failure: the whole transaction reverts.
    y1 = y0 + 292
    s.line(220, y1, 220, y1 + 32, RED, sw=3, arrow="red")
    s.text(220, y1 + 66, "1 件でも検証に失敗すると", size=20)
    s.text(220, y1 + 96, "handleOps 全体が取り消し（FailedOp など）", size=20)
    s.text(220, y1 + 128, "前払いも戻り、ガス代は Bundler の損", size=20, color=SUB)
    s.text(740, y1 + 66, "実行が失敗しても、使ったガスの", size=20, color=SUB)
    s.text(740, y1 + 96, "手数料はアカウントか Paymaster が払う", size=20, color=SUB)
    s.save("erc-4337_loops.webp")


def payflow_figure():
    s = Svg(960, 500, "手数料の ETH は、アカウントの残高か Paymaster の deposit から EntryPoint を経て Bundler に渡る")
    # Sources.
    s.box(20, 60, 220, 110, BLUE_F, BLUE)
    s.text(130, 104, "アカウントの残高", size=24)
    s.text(130, 140, "（ETH）", size=20, color=SUB)
    s.box(20, 300, 220, 110, OCHRE_F, OCHRE)
    s.text(130, 344, "Paymaster", size=24)
    s.text(130, 380, "前もって預ける", size=20, color=SUB)
    # EntryPoint deposits.
    s.box(380, 30, 280, 420, "#ffffff", INK, sw=2, rx=14)
    s.text(520, 70, "EntryPoint", size=26)
    s.box(400, 90, 240, 110, BLUE_F, BLUE)
    s.text(520, 134, "アカウントの", size=22)
    s.text(520, 166, "deposit", size=22)
    s.box(400, 300, 240, 110, OCHRE_F, OCHRE)
    s.text(520, 344, "Paymaster の", size=22)
    s.text(520, 376, "deposit", size=22)
    s.line(242, 125, 392, 140, INK, sw=3, arrow="ink")
    s.text(306, 82, "検証の中で", size=18, color=SUB)
    s.text(306, 108, "不足分を前払い", size=18, color=SUB)
    s.line(242, 355, 392, 355, INK, sw=3, arrow="ink")
    # Bundler.
    s.box(730, 180, 210, 120, GRAY_F, SUB)
    s.text(835, 226, "Bundler", size=26)
    s.text(835, 264, "beneficiary", size=20, color=SUB)
    s.line(642, 150, 722, 215, OCHRE, sw=3, arrow="ochre")
    s.line(642, 350, 722, 270, OCHRE, sw=3, arrow="ochre")
    s.text(835, 340, "実際に使った分を払う", size=20, color=SUB)
    s.text(835, 368, "余りは deposit に残る", size=20, color=SUB)
    s.text(480, 484, "Paymaster を指定した UserOperation は、Paymaster の deposit から払う", size=20, color=SUB)
    s.save("erc-4337_payflow.webp")


def load_summary():
    text = (HERE / "lab" / "output" / "summary.txt").read_text().splitlines()
    addr = next(l.split(":")[1].strip() for l in text if l.startswith("CREATE2 formula"))
    funded = next(l for l in text if l.startswith("code before"))
    code_after = next(l for l in text if l.startswith("code after op1"))
    balance = funded.split("balance:")[1].strip()
    code_bytes = int(code_after.split(":")[1].split()[0])
    fees, gas, section = [], [], None
    for line in text:
        if line.startswith("# "):
            section = line[2]
            continue
        cells = [c.strip() for c in line.split("|")]
        if section == "3" and line.startswith("op"):
            sender, pm, tx_fee, received = (int(c) for c in cells[1:5])
            # The account also sent 0.01 ETH = 10,000,000 gwei; the rest is the fee.
            fees.append((cells[0], -sender - 10_000_000, -pm, -tx_fee, received))
        if section == "4" and not line.startswith(("case", "Assertions")):
            gas.append((cells[0], [int(c) for c in cells[1:] if c]))
    return addr, balance, code_bytes, fees, gas


def fees_figure():
    *_, fees, _ = load_summary()
    s = Svg(960, 540, "UserOperation ごとの手数料の出どころと、Bundler 自身の取引のガス代")
    legend = [(BLUE_F, BLUE, "アカウントが払う"), (OCHRE_F, OCHRE, "Paymaster が払う"),
              (GRAY_F, SUB, "Bundler 自身の取引のガス代")]
    for i, (face, edge, label) in enumerate(legend):
        x = 40 + i * 270
        s.box(x, 30, 32, 26, face, edge, rx=4)
        s.text(x + 44, 52, label, size=22, anchor="start")
    names = {"op1 initCode, self-paid": ("op1", "作成・自分で払う"),
             "op2 self-paid": ("op2", "自分で払う"),
             "op3 paymaster": ("op3", "Paymaster")}
    scale = 420 / max(max(a, p, t) for _, a, p, t, _r in fees)
    x0 = 260
    for i, (name, by_account, by_pm, tx_fee, _received) in enumerate(fees):
        y = 110 + i * 136
        head, sub = names[name]
        s.text(30, y + 32, head, size=28, anchor="start")
        s.text(30, y + 70, sub, size=22, color=SUB, anchor="start")
        charged = by_account + by_pm
        face, edge = (BLUE_F, BLUE) if by_account else (OCHRE_F, OCHRE)
        s.box(x0, y + 8, charged * scale, 34, face, edge, rx=3)
        s.text(x0 + charged * scale + 14, y + 35, f"{charged:,}", size=22, anchor="start")
        s.box(x0, y + 52, tx_fee * scale, 34, GRAY_F, SUB, rx=3)
        s.text(x0 + tx_fee * scale + 14, y + 79, f"{tx_fee:,}（差 +{_received - tx_fee:,}）", size=22, color=SUB, anchor="start")
    s.text(930, 520, "単位は gwei", size=22, color=SUB, anchor="end")
    s.save("erc-4337_fees.webp")


def gas_figure():
    *_, gas = load_summary()
    s = Svg(960, 500, "1 件の取引のガスの内訳と、EOA の送金との比較")
    legend = [(OCHRE_F, OCHRE, "アカウントの作成"), (BLUE_F, BLUE, "検証（アカウント＋Paymaster）"),
              (GREEN_F, GREEN, "実行"), (GRAY_F, SUB, "EntryPoint・呼び出しデータ・基本料")]
    for i, (face, edge, label) in enumerate(legend):
        x, y = 40 + (i % 2) * 440, 24 + (i // 2) * 40
        s.box(x, y, 30, 24, face, edge, rx=4)
        s.text(x + 42, y + 21, label, size=20, anchor="start")
    names = {"op1 initCode, self-paid": "op1：作成・自分で払う", "op2 self-paid": "op2：自分で払う",
             "op3 paymaster": "op3：Paymaster", "EOA transfer (baseline)": "EOA の送金"}
    x0, scale = 260, 560 / 300_000
    for i, (name, nums) in enumerate(gas):
        y = 130 + i * 80
        s.text(x0 - 16, y + 30, names[name], size=21, anchor="end")
        if len(nums) == 1:
            parts, tx = [(nums[0], GRAY_F, SUB)], nums[0]
        else:
            tx, _op, create, validate, pm, execute = nums
            parts = [(create, OCHRE_F, OCHRE), (validate + pm, BLUE_F, BLUE),
                     (execute, GREEN_F, GREEN), (tx - create - validate - pm - execute, GRAY_F, SUB)]
        left = x0
        for width, face, edge in parts:
            if width:
                s.box(left, y + 4, width * scale, 40, face, edge, sw=2, rx=2)
            left += width * scale
        s.text(left + 12, y + 32, f"{tx:,}", size=21, anchor="start")
    s.line(x0, 120, x0, 450, SUB, sw=2)
    s.text(x0 + 280, 486, "取引が使ったガス", size=20, color=SUB)
    s.save("erc-4337_gas.webp")


if __name__ == "__main__":
    concept_figure()
    loops_figure()
    payflow_figure()
    fees_figure()
    gas_figure()
