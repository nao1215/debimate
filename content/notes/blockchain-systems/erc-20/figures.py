"""Generate the figures of the ERC-20 note.

concept_figure() draws the token contract as a hand-written SVG (stdlib only):
the balanceOf table and the allowance table inside the contract, and the ETH
balance outside it. transfer 5 changes two rows of balanceOf, approve 30
changes one row of allowance. The values are those of lab/output/summary.txt.

stages_figure() plots lab/output/summary.txt (owner, receiver, allowance per
stage) as steps and marks the stages whose transaction failed (status 0).
It reads the saved output and does not rerun the experiment.

Both are rendered to PNG (the SVG with headless Chrome at 2x, the plot with
dpi 200) and saved as WebP with Pillow. Only the WebP files are kept in images/.
Needs google-chrome, matplotlib and Pillow.

Run: python3 content/notes/blockchain-systems/erc-20/figures.py
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE = "#d4a24c"


class Svg:
    def __init__(self, width, height, title):
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("ink", INK), ("sub", SUB), ("accent", ACCENT), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle",
             rotate=None):
        r = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}"{r}>{escape(s)}</text>')

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
        to_webp_from_svg("\n".join(self.parts + ["</svg>"]) + "\n",
                         self.width, self.height, name)


def to_webp(png, name):
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP",
                                        quality=90, method=6)


def to_webp_from_svg(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu",
                        "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size={w},{h}", f"--screenshot={png}",
                        svg.as_uri()], check=True, capture_output=True)
        to_webp(png, name)

plt.rcParams.update({
    "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "erc-20",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def load():
    rows = []
    for line in (HERE / "lab" / "output" / "summary.txt").read_text().splitlines()[1:]:
        cols = [c.strip() for c in line.split("|")]
        if len(cols) != 5:
            continue
        label, owner, receiver, allowance, status = cols
        rows.append((label, int(owner), int(receiver), int(allowance),
                     None if status == "-" else int(status)))
    assert len(rows) == 7, rows
    return rows


def stages_figure():
    rows = load()
    x = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    series = [(1, "所有者の残高", INK, "-"), (2, "受取人の残高", ACCENT, "-"),
              (3, "承認額（所有者 → spender）", SUB, "--")]
    for i, label, color, ls in series:
        ax.step(x, [r[i] for r in rows], where="mid", color=color, lw=2.4,
                ls=ls, label=label)
        ax.plot(x, [r[i] for r in rows], "o", color=color, ms=4)
    failed = [k for k, r in enumerate(rows) if r[4] == 0]
    for k in failed:
        ax.axvspan(k - 0.5, k + 0.5, color=RED, alpha=0.12, lw=0)
    ax.plot(failed, [108] * len(failed), "x", color=RED, ms=10, mew=2.6,
            label="失敗した取引（status 0）")
    names = {"initial": "初期", "spend 10": "10 枚利用", "overspend 21": "21 枚利用",
             "revoke": "approve 0", "spend after revoke": "取り消し後に\n1 枚利用"}
    ax.set_xticks(x, [names.get(r[0], r[0]) for r in rows],
                  fontsize=9, rotation=25, ha="right")
    ax.set_ylabel("枚数")
    ax.set_ylim(-4, 115)
    ax.set_xlim(-0.5, len(rows) - 0.5)
    ax.legend(loc="center left", bbox_to_anchor=(0.01, 0.55), frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        to_webp(png, "erc-20_stages.webp")


def concept_figure():
    rows = {r[0]: r for r in load()}
    init, sent, appr = rows["initial"], rows["transfer 5"], rows["approve 30"]
    f = Svg(960, 540, "transfer と approve がトークンコントラクトのどの行を変えるか")

    # The token contract holds both tables.
    f.box(25, 30, 640, 400, "#ffffff", INK, sw=3, rx=16)
    f.text(345, 72, "トークンコントラクト", 28, weight="normal")

    def table(x, title, cells):
        f.text(x + 135, 125, title, 26, SUB)
        for i, (key, value, style) in enumerate(cells):
            y = 145 + i * 82
            fill, stroke, color, weight = {
                "plain": ("#ffffff", SUB, INK, "normal"),
                "blue": (ACCENT, ACCENT, INK, "normal"),
                "ochre": (OCHRE, OCHRE, INK, "normal"),
            }[style]
            f.box(x, y, 270, 70, fill, stroke, sw=2.5, rx=8)
            f.text(x + 62, y + 44, key, 24, color, weight)
            f.line(x + 124, y + 10, x + 124, y + 60,
                   "#ffffff" if style != "plain" else SUB, sw=2)
            f.text(x + 197, y + 44, value, 24, color, weight)

    table(55, "balanceOf", [
        ("所有者", f"{init[1]} → {sent[1]}", "blue"),
        ("受取人", f"{init[2]} → {sent[2]}", "blue"),
        ("spender", "0", "plain"),
    ])
    table(365, "allowance", [
        ("spender", f"{sent[3]} → {appr[3]}", "ochre"),
    ])
    f.text(500, 270, "所有者が spender に", 24, SUB)
    f.text(500, 302, "認めた額", 24, SUB)

    # ETH balances live in the account state, outside the contract.
    f.box(700, 120, 235, 230, FILL, SUB, sw=2.5, dash="10 7", rx=14)
    f.text(817, 100, "コントラクトの外", 24, SUB)
    f.text(817, 165, "アカウントの状態", 24, INK)
    for i, name in enumerate(("所有者", "受取人")):
        y = 190 + i * 74
        f.box(725, y, 185, 60, "#ffffff", SUB, sw=2, rx=8)
        f.text(817, y + 40, f"{name}の ETH", 24, INK)

    ly = 490
    for x, fill, label in ((60, ACCENT, "transfer 5 で変わる"),
                           (400, OCHRE, "approve 30 で変わる")):
        f.box(x, ly - 23, 30, 30, fill, fill, sw=2, rx=4)
        f.text(x + 44, ly, label, 26, INK, anchor="start")
    f.save("erc-20_concept.webp")


if __name__ == "__main__":
    concept_figure()
    stages_figure()
