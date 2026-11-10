"""Generate the cover figure of the Domain Event note (Python stdlib only).

concept_figure() lays the transactions out on a time axis. Transaction 1
confirms the order and records OrderConfirmed (token E1); the token crosses the
gap to transaction 2, which reserves the stock. The gap is the time when the
order and the stock disagree. The same token E1 can arrive again (ochre); the
receiver finds it already processed and safely does nothing (green).

redelivery_figure() plots lab/redelivery_output.txt (lab/redelivery.py):
stock reserved twice under at-least-once delivery, with and without the
processed-event record.

Run: python3 content/notes/software-architecture/domain-event/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE, WHITE = "#f2f2f2", "#eaf1f5", "#ffffff"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MARKERS = {"ink": SUB, "accent": ACCENT, "ochre": OCHRE}


class Svg:
    def __init__(self, width, height, title):
        defs = "".join(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for name, color in MARKERS.items())
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<defs>{defs}</defs>',
            f'<rect width="{width}" height="{height}" fill="{WHITE}"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def ellipse(self, cx, cy, rx, ry, fill, stroke, sw=2.5):
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow="", dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, color, sw=4, arrow="", dash="", fill="none"):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"{da}{m}/>')

    def cross(self, cx, cy, r, color, sw=6):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)

    def db(self, cx, top, w, h, label):
        rx, ry = w / 2, 14
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{FILL}" stroke="{SUB}" stroke-width="2.5"/>')
        self.ellipse(cx, top, rx, ry, FILL, SUB)
        self.text(cx, top + h / 2 + 18, label)

    def save(self, name):
        out = HERE / "images"
        out.mkdir(exist_ok=True)
        (out / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n",
                                encoding="utf-8")


def token(f, cx, cy, color):
    f.box(cx - 34, cy - 22, 68, 44, color, color, sw=0, rx=22)
    f.text(cx, cy + 9, "E1", 24, INK, weight="normal")


def concept_figure():
    f = Svg(960, 540, "Domain Event でトランザクションを分けた時の時間の流れ")

    # Time axis.
    f.line(20, 484, 924, 484, SUB, 3, arrow="ink")
    f.text(926, 522, "時間", 24, SUB, anchor="end")

    # The time when the order is confirmed but the stock is not reserved yet.
    f.path("M286,108 V96 H384 V108", OCHRE, 2.5)
    f.text(335, 80, "状態がずれている時間", 24, SUB)

    boxes = [
        (20, "トランザクション 1", ["Order を確定", "イベント E1 を記録"], ACCENT),
        (390, "トランザクション 2", ["在庫を引き当て", "E1 を処理済みに"], ACCENT),
        (700, "2 回目の受信", ["E1 は処理済み", "何もしない"], GREEN),
    ]
    for x, title, lines, color in boxes:
        w = 260 if x < 700 else 236
        f.box(x, 120, w, 230, PALE if color == ACCENT else GREEN_PALE, color,
              sw=3)
        f.text(x + w / 2, 166, title, 24, weight="normal")
        for i, s in enumerate(lines):
            f.text(x + w / 2, 236 + 44 * i, s, 24)

    # First delivery: E1 crosses the gap from transaction 1 to 2.
    f.line(280, 236, 384, 236, ACCENT, 4, arrow="accent")
    token(f, 335, 200, ACCENT)

    # Second delivery of the same E1.
    f.path("M150,350 V412 H818 V358", OCHRE, 4, arrow="ochre", dash="10 8")
    token(f, 520, 412, OCHRE)
    f.text(520, 466, "同じ E1 がもう一度届く", 24)

    f.save("domain-event_concept.svg")


def redelivery_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "domain-event",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = []
    for line in (HERE / "lab" / "redelivery_output.txt").read_text().splitlines():
        parts = line.replace("|", " ").replace(",", "").replace("%", "").split()
        if len(parts) == 4 and parts[0][0].isdigit():
            rows.append([float(v) for v in parts])
    rate = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(rate, [r[2] for r in rows], color=RED, lw=2.4, marker="o",
            label="no processed record")
    ax.plot(rate, [r[3] for r in rows], color=ACCENT, lw=2.4, marker="s",
            label="processed record (EventID)")
    for x, y in zip(rate, [r[2] for r in rows]):
        if x >= 5:
            ax.text(x, y + 90, f"{y:,.0f}", ha="center", va="bottom", fontsize=10, color=RED)
    ax.set_xlabel("Crash rate between commit and ack (%)")
    ax.set_ylabel("Extra units reserved\n(10,000 events, 1 unit each)")
    ax.set_ylim(-100, 3000)
    ax.set_xticks([0, 1, 5, 10, 20])
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e6e6", lw=0.8)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "domain-event_redelivery.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    redelivery_figure()
