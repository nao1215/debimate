"""Generate the figures of the stdio buffering note.

Run: python3 figures.py  -> images/*.webp

The plots read the experiment outputs in lab/output/ (exp1.tsv, exp2.tsv,
exp3.txt, exp4.txt, exp5.txt), so rerun the lab scripts first when the
environment changes. The concept figure is built as SVG text here, rendered by
headless Chrome at 2x and saved as WebP (Pillow). Only the WebP files are kept
in images/.

- arrival_c_figure(): animation of the lines of the C program waiting in the
  buffer and reaching the reader (terminal, pipe, pipe with stdbuf -oL), driven
  by the measured arrival times. Also the cover of the note.
- buffer_path_figure(): where the stdio buffer lives and when it is written.
- interrupt_figure(): animation; SIGINT after 1.2 s loses the lines left in the buffer.
- arrival_languages_figure(): animation of the same experiment for C, Python, Go and Rust.
- coreutils_figure(): GNU and uutils filters in the middle of a pipeline.
- failure_figure(): whether each program reports a broken pipe, a full disk
  and a closed stdout.
- closed_stdout_figure(): where hello goes when stdout is closed (>&-).
"""

from html import escape
from pathlib import Path
import io
import re
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED = "#7aa6c2", "#e15759"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP",
    "font.size": 11,
    "axes.edgecolor": SUB,
    "axes.labelcolor": INK,
    "xtick.color": SUB,
    "ytick.color": INK,
})


