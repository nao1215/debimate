"""Generate the figures of the Snowman note.

python3 figures.py

The concept, counter and finality figures are hand-written SVG rendered with
headless Chrome. The graphs use matplotlib and the simulation in lab/snow_sim.py
(fixed seeds). Every figure is written to images/ as WebP.
Needs google-chrome, matplotlib, NumPy and Pillow.
"""

import io
import math
import random
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # keep the Page Bundle free of __pycache__
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED_INK, RED_PALE = "#c0504d", "#f6e3e2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls="", color=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{color}"' if color else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                      f'text-anchor="{anchor}"{c}{f}>{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, color=SUB, width=1.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{color}" stroke-width="{width}"{d}/>')

    def rect(self, x, y, w, h, fill, stroke, width=2.5, rx=6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"{d}/>')

    def circle(self, x, y, r, fill, stroke, width=2):
        self.p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{width}"/>')

    def arrow(self, x1, y, x2, color=INK, width=3):
        self.line(x1, y, x2 - 12, y, color, width)
        self.p.append(f'<polygon points="{x2},{y} {x2 - 14},{y - 8} {x2 - 14},{y + 8}" '
                      f'fill="{color}"/>')

    def save(self, name):
        """Render the SVG with headless Chrome at 2x and store it as WebP."""
        self.p.append("</svg>")
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.p) + "\n", encoding="utf-8")
            subprocess.run(
                ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                 f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def concept_figure():
    """Left: every node talks to every node. Right: one node asks a few, again and again."""
    s = Svg(960, 540, "全員と通信する BFT と、少数への問い合わせを繰り返す Snowman")
    s.text(210, 52, "PBFT・CometBFT", 28)
    s.text(210, 90, "全員が全員に送る", 24, cls="sub")
    cx, cy, r = 210, 290, 150
    pts = [(cx + r * math.cos(2 * math.pi * i / 8 - math.pi / 2),
            cy + r * math.sin(2 * math.pi * i / 8 - math.pi / 2)) for i in range(8)]
    for i in range(8):
        for j in range(i + 1, 8):
            s.line(*pts[i], *pts[j])
    for x, y in pts:
        s.circle(x, y, 22, OCHRE_PALE, OCHRE, 2.5)
    s.text(210, 500, "1 段階で約 n² 通", 24, cls="sub")
    s.line(425, 30, 425, 510, SUB, 1, "4 4")

    s.text(690, 52, "Snowman", 28)
    s.text(690, 90, "無作為に選んだ k 台に聞き、繰り返す", 24, cls="sub")
    rng = random.Random(7)
    field = []
    for row in range(5):
        for col in range(9):
            x = 470 + col * 55 + rng.uniform(-10, 10)
            y = 135 + row * 62 + rng.uniform(-10, 10)
            if abs(x - 690) < 60 and abs(y - 260) < 50:
                continue  # leave room for the querier
            field.append((x, y))
    sampled = [3, 9, 15, 24, 30, 36]
    qx, qy = 690, 260
    for i in sampled:
        s.line(qx, qy, *field[i], INK, 2.5)
    for i, (x, y) in enumerate(field):
        if i in sampled:
            s.circle(x, y, 14, BLUE_PALE, BLUE, 3)
        else:
            s.circle(x, y, 11, FILL, SUB, 1.5)
    s.circle(qx, qy, 28, BLUE_PALE, BLUE, 4)

    s.text(470, 478, "α 台以上が一致", 24, "start")
    for i in range(5):
        s.rect(650 + i * 40, 452, 32, 34, GREEN_PALE, GREEN, rx=4)
    s.arrow(858, 469, 892)
    s.text(924, 478, "確定", 24)
    s.text(740, 522, "β 回続く", 24, cls="sub")
    s.save("snowman_concept.webp")


# One illustrative run with k = 20, alpha = 15, beta = 4.
POLLS = [16, 12, 15, 5, 18, 16, 17, 19]  # blue answers out of 20 in each poll


def counter_figure():
    """Consecutive successes (Snowflake) and per-color totals (Snowball), poll by poll."""
    k, alpha, beta = 20, 15, 4
    col0, cw = 250, 96
    s = Svg(col0 + cw * len(POLLS) + 30, 535,
            "Snowflake の連続の回数と Snowball の累計を、問い合わせごとに追う")
    s.text(col0 + cw * len(POLLS) / 2, 36,
           f"k = {k}、α = {alpha}、β = {beta} の例（左から順に問い合わせる）", 22, cls="sub")
    labels = ["問い合わせ", "20 台中の答え", "成功（α 台以上）", "連続の回数",
              "Snowflake の支持", "累計（青：赤）", "Snowball の支持"]
    ys = [84, 140, 208, 272, 370, 434, 498]
    for y, lab in zip(ys, labels):
        s.text(20, y + 8, lab, 21, "start")
    conf, last, tot = 0, None, {"青": 0, "赤": 0}
    pref = "青"
    for i, blue in enumerate(POLLS):
        x = col0 + cw * i + cw / 2
        s.text(x, ys[0] + 8, f"{i + 1} 回目", 20, cls="sub")
        red = k - blue
        color = "青" if blue >= alpha else "赤" if red >= alpha else None
        s.text(x, ys[1] - 4, f"青 {blue}", 20, color=BLUE if blue >= red else SUB)
        s.text(x, ys[1] + 22, f"赤 {red}", 20, color=RED_INK if red > blue else SUB)
        if color:
            fill, stroke = (BLUE_PALE, BLUE) if color == "青" else (RED_PALE, RED_INK)
            s.rect(x - 38, ys[2] - 20, 76, 40, fill, stroke)
            s.text(x, ys[2] + 8, color, 22)
            conf = conf + 1 if color == last else 1
            last = color
            tot[color] += 1
            if tot[color] > tot["赤" if color == "青" else "青"]:
                pref = color
        else:
            s.rect(x - 38, ys[2] - 20, 76, 40, FILL, SUB, dash="5 4")
            s.text(x, ys[2] + 8, "失敗", 22, cls="sub")
            conf = 0
        done = conf >= beta
        if done:
            s.rect(x - 38, ys[3] - 22, 76, 44, GREEN_PALE, GREEN, 3)
        reset = (not color) or (color and conf == 1 and i > 0)
        s.text(x, ys[3] + 8, f"{conf}", 24, color=OCHRE if reset else INK)
        s.text(x, ys[4] + 8, last or "青", 22)
        s.text(x, ys[5] + 8, f"{tot['青']}：{tot['赤']}", 22)
        s.text(x, ys[6] + 8, pref, 22)
        if done:
            s.text(x - 50, ys[3] + 46, "β = 4 に届き、青で確定", 20, color=INK)
    s.text(col0 + cw * 2.5, ys[3] + 46, "失敗で 0、色が変わると 1 からやり直し", 18, cls="sub")
    s.save("snowman_counter.webp")


def finality_figure():
    """Where the probability lies: PoW reorgs vs. Snowman's disagreement chance."""
    s = Svg(1000, 420, "PoW と Snowman で、確率が掛かる場所の違い")
    s.text(250, 44, "PoW（Bitcoin）", 26)
    s.text(250, 78, "待つほど覆りにくいが、ノードは列を組み替える", 20, cls="sub")
    bw, gap = 52, 22
    s.rect(30, 140, bw, 40, FILL, SUB)
    for i in range(4):
        x = 30 + (i + 1) * (bw + gap)
        s.line(x - gap, 160, x, 160, SUB, 2.5)
        mine = i == 0
        s.rect(x, 140, bw, 40, BLUE_PALE, INK if mine else BLUE, 4 if mine else 2.5)
    mx = 30 + (bw + gap) + bw / 2
    s.text(mx, 112, "自分の取引を含むブロック", 18, "start" if False else "middle")
    s.p.append(f'<polygon points="{mx},{136} {mx - 7},{122} {mx + 7},{122}" fill="{INK}"/>')
    s.text(30 + 2.5 * (bw + gap) + bw / 2, 210, "後ろに積まれるほど覆りにくい", 18, cls="sub")
    s.line(30 + bw, 170, 30 + bw + gap, 260, OCHRE, 2.5)
    for i in range(5):
        x = 30 + (i + 1) * (bw + gap)
        if i:
            s.line(x - gap, 270, x, 270, OCHRE, 2.5)
        s.rect(x, 250, bw, 40, OCHRE_PALE, OCHRE)
    s.text(30 + 3 * (bw + gap) + bw / 2, 318, "後から届いた、より重い別の列", 18)
    s.text(250, 370, "重い列が届いたら、上の列を捨てて組み替える", 20)
    s.text(250, 400, "覆る確率は、待った確認の数で下がる", 20, cls="sub")

    s.line(500, 30, 500, 400, SUB, 1, "4 4")

    s.text(750, 44, "Snowman", 26)
    s.text(750, 78, "確定したブロックは、後から外さない", 20, cls="sub")
    for y, lab in [(130, "正しいノード A"), (220, "正しいノード B")]:
        s.text(530, y + 28, lab, 20, "start")
        for i in range(3):
            x = 700 + i * (bw + gap)
            if i:
                s.line(x - gap, y + 20, x, y + 20, SUB, 2.5)
            s.rect(x, y, bw, 40, BLUE_PALE, BLUE)
        s.rect(700 + 2 * (bw + gap) - 5, y - 5, bw + 10, 50, "none", GREEN, 3)
    s.text(700 + 2 * (bw + gap) + bw / 2 + 64, 205, "確定", 20)
    s.text(750, 330, "通常は、A と B が同じブロックを確定する", 20)
    s.text(750, 370, "確率 ε で、A と B が別のブロックを確定する", 20)
    s.text(750, 400, "起きても、プロトコルの中では直らない", 20, cls="sub")
    s.save("snowman_finality.webp")


def setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "axes.unicode_minus": False,
    })
    return plt


