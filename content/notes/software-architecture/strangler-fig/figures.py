"""Generate the figures of the strangler fig note.

strangler-fig_concept.svg is hand-written SVG (Python stdlib only).
strangler-fig_route_alert.svg is drawn with matplotlib from lab/route_alert.py.
"""

import sys
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from route_alert import (MINUTES, ROUTE_LIMIT, SWITCH, TOTAL_LIMIT,  # noqa: E402
                         run, sweep)

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "strangler-fig",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


FILL, NEW_FILL = "#f2f2f2", "#eaf1f5"
OCHRE, OLD_FILL = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Figure:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", weight="normal", color=None):
        fill = f' style="fill:{color}"' if color else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}"{fill}>{escape(s)}</text>'
        )

    def rect(self, x, y, w, h, fill="#ffffff", stroke=SUB, dash=False, sw=2, r=8):
        d = ' stroke-dasharray="8 6"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>'
        )

    def arrow(self, x1, y1, x2, y2, sw=3):
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" '
            f'stroke-width="{sw}" marker-end="url(#arrow)"/>'
        )

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n")


FEATURES = ["受付", "配送", "請求"]
# Which features the new system owns at each stage.
STAGES = [("入口を置く", []), ("請求を移す", ["請求"]),
          ("モノリスを止める", ["受付", "配送", "請求"])]


def concept_figure():
    """Three stages: the facade stays, features move from the old box to the new."""
    f = Figure(960, 540, "ファサードの裏で機能を 1 つずつ新システムへ移し、最後にモノリスを止める 3 段階")
    pw, gap, x0 = 276, 42, 24
    box_w, box_y, box_h = 134, 236, 284
    tile_w, tile_h = 102, 60
    for i, (label, moved) in enumerate(STAGES):
        px = x0 + i * (pw + gap)
        cx = px + pw / 2
        f.text(cx, 44, f"{i + 1}. {label}", 28, weight="normal")
        # Client request enters the facade from above.
        f.arrow(cx, 62, cx, 98)
        f.rect(px, 102, pw, 58, FILL, INK, sw=2.5, r=10)
        f.text(cx, 141, "ファサード", 26, weight="normal")
        old_x, new_x = px, px + pw - box_w
        stopped = len(moved) == len(FEATURES)
        if not stopped:
            f.arrow(old_x + box_w / 2, 160, old_x + box_w / 2, box_y - 6)
        if moved:
            f.arrow(new_x + box_w / 2, 160, new_x + box_w / 2, box_y - 6)
        f.rect(old_x, box_y, box_w, box_h, OLD_FILL if not stopped else "#ffffff",
               SUB if stopped else OCHRE, dash=stopped, sw=2 if stopped else 2.5)
        f.text(old_x + box_w / 2, box_y + 36, "モノリス", 24, color=SUB)
        if moved:
            f.rect(new_x, box_y, box_w, box_h, NEW_FILL, ACCENT, sw=2.5)
            f.text(new_x + box_w / 2, box_y + 36, "新システム", 24, color=SUB)
        for k, name in enumerate(FEATURES):
            ty = box_y + 56 + k * (tile_h + 12)
            if name in moved:
                f.rect(new_x + (box_w - tile_w) / 2, ty, tile_w, tile_h, ACCENT, ACCENT)
                f.text(new_x + box_w / 2, ty + 39, name, 24)
                if not stopped:
                    f.rect(old_x + (box_w - tile_w) / 2, ty, tile_w, tile_h,
                           "none", SUB, dash=True)
            else:
                f.rect(old_x + (box_w - tile_w) / 2, ty, tile_w, tile_h, "#ffffff", OCHRE)
                f.text(old_x + box_w / 2, ty + 39, name, 24)
        if stopped:
            f.text(old_x + box_w / 2, box_y + box_h / 2 + 12, "停止", 30,
                   weight="normal", color=INK)
        if i < len(STAGES) - 1:
            f.text(px + pw + gap / 2, box_y + box_h / 2 + 12, "›", 64, color=SUB)
    f.save(HERE / "images" / "strangler-fig_concept.svg")


