"""Generate the figures of the Nonce note.

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

tls_krack_figure(): TLS 1.3 starts the sequence number from 0 only after a new
traffic key, while KRACK reset the packet number under the same key.

Every figure is built as SVG or matplotlib here and only the WebP is kept in
images/ (SVG via headless Chrome at 2x, plots via PNG at dpi 200).

Run: uv run --with matplotlib --with pillow python content/notes/security/nonce/figures.py
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
        self.width, self.height = width, height
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
        """Write the SVG to a temporary file and keep only the WebP in images/."""
        import tempfile

        path = Path(path).with_suffix(".webp")
        path.parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "fig.svg"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            svg_to_webp(svg, path, self.width, self.height)


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
    seg(f, 0, 90, 230, 40, PALE, ACCENT, "")
    f.text((x(42) + x(90)) / 2, 259, "再起動前", 24)
    seg(f, 0, 40, 270, 40, OCHRE_PALE, OCHRE, "再起動後")
    f.box(x(0) - 4, 224, x(40) - x(0) + 8, 92, "none", RED, sw=4, rx=6)
    f.text(x(40) + 24, 300, "同じ nonce を 2 度使う", 24, RED, anchor="start")

    # Row 3: the next reservation (200) is saved before use; 61..199 are skipped.
    f.text(X0, 384, "使う前に先の番号を保存する", 24, weight="normal", anchor="start")
    f.text(x(200), 384, "保存値 200", 24, SUB)
    f.box(X0, 402, X1 - X0, 84, "#ffffff", SUB, sw=2.5, rx=4)
    seg(f, 0, 60, 404, 40, PALE, ACCENT, "再起動前")
    seg(f, 60, 200, 404, 40, FILL, SUB, "予約したが使わずに捨てる", SUB, dash="8 6")
    seg(f, 200, 240, 444, 40, OCHRE_PALE, OCHRE, "再起動後")
    f.line(x(200), 396, x(200), 492, SUB, sw=3)

    f.save(HERE / "images" / "nonce_concept.webp")


def save_plot(fig, name):
    """matplotlib figure -> PNG (dpi 200) -> WebP, white background."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    buf.seek(0)
    Image.open(buf).convert("RGB").save(
        HERE / "images" / name, "WEBP", quality=90, method=6)


JP_FONT = ["Noto Sans CJK JP"]


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
        "font.family": JP_FONT,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    crashes = cr.crash_points(cr.random.Random(cr.SEED))
    xs = sorted({int(10 ** (3 + i / 20)) for i in range(81)})  # 1e3 .. 1e7
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for m, ls in zip(cr.MS, ("--", "-")):
        res = cr.simulate(m, False, crashes, xs)
        pts = [(x, res[x]) for x in xs if res[x] > 0]
        ax.plot(*zip(*pts), color=RED, lw=2.4, ls=ls,
                label=f"カウンタ、{m:,} 本使うごとに保存")
    ax.plot(xs, [x * (x - 1) / 2 / 2**96 for x in xs], color=ACCENT, lw=2.4,
            label="96 bit の乱数の nonce（期待値）")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(1e-24, 1e8)
    ax.set_yticks([1e-20, 1e-15, 1e-10, 1e-5, 1, 1e5])
    ax.set_xlabel("1 つの鍵で送った通数（平均 1 万通に 1 回落ちる）")
    ax.set_ylabel("再利用した鍵と nonce の組の数")
    ax.text(1.2e3, 3e-4, "予約を先に保存するカウンタ：全ての点で 0",
            color=SUB, fontsize=10)
    ax.legend(loc="center right", frameon=False, fontsize=10,
              bbox_to_anchor=(1.0, 0.42))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.3, lw=0.6)
    fig.tight_layout()
    save_plot(fig, "nonce_counter_restart.webp")
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
    f.save(HERE / "images" / "nonce_layout.webp")


def birthday_figure():
    import math

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "font.family": JP_FONT,
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
    ax.text(32.6, p32 * 3, "NIST の上限：鍵あたり 2^32 回\nどれか 2 本が重なる確率：約 2^-33",
            color=INK, fontsize=10, va="bottom")
    ax.set_xlim(20, 56)
    ax.set_ylim(1e-18, 2)
    ax.set_xticks(range(20, 57, 4))
    ax.set_xticklabels([f"2^{e}" for e in range(20, 57, 4)])
    ax.set_xlabel("1 つの鍵で発行した 96 bit の乱数の nonce の本数")
    ax.set_ylabel("どれか 2 本が重なる確率")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.3, lw=0.6)
    fig.tight_layout()
    save_plot(fig, "nonce_birthday.webp")
    plt.close(fig)


def svg_to_webp(svg_path, webp_path, width, height):
    """Render a hand-written SVG with headless Chrome at 2x, then save it as WebP."""
    import subprocess
    import tempfile

    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "page.html"
        png = Path(tmp) / "shot.png"
        html.write_text(
            '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}'
            f'img{{display:block}}</style><img src="{svg_path.as_uri()}" '
            f'width="{width}" height="{height}">', encoding="utf-8")
        subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--allow-file-access-from-files", "--force-device-scale-factor=2",
             f"--window-size={width},{height}", f"--screenshot={png}", html.as_uri()],
            check=True, capture_output=True)
        Image.open(png).convert("RGB").save(webp_path, "WEBP", quality=90, method=6)


