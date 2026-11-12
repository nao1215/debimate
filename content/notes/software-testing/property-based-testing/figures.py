"""Property-Based Testing のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

止め絵は SVG の文字列をここで組み、headless Chrome で 2 倍で描いて WebP にする（Pillow）。
動く図は Pillow の ImageDraw でコマを描く。images/ には WebP だけを残す。
数値と反例は lab/output/ から読むので、実験の script を回し直したら、この script も回し直す。

- cover_figure(): 表紙。修正前の Distinct に同じ性質を掛けた時、testing/quick が報告した反例（10 行）と
  rapid が縮めた反例（2 行）を並べる（lab/output/exp1_shrink.tsv の種 1）。
- keys_figure(): 修正前の makeRowKey が、異なる 2 行に同じ鍵を作る 3 つの組（filesql Issue #354）。
- shrink_animation(): rapid が種 1 の反例を縮める途中で、性質が破れた表を順に見せる動画
  （lab/output/exp1_shrink_steps_seed1.txt）。
- float_figure(): 修正後の鍵が整数を float64 にしてから文字列にするので、2^53 を超えると
  隣り合う整数が同じ鍵になる（filesql Issue #379）。
- fuzz_figure(): go test -fuzz が縮めたバイト列と、それを表に読み替えた結果
  （lab/output/exp3_crashers/fixed_run1.txt）。
"""

import ast
import csv
import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#7aa6c2", "#d64545", "#fbe3e3"
LINE = "#9a9a9a"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"


def render_svg(svg_text, w, h, name):
    """SVG の文字列 -> PNG（headless Chrome、2 倍）-> images/<name>（WebP）。"""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        (HERE / "images").mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                  f'<style>text{{font-family:{FONT};fill:{INK}}} .m{{font-family:{MONO}}}</style>',
                  '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
                  f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
                  f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def box(self, x, y, bw, bh, fill, stroke=SUB, dash=False, rx=8, width=1.5):
        d = ' stroke-dasharray="6 4"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{width}"{d}/>')

    def text(self, x, y, s, size=15, color=INK, anchor="middle", mono=False):
        cls = ' class="m"' if mono else ""
        self.p.append(f'<text{cls} x="{x}" y="{y}" font-size="{size}" fill="{color}" '
                      f'text-anchor="{anchor}" style="fill:{color}" xml:space="preserve">{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, color=LINE, dash=False, width=1.5):
        d = ' stroke-dasharray="5 4"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{width}"{d}/>')

    def arrow(self, x1, y1, x2, y2):
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="1.8" '
                      'marker-end="url(#a)"/>')

    def save(self, name):
        self.p.append("</svg>")
        render_svg("".join(self.p), self.w, self.h, name)


# ---- 反例の読み取り（distinct_test.go の show() の形） ----

CELL = re.compile(r'nil|int64\((-?\d+)\)|"(?:[^"\\]|\\.)*"')


def parse_table(s):
    """'[{a:nil b:int64(8)} ...]' -> [(a, b), ...]。nil は None、整数は int、文字列は str。"""
    rows = []
    for a, b in re.findall(r'\{a:(.*?) b:(.*?)\}', s):
        rows.append((parse_cell(a), parse_cell(b)))
    return rows


def parse_cell(c):
    if c == "nil":
        return None
    m = re.fullmatch(r'int64\((-?\d+)\)', c)
    if m:
        return int(m.group(1))
    return ast.literal_eval(c)


def show_cell(v):
    if v is None:
        return "nil"
    if isinstance(v, int):
        return f"int64({v})"
    return '"' + v.replace("\x00", "\\x00") + '"'


def buggy_key(row):
    """修正前の makeRowKey: 値を %v で文字列にし、NUL でつなぐ。"""
    return "\x00".join("<nil>" if v is None else str(v) for v in row)


def colliding(rows, key=buggy_key):
    """鍵は同じなのに値が異なる行の番号。"""
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(key(r), []).append(i)
    bad = set()
    for idx in groups.values():
        if len({(type(rows[i][0]), rows[i][0], type(rows[i][1]), rows[i][1]) for i in idx}) > 1:
            bad.update(idx)
    return bad


