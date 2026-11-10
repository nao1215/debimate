"""Generate the cover diagram of the Rollup note (Python stdlib only).

concept_figure() puts L2 above L1. Many L2 transactions are ordered and
executed by the sequencer and packed into a batch; only a state root and the
transaction data go down to the rollup contract on L1, which accepts the update
with a validity proof or after the challenge period.

Run: python3 content/notes/blockchain-systems/rollup/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """A tiny hand-written SVG builder (960x540, white background)."""

    def __init__(self, title, width=960, height=540):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
                for name, color in (("sub", SUB), ("accent", ACCENT), ("ochre", OCHRE)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}"{o} stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5, dash="", opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{o} '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, stroke, sw=4, fill="none"):
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg("L2 で実行した多数の取引と、L1 に届く state root と取引データ")
    # L2: many transactions are executed off L1.
    f.box(24, 24, 912, 266, PALE, rx=16)
    f.text(56, 68, "L2", 32, weight="normal", anchor="start")
    for row in range(5):
        for col in range(9):
            f.circle(118 + col * 34, 104 + row * 34, 9, ACCENT)
    f.text(254, 278, "利用者の取引", 24, SUB)
    f.line(416, 172, 456, 172, SUB, sw=4, arrow="sub")
    f.box(466, 112, 196, 120, "#ffffff", ACCENT, sw=3)
    f.text(564, 164, "sequencer", 26)
    f.text(564, 200, "順序付け・実行", 24, SUB)
    f.line(668, 172, 708, 172, SUB, sw=4, arrow="sub")
    for i in range(3):
        f.box(722 + i * 8, 104 + i * 8, 150, 112, PALE if i < 2 else "#ffffff",
              ACCENT, sw=3, rx=8)
    # The same transactions, packed tightly into one batch.
    for row in range(5):
        for col in range(9):
            f.circle(769 + col * 11, 154 + row * 11, 3.6, ACCENT)
    f.text(813, 254, "batch", 26)

    # L1: only a state root and the data arrive.
    f.box(24, 316, 912, 200, FILL, rx=16)
    f.text(56, 360, "L1", 32, weight="normal", anchor="start")
    f.line(813, 264, 813, 372, SUB, sw=4, arrow="sub")
    f.box(530, 382, 382, 116, "#ffffff", SUB, sw=3)
    f.text(721, 418, "rollup contract", 24, SUB)
    f.box(552, 438, 34, 34, ACCENT, rx=4)
    f.text(596, 465, "state root", 24, anchor="start")
    f.box(736, 446, 30, 18, ACCENT, rx=3)
    f.text(774, 465, "取引データ", 24, anchor="start")
    # The checker is a second actor on L1 (ochre), not a failure.
    f.box(70, 410, 330, 64, OCHRE_PALE, OCHRE, sw=3)
    f.text(235, 452, "証明 または challenge", 24, INK)
    f.line(406, 442, 518, 442, OCHRE, sw=4, arrow="ochre")
    f.save(HERE / "images" / "rollup_concept.svg")


def _plt(salt):
    """matplotlib with the site's monochrome settings (imported lazily)."""
    import sys
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(HERE / "lab"))
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": salt,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(HERE / "images" / name, metadata={"Date": None})


def batch_cost_figure():
    plt = _plt("rollup-batch-cost")
    from batch_cost import BLOB_BYTES, TX_BYTES, per_tx
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    n = list(range(1, 6001))
    exec_gas, blob_gas = zip(*(per_tx(k) for k in n))
    ax.plot(n, blob_gas, color=ACCENT, lw=2.4, label="blob gas per tx")
    ax.plot(n, exec_gas, color=RED, lw=2.4, label="execution gas per tx (21,000 / n)")
    full = BLOB_BYTES // TX_BYTES
    ax.axvline(full, color=SUB, ls="--", lw=1.2)
    ax.text(full * 1.08, 3e4, f"one blob full\nat {full} txs", color=SUB)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1, 6000)
    ax.set_xlabel(f"L2 transactions in one batch ({TX_BYTES} bytes each)")
    ax.set_ylabel("L1 gas per L2 transaction")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower left")
    _save(fig, "rollup_batch_cost.svg")


def retention_figure():
    """Blob retention (4096 epochs) against the withdrawal challenge periods."""
    blob_days = 4096 * 32 * 12 / 86400
    arbitrum_days = 45818 * 12 / 86400
    rows = [("blob の保持", blob_days, PALE, ACCENT, f"約 {blob_days:.0f} 日（4096 epoch）"),
            ("OP Mainnet", 7, OCHRE_PALE, OCHRE, "7 日"),
            ("Arbitrum One", arbitrum_days, OCHRE_PALE, OCHRE, f"約 {arbitrum_days:.1f} 日")]
    f = Svg("blob の保持期間約 18 日の内側に、約 1 週間の challenge 期間が収まる")
    f.text(480, 50, "blob の保持期間と、出金の challenge 期間", 26)
    x0, per_day, top = 250, 32, 110
    for d in range(0, 21, 5):
        x = x0 + d * per_day
        f.line(x, top - 10, x, 420, "#dddddd", sw=2)
        f.text(x, 455, f"{d}", 24, SUB)
    f.text(x0 + 10 * per_day, 500, "日", 24, SUB)
    for i, (label, days, fill, stroke, value) in enumerate(rows):
        y = top + i * 105
        f.text(x0 - 20, y + 45, label, 24, anchor="end")
        f.box(x0, y + 10, days * per_day, 56, fill, stroke, sw=2.5, rx=4)
        end = x0 + days * per_day
        if end + 14 + 20 * len(value) > 940:  # no room on the right: write inside
            f.text(end - 16, y + 47, value, 24, anchor="end")
        else:
            f.text(end + 14, y + 47, value, 24, anchor="start")
    f.save(HERE / "images" / "rollup_retention.svg")


if __name__ == "__main__":
    concept_figure()
    batch_cost_figure()
    retention_figure()