def alert_figure():
    total, route, _, _ = run(0.08, 0)
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 4.0))
    t = list(range(MINUTES))
    left.axvline(SWITCH, color=SUB, lw=1.0, ls=":")
    left.plot(t, [100 * r for r in total], color=INK, lw=2.0, label="all routes")
    rt = [(x, 100 * r) for x, r in zip(t, route) if r is not None]
    left.plot([x for x, _ in rt], [r for _, r in rt], color=RED, lw=2.0,
              label="migrated route (new)")
    left.axhline(100 * TOTAL_LIMIT, color=INK, lw=1.2, ls="--")
    left.axhline(100 * ROUTE_LIMIT, color=RED, lw=1.2, ls="--")
    left.text(1, 100 * TOTAL_LIMIT + 0.3, "total alert 1%", color=INK, fontsize=9)
    left.text(1, 100 * ROUTE_LIMIT + 0.3, "route alert 3%", color=RED, fontsize=9)
    left.text(SWITCH + 1, 4.2, "switch at 30 min", color=SUB, fontsize=9)
    left.set_xlabel("Time (min)")
    left.set_ylabel("Error rate, last 5 min (%)")
    left.set_ylim(0, max(r for _, r in rt) + 1)
    left.set_xlim(0, MINUTES)
    left.legend(loc="upper left", frameon=False, fontsize=9)

    rows = sweep()
    x = [100 * e for e, _, _ in rows]
    right.plot(x, [100 * p for _, p, _ in rows], color=INK, lw=2.0,
               marker="o", ms=4, label="total alert")
    right.plot(x, [100 * p for _, _, p in rows], color=RED, lw=2.0,
               marker="o", ms=4, label="route alert")
    right.set_xlabel("Error rate of the new system (%)")
    right.set_ylabel("Alerted within 60 min (%)")
    right.set_ylim(-3, 103)
    right.legend(loc="lower right", frameon=False, fontsize=9)
    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "strangler-fig_route_alert.svg",
                metadata={"Date": None})
    if len(sys.argv) > 1:
        fig.savefig(sys.argv[1], dpi=60)


def epoch_figure():
    """所有者を切り替えた後の更新番号の比べ方（模式図）。

    レガシーの DB が振った大きな番号と、新しい DB が 1 から振った番号を、
    番号だけで比べる場合と、epoch を先に比べる場合で並べる。
    黄土色はレガシーの DB、青は新しい DB の番号。
    """
    f = Figure(960, 540, "更新番号と epoch の比べ方")
    rows = [
        (70, "番号だけで比べる", "旧  #1000", ">", "新  #1", "新しい変更を捨てる", RED),
        (300, "epoch を先に比べる", "旧  e1 · #1000", "<", "新  e2 · #1", "新しい変更を残す", ACCENT),
    ]
    for top, label, old, op, new, result, mark in rows:
        f.text(40, top + 30, label, 26, anchor="start")
        y = top + 70
        f.rect(40, y, 270, 76, fill=OLD_FILL, stroke=OCHRE)
        f.text(175, y + 48, old, 26)
        f.text(350, y + 50, op, 34)
        f.rect(390, y, 270, 76, fill=NEW_FILL, stroke=ACCENT)
        f.text(525, y + 48, new, 26)
        f.text(718, y + 47, result, 24, anchor="start", color=SUB)
        cx, cy = 692, y + 38
        if mark == RED:
            f.parts.append(
                f'<path d="M{cx - 10},{cy - 10} l20,20 M{cx + 10},{cy - 10} l-20,20" '
                f'stroke="{RED}" stroke-width="5" stroke-linecap="round"/>')
        else:
            f.parts.append(
                f'<path d="M{cx - 12},{cy} l8,9 l16,-20" fill="none" '
                f'stroke="{ACCENT}" stroke-width="5" stroke-linecap="round"/>')
    f.text(480, 520, "e: 所有者を切り替える度に 1 つ増やす番号（epoch）", 24, color=SUB)
    f.save(HERE / "images" / "strangler-fig_epoch.svg")


if __name__ == "__main__":
    concept_figure()
    alert_figure()
    epoch_figure()