def save_plot(fig, name):
    """matplotlib figure -> PNG (dpi 200, white) -> images/<name> (WebP)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(buf).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def render_svg(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        (HERE / "images").mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def read_exp1():
    """{(言語, 条件): [到着秒, ...]}"""
    rows = {}
    for line in (OUT / "exp1.tsv").read_text(encoding="utf-8").splitlines():
        lang, cond, rest = line.split("\t")
        rows.setdefault((lang, cond), []).append(float(rest.split()[0]))
    return rows


WRITES = [0.0, 0.5, 1.0, 1.5, 2.0]  # slow.* が各行を書いた時刻（起動からの秒）
CONDS = ["端末", "パイプ", "パイプ+stdbuf -oL"]


from PIL import ImageDraw, ImageFont  # noqa: E402

JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
S = 2  # 2 倍で描き、高解像度の画面でも文字を潰さない


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, size * S, index=0 if mono else 0)


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def animate(rows, name, t_end, kill=None, row_h=96, hold=3.0, fps=10, speed=0.5, exit_at=2.5):
    """各行を「バッファに溜まっている行」と「読む側に届いた行」の 2 つの箱で見せる動画。

    rows: [(見出し, 書いた時刻のリスト, 届いた時刻のリスト)]。届いた時刻が足りない行は、
    kill の時刻にバッファの中で消える。時刻は 1/fps 秒ずつ進め、speed 倍速で再生し、最後の状態で hold 秒止める。
    """
    W, top = 900, 92
    H = top + row_h * len(rows) + 16
    lab_w, box_w, gap = 190, 300, 60
    bx = lab_w + 10
    rx = bx + box_w + gap
    frames, durations = [], []
    steps = int(round(t_end * fps))
    for k in range(steps + 1):
        t = k / fps
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        # 時計と時間の帯
        d.text((20 * S, 14 * S), f"経過 {t:.1f} 秒", font=font(20), fill=hex2rgb(INK))
        d.text((20 * S, 44 * S), f"{speed:g} 倍速で再生", font=font(11), fill=hex2rgb(SUB))
        d.text((170 * S, 19 * S), "プログラムは 0.5 秒ごとに 1 行書く", font=font(14), fill=hex2rgb(SUB))
        x0, x1, yb = 520, 880, 30
        d.line([(x0 * S, yb * S), (x1 * S, yb * S)], fill=hex2rgb("#cfcfcf"), width=3 * S)
        for w in WRITES:
            if w <= t_end:
                xx = x0 + (x1 - x0) * w / t_end
                d.line([(xx * S, (yb - 5) * S), (xx * S, (yb + 5) * S)], fill=hex2rgb(SUB), width=S)
        if kill is None and exit_at is not None:
            xx = x0 + (x1 - x0) * exit_at / t_end
            d.line([(xx * S, (yb - 9) * S), (xx * S, (yb + 9) * S)], fill=hex2rgb(INK), width=2 * S)
            d.text(((xx - 12) * S, (yb + 10) * S), "終了", font=font(11), fill=hex2rgb(INK))
        if kill is not None:
            xx = x0 + (x1 - x0) * kill / t_end
            d.line([(xx * S, (yb - 9) * S), (xx * S, (yb + 9) * S)], fill=hex2rgb(RED), width=2 * S)
            d.text(((xx - 30) * S, (yb + 10) * S), "Ctrl-C", font=font(11), fill=hex2rgb(RED))
        d.text(((x0 - 4) * S, (yb + 9) * S), "0 秒", font=font(11), fill=hex2rgb(SUB))
        d.text(((x1 - 22) * S, (yb + 9) * S), f"{t_end:.0f} 秒", font=font(11), fill=hex2rgb(SUB))
        xx = x0 + (x1 - x0) * min(t, t_end) / t_end
        d.ellipse([((xx - 6) * S, (yb - 6) * S), ((xx + 6) * S, (yb + 6) * S)], fill=hex2rgb(INK))
        # 列の見出し
        d.text((bx * S, 62 * S), "バッファに溜まっている行", font=font(14), fill=hex2rgb(SUB))
        d.text((rx * S, 62 * S), "読む側に届いた行", font=font(14), fill=hex2rgb(SUB))
        for i, (label, writes, arrived) in enumerate(rows):
            y = top + i * row_h
            d.text((20 * S, (y + row_h / 2 - 22) * S), label, font=font(15), fill=hex2rgb(INK))
            killed = kill is not None and t >= kill
            # 計測の遅れ（0.02 秒前後）でバッファに一瞬映らないよう、0.1 秒未満の遅れは即時とみなす
            shown = [w if a - w < 0.1 else a for w, a in zip(writes, arrived)]
            waiting = [n for n, w in enumerate(writes, 1)
                       if w <= t + 1e-9 and (n > len(shown) or shown[n - 1] > t + 1e-9)]
            got = [n for n, a in enumerate(shown, 1) if a <= t + 1e-9]
            # バッファの箱
            fill = hex2rgb(RED_PALE) if waiting else hex2rgb(FILL)
            d.rounded_rectangle([bx * S, (y + 4) * S, (bx + box_w) * S, (y + row_h - 10) * S],
                                radius=8 * S, fill=fill, outline=hex2rgb("#bdbdbd"), width=S)
            # 読む側の箱
            d.rounded_rectangle([rx * S, (y + 4) * S, (rx + box_w) * S, (y + row_h - 10) * S],
                                radius=8 * S, fill=hex2rgb("#ffffff"), outline=hex2rgb("#bdbdbd"), width=S)
            ax_ = (bx + box_w + 8) * S
            d.line([(ax_, (y + row_h / 2 - 3) * S), (ax_ + (gap - 16) * S, (y + row_h / 2 - 3) * S)],
                   fill=hex2rgb(SUB), width=2 * S)
            tip = ax_ + (gap - 16) * S
            d.polygon([(tip, (y + row_h / 2 - 8) * S), (tip + 8 * S, (y + row_h / 2 - 3) * S),
                       (tip, (y + row_h / 2 + 2) * S)], fill=hex2rgb(SUB))

            def chips(x, nums, color, strike=False):
                for j, n in enumerate(nums):
                    cx, cy = x + 10 + (j % 3) * 96, y + 12 + (j // 3) * 34
                    d.rounded_rectangle([cx * S, cy * S, (cx + 88) * S, (cy + 28) * S], radius=5 * S,
                                        fill=hex2rgb("#ffffff"), outline=hex2rgb(color), width=2 * S)
                    d.text(((cx + 10) * S, (cy + 4) * S), f"line {n}", font=font(14, mono=True),
                           fill=hex2rgb(color))
                    if strike:
                        d.line([((cx + 4) * S, (cy + 24) * S), ((cx + 84) * S, (cy + 4) * S)],
                               fill=hex2rgb(RED), width=2 * S)

            if killed and waiting:
                chips(bx, waiting, RED, strike=True)
                d.text(((bx + 10) * S, (y + row_h - 34) * S), "強制終了で消えた", font=font(13),
                       fill=hex2rgb(RED))
            else:
                chips(bx, waiting, RED)
            chips(rx, got, INK)
        frames.append(im.resize((W * 3 // 2, H * 3 // 2), Image.LANCZOS))
        durations.append(int(1000 / fps / speed))
    durations[-1] = int(hold * 1000)
    (HERE / "images").mkdir(exist_ok=True)
    frames[0].save(HERE / "images" / name, "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=80, method=6)


def arrival_c_figure():
    rows = read_exp1()
    animate([(c, WRITES, rows[("C", c)]) for c in CONDS], "arrival_c.webp", t_end=3.0)


def arrival_languages_figure():
    rows = read_exp1()
    sel = [("C", "パイプ"), ("C", "パイプ+stdbuf -oL"), ("Python", "パイプ"),
           ("Python", "パイプ+stdbuf -oL"), ("Go", "パイプ"), ("Rust", "パイプ")]
    animate([(f"{lang}\n{cond}", WRITES, rows[(lang, cond)]) for lang, cond in sel],
            "arrival_languages.webp", t_end=3.0, row_h=84)


def interrupt_figure():
    text = (OUT / "exp5.txt").read_text(encoding="utf-8")
    blocks = re.split(r"^== .*$", text, flags=re.M)[1:]
    arrivals = [[float(m) for m in re.findall(r"^([0-9.]+) line", b, re.M)] for b in blocks]
    labels = ["パイプ", "パイプ+stdbuf -oL"]
    written = [w for w in WRITES if w < 1.2]
    animate([(lab, written, got) for lab, got in zip(labels, arrivals)], "interrupt.webp",
            t_end=2.0, kill=1.2)


def coreutils_figure():
    first = {}
    for line in (OUT / "exp2.tsv").read_text(encoding="utf-8").splitlines():
        impl, cond, flt, rest = line.split("\t", 3)
        first.setdefault((impl, cond, flt), float(rest.split()[0]))
    filters = ["cat", "tee", "head", "tr", "cut", "fold", "uniq", "nl"]
    cols = [("GNU", "そのまま"), ("GNU", "stdbuf -oL"), ("uutils", "そのまま"), ("uutils", "stdbuf -oL")]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for x, col in enumerate(cols):
        for y, flt in enumerate(filters):
            t = first[(col[0], col[1], flt)]
            streaming = t < 1.0
            # 無彩色を基本にする。1 行ずつは白、最後にまとめては灰。
            # 赤は uutils で stdbuf -oL が効かなかったマスだけに使う。
            failed = col == ("uutils", "stdbuf -oL") and not streaming
            ax.add_patch(plt.Rectangle((x + 0.04, y + 0.06), 0.92, 0.88,
                                       facecolor="#ffffff" if streaming else "#e9e9e9",
                                       edgecolor=RED if failed else "#c8c8c8", lw=2 if failed else 1))
            ax.text(x + 0.5, y + 0.5, "1 行ずつ" if streaming else "最後にまとめて",
                    ha="center", va="center", fontsize=10, color=RED if failed else (INK if streaming else SUB))
    ax.set_xlim(0, len(cols))
    ax.set_ylim(len(filters), 0)
    ax.set_xticks([i + 0.5 for i in range(len(cols))])
    ax.set_xticklabels([f"{a}\n{b}" for a, b in cols])
    ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(filters))])
    ax.set_yticklabels(filters, fontfamily="monospace")
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.axvline(2, color=SUB, lw=1)
    save_plot(fig, "coreutils.webp")


def failure_figure():
    def codes(path):
        text = (OUT / path).read_text(encoding="utf-8")
        return {m.group(1): (m.group(2), m.group(3).strip())
                for m in re.finditer(r"== (.+?)\nexit=(\d+)\n(.*?)(?=\n== |\Z)", text, re.S)}
    pipe, wr = codes("exp3.txt"), codes("exp4.txt")
    progs = [("C", "bin/loop_c", "bin/hello_c"), ("Python", "python3 src/loop.py", "python3 src/hello.py"),
             ("Go", "bin/loop_go", "bin/hello_go"), ("Rust", "bin/loop_rs", "bin/hello_rs"),
             ("GNU yes / cat", "gnuyes", "gnucat hello.txt"), ("uutils yes / cat", "yes", "cat hello.txt")]
    cols = ["読む側が先に終わる\n（| head -n 1）", "書き込み先が満杯\n（> /dev/full）", "標準出力が閉じている\n（>&-）"]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    for y, (name, loop, hello) in enumerate(progs):
        cells = [pipe[loop], wr[f"{hello} > /dev/full"], wr[f"{hello} > closed"]]
        for x, (code, err) in enumerate(cells):
            silent = code == "0" and not err
            if x == 0:
                note = {"141": "SIGPIPE で終了", "120": "例外を表示", "101": "panic"}.get(code, "")
            else:
                closed_note = {"C": "書けないまま終了", "Python": "何も書かない"}.get(name, "/dev/null に書く")
                note = ((closed_note if x == 2 else "失敗を報告しない") if silent else
                        "例外を表示" if "Error" in err else
                        "panic" if "panicked" in err else "エラーを表示")
            ax.add_patch(plt.Rectangle((x + 0.04, y + 0.06), 0.92, 0.88,
                                       color=RED_PALE if silent else FILL, lw=0))
            ax.text(x + 0.5, y + 0.5, f"終了コード {code}\n{note}", ha="center", va="center",
                    fontsize=10, color=RED if silent else INK, linespacing=1.4)
    ax.set_xlim(0, 3)
    ax.set_ylim(len(progs), 0)
    ax.set_xticks([0.5, 1.5, 2.5])
    ax.set_xticklabels(cols)
    ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(progs))])
    ax.set_yticklabels([p[0] for p in progs])
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    save_plot(fig, "failures.webp")


def buffer_path_figure():
    w, h = 900, 330
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
         '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
         f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def box(x, y, bw, bh, fill, stroke=SUB, dash=False):
        d = ' stroke-dasharray="6 4"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="1.5"{d}/>')

    def text(x, y, s, size=15, color=INK, anchor="middle"):
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">'
                 f'{escape(s)}</text>')

    def arrow(x1, y1, x2, y2):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="1.8" '
                 'marker-end="url(#a)"/>')

    # 書く側のプロセス
    box(20, 30, 360, 200, FILL, dash=True)
    text(200, 56, "書く側のプロセス", 15, SUB)
    box(45, 80, 130, 56, "#ffffff")
    text(110, 104, "printf", 15)
    text(110, 124, "（C の例）", 12, SUB)
    box(220, 72, 140, 72, PALE, stroke=ACCENT)
    text(290, 100, "stdio のバッファ", 15)
    text(290, 122, "（プロセスのメモリ）", 12, SUB)
    arrow(175, 108, 218, 108)
    text(200, 178, "ここに溜まった行は、まだ誰にも見えない", 13, RED)
    text(200, 200, "プロセスが強制終了すると消える", 13, RED)
    # カーネル
    box(455, 30, 200, 200, "#ffffff", dash=True)
    text(555, 56, "カーネル", 15, SUB)
    box(480, 80, 150, 56, FILL)
    text(555, 104, "パイプ", 15)
    text(555, 124, "（カーネルのバッファ）", 12, SUB)
    arrow(362, 108, 478, 108)
    text(408, 96, "write(2)", 12, SUB)
    # 読む側
    box(700, 80, 180, 56, FILL)
    text(790, 104, "読む側のプロセス", 15)
    text(790, 124, "grep・cut など", 12, SUB)
    arrow(632, 108, 698, 108)
    # 書き出す契機
    text(20, 268, "write(2) を呼ぶ契機", 14, SUB, "start")
    modes = [("バッファ無し", "書くたびに"), ("行バッファ", "改行を書いた時"), ("全バッファ", "満杯になった時・終了時")]
    for i, (name, when) in enumerate(modes):
        x = 20 + i * 290
        box(x, 282, 270, 36, "#ffffff")
        text(x + 14, 306, name, 14, INK, "start")
        text(x + 256, 306, when, 13, SUB, "end")
    p.append("</svg>")
    render_svg("".join(p), w, h, "buffer_path.webp")


def closed_stdout_figure():
    """閉じた標準出力（>&-）で、hello がどこへ行くかを 3 通り並べる。"""
    w, h = 900, 300
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
         '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
         f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def box(x, y, bw, bh, fill, stroke=SUB):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="1.5"/>')

    def text(x, y, t, size=14, color=INK, anchor="middle"):
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">'
                 f'{escape(t)}</text>')

    def arrow(x1, y1, x2, y2):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="1.8" '
                 'marker-end="url(#a)"/>')

    text(20, 30, "シェルが標準出力（1 番）を閉じて起動した後、hello はどこへ行くか", 15, SUB, "start")
    rows = [
        ("C", "起動時は何もしない", "printf → バッファ", "終了時の 1 番への write(2) が EBADF", RED_PALE, "失敗を確かめず 0"),
        ("Go・Rust・uutils", "起動時に 1 番へ /dev/null を開く", "1 番への write(2) は成功", "/dev/null に捨てられる", RED_PALE, "成功なので 0"),
        ("Python", "起動時に sys.stdout を None にする", "print は何もしない", "どこにも書かれない", RED_PALE, "何も起きず 0"),
    ]
    for i, (name, start, mid, end, fill, result) in enumerate(rows):
        y = 52 + i * 80
        text(20, y + 34, name, 15, INK, "start")
        box(170, y + 8, 230, 44, FILL)
        text(285, y + 35, start, 13)
        arrow(402, y + 30, 430, y + 30)
        box(432, y + 8, 170, 44, "#ffffff")
        text(517, y + 35, mid, 13)
        arrow(604, y + 30, 632, y + 30)
        box(634, y + 8, 250, 44, fill, RED)
        text(759, y + 27, end, 13)
        text(759, y + 45, result, 12, RED)
    p.append("</svg>")
    render_svg("".join(p), w, h, "closed_stdout.webp")


if __name__ == "__main__":
    arrival_c_figure()
    buffer_path_figure()
    interrupt_figure()
    arrival_languages_figure()
    coreutils_figure()
    failure_figure()
    closed_stdout_figure()