def ecdsa_k_figure():
    """ECDSA per-message secret k (same notation as the Digital Signature note).

    Left: a fresh secret k per signature, so the public (r, s, z) do not give d.
    Middle: the same k twice gives the same r, so k = (z1 - z2) / (s1 - s2).
    Right: a predictable k gives d = (s * k - z) / r from one signature.
    All arithmetic is modulo the curve order n. SVG is built here and only the
    WebP is kept in images/.
    """
    import tempfile

    w, h = 960, 470
    f = Svg(w, h, "ECDSA の k の扱いと、秘密鍵が求まる条件")
    cols = [(20, "署名ごとに違う k を", "秘密に保つ"),
            (340, "違うメッセージに", "同じ k を使う"),
            (660, "k を予測できる", "")]
    cw = 280
    for x0, t1, t2 in cols:
        f.text(x0 + cw / 2, 44, t1, 24)
        if t2:
            f.text(x0 + cw / 2, 74, t2, 24)

    def sig(x0, y, label, r, s, r_fill, r_stroke):
        f.box(x0, y, cw, 64, PALE, ACCENT, sw=2)
        f.text(x0 + 16, y + 41, label, 22, anchor="start")
        f.box(x0 + 108, y + 12, 70, 40, r_fill, r_stroke, sw=2, rx=6)
        f.text(x0 + 143, y + 40, r, 22)
        f.text(x0 + 228, y + 40, s, 22)

    # left: safe
    x0 = cols[0][0]
    sig(x0, 110, "署名 1", "r₁", "s₁", "#ffffff", ACCENT)
    sig(x0, 194, "署名 2", "r₂", "s₂", "#ffffff", ACCENT)
    f.line(x0 + cw / 2, 270, x0 + cw / 2, 316, SUB, sw=3)
    f.box(x0, 324, cw, 84, FILL, SUB, sw=2)
    f.text(x0 + cw / 2, 360, "公開値の r・s・z からは", 22)
    f.text(x0 + cw / 2, 390, "d が求まらない", 22)

    # middle: reuse
    x0 = cols[1][0]
    sig(x0, 110, "署名 1", "r", "s₁", OCHRE_PALE, OCHRE)
    sig(x0, 194, "署名 2", "r", "s₂", OCHRE_PALE, OCHRE)
    f.line(x0 + cw / 2, 270, x0 + cw / 2, 316, SUB, sw=3)
    f.box(x0, 324, cw, 84, "#fdecec", RED, sw=2.5)
    f.text(x0 + cw / 2, 358, "k = (z₁ − z₂) / (s₁ − s₂)", 21)
    f.text(x0 + cw / 2, 392, "続けて秘密鍵 d が求まる", 22)

    # right: predictable
    x0 = cols[2][0]
    sig(x0, 110, "署名", "r", "s", "#ffffff", ACCENT)
    f.box(x0, 194, cw, 64, FILL, SUB, sw=2, dash="8 6")
    f.text(x0 + cw / 2, 235, "予測した k", 22)
    f.line(x0 + cw / 2, 270, x0 + cw / 2, 316, SUB, sw=3)
    f.box(x0, 324, cw, 84, "#fdecec", RED, sw=2.5)
    f.text(x0 + cw / 2, 358, "d = (s·k − z) / r", 21)
    f.text(x0 + cw / 2, 392, "署名 1 つで秘密鍵が求まる", 22)

    f.text(w / 2, 450, "z はメッセージのハッシュ値。計算は全て n で割った余りで行う", 20, SUB)
    f.save(HERE / "images" / "nonce_ecdsa_k.webp")


def tls_krack_figure():
    """TLS 1.3 vs KRACK. Each band is the nonce space of one key.

    TLS 1.3 (RFC 8446 section 5.3) installs a new traffic key and then starts the
    sequence number from 0 again, so no (key, nonce) pair repeats. KRACK
    reinstalled the key already in use, so the packet number went back to its
    initial value under the same key (red overlap).
    """
    f = Svg(960, 400, "TLS 1.3 と KRACK の違い")
    f.text(X0, 60, "TLS 1.3：鍵を替えてから番号を 0 に戻す", 24, anchor="start")
    f.text(X1, 60, "帯 1 本 = 1 つの鍵", 24, SUB, anchor="end")
    f.box(X0, 78, x(110) - X0, 60, "#ffffff", SUB, sw=2.5, rx=4)
    seg(f, 0, 80, 78, 60, PALE, ACCENT, "鍵 1 で 0 から")
    f.box(x(130), 78, X1 - x(130), 60, "#ffffff", SUB, sw=2.5, rx=4)
    f.parts.append(
        f'<rect x="{x(130)}" y="78" width="{x(210) - x(130)}" height="60" rx="4" '
        f'fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="2.5"/>')
    f.text((x(130) + x(210)) / 2, 117, "鍵 2 で 0 から", 24)
    f.text((x(110) + x(130)) / 2, 174, "鍵を替える", 20, SUB)

    f.text(X0, 236, "KRACK：同じ鍵を設定し直し、番号だけが戻る", 24, anchor="start")
    f.box(X0, 254, X1 - X0, 84, "#ffffff", SUB, sw=2.5, rx=4)
    seg(f, 0, 120, 256, 40, PALE, ACCENT, "")
    f.text((x(52) + x(120)) / 2, 285, "設定し直す前", 24)
    seg(f, 0, 50, 296, 40, OCHRE_PALE, OCHRE, "設定し直した後")
    f.box(x(0) - 4, 250, x(50) - x(0) + 8, 92, "none", RED, sw=4, rx=6)
    f.text(x(50) + 24, 326, "同じ鍵と nonce の組を 2 度使う", 24, RED, anchor="start")
    f.save(HERE / "images" / "nonce_tls_krack.webp")


if __name__ == "__main__":
    ecdsa_k_figure()
    tls_krack_figure()
    concept_figure()
    counter_restart_figure()
    layout_figure()
    birthday_figure()
