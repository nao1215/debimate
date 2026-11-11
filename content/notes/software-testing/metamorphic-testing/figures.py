"""Generate the figures of the Metamorphic Testing note.

Run: python3 figures.py  -> images/*.webp

The figures are built as SVG text here, rendered by headless Chrome at 2x and
saved as WebP (Pillow). Only the WebP files are kept in images/. The token
figure reads lab/output/exp2_token_sweep.json, so rerun
`python3 lab/exp2_token_sweep.py lab/output/exp2_token_sweep.json` first when
the experiment changes.

- wc_relation_figure(): reading `wc a.txt b.txt` at once versus one file at a
  time and joining the results (lab/output/exp1_wc_concat.txt). The cover.
- concept_figure(): the source input, the follow-up input and the relation.
- token_figure(): which tokens reach the output, before and after the fix.
- shrink_figure(): the counterexample testing/quick found and the one shrunk by hand.
"""

from html import escape
from pathlib import Path
import json
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#7aa6c2", "#d64545", "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"


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


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                  f'<style>text{{font-family:{FONT};fill:{INK}}} .m{{font-family:{MONO}}}</style>',
                  '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
                  f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
                  f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def box(self, x, y, bw, bh, fill, stroke=SUB, dash=False, rx=8):
        d = ' stroke-dasharray="6 4"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="1.5"{d}/>')

    def text(self, x, y, s, size=15, color=INK, anchor="middle", mono=False):
        cls = ' class="m"' if mono else ""
        self.p.append(f'<text{cls} x="{x}" y="{y}" font-size="{size}" fill="{color}" '
                      f'text-anchor="{anchor}" style="fill:{color}" xml:space="preserve">{escape(s)}</text>')

    def arrow(self, x1, y1, x2, y2):
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="1.8" '
                      'marker-end="url(#a)"/>')

    def save(self, name):
        self.p.append("</svg>")
        render_svg("".join(self.p), self.w, self.h, name)


def read_exp1():
    """together/separate rows of `jz run wc a.txt b.txt` from the lab output."""
    lines = (OUT / "exp1_wc_concat.txt").read_text().splitlines()
    i = lines.index("$ jz run wc a.txt b.txt")
    together = json.loads(lines[i + 1].split(": ", 1)[1])
    separate = json.loads(lines[i + 2].split(": ", 1)[1])
    return together, separate


def row_text(r):
    return f'lines:{r["lines"]} words:{r["words"]} bytes:{r["bytes"]:<2} filename:{r["filename"]}'


def wc_relation_figure():
    together, separate = read_exp1()
    s = Svg(820, 330)
    mono = 13

    def row(r):
        return f'{r["lines"]} {r["words"]} {r["bytes"]:>2} {r["filename"]}'

    def wc_box(x, y, lines, red_last=False):
        s.box(x, y, 150, 24 * len(lines) + 14, "#ffffff")
        for i, ln in enumerate(lines):
            red = red_last and i == len(lines) - 1
            s.text(x + 12, y + 25 + i * 24, ln, mono, RED if red else INK, "start", mono=True)

    def json_box(x, y, rows, extra_last=False):
        s.box(x, y, 290, 24 * len(rows) + 14, FILL)
        for i, r in enumerate(rows):
            red = extra_last and i == len(rows) - 1
            if red:
                s.box(x + 6, y + 8 + i * 24, 278, 23, RED_PALE, RED, rx=4)
            s.text(x + 14, y + 25 + i * 24, f'{{"filename":"{r["filename"]}", "lines":{r["lines"]}, …}}',
                   mono, RED if red else INK, "start", mono=True)

    # 上段: 1 回で読む
    s.text(20, 28, "1 回で読む", 15, INK, "start")
    s.text(112, 28, "jz run wc a.txt b.txt", mono, SUB, "start", mono=True)
    s.text(20, 56, "wc の出力", 12, SUB, "start")
    wc_box(20, 64, [row(r) for r in together], red_last=True)
    s.text(178, 137, "← 合計行", 12, RED, "start")
    s.arrow(248, 101, 318, 101)
    s.text(283, 92, "jz", 12, SUB, mono=True)
    s.text(326, 56, "JSON の要素", 12, SUB, "start")
    json_box(326, 64, together, extra_last=True)
    s.text(632, 96, "3 要素", 16, RED, "start")
    s.text(632, 118, "合計行も 1 件のファイル", 12, RED, "start")
    # 下段: 1 ファイルずつ
    y0 = 190
    s.text(20, y0, "1 ファイルずつ読んでつなぐ", 15, INK, "start")
    s.text(220, y0, "jz run wc a.txt  と  jz run wc b.txt", mono, SUB, "start", mono=True)
    wc_box(20, y0 + 14, [row(separate[0])])
    wc_box(20, y0 + 62, [row(separate[1])])
    s.arrow(248, y0 + 55, 318, y0 + 55)
    s.text(283, y0 + 46, "jz", 12, SUB, mono=True)
    json_box(326, y0 + 24, separate)
    s.text(632, y0 + 60, "2 要素", 16, INK, "start")
    s.text(410, 318, "2 つの結果が一致しない（関係を満たさない）", 14, RED)
    s.save("wc_relation.webp")


