"""Generate the figures of the Blob note (written to images/ as WebP).

concept_figure()   calldata stays forever and is readable by the EVM; a blob is
                   attached to the transaction and dropped after about 18 days.
params_figure()    target / max blobs per block over time.
batch_cost_figure() L1 gas per L2 transaction against the batch size (lab/batch_cost.py).

Run: python3 content/notes/blockchain-systems/blob/figures.py
Needs google-chrome (headless, to render the SVG), matplotlib and Pillow.
"""

import io
import subprocess
import sys
import tempfile
from datetime import date
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, title, width=960, height=540):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" '
            f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/>'
            '</marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="normal" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=3, dash="", arrow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, name):
        IMAGES.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(
                ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                 f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def concept_figure():
    f = Svg("calldata は消す期限が無く EVM から読める。blob は取引に添付され、約 18 日で消える")
    x0, per_day = 300, 24  # 0..26 days
    for d in (0, 6, 12, 18, 24):
        x = x0 + d * per_day
        f.line(x, 80, x, 430, "#dddddd", sw=2)
        f.text(x, 462, str(d), 22, SUB)
    f.text(x0 + 13 * per_day, 500, "取引がブロックに入ってからの日数", 22, SUB)

    # calldata: inside the transaction, kept by every node.
    f.text(270, 150, "calldata", 26, anchor="end")
    f.text(270, 184, "取引の data 欄", 22, SUB, anchor="end")
    f.box(x0, 128, 26 * per_day - 10, 50, FILL, SUB, rx=4)
    f.text(x0 + 16, 162, "消す期限は無い　実行中は EVM から読める", 22, anchor="start")
    f.text(x0 + 16, 222, "実行と同じ gas で払う", 22, SUB, anchor="start")

    # blob: attached to the transaction, dropped after about 18 days.
    blob_days = 4096 * 32 * 12 / 86400
    f.text(270, 320, "blob", 26, anchor="end")
    f.text(270, 354, "取引に添付", 22, SUB, anchor="end")
    f.box(x0, 298, blob_days * per_day, 50, PALE, ACCENT, rx=4)
    f.box(x0 + blob_days * per_day + 6, 298, (26 - blob_days) * per_day - 16, 50,
          "#ffffff", SUB, sw=2, dash="6 6", rx=4)
    f.text(x0 + 16, 332, "約 18 日　中身は読めない", 22, anchor="start")
    f.text(x0 + blob_days * per_day + 20, 332, "消える", 22, SUB, anchor="start")
    f.text(x0 + 16, 392, "blob 用の gas で別に払う", 22, SUB, anchor="start")
    f.save("blob_concept.webp")


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 11, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def _save(fig, name):
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    buf.seek(0)
    Image.open(buf).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def params_figure():
    plt = _plt()
    changes = [(date(2024, 3, 13), 3, 6, "Cancun"), (date(2025, 5, 7), 6, 9, "Prague"),
               (date(2025, 12, 9), 10, 15, "BPO1"), (date(2026, 1, 7), 14, 21, "BPO2")]
    end = date(2026, 11, 10)
    xs = [c[0] for c in changes] + [end]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.step(xs, [c[2] for c in changes] + [changes[-1][2]], where="post", color=OCHRE,
            lw=2.4, label="1 ブロックの上限（max）")
    ax.step(xs, [c[1] for c in changes] + [changes[-1][1]], where="post", color=ACCENT,
            lw=2.4, label="1 ブロックの目標（target）")
    for i, (d, target, most, name) in enumerate(changes):
        label = f"{name}\n目標 {target} / 上限 {most}" if i == 0 else f"{name}\n{target} / {most}"
        dx = 4 if name == "BPO1" else 0
        ax.annotate(label, (d, most), xytext=(dx, 8), textcoords="offset points",
                    fontsize=9, color=SUB)
    fusaka = date(2025, 12, 3)
    ax.axvline(fusaka, color=SUB, ls=":", lw=1)
    ax.text(fusaka, 1, "Fusaka ", fontsize=9, color=SUB, ha="right")
    ax.set_ylabel("blob の個数")
    ax.set_ylim(0, 26)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    _save(fig, "blob_params.webp")


def batch_cost_figure():
    plt = _plt()
    sys.path.insert(0, str(HERE / "lab"))
    from batch_cost import BLOB_BYTES, TX_BYTES, per_tx
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    n = list(range(1, 6001))
    exec_gas, blob_gas = zip(*(per_tx(k) for k in n))
    ax.plot(n, blob_gas, color=ACCENT, lw=2.4, label="1 件あたりの blob gas")
    ax.plot(n, exec_gas, color=RED, lw=2.4, label="1 件あたりの実行の gas（execution gas、21,000 / 件数）")
    full = BLOB_BYTES // TX_BYTES
    ax.axvline(full, color=SUB, ls="--", lw=1.2)
    ax.text(full * 1.08, 3e4, f"{full} 件で\nblob 1 個が埋まる", color=SUB)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1, 6000)
    ax.set_xlabel(f"1 つの batch に入れる L2 の取引の件数（1 件 {TX_BYTES} バイト）")
    ax.set_ylabel("L2 の取引 1 件あたりの L1 の gas")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower left")
    _save(fig, "blob_batch_cost.webp")


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    concept_figure()
    params_figure()
    batch_cost_figure()
