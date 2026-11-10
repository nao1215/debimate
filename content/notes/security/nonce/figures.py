"""Generate the cover diagram of the Nonce note as a hand-written SVG (stdlib only).

concept_figure(): each band is the nonce space of one key. Row 1 gives each
sender its own range (Fixed field). Row 2 loses the counter on restart and
reuses 0..40 (red overlap). Row 3 saves the next reservation (200) before use,
so 61..199 are skipped and nothing is reused. Numbers follow the note's example.

counter_restart_figure(): reused nonces over time for counters saved after use,
counters reserved ahead, and random 96-bit nonces, from lab/counter_restart.py
(needs matplotlib).

layout_figure(): byte layout of a 12-octet nonce. RFC 5116 section 3.2 joins an
8-octet Fixed field and a 4-octet Counter field. TLS 1.3 (RFC 8446 section 5.3)
pads the 64-bit sequence number with 4 zero octets on the left and XORs it with
the 12-octet static IV.

birthday_figure(): probability that any two of n random 96-bit nonces collide,
1 - exp(-n(n-1)/2 / 2^96), with the NIST SP 800-38D limit of 2^32 calls marked
(about 2^-33 there). Formula only (needs matplotlib).

Run: uv run --with matplotlib python content/notes/security/nonce/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
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

    def line(self, x1, y1, x2, y2, color, sw=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


X0, X1, N = 60, 900, 240  # band from x=60 to x=900 covers counter 0..240


def x(n):
    return X0 + (X1 - X0) * n / N


def seg(f, n1, n2, y, h, fill, stroke, label, color=INK, dash=""):
    f.box(x(n1), y, x(n2) - x(n1), h, fill, stroke, sw=2.5, dash=dash, rx=4)
    if label:
        f.text((x(n1) + x(n2)) / 2, y + h / 2 + 9, label, 24, color)


def concept_figure():
    f = Svg(960, 540, "1 つの鍵の nonce の範囲と、重なって再使用される区間")

    # Row 1: a different Fixed field per sender splits the space.
    f.text(X0, 66, "送信者ごとに範囲を分ける", 24, weight="normal", anchor="start")
    f.text(X1, 66, "帯 1 本 = 1 つの鍵", 24, SUB, anchor="end")
    f.box(X0, 84, X1 - X0, 60, "#ffffff", SUB, sw=2.5, rx=4)
    seg(f, 0, 70, 84, 60, PALE, ACCENT, "送信者 A")
    seg(f, 120, 190, 84, 60, OCHRE_PALE, OCHRE, "送信者 B")
    f.line(x(120), 76, x(120), 152, SUB, sw=3)

    # Row 2: the counter is lost on restart and starts again from 0.
    f.text(X0, 210, "再起動でカウンタが 0 に戻る", 24, weight="normal", anchor="start")
    f.box(X0, 228, X1 - X0, 84, "#ffffff", SUB, sw=2.5, rx=4)
    seg(f, 0, 60, 230, 40, PALE, ACCENT, "再起動前")
    seg(f, 0, 40, 270, 40, OCHRE_PALE, OCHRE, "再起動後")
    f.box(x(0) - 4, 224, x(40) - x(0) + 8, 92, "none", RED, sw=4, rx=6)
    f.text(x(40) + 30, 299, "同じ nonce を 2 度使う", 24, RED, anchor="start")

    # Row 3: the next reservation (200) is saved before use; 61..199 are skipped.
    f.text(X0, 384, "使う前に先の番号を保存する", 24, weight="normal", anchor="start")
    f.text(x(200), 384, "保存値 200", 24, SUB)
    f.box(X0, 402, X1 - X0, 84, "#ffffff", SUB, sw=2.5, rx=4)
    seg(f, 0, 60, 404, 40, PALE, ACCENT, "再起動前")
    seg(f, 60, 200, 404, 40, FILL, SUB, "予約したが使わずに捨てる", SUB, dash="8 6")
    seg(f, 200, 240, 444, 40, OCHRE_PALE, OCHRE, "再起動後")
    f.line(x(200), 396, x(200), 492, SUB, sw=3)

    f.save(HERE / "images" / "nonce_concept.svg")


def counter_restart_figure():
    import sys

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sys.path.insert(0, str(HERE / "lab"))
    import counter_restart as cr

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "nonce-counter-restart",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    crashes = cr.crash_points(cr.random.Random(cr.SEED))
    xs = sorted({int(10 ** (3 + i / 20)) for i in range(81)})  # 1e3 .. 1e7
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for k, ls in zip(cr.KS, ("--", "-")):
        res = cr.simulate(k, False, crashes, xs)
        pts = [(x, res[x]) for x in xs if res[x] > 0]
        ax.plot(*zip(*pts), color=RED, lw=2.4, ls=ls,
                label=f"counter, save after every {k:,} uses")
    ax.plot(xs, [x * (x - 1) / 2 / 2**96 for x in xs], color=ACCENT, lw=2.4,
            label="random 96-bit nonce (expected)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(1e-24, 1e8)
    ax.set_yticks([1e-20, 1e-15, 1e-10, 1e-5, 1, 1e5])
    ax.set_xlabel("Messages sent with one key (about one crash per 10,000)")
    ax.set_ylabel("Reused (key, nonce) pairs")
    ax.text(1.2e3, 3e-4, "counter that reserves ahead: 0 at every point",
            color=SUB, fontsize=10)
    ax.legend(loc="center right", frameon=False, fontsize=10,
              bbox_to_anchor=(1.0, 0.42))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.3, lw=0.6)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "nonce_counter_restart.svg", metadata={"Date": None})
    plt.close(fig)


def octets(f, x0, y, n, w, fill, stroke, label, sub=""):
    f.box(x0, y, n * w, 64, fill, stroke, sw=2, rx=2)
    for i in range(1, n):  # short ticks keep the label readable
        f.line(x0 + i * w, y, x0 + i * w, y + 12, stroke, sw=2)
        f.line(x0 + i * w, y + 52, x0 + i * w, y + 64, stroke, sw=2)
    f.text(x0 + n * w / 2, y + 41, label, 24)
    if sub:
        f.text(x0 + n * w / 2, y + 100, sub, 24, SUB)


def layout_figure():
    f = Svg(960, 540, "12 octet の nonce の組み立て。RFC 5116 の推奨形と TLS 1.3")
    w, x0 = 64, 96
    f.text(x0, 60, "RFC 5116 の推奨形", 26, anchor="start")
    f.text(x0 + 12 * w, 60, "1 マス = 1 octet", 24, SUB, anchor="end")
    octets(f, x0, 84, 8, w, PALE, ACCENT, "Fixed field", "送信者ごとに違う")
    octets(f, x0 + 8 * w, 84, 4, w, OCHRE_PALE, OCHRE, "Counter", "1 ずつ進む")

    f.text(x0, 290, "TLS 1.3 のレコードごとの nonce", 26, anchor="start")
    octets(f, x0, 312, 4, w, FILL, SUB, "0 で埋める")
    octets(f, x0 + 4 * w, 312, 8, w, OCHRE_PALE, OCHRE, "sequence number（64 bit）")
    f.text(x0 + 12 * w + 40, 354, "XOR", 26)
    octets(f, x0, 400, 12, w, PALE, ACCENT, "static IV（送信の方向ごと）")
    f.text(x0 + 12 * w + 40, 442, "=", 26)
    f.text(x0 + 6 * w, 510, "結果が nonce。static IV は外に出ない", 24, SUB)
    f.save(HERE / "images" / "nonce_layout.svg")


def birthday_figure():
    import math

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "nonce-birthday",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    es = [i / 4 for i in range(20 * 4, 56 * 4 + 1)]  # n = 2^20 .. 2^56
    ps = [-math.expm1(-(2**e) * (2**e - 1) / 2 / 2**96) for e in es]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(es, ps, color=ACCENT, lw=2.4)
    ax.set_yscale("log")
    ax.axvline(32, color=OCHRE, lw=1.8, ls="--")
    p32 = -math.expm1(-(2**32) * (2**32 - 1) / 2 / 2**96)
    ax.plot([32], [p32], "o", color=OCHRE, ms=7)
    ax.text(32.6, p32 * 3, "NIST limit: 2^32 calls per key\nany collision: about 2^-33",
            color=INK, fontsize=10, va="bottom")
    ax.set_xlim(20, 56)
    ax.set_ylim(1e-18, 2)
    ax.set_xticks(range(20, 57, 4))
    ax.set_xticklabels([f"2^{e}" for e in range(20, 57, 4)])
    ax.set_xlabel("Random 96-bit nonces issued with one key")
    ax.set_ylabel("Probability that any two collide")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.3, lw=0.6)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "nonce_birthday.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    counter_restart_figure()
    layout_figure()
    birthday_figure()
