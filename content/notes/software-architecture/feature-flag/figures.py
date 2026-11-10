"""Generate the figure of the feature flag note from lab/rollout.py."""

import sys
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from rollout import REQUESTS, run  # noqa: E402

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "feature-flag",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def rollout_figure():
    rows = run()
    x = list(range(len(rows)))
    labels = [f"{r['pct']}%" for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.0))
    panels = [
        ("exposed", "Users who hit the new\n(broken) feature (%)"),
        ("mixed", "Users who saw both old\nand new in one stage (%)"),
    ]
    for ax, (key, label) in zip(axes, panels):
        rnd = [100 * r[f"random_{key}"] / 100_000 for r in rows]
        hsh = [100 * r[f"hash_{key}"] / 100_000 for r in rows]
        ax.plot(x, rnd, color=RED, lw=2.0, marker="o", label="coin flip per request")
        ax.plot(x, hsh, color=ACCENT, lw=2.0, marker="o", ls="--",
                label="hash of user ID")
        ax.set_xticks(x, labels)
        ax.set_xlabel("Rollout stage")
        ax.set_ylabel(label)
        ax.set_ylim(-3, 105)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(loc="lower right", frameon=False, fontsize=9)
    axes[1].text(1.6, 16, f"{REQUESTS} requests / user / stage", ha="center",
                 color=SUB, fontsize=9)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "feature-flag_rollout.svg", metadata={"Date": None})


FILL, FONT = "#f2f2f2", "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


def concept_figure():
    """Same build in two rows: the flag only decides which path users reach."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("同じビルドのまま flag の Off と On でユーザーに届く処理が変わる")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def lane(y, label, fill, active):
        stroke, sw, dash = (INK, 2.5, "") if active else (SUB, 1.5, ' stroke-dasharray="6 5"')
        p.append(f'<rect x="150" y="{y}" width="190" height="60" rx="8" '
                 f'fill="{fill if active else "#ffffff"}" stroke="{stroke}" '
                 f'stroke-width="{sw}"{dash}/>')
        text(245, y + 39, label, 26, cls="" if active else "sub")

    def wire(x1, y1, x2, y2, active):
        if active:
            p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" '
                     'stroke-width="4"/>')
        else:
            p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" '
                     'stroke-width="1.5" stroke-dasharray="6 5"/>')

    for top, on in ((20, False), (290, True)):
        new = ACCENT if on else FILL
        users = ACCENT if on else OCHRE
        text(62, top + 140, "On" if on else "Off", 38, weight="normal")
        # The deployed build always holds both paths.
        p.append(f'<rect x="120" y="{top + 10}" width="380" height="220" rx="12" '
                 f'fill="#ffffff" stroke="{SUB}" stroke-width="1.5"/>')
        text(140, top + 48, "同じビルド", 24, "start", cls="sub")
        lane(top + 70, "旧決済", OCHRE, not on)
        lane(top + 150, "新決済", ACCENT, on)
        cy = top + 140
        wire(340, top + 100, 390, cy, not on)
        wire(340, top + 180, 390, cy, on)
        # Flag switch: knob left (Off) or right (On).
        p.append(f'<rect x="390" y="{cy - 24}" width="92" height="48" rx="24" '
                 f'fill="{new}" stroke="{INK}" stroke-width="2.5"/>')
        p.append(f'<circle cx="{458 if on else 414}" cy="{cy}" r="17" fill="#ffffff" '
                 f'stroke="{INK}" stroke-width="2.5"/>')
        # Arrow to users.
        p.append(f'<line x1="482" y1="{cy}" x2="592" y2="{cy}" stroke="{INK}" '
                 'stroke-width="4"/>')
        p.append(f'<polygon points="606,{cy} 586,{cy - 12} 586,{cy + 12}" fill="{INK}"/>')
        text(770, top + 48, "ユーザー", 24, cls="sub")
        for r in range(3):
            for c in range(5):
                p.append(f'<circle cx="{660 + c * 56}" cy="{top + 92 + r * 56}" r="20" '
                         f'fill="{users}" stroke="{INK if on else SUB}" stroke-width="2"/>')
    p.append(f'<line x1="30" y1="270" x2="930" y2="270" stroke="{SUB}" '
             'stroke-width="1" stroke-dasharray="4 4"/>')
    (HERE / "images" / "feature-flag_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


if __name__ == "__main__":
    rollout_figure()
    concept_figure()
