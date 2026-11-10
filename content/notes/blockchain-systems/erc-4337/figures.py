"""Generate the figures of the ERC-4337 note.

concept_figure() draws, as a hand-written SVG (stdlib only), the two layers of
ERC-4337: UserOperations travel off-chain through their own mempool to a
bundler, and only the bundler's ordinary transaction (handleOps) reaches the
unchanged Ethereum protocol, where the EntryPoint validates and then executes.

gas_figure() plots the gas columns of lab/output/summary.txt as stacked bars.
It reads the saved output and does not rerun the experiment.

counterfactual_figure() and fees_figure() draw, as hand-written SVGs, the
address steps (section 1) and the fee rows (section 3) of the same summary.txt.

Run: python3 content/notes/blockchain-systems/erc-4337/figures.py
"""

from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_F = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_F = "#d4a24c", "#f8eed8"
GREEN, GREEN_F = "#8fae86", "#e9f1e6"
GRAY_F = "#f2f2f2"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("ink", INK), ("sub", SUB), ("ochre", OCHRE)))
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

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    s = Svg(960, 540, "ERC-4337: UserOperations off-chain, one ordinary transaction on-chain")
    # Off-chain layer: dashed outline, no fill.
    s.box(16, 16, 928, 248, "none", SUB, sw=2, dash="8 6")
    s.text(36, 54, "off-chain: UserOperation mempool", size=24, color=SUB, anchor="start")
    for i in range(3):  # stacked UserOperation cards
        s.box(52 + i * 14, 92 + i * 14, 236, 92, BLUE_F, BLUE)
    s.text(198, 152, "UserOperation", size=26)
    s.text(198, 186, "any signature", size=24, color=SUB)
    s.line(320, 150, 430, 150, INK, arrow="ink")
    s.box(440, 96, 220, 108, OCHRE_F, OCHRE)
    s.text(550, 142, "Bundler", size=28)
    s.text(550, 180, "EOA, pays gas", size=24, color=SUB)
    # On-chain layer: gray fill = the protocol, unchanged.
    s.box(16, 284, 928, 240, GRAY_F)
    s.text(36, 322, "on-chain: unchanged protocol", size=24, color=SUB, anchor="start")
    s.line(500, 208, 500, 350, INK, arrow="ink")
    s.text(488, 244, "handleOps tx", size=24, anchor="end")
    s.line(610, 350, 610, 214, OCHRE, dash="10 8", arrow="ochre")
    s.text(626, 244, "fees paid in ETH", size=24, anchor="start")
    s.box(36, 356, 600, 148, "#ffffff", INK, sw=2)
    s.text(70, 390, "EntryPoint", size=26, anchor="start")
    s.box(56, 408, 260, 80, BLUE_F, BLUE)
    s.text(186, 444, "1. validate", size=26)
    s.text(186, 476, "restricted", size=24, color=SUB)
    s.line(324, 448, 354, 448, INK, arrow="ink")
    s.box(362, 408, 256, 80, GREEN_F, GREEN)
    s.text(490, 444, "2. execute", size=26)
    s.text(490, 476, "any code", size=24, color=SUB)
    s.box(676, 346, 248, 70, BLUE_F, BLUE)
    s.text(800, 390, "smart account", size=26)
    s.box(676, 434, 248, 70, BLUE_F, BLUE, dash="8 6")
    s.text(800, 478, "paymaster", size=26)
    s.line(636, 380, 668, 380, INK, arrow="ink")
    s.line(636, 468, 668, 468, INK, arrow="ink")
    s.save(HERE / "images" / "erc-4337_concept.svg")


def load_gas():
    rows, in_gas = [], False
    for line in (HERE / "lab" / "output" / "summary.txt").read_text().splitlines():
        if line.startswith("# 4."):
            in_gas = True
            continue
        if not in_gas or line.startswith(("case", "Assertions")):
            continue
        cells = [c.strip() for c in line.split("|")]
        nums = [int(c) for c in cells[1:] if c]
        rows.append((cells[0], nums))
    return rows


def gas_figure():
    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "erc-4337",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = load_gas()
    labels = {"op1 initCode, self-paid": "op1: create + self-paid",
              "op2 self-paid": "op2: self-paid",
              "op3 paymaster": "op3: paymaster",
              "EOA transfer (baseline)": "EOA transfer"}
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    for y, (name, nums) in enumerate(reversed(rows)):
        if len(nums) == 1:
            ax.barh(y, nums[0], color=GRAY_F, edgecolor=SUB, height=0.6)
            ax.text(nums[0] + 3000, y, f"{nums[0]:,}", va="center", fontsize=10)
            continue
        tx, _op, create, validate, pm, execute = nums
        parts = [(create, OCHRE_F, OCHRE), (validate + pm, BLUE_F, BLUE),
                 (execute, GREEN_F, GREEN), (tx - create - validate - pm - execute, GRAY_F, SUB)]
        left = 0
        for width, face, edge in parts:
            ax.barh(y, width, left=left, color=face, edgecolor=edge, height=0.6)
            left += width
        ax.text(tx + 3000, y, f"{tx:,}", va="center", fontsize=10)
    ax.set_yticks(range(len(rows)), [labels[n] for n, _ in reversed(rows)])
    ax.set_xlabel("gas used by the transaction")
    ax.set_xlim(0, 340000)
    ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=f, edgecolor=e) for _, f, e in
               ((0, OCHRE_F, OCHRE), (0, BLUE_F, BLUE), (0, GREEN_F, GREEN), (0, GRAY_F, SUB))]
    ax.legend(handles, ["create account", "validate (account + paymaster)", "execute",
                        "EntryPoint, calldata, 21,000 base"],
              loc="lower right", fontsize=10, frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "erc-4337_gas.svg", metadata={"Date": None})
    plt.close(fig)


