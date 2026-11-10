"""Generate the cover diagram of the Authentication note.

concept_figure() draws a hand-written SVG (stdlib only). The account sits
behind one wall, and every way in is a door in that wall: the normal login
(a phishing-resistant method such as a passkey) and the three recovery paths
of the "Account Recovery と認証の強さ" section. The colour of a door is how
hard it is to get through, and the attacker walks through the weakest one.

otp_guessing_figure(): the chance of guessing a 6-digit confirmation code
under different attempt limits, from lab/otp_guessing.py (needs matplotlib).

Run: uv run --with matplotlib python content/notes/security/authentication/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE = "#d4a24c"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, rx=0):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def poly(self, points, fill, stroke="none", sw=2.5):
        pts = " ".join(f"{x},{y}" for x, y in points)
        self.parts.append(
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color, sw=5, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


# (label lines, kind). strong: closed and hard, depends: as strong as the
# e-mail account, weak: guessable or talked through.
DOORS = [
    (["Passkey"], "strong"),
    (["メールの", "コード"], "depends"),
    (["秘密の", "質問"], "weak"),
    (["サポート", "窓口"], "weak"),
]


def door(f, cx, top, bottom, lines, kind):
    w = 150
    x = cx - w / 2
    ty = (top + bottom) / 2 - (len(lines) - 1) * 16 + 8
    if kind == "weak":
        # An open door: the frame shows the way through, the ochre leaf swings out.
        f.box(x, top, w, bottom - top, "#ffffff", OCHRE, sw=4)
        f.poly([(x, top), (x + 34, top + 22), (x + 34, bottom + 14), (x, bottom)], OCHRE)
        for i, s in enumerate(lines):
            f.text(cx + 16, ty + i * 32, s, 24)
    else:
        fill, stroke, sw = (ACCENT, ACCENT, 6) if kind == "strong" else ("#ffffff", SUB, 3)
        f.box(x, top, w, bottom - top, fill, stroke, sw=sw)
        f.parts.append(f'<circle cx="{x + w - 22}" cy="{bottom - 50}" r="6" '
                       f'fill="{INK if kind == "strong" else SUB}"/>')
        for i, s in enumerate(lines):
            f.text(cx, ty + i * 32, s, 24)


def concept_figure():
    f = Svg(960, 540, "アカウントに入る扉と、その強さ")
    xs = [150, 370, 590, 810]
    wall_top, door_top, floor = 120, 196, 390

    f.box(40, 20, 880, 70, PALE, ACCENT, sw=2.5, rx=10)
    f.text(480, 66, "アカウント", 28, weight="normal")

    f.box(40, wall_top, 880, floor - wall_top, FILL)
    f.text(xs[0], wall_top + 40, "通常のログイン", 24, SUB)
    f.text(xs[2], wall_top + 40, "復旧の経路", 24, SUB)
    f.line(xs[1] - 75, wall_top + 56, xs[3] + 75, wall_top + 56, SUB, sw=2)
    for cx, (lines, kind) in zip(xs, DOORS):
        door(f, cx, door_top, floor, lines, kind)
    f.line(30, floor, 930, floor, SUB, sw=3)

    # The attacker picks the weakest door, not the strongest one.
    # Only the attacker's way in is red; the words stay black.
    f.text(xs[3] + 40, 515, "攻撃者", 26, INK, weight="normal", anchor="end")
    f.line(xs[3] + 60, 500, xs[3] + 60, floor - 36, RED, sw=6, arrow=True)
    f.text(60, 458, "アカウントの強さは", 26, anchor="start")
    f.text(60, 500, "最も弱い扉で決まる", 26, INK, weight="normal", anchor="start")

    (HERE / "images").mkdir(exist_ok=True)
    f.save(HERE / "images" / "authentication_concept.svg")


def otp_guessing_figure():
    import sys

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sys.path.insert(0, str(HERE / "lab"))
    import otp_guessing as og

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "authentication-otp",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    hours = [10 ** (i / 50) for i in range(-100, 144)]  # 0.6 min .. 30 days
    styles = [(RED, "-"), (RED, "--"), (ACCENT, "-"), (ACCENT, "--")]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (name, rate, lockout), (color, ls) in zip(og.SETTINGS, styles):
        ys = [100 * og.success(rate, lockout, h * 3600) for h in hours]
        ax.plot(hours, ys, color=color, ls=ls, lw=2.4, label=name)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(hours[0], hours[-1])
    ax.set_ylim(1e-4, 200)
    ticks = [1 / 60, 1, 24, 24 * 30]
    ax.set_xticks(ticks, ["1 min", "1 hour", "1 day", "30 days"])
    ax.minorticks_off()
    ax.set_yticks([1e-3, 1e-2, 1e-1, 1, 10, 100],
                  ["0.001%", "0.01%", "0.1%", "1%", "10%", "100%"])
    ax.set_xlabel("Time the attacker keeps guessing")
    ax.set_ylabel("Chance of guessing\nthe 6-digit code")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.3, lw=0.6)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "authentication_otp_guessing.svg",
                metadata={"Date": None})
    plt.close(fig)


def revocation_figure():
    """What happens to a stolen value after the user logs out.

    Two lanes on one time axis. Top: the server looks up its record, so
    deleting the record at logout rejects the stolen value (one red cross).
    Bottom: the server checks only the value, so the stolen value keeps
    working (ochre) until the expiry written inside it.
    """
    f = Svg(960, 540, "ログアウトの後に盗まれた値が使われた時の、2 つの検証方式の違い")
    x0, xo, xs, xe = 300, 500, 640, 880  # issue, logout, stolen use, expiry
    for y, label, token in ((140, "記録を引く", False), (360, "値の中だけ", True)):
        f.text(40, y + 10, label, 26, anchor="start")
        f.box(x0, y - 22, xo - x0, 44, PALE, ACCENT, rx=8)
        f.text((x0 + xo) / 2, y + 9, "利用者が使う", 24)
        f.line(xo, y - 46, xo, y + 46, SUB, sw=3)
        f.text(xo, y + 78, "ログアウト", 24, SUB)
        f.text(xs, y - 78, "盗んだ値", 24)
        f.line(xs, y - 70, xs, y - 26, INK, sw=3)
        if token:
            f.box(xo, y - 22, xe - xo, 44, "#f8eed8", OCHRE, rx=8)
            f.text((xo + xs) / 2, y + 9, "有効", 24)
            f.text(xs + 120, y + 9, "通る", 24)
            f.line(xe, y - 46, xe, y + 46, SUB, sw=3)
            f.text(xe, y + 78, "有効期限", 24, SUB)
        else:
            for d in (-1, 1):
                f.line(xs - 14, y - 14 * d, xs + 14, y + 14 * d, RED, sw=6)
            f.text(xs + 120, y + 9, "弾かれる", 24)
    f.line(x0, 484, xe + 40, 484, SUB, sw=2)
    f.poly([(xe + 40, 476), (xe + 54, 484), (xe + 40, 492)], SUB)
    f.text(xe + 20, 520, "時間", 24, SUB)
    f.save(HERE / "images" / "authentication_revocation.svg")

if __name__ == "__main__":
    concept_figure()
    otp_guessing_figure()
    revocation_figure()
