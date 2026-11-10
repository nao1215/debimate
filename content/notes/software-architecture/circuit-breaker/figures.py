"""Generate the figures of the circuit breaker note from lab/sim.py."""

import sys
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from sim import OUTAGE, POOL, run  # noqa: E402

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "circuit-breaker",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def outage_figure():
    none, cb = run(), run(use_breaker=True)
    for st in (none, cb):
        st["b_rate"] = [100 * ok / max(ok + ng, 1)
                        for ok, ng in zip(st["b_ok"], st["b_rejected"])]
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 6.4), sharex=True)
    t_busy = [i / 10 for i in range(len(none["busy"]))]
    t_sec = [i + 0.5 for i in range(60)]
    panels = [
        (t_busy, "busy", f"Busy threads (pool = {POOL})", (0, POOL * 1.15)),
        (t_sec, "b_rate", "Local requests B\nserved (%)", (0, 105)),
        (t_sec, "down_calls", "Calls reaching\ndownstream / s", (0, 70)),
    ]
    for ax, (t, key, label, ylim) in zip(axes, panels):
        ax.axvspan(OUTAGE[0] / 1000, OUTAGE[1] / 1000, color="#f2f2f2", zorder=0)
        ax.step(t, none[key], where="mid", color=RED, lw=1.6, label="no breaker")
        ax.step(t, cb[key], where="mid", color=ACCENT, lw=1.6, ls="--",
                label="with breaker")
        ax.set_ylabel(label)
        ax.set_ylim(*ylim)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].text(25, POOL * 0.5, "downstream silent (10 s - 40 s)", ha="center",
                 color=SUB, fontsize=9)
    axes[0].legend(loc="upper right", frameon=False, fontsize=9,
                   bbox_to_anchor=(1.0, 0.92))
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(0, 60)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "outage_simulation.svg")


FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
FILL, PALE = "#f2f2f2", "#eaf1f5"