def read_exp1(tool, gen="narrow", seed="1"):
    for r in csv.DictReader(open(OUT / "exp1_shrink.tsv"), delimiter="\t"):
        if (r["tool"], r["gen"], r["seed"]) == (tool, gen, seed):
            return r
    raise KeyError(tool)


def table_svg(s, x, y, rows, w, title, sub):
    s.text(x, y, title, 17, INK, "start")
    s.text(x, y + 22, sub, 13, SUB, "start")
    bad = colliding(rows)
    top = y + 38
    for i, (a, b) in enumerate(rows):
        ry = top + i * 26
        fill = RED_PALE if i in bad else (FILL if i % 2 == 0 else "#ffffff")
        stroke = RED if i in bad else "#dddddd"
        s.box(x, ry, w, 24, fill, stroke, rx=3, width=1.2)
        s.text(x + 10, ry + 17, f"{i + 1:>2}", 12, SUB, "start", mono=True)
        s.text(x + 42, ry + 17, f"a: {show_cell(a)}", 13, RED if i in bad else INK, "start", mono=True)
        s.text(x + w / 2 + 20, ry + 17, f"b: {show_cell(b)}", 13, RED if i in bad else INK, "start", mono=True)
    return top + len(rows) * 26


def cover_figure():
    q, r = read_exp1("quick"), read_exp1("rapid")
    qrows, rrows = parse_table(q["counterexample"]), parse_table(r["counterexample"])
    s = Svg(960, 400)
    s.text(30, 36, "修正前の Distinct に同じ性質を掛けて、報告された反例（種 1）", 20, INK, "start")
    end = table_svg(s, 30, 74, qrows, 400, f"testing/quick: {len(qrows)} 行",
                    f"{q['case']} 個目の入力で破れた表を、そのまま報告する")
    table_svg(s, 520, 74, rrows, 400, f"rapid: {len(rrows)} 行",
              f"{r['case']} 個目の入力で破れ、破れたまま縮めた表")
    s.arrow(450, 180, 505, 180)
    s.text(520, 210, "赤い行: 値が異なるのに 1 行にまとめられた 2 行", 13, RED, "start")
    s.text(520, 236, "他の行は、性質が破れたことに関係しない", 13, SUB, "start")
    s.h = max(end + 20, 300)
    s.p[0] = f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{s.h}" viewBox="0 0 960 {s.h}">'
    s.p[3] = f'<rect width="960" height="{s.h}" fill="#ffffff"/>'
    s.save("cover.webp")


def keys_figure():
    pairs = [
        ("整数と、それを書いた文字列", [(7,), ("7",)]),
        ("nil と、文字列の <nil>", [(None,), ("<nil>",)]),
        ("区切りの NUL を含む文字列", [("x\x00y", "z"), ("x", "y\x00z")]),
    ]
    s = Svg(960, 360)
    s.text(30, 36, "修正前の makeRowKey: 値を %v で文字列にし、NUL（\\x00）でつなぐ", 19, INK, "start")
    for i, (label, (r1, r2)) in enumerate(pairs):
        y = 66 + i * 86
        s.text(30, y + 18, label, 15, INK, "start")
        for j, r in enumerate((r1, r2)):
            cols = " ".join(f"{c}: {show_cell(v)}" for c, v in zip("ab", r))
            s.box(270, y + j * 34, 330, 28, FILL, rx=4)
            s.text(282, y + j * 34 + 19, cols, 14, INK, "start", mono=True)
            s.arrow(604, y + j * 34 + 14, 680, y + 31)
        key = buggy_key(r1 + ((None,) * 0)).replace("\x00", "\\x00")
        s.box(686, y + 14, 240, 34, RED_PALE, RED, rx=4)
        s.text(698, y + 37, f'鍵 "{key}"', 15, RED, "start", mono=True)
    s.text(30, 344, "どの組も 2 行の値は異なるが、鍵が同じなので Distinct は 2 行目を捨てる", 14, SUB, "start")
    s.save("keys.webp")


# ---- 動く図（Pillow） ----

JP_TTF = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO_TTF = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
S = 2