def save_plot(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    buf.seek(0)
    Image.open(buf).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def slush_figure(plt):
    sys.path.insert(0, str(HERE / "lab"))
    from snow_sim import slush

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    panels = [(0.0, "不正なノードなし", BLUE), (0.2, "不正なノード 20%（少ない方の色を答える）", OCHRE)]
    for ax, (byz, title, color) in zip(axes, panels):
        for seed in range(1, 6):
            trace = slush(500, 20, 15, 60, byz=byz, seed=seed)
            ax.plot(range(len(trace)), trace, color=color, lw=1.6)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("ラウンド")
        ax.set_ylim(-0.03, 1.03)
        ax.axhline(0.5, color=SUB, lw=0.8, ls=":")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("青を支持する\n正しいノードの割合")
    fig.tight_layout()
    save_plot(fig, "snowman_slush.webp")


def slush_push_figure(plt):
    """Chance that one poll of k=20 crosses alpha=15 for blue, against the share of blue."""
    from math import comb

    k, alpha = 20, 15
    xs = [i / 100 for i in range(0, 101)]

    def over(p):
        return sum(comb(k, i) * p**i * (1 - p) ** (k - i) for i in range(alpha, k + 1))

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot([100 * x for x in xs], [over(x) for x in xs], color=BLUE, lw=2.0,
            label="青への乗り換えが起きる（20 台中 15 台以上が青）")
    ax.plot([100 * x for x in xs], [over(1 - x) for x in xs], color=OCHRE, lw=2.0, ls="--",
            label="赤への乗り換えが起きる（20 台中 15 台以上が赤）")
    for x in (0.5, 0.6, 0.7):
        ax.plot([100 * x], [over(x)], "o", color=BLUE)
        ax.annotate(f"{over(x):.2f}", (100 * x, over(x)), textcoords="offset points",
                    xytext=(-30, 6), fontsize=9)
    ax.axvline(50, color=SUB, lw=0.8, ls=":")
    ax.set_xlabel("青を支持するノードの割合（%）")
    ax.set_ylabel("1 回の問い合わせで\n乗り換えが起きる確率")
    ax.set_ylim(-0.03, 1.08)
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_plot(fig, "snowman_slush_push.webp")


def epsilon_figure(plt):
    """The rough safety estimate (1 - alpha/k)^beta from the Avalanche docs, k = 20."""
    k = 20
    betas = list(range(1, 31))
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    styles = {11: (OCHRE, "--"), 13: (OCHRE, ":"), 15: (BLUE, "-"), 17: (BLUE, "-.")}
    for alpha, (color, ls) in styles.items():
        ax.plot(betas, [(1 - alpha / k) ** b for b in betas], color=color, ls=ls, lw=2.0,
                label=f"α = {alpha}")
    est = (1 - 15 / k) ** 20
    ax.plot([20], [est], "o", color=BLUE)
    ax.annotate("既定値（α = 15、β = 20）\n約 $9 \\times 10^{-13}$", (20, est),
                xytext=(19, 1e-4), fontsize=9,
                arrowprops={"arrowstyle": "-", "color": SUB, "lw": 0.8})
    ax.set_yscale("log")
    ax.set_ylim(1e-20, 2)
    ax.set_xlabel("β")
    ax.set_ylabel("$(1 - \\alpha / k)^{\\beta}$")
    ax.legend(frameon=False, loc="lower left", fontsize=9, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_plot(fig, "snowman_epsilon.webp")


def messages_figure(plt):
    sys.path.insert(0, str(HERE / "lab"))
    from snow_sim import pbft_messages, sweep

    ns = [50, 100, 200, 500, 1000, 2000, 5000]
    snow = [sweep(n, 0.0, 20, 15, 20, "agree", trials=20)["msgs_per_node"] * n for n in ns]
    split = [sweep(n, 0.0, 20, 15, 20, "split", trials=20)["msgs_per_node"] * n for n in ns]
    pbft = [pbft_messages(n) for n in ns]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(ns, pbft, color=OCHRE, lw=2.0, marker="o", ls="--",
            label="PBFT の通常動作（全員が全員に送る）")
    ax.plot(ns, snow, color=BLUE, lw=2.0, marker="o",
            label="Snowball、全員が同じ値から始める")
    ax.plot(ns, split, color=BLUE, lw=1.5, marker="s", ls=":",
            label="Snowball、半々に割れて始める")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("ノード数 n")
    ax.set_ylabel("1 回の決定に使うメッセージ数")
    ax.legend(frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_plot(fig, "snowman_messages.webp")


def poll_probability_figure(plt):
    """Chance that one poll succeeds, and that beta polls succeed in a row.

    Exact binomial values for k=20, alpha=15, beta=20, when Byzantine nodes
    always answer the other color (experiment 1 in lab/output.txt).
    """
    from math import comb

    k, alpha, beta = 20, 15, 20
    shares = [i / 200 for i in range(0, 71)]

    def one(f):
        q = 1 - f
        return sum(comb(k, i) * q**i * f ** (k - i) for i in range(alpha, k + 1))

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot([100 * f for f in shares], [one(f) for f in shares], color=BLUE, lw=2.0,
            label="1 回の問い合わせが成功（20 台中 15 台以上が青）")
    ax.plot([100 * f for f in shares], [one(f) ** beta for f in shares], color=OCHRE,
            lw=2.0, ls="--", label="20 回続けて成功")
    for f in (0.2, 0.25):
        ax.plot([100 * f], [one(f)], "o", color=BLUE)
        ax.annotate(f"{one(f):.2f}", (100 * f, one(f)), textcoords="offset points",
                    xytext=(6, 4), fontsize=9)
    ax.axvline(25, color=SUB, lw=0.8, ls=":")
    ax.set_yscale("log")
    ax.set_ylim(1e-9, 2)
    ax.set_xlabel("不正なノードの割合（%）")
    ax.set_ylabel("確率")
    ax.legend(frameon=False, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_plot(fig, "snowman_poll_probability.webp")


def beta_sweep_figure(plt):
    """Splits and unfinished runs out of 100, from experiment 2 in lab/output.txt."""
    rows = {}
    section = None
    for line in (HERE / "lab" / "output.txt").read_text().splitlines():
        if line.startswith("=="):
            section = line.split(".")[0].strip("= ")
            continue
        parts = line.split()
        if section == "2" and parts and parts[0][0].isdigit():
            byz, beta = float(parts[0]), int(parts[1])
            rows.setdefault(byz, []).append((beta, int(parts[3]), int(parts[4])))

    styles = {0.0: (BLUE, "-", "o"), 0.05: (BLUE, ":", "s"),
              0.1: (OCHRE, "-", "o"), 0.2: (OCHRE, "--", "s")}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    for byz, pts in rows.items():
        color, ls, marker = styles[byz]
        betas = [b for b, _, _ in pts]
        label = f"不正なノード {int(byz * 100)}%"
        axes[0].plot(betas, [s for _, s, _ in pts], color=color, ls=ls, marker=marker,
                     lw=1.6, label=label)
        axes[1].plot(betas, [u for _, _, u in pts], color=color, ls=ls, marker=marker,
                     lw=1.6, label=label)
    axes[0].set_title("意見が割れた試行（赤と青の両方が確定）", fontsize=10)
    axes[1].set_title("確定しないノードが残った試行", fontsize=10)
    axes[0].set_ylabel("100 回中の回数")
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks([1, 2, 4, 8, 20], ["1", "2", "4", "8", "20"])
        ax.set_xlabel("β")
        ax.set_ylim(-4, 104)
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].legend(frameon=False, loc="center right", fontsize=9)
    fig.tight_layout()
    save_plot(fig, "snowman_beta_sweep.webp")


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    concept_figure()
    counter_figure()
    finality_figure()
    plt = setup_matplotlib()
    slush_figure(plt)
    slush_push_figure(plt)
    epsilon_figure(plt)
    messages_figure(plt)
    poll_probability_figure(plt)
    beta_sweep_figure(plt)