class Svg:
    def __init__(self, width, height, title):
        marks = "".join(
            f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerUnits="userSpaceOnUse" markerWidth="22" markerHeight="22" '
            f'orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for n, c in (("red", RED), ("accent", ACCENT)))
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<defs>{marks}</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, rx=8):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def path(self, d, color, sw, arrow=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="butt"{m}/>')

    def poly(self, pts, color):
        d = " ".join(f"{x},{y}" for x, y in pts)
        self.parts.append(f'<polygon points="{d}" fill="{color}"/>')

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    """3 つの状態を、呼び出しの通り道に置いた弁の開き具合で描く。

    左から来る呼び出しの量は 3 状態で同じ。弁を通って下流に届く量を線の
    太さで、弁で止めてすぐ失敗として返す分を赤い戻りの矢印で表す。
    """
    f = Svg(960, 540, "サーキットブレーカーの 3 つの状態と下流に届く呼び出し")
    pipe, x_in, x_valve, x_down = 28, 250, 560, 790
    lanes = (
        ("Closed", "全て通す", 150, pipe, 0),
        ("Half-Open", "少数だけ通す", 300, 6, pipe - 6),
        ("Open", "通さない", 450, 0, pipe),
    )
    f.text(330, 52, "呼び出し側", 24, SUB)
    f.text(x_valve, 52, "ブレーカー", 24, SUB)
    f.box(x_down, 80, 140, 430, FILL, SUB, sw=2.5, rx=12)
    f.text(x_down + 70, 310, "下流", 28, weight="normal")

    for name, note, cy, through, back in lanes:
        f.text(30, cy - 4, name, 30, weight="normal", anchor="start")
        f.text(30, cy + 34, note, 24, SUB, anchor="start")
        # Calls arriving from the caller: the same amount in every state.
        f.path(f"M{x_in},{cy} H{x_valve - 12}", ACCENT, pipe)
        if through:
            # What reaches the downstream, drawn as thick as it is.
            head, half = 30, max(through * 0.8, 10)
            y0 = cy + pipe / 2 - through / 2
            f.path(f"M{x_valve - 14},{y0} H{x_down - head}", ACCENT, through)
            f.poly([(x_down - head - 2, y0 - half), (x_down - 4, y0),
                    (x_down - head - 2, y0 + half)], ACCENT)
        # The valve: a gate that slides down into the pipe from above.
        # Its lower edge leaves an opening as wide as what gets through.
        f.box(x_valve - 15, cy - pipe / 2 - 34, 30, pipe + 68, "none", SUB,
              sw=2, rx=4)
        f.box(x_valve - 10, cy - pipe / 2 - 30, 20, 26 + pipe - through, INK,
              INK, sw=0, rx=2)
        if back:
            # Calls stopped at the valve return to the caller at once.
            y0 = cy - pipe / 2 - 8
            f.path(f"M{x_valve - 22},{y0} C{x_valve - 90},{cy - 78} "
                   f"{x_in + 90},{cy - 78} {x_in + 30},{y0 - 6}",
                   RED, max(back / 3, 4), arrow="red")
            f.text((x_in + x_valve) / 2, cy - 72, "すぐ失敗を返す", 24, SUB)

    (HERE / "images").mkdir(exist_ok=True)
    f.save(HERE / "images" / "circuit-breaker_concept.svg")


def configs_figure():
    """Six configurations of lab/output.txt: B served and downstream calls during the outage."""
    import re
    out = (HERE / "lab" / "output.txt").read_text(encoding="utf-8")
    blocks = re.findall(r"== (.+)\n  downstream calls during outage: (\d+)\n"
                        r"  B \(local\) served during outage: (\d+)/(\d+)", out)
    names = {"no breaker": "ブレーカーなし", "breaker": "ブレーカー",
             "breaker, timeout 30 s": "ブレーカー、timeout 30 秒",
             "3 attempts, no breaker": "試行 3 回、ブレーカーなし",
             "Retry(CircuitBreaker), 3 attempts": "Retry(CircuitBreaker)",
             "CircuitBreaker(Retry), 3 attempts": "CircuitBreaker(Retry)"}
    f = Svg(960, 540, "6 つの構成で、停止中に処理できた要求 B と下流に届いた呼び出し")
    total = int(blocks[0][3])
    bx, cx = 340, 670
    f.text(bx, 52, "処理できた要求 B", 24, SUB, anchor="start")
    f.text(cx, 52, "下流に届いた呼び出し", 24, SUB, anchor="start")
    max_calls = max(int(b[1]) for b in blocks)
    for i, (name, calls, served, _) in enumerate(blocks):
        y = 84 + i * 64 + (24 if i >= 3 else 0)
        breaker = "breaker" in name.lower() and "no breaker" not in name
        fill, stroke = (PALE, ACCENT) if breaker else (FILL, SUB)
        f.text(20, y + 30, names[name], 24, anchor="start")
        w1 = 200 * int(served) / total
        f.box(bx, y + 4, max(w1, 2), 36, fill, stroke, sw=2, rx=3)
        f.text(bx + w1 + 10, y + 31, f"{int(served):,}", 24, anchor="start")
        w2 = 180 * int(calls) / max_calls
        f.box(cx, y + 4, max(w2, 2), 36, fill, stroke, sw=2, rx=3)
        f.text(cx + w2 + 10, y + 31, f"{int(calls):,}", 24, anchor="start")
    f.path(f"M20,{84 + 3 * 64 + 10} H940", "#d9d9d9", 2)
    f.text(480, 524, f"下流が黙っていた 30 秒間の件数（要求 B は {total:,} 件中）。青はブレーカーあり", 24, SUB)
    f.save(HERE / "images" / "circuit-breaker_configs.svg")


if __name__ == "__main__":
    outage_figure()
    concept_figure()
    configs_figure()