def font(size, mono=False):
    return ImageFont.truetype(MONO_TTF if mono else JP_TTF, size * S)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def shrink_animation(step_sec=0.5, hold=3.0):
    steps = []
    for line in (OUT / "exp1_shrink_steps_seed1.txt").read_text().splitlines():
        n, t = line.split("\t", 1)
        steps.append(parse_table(t))
    W, H = 900, 680
    frames, durations = [], []
    for k, rows in enumerate(steps):
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((24 * S, 18 * S), "rapid が反例を縮める様子（修正前の Distinct、種 1）", font=font(19), fill=rgb(INK))
        d.text((24 * S, 50 * S), f"性質が破れた表 {k + 1} 個目 / {len(steps)} 個（1 個目が見つけた反例）　　行の数 {len(rows)}",
               font=font(15), fill=rgb(SUB))
        # 何個目かが分かる帯
        bx, by, bw = 24, 80, 852
        d.rectangle([bx * S, by * S, (bx + bw) * S, (by + 8) * S], fill=rgb(FILL))
        d.rectangle([bx * S, by * S, int((bx + bw * (k + 1) / len(steps)) * S), (by + 8) * S], fill=rgb(ACCENT))
        bad = colliding(rows)
        top = 104
        for i, (a, b) in enumerate(rows):
            y = top + i * 26
            red = i in bad
            fill = RED_PALE if red else (FILL if i % 2 == 0 else "#ffffff")
            d.rectangle([24 * S, y * S, 876 * S, (y + 23) * S], fill=rgb(fill),
                        outline=rgb(RED if red else "#dddddd"), width=S)
            col = rgb(RED if red else INK)
            d.text((34 * S, (y + 3) * S), f"{i + 1:>2}", font=font(13, True), fill=rgb(SUB))
            d.text((74 * S, (y + 3) * S), f"a: {show_cell(a)}", font=font(13, True), fill=col)
            d.text((470 * S, (y + 3) * S), f"b: {show_cell(b)}", font=font(13, True), fill=col)
        d.text((24 * S, 646 * S), "赤い行: 値が異なるのに 1 行にまとめられた 2 行。1 個 0.5 秒で表示し、最後で 3 秒止める",
               font=font(13), fill=rgb(SUB))
        frames.append(im.resize((W * 3 // 2, H * 3 // 2), Image.LANCZOS))
        durations.append(int(step_sec * 1000))
    durations[-1] = int(hold * 1000)
    (HERE / "images").mkdir(exist_ok=True)
    frames[0].save(HERE / "images" / "shrink.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, lossless=True, method=6)  # 非可逆だと前のコマの行が薄く残る


def float_figure():
    base = 1 << 53
    ints = list(range(base - 1, base + 5))
    s = Svg(960, 300)
    s.text(30, 36, "修正後の鍵は整数を float64 にしてから文字列にする", 19, INK, "start")
    s.text(30, 62, "float64 が正確に表せる整数は 2^53 まで。超えると 2 つおきになり、間の整数は両隣のうち 4 の倍数の方へ丸まる", 14, SUB, "start")
    x0, dx, y_int, y_f = 90, 138, 130, 230
    s.text(30, y_int + 5, "int64", 14, INK, "start")
    s.text(30, y_f + 5, "float64", 14, INK, "start")
    for i, v in enumerate(ints):
        x = x0 + 40 + i * dx
        f = int(float(v))
        exact = f == v
        s.box(x - 52, y_int - 16, 104, 30, FILL if exact else RED_PALE, SUB if exact else RED, rx=4)
        s.text(x, y_int + 4, f"2^53{v - base:+d}" if v != base else "2^53", 14, INK if exact else RED, mono=True)
        fx = x0 + 40 + ints.index(f) * dx if f in ints else x
        s.arrow(x, y_int + 16, fx, y_f - 18)
    for i, v in enumerate(ints):
        if int(float(v)) == v:
            x = x0 + 40 + i * dx
            s.box(x - 52, y_f - 16, 104, 30, PALE, ACCENT, rx=4)
            s.text(x, y_f + 4, f"2^53{v - base:+d}" if v != base else "2^53", 14, INK, mono=True)
    s.text(30, 286, "2^53 = 9007199254740992。2^53+1 は 2^53 と同じ float64 になり、同じ鍵になる（赤）", 14, RED, "start")
    s.save("float.webp")


def decode(data):
    """distinct_test.go の decode と同じ読み替え。読んだバイトの区切りも返す。"""
    pos = 0
    spans = []

    def nxt(n, label):
        nonlocal pos
        b = data[pos:pos + n]
        if b:
            spans.append((pos, pos + len(b), label))
        pos += len(b)
        return b

    def cell(name):
        k = nxt(1, f"{name} の種類")
        if not k:
            return None
        if k[0] % 3 == 0:
            return None
        if k[0] % 3 == 1:
            b = nxt(8, f"{name} の整数").ljust(8, b"\x00")
            return int.from_bytes(b, "little", signed=True)
        n = nxt(1, f"{name} の長さ")
        if not n:
            return ""
        return nxt(n[0] % 16, f"{name} の文字列").decode("latin-1")

    h = nxt(1, "行の数")
    rows = []
    for i in range(h[0] % 21 if h else 0):
        rows.append((cell(f"{i + 1} 行目の a"), cell(f"{i + 1} 行目の b")))
    return rows, spans


def fuzz_figure():
    raw = (OUT / "exp3_crashers" / "fixed_run1.txt").read_text().splitlines()[1]
    data = ast.literal_eval(raw[len("[]byte("):-1]).encode("latin-1")
    rows, spans = decode(data)
    s = Svg(960, 420)
    s.text(30, 36, "go test -fuzz が縮めた入力（修正後の鍵、1 回目）を、表に読み替える", 19, INK, "start")
    s.text(30, 62, f"{len(data)} バイト。縮める時に各バイトを '0' などの印字できる文字に置き換えるので、ほぼ '0' になる", 14, SUB, "start")
    x, y, cw = 30, 86, 29
    for i, c in enumerate(data):
        first = i == 0
        s.box(x + i * cw, y, cw - 3, 30, PALE if first else FILL, ACCENT if first else SUB, rx=3, width=2 if first else 1)
        s.text(x + i * cw + (cw - 3) / 2, y + 21, chr(c), 15, INK, mono=True)
    # バイトの区切り: 行の数、1 行目の a（種類 + 整数 8 バイト）、1 行目の b（種類だけで nil）、2 行目の a
    groups = [(0, 1, "行の数"), (1, 10, "1 行目の a: 種類 '1' と整数"), (10, 11, "b: nil"), (11, 20, "2 行目の a: 種類 '1' と整数")]
    for a, b, label in groups:
        x1, x2 = x + a * cw + 2, x + b * cw - 5
        s.line(x1, y + 40, x2, y + 40, SUB, width=1.5)
        s.line(x1, y + 35, x1, y + 40, SUB, width=1.5)
        s.line(x2, y + 35, x2, y + 40, SUB, width=1.5)
        s.text((x1 + x2) / 2, y + 60, label, 12, SUB)
    s.text(x, y + 96, "1 バイト目の '0' は 48。48 % 21 = 6 なので、表は 6 行になる", 14, INK, "start")
    s.text(x, y + 120, "2 つの整数は 8 バイトのうち 1 バイト（'0' と '1'）だけが違う。2 行目の a でバイトが尽き、残りのセルは全て nil になる", 14, SUB, "start")
    bad = colliding(rows, key=lambda r: "|".join("z" if v is None else repr(float(v)) if isinstance(v, int) else "s" + v for v in r))
    top = y + 140
    for i, (a, b) in enumerate(rows):
        ry = top + i * 28
        red = i in bad
        s.box(x, ry, 900, 25, RED_PALE if red else (FILL if i % 2 == 0 else "#ffffff"), RED if red else "#dddddd", rx=3, width=1.2)
        s.text(x + 10, ry + 18, f"{i + 1}", 12, SUB, "start", mono=True)
        s.text(x + 40, ry + 18, f"a: {show_cell(a)}", 13, RED if red else INK, "start", mono=True)
        s.text(x + 470, ry + 18, f"b: {show_cell(b)}", 13, RED if red else INK, "start", mono=True)
    s.save("fuzz.webp")


if __name__ == "__main__":
    cover_figure()
    keys_figure()
    shrink_animation()
    float_figure()
    fuzz_figure()