def load_summary():
    text = (HERE / "lab" / "output" / "summary.txt").read_text().splitlines()
    addr = next(l.split(":")[1].strip() for l in text if l.startswith("CREATE2 formula"))
    funded = next(l for l in text if l.startswith("code before"))
    code_after = next(l for l in text if l.startswith("code after op1"))
    balance = funded.split("balance:")[1].strip()
    code_bytes = int(code_after.split(":")[1].split()[0])
    fees, in_fee = [], False
    for line in text:
        if line.startswith("# 3."):
            in_fee = True
            continue
        if line.startswith("# 4."):
            break
        if in_fee and line.startswith("op"):
            cells = [c.strip() for c in line.split("|")]
            sender, pm, tx_fee, received = (int(c) for c in cells[1:5])
            # The account also sent 0.01 ETH = 10,000,000 gwei; the rest is the fee.
            fees.append((cells[0], -sender - 10_000_000, -pm, -tx_fee, received))
    return addr, balance, code_bytes, fees


def counterfactual_figure():
    addr, balance, code_bytes, _ = load_summary()
    s = Svg(960, 540, "The account address is fixed before the account exists")
    short = f"{addr[:6]}...{addr[-4:]}"
    s.text(480, 56, f"account address {short}", size=28)
    s.text(480, 94, "the same address in all three steps", size=24, color=SUB)
    cols = [
        (BLUE_F, BLUE, "1. compute", ["CREATE2 formula", "factory.getAddress", "getSenderAddress", "all three equal"]),
        (OCHRE_F, OCHRE, "2. receive ETH", ["code: 0x (empty)", f"balance: {balance}"]),
        (GREEN_F, GREEN, "3. op1 initCode", [f"code: {code_bytes} bytes", "ERC1967Proxy"]),
    ]
    for i, (face, edge, head, lines) in enumerate(cols):
        x = 24 + i * 316
        s.box(x, 140, 280, 340, face, edge)
        s.text(x + 140, 196, head, size=28)
        for j, ln in enumerate(lines):
            last = head.startswith("1.") and j == len(lines) - 1
            s.text(x + 140, 270 + j * 52 + (24 if last else 0), ln, size=24, color=INK if last else SUB)
        if i < 2:
            s.line(x + 284, 310, x + 312, 310, INK, sw=3, arrow="ink")
    s.save(HERE / "images" / "erc-4337_counterfactual.svg")


def fees_figure():
    *_, fees = load_summary()
    s = Svg(960, 540, "Who pays the fee of each UserOperation, and what the bundler spends")
    legend = [(BLUE_F, BLUE, "account pays"), (OCHRE_F, OCHRE, "paymaster pays"),
              (GRAY_F, SUB, "bundler's own tx fee")]
    for i, (face, edge, label) in enumerate(legend):
        x = 40 + i * 300
        s.box(x, 30, 32, 26, face, edge, rx=4)
        s.text(x + 44, 52, label, size=24, anchor="start")
    names = {"op1 initCode, self-paid": ("op1", "create, self-paid"),
             "op2 self-paid": ("op2", "self-paid"),
             "op3 paymaster": ("op3", "paymaster")}
    scale = 520 / max(max(a, p, t) for _, a, p, t, _r in fees)
    x0 = 250
    for i, (name, by_account, by_pm, tx_fee, _received) in enumerate(fees):
        y = 110 + i * 136
        head, sub = names[name]
        s.text(30, y + 32, head, size=28, anchor="start")
        s.text(30, y + 70, sub, size=24, color=SUB, anchor="start")
        charged = by_account + by_pm
        face, edge = (BLUE_F, BLUE) if by_account else (OCHRE_F, OCHRE)
        s.box(x0, y + 8, charged * scale, 34, face, edge, rx=3)
        s.text(x0 + charged * scale + 14, y + 35, f"{charged:,}", size=24, anchor="start")
        s.box(x0, y + 52, tx_fee * scale, 34, GRAY_F, SUB, rx=3)
        s.text(x0 + tx_fee * scale + 14, y + 79, f"{tx_fee:,}", size=24, color=SUB, anchor="start")
    s.text(930, 520, "gwei", size=24, color=SUB, anchor="end")
    s.save(HERE / "images" / "erc-4337_fees.svg")


if __name__ == "__main__":
    concept_figure()
    gas_figure()
    counterfactual_figure()
    fees_figure()