def concept_figure():
    s = Svg(940, 330)

    def node(x, y, label, sub, fill=FILL, w=170):
        s.box(x, y, w, 64, fill)
        s.text(x + w / 2, y + 28, label, 18)
        s.text(x + w / 2, y + 52, sub, 14, SUB, mono=sub.isascii())

    # 上段: 元の入力
    s.text(20, 30, "元の入力", 16, SUB, "start")
    node(20, 44, "x", "a.txt b.txt")
    s.arrow(192, 76, 300, 76)
    s.text(246, 66, "f", 15, INK)
    s.text(246, 98, "jz run wc", 14, SUB, mono=True)
    node(302, 44, "f(x)", "3 要素の配列")
    # 下段: 変換後の入力
    s.arrow(105, 110, 105, 196)
    s.text(115, 150, "変換 T", 17, INK, "start")
    s.text(115, 174, "1 つずつに分ける", 14, SUB, "start")
    s.text(20, 222, "変換後の入力", 16, SUB, "start")
    node(20, 236, "T(x)", "a.txt / b.txt")
    s.arrow(192, 268, 300, 268)
    s.text(246, 258, "f", 15, INK)
    s.text(246, 292, "2 回実行", 14, SUB)
    node(302, 236, "f(T(x))", "2 つの結果をつなぐ")
    # 関係
    s.box(600, 112, 320, 104, PALE, ACCENT)
    s.text(760, 142, "関係 R（metamorphic relation）", 17)
    s.text(760, 172, "f(x) ＝ f(T(x)) のはず", 18)
    s.text(760, 200, "どちらの値が正しいかは問わない", 14, SUB)
    s.p.append(f'<path d="M474,76 C540,76 560,140 598,150" fill="none" stroke="{SUB}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    s.p.append(f'<path d="M474,268 C540,268 560,196 598,184" fill="none" stroke="{SUB}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    s.save("mt_concept.webp")


def token_figure():
    data = json.loads((OUT / "exp2_token_sweep.json").read_text())
    fixture = data["fixture"]
    size, cw, lh = 16, 9.63, 32   # DejaVu Sans Mono: 0.602em per character
    lines = fixture.splitlines()
    starts = [0]
    for ln in lines[:-1]:
        starts.append(starts[-1] + len(ln) + 1)
    pw = int(max(len(ln) for ln in lines) * cw) + 40
    s = Svg(pw * 2 + 60, 290)
    panels = [(20, "直す前（BUGGY）", data["buggy"]), (pw + 40, "直した後（FIXED）", data["fixed"])]
    for x0, title, result in panels:
        lost = sum(not r["reflected"] for r in result)
        s.text(x0, 30, f"{title}：出力に反映されないトークン {lost} 個", 18, RED if lost else INK, "start")
        s.box(x0, 46, pw, len(lines) * lh + 24, "#ffffff")
        for r in result:
            li = max(i for i, st in enumerate(starts) if st <= r["start"])
            col = r["start"] - starts[li]
            bx = x0 + 20 + col * cw - 1
            by = 46 + 12 + li * lh + 2
            fill, stroke = (FILL, "#c8c8c8") if r["reflected"] else (RED_PALE, RED)
            s.box(bx, by, len(r["token"]) * cw + 2, lh - 6, fill, stroke, rx=3)
        for i, ln in enumerate(lines):
            s.text(x0 + 20, 46 + 12 + i * lh + 19, ln, size, INK, "start", mono=True)
    yl = 46 + len(lines) * lh + 24 + 34
    s.box(20, yl - 14, 18, 18, FILL, "#c8c8c8", rx=3)
    s.text(46, yl, "1 文字変えると出力が変わるか、エラーになる（出力に反映されている）", 15, SUB, "start")
    s.box(20, yl + 14, 18, 18, RED_PALE, RED, rx=3)
    s.text(46, yl + 28, "1 文字変えても出力が同じ（出力に反映されていない）", 15, RED, "start")
    s.save("token_sweep.webp")


def shrink_figure():
    lines = (OUT / "exp3_quick.txt").read_text().splitlines()
    def ascii_only(v):
        # 環境のフォントに字形が無い文字を豆腐にしないよう、ASCII の外は \U で書く
        return "".join(c if ord(c) < 0x80 else f"\\U{ord(c):08x}" for c in v)
    a = ascii_only(lines[1].split(" = ", 1)[1])
    b = ascii_only(lines[2].split(" = ", 1)[1])
    s = Svg(940, 300)
    s.text(20, 32, "testing/quick が見つけた反例（最小化なし。ASCII 以外の文字は \\U で表示）", 18, INK, "start")
    s.box(20, 46, 900, 92, FILL)
    s.text(36, 78, "a = " + a.split(" (")[0][:78] + "…", 13, INK, "start", mono=True)
    s.text(36, 104, "b = " + b.split(" (")[0][:78] + "…", 13, INK, "start", mono=True)
    s.text(904, 128, f'a は {a.split(" (")[1].split()[0]} 文字、b は {b.split(" (")[1].split()[0]} 文字', 14, SUB, "end")
    s.text(20, 182, "手で最小化した反例", 18, INK, "start")
    s.box(20, 196, 900, 84, PALE, ACCENT)
    s.text(40, 232, 'a = "x"   b = "y"', 17, INK, "start", mono=True)
    s.text(40, 262, 'Words("xy") = 1   Words("x") + Words("y") = 2', 17, INK, "start", mono=True)
    s.text(900, 248, "つなぐと 2 語が 1 語になる", 16, RED, "end")
    s.save("quick_shrink.webp")


if __name__ == "__main__":
    wc_relation_figure()
    concept_figure()
    token_figure()
    shrink_figure()
