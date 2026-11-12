"""Generate the figures of the Fuzzing note.

Run: python3 figures.py  -> images/*.webp

The figures are built as SVG text here, rendered by headless Chrome at 2x and
saved as WebP (Pillow). Only the WebP files are kept in images/. The numbers come
from lab/output/, so rerun the experiment scripts first when they change.

- retain_figure(): the cover. What jsonize's table reading held before the fix,
  drawn as two squares whose areas are the input and the heap
  (lab/output/exp0_jsonize_retain.txt).
- loop_figure(): the loop of a coverage-guided fuzzer.
- steps_figure(): experiment 1. Byte-by-byte comparisons give the fuzzer a step
  for each byte; one 4-byte comparison gives it none (lab/output/exp1_magic.txt).
- row_figure(): why one 2-byte line of input becomes 256 values in jsonize.
- parquet_figure(): experiment 2. The 473-byte Parquet whose column chunk claims
  3113 bytes, before and after the fix (lab/output/exp2_parquet.txt).
- matrix_figure(): filesql's nightly fuzz matrix against the fuzz targets in the
  repository at v0.56.0 (Issue #1051).
"""

import re
from html import escape
from pathlib import Path

import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#7aa6c2", "#d64545", "#fbe3e3"
AMBER, AMBER_PALE, LINE = "#b7791f", "#fdf1dc", "#9a9a9a"
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


def poly(s, pts, fill, stroke=SUB, width=1.5):
    d = " ".join(f"{x},{y}" for x, y in pts)
    s.p.append(f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


def path_arrow(s, d, color=SUB, dash=False):
    da = ' stroke-dasharray="6 4"' if dash else ""
    s.p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8"{da} marker-end="url(#a)"/>')


def retain_figure():
    """The cover: input and retained heap of jsonize's aligned table reading, as areas."""
    text = (OUT / "exp0_jsonize_retain.txt").read_text()
    before = text.split("== jsonize")[1]
    m = re.findall(r"rows=(\d+) input=([\d.]+) KB heap=([\d.]+) GB ratio=(\d+)", before)[-1]
    rows, kb, gb, ratio = int(m[0]), float(m[1]), float(m[2]), int(m[3])
    s = Svg(760, 400)
    s.text(24, 34, "jsonize の表の読み取り（修正前）が保持したメモリ", 17, INK, "start")
    s.text(24, 58, f"256 列の見出しの下に x だけの行を {rows:,} 行。面積が大きさに比例", 13, SUB, "start")
    big = 300
    small = big / ratio ** 0.5
    bx, by = 400, 80
    s.box(bx, by, big, big, RED_PALE, RED, rx=2)
    s.text(bx + big / 2, by + big / 2 - 6, f"保持したメモリ {gb:.2f} GB", 17, INK)
    s.text(bx + big / 2, by + big / 2 + 20, f"入力の約 {ratio:,} 倍", 15, RED)
    sx, sy = 330, by + big - small
    s.box(sx, sy, max(small, 2), max(small, 2), INK, INK, rx=0, width=0.5)
    s.line(sx - 4, sy - 2, 250, sy - 50, SUB)
    s.text(246, sy - 78, f"入力 {kb:.1f} KB", 17, INK, "end")
    s.text(246, sy - 56, "（この点）", 13, SUB, "end")
    s.save("retain.webp")


def loop_figure():
    """A coverage-guided fuzzer: keep the inputs that reach new branches, mutate them."""
    s = Svg(900, 330)
    y, h = 120, 74
    boxes = [(20, 190, "corpus", "seed と、新しい分岐に", "届いた入力"),
             (250, 170, "変異", "1 つ選び、バイトを", "足す・消す・変える"),
             (460, 170, "実行", "対象の関数に", "入力を渡す"),
             (670, 210, "カバレッジ", "前に通っていない", "分岐を通ったか")]
    for x, w, head, l1, l2 in boxes:
        s.box(x, y, w, h, PALE if head != "カバレッジ" else FILL)
        s.text(x + w / 2, y + 24, head, 15)
        s.text(x + w / 2, y + 46, l1, 12.5, SUB)
        s.text(x + w / 2, y + 63, l2, 12.5, SUB)
    for (x1, w1, *_), (x2, *_) in zip(boxes, boxes[1:]):
        s.arrow(x1 + w1 + 2, y + h / 2, x2 - 4, y + h / 2)
    path_arrow(s, f"M775,{y} L775,60 L115,60 L115,{y - 4}")
    s.text(445, 50, "通った: corpus に足す", 13.5, INK)
    s.arrow(830, y + h + 2, 830, y + h + 46)
    s.text(830, y + h + 70, "通らない: 捨てる", 13.5, SUB)
    s.arrow(545, y + h + 2, 545, y + h + 46)
    s.box(330, y + h + 50, 430, 66, RED_PALE, RED)
    s.text(545, y + h + 76, "検査に失敗（panic・t.Fatal・10 秒を超える）", 14, INK)
    s.text(545, y + h + 98, "入力を testdata/fuzz/ に保存して止まる", 13, RED, mono=False)
    s.save("loop.webp")


def steps_figure():
    """Experiment 1: four gates of one byte each, against one gate of four bytes."""
    text = (OUT / "exp1_magic.txt").read_text()
    calls = [int(c) for c in re.findall(r"FuzzByteByByte run\d+: found at call (\d+)", text)]
    execs = [int(e) for e in re.findall(r"FuzzAtOnce run\d+: fuzz: elapsed: [^,]+, execs: (\d+)", text)]
    s = Svg(900, 380)
    s.text(225, 30, "ByteByByte: 1 バイトずつ比べる", 15)
    s.text(675, 30, "AtOnce: 4 バイトをまとめて比べる", 15)
    s.line(450, 20, 450, 360, "#dddddd")
    base, step, w0 = 300, 52, 70
    labels = ["seed", "F...", "FU..", "FUZ.", "FUZZ"]
    for i, lab in enumerate(labels):
        x = 30 + i * w0
        top = base - i * step
        fill = RED_PALE if i == 4 else PALE
        s.box(x, top, w0, base - top + 20 if i else 20, fill, RED if i == 4 else SUB, rx=2)
        s.text(x + w0 / 2, top - 8, lab, 13.5, RED if i == 4 else INK, mono=True)
    s.text(30, 346, "1 段上がるたびに新しい分岐を通るので、その入力が corpus に残る", 12.5, SUB, "start")
    s.text(30, 366, f"見つかるまで {min(calls):,}〜{max(calls):,} 回（5 回の実行）", 13.5, INK, "start")
    x = 480
    s.box(x, base, w0, 20, PALE, rx=2)
    s.text(x + w0 / 2, base - 8, "seed", 13.5, INK, mono=True)
    s.box(x + w0 + 140, base - 4 * step, w0, 4 * step + 20, RED_PALE, RED, rx=2)
    s.text(x + w0 + 140 + w0 / 2, base - 4 * step - 8, "FUZZ", 13.5, RED, mono=True)
    s.line(x + w0, base + 10, x + w0 + 140, base + 10, LINE, dash=True)
    s.text(x + w0 + 70, base - 110, "途中の段が無い。", 13, SUB)
    s.text(x + w0 + 70, base - 88, "4 バイト全てを", 13, SUB)
    s.text(x + w0 + 70, base - 66, "一度に当てる", 13, SUB)
    s.text(480, 346, "当たる確率は 1/4,294,967,296。途中で残る入力が無い", 12.5, SUB, "start")
    assert all(0.9e8 < e < 1.1e8 for e in execs), execs
    s.text(480, 366, f"2 分で約 1 億回実行しても見つからない（{len(execs)} 回）", 13.5, INK, "start")
    s.save("steps.webp")


def row_figure():
    """jsonize before the fix: a 2-byte line becomes one object of 256 values."""
    s = Svg(900, 250)
    s.text(24, 32, "入力", 15, INK, "start")
    s.box(24, 48, 210, 150, FILL)
    for i, line in enumerate(["c0 c1 c2 … c255", "x", "x", "x", "…"]):
        s.text(38, 76 + i * 26, line, 14, INK if i else SUB, "start", mono=True)
    s.box(30, 82, 198, 22, "none", RED, rx=3)
    s.text(129, 222, "1 行は x と改行の 2 バイト", 13, RED)
    s.arrow(246, 93, 300, 93)
    s.text(316, 32, "読み取りが保持する 1 行分（256 個の値）", 15, INK, "start")
    x0, cw = 316, 2.1
    for i in range(256):
        s.box(x0 + i * cw, 80, cw, 26, RED_PALE if i == 0 else PALE, "#b9c9d3", rx=0, width=0.3)
    s.text(x0, 128, 'c0: "x"', 13, RED, "start", mono=True)
    s.text(x0 + 255 * cw + cw, 128, "c1 〜 c255: null", 13, SUB, "end", mono=True)
    s.text(316, 168, "1 行 2 バイトの入力が、1 行約 29 KB のメモリになる", 13.5, INK, "start")
    s.save("row.webp")


def parquet_figure():
    """Experiment 2: the 473-byte file whose first column chunk claims 3113 bytes."""
    text = (OUT / "exp2_parquet.txt").read_text()
    kib = [float(v) for v in re.findall(r"allocated ([\d.]+) KiB", text)]
    s = Svg(900, 330)
    k = 0.24
    x0, y0 = 40, 70
    size, off, claim = 473, 42, 3113
    s.text(x0, 36, "fuzz が見つけた 473 バイトの Parquet", 15, INK, "start")
    s.box(x0, y0, size * k, 34, PALE, rx=2)
    s.text(x0 + size * k / 2, y0 + 22, "ファイル", 13)
    s.text(x0 + size * k + 10, y0 + 22, "← ファイルはここ（473 バイト）で終わる", 12.5, SUB, "start")
    s.box(x0 + off * k, y0 + 70, claim * k, 30, RED_PALE, RED, dash=True, rx=2)
    s.text(x0 + size * k + 10, y0 + 90, "列のチャンク 0 が「42 バイト目から 3113 バイト」と宣言", 13, INK, "start")
    s.line(x0 + size * k, y0 - 8, x0 + size * k, y0 + 110, RED, dash=True)
    yb = 220
    s.box(x0, yb, 400, 86, FILL)
    s.text(x0 + 16, yb + 26, "修正前", 14, INK, "start")
    s.text(x0 + 16, yb + 50, "中のページの見出しが宣言する大きさを", 12.5, SUB, "start")
    s.text(x0 + 16, yb + 70, f"先に確保してから読み、ファイルの終わりで失敗。{kib[0] / 1024:.1f} MiB", 12.5, RED, "start")
    s.box(x0 + 430, yb, 400, 86, FILL)
    s.text(x0 + 446, yb + 26, "修正後", 14, INK, "start")
    s.text(x0 + 446, yb + 50, "読む前に、チャンクとページの宣言が収まるかを見て", 12.5, SUB, "start")
    s.text(x0 + 446, yb + 70, f"拒否する。{kib[1]:.1f} KiB", 12.5, INK, "start")
    s.save("parquet.webp")


def matrix_figure():
    """filesql v0.56.0: the nightly matrix names ./parser, the targets live in ./internal/parser."""
    matrix = [("./internal/reader", "FuzzCSVReader", 0), ("./parser", "FuzzParseFormats", None),
              ("./parser", "FuzzParseBinary", None), ("./dialect", "FuzzTranslate", 3),
              ("./dialect/internal/parser", "FuzzParse", 4), ("./dialect/internal/parser", "FuzzLex", 5),
              ("./internal/codec", "FuzzCodecReader", 6)]
    tree = [("internal/reader", "FuzzCSVReader"), ("internal/parser", "FuzzParseFormats"),
            ("internal/parser", "FuzzParseBinary"), ("dialect", "FuzzTranslate"),
            ("dialect/internal/parser", "FuzzParse"), ("dialect/internal/parser", "FuzzLex"),
            ("internal/codec", "FuzzCodecReader")]
    s = Svg(900, 424)
    s.text(30, 32, "夜間の fuzz の matrix（fuzz.yml）", 15, INK, "start")
    s.text(560, 32, "リポジトリにある Fuzz 関数", 15, INK, "start")
    y0, dy = 56, 44
    for i, (pkg, name, j) in enumerate(matrix):
        bad = j is None
        y = y0 + i * dy
        s.box(30, y, 320, 34, RED_PALE if bad else PALE, RED if bad else SUB, rx=4)
        s.text(42, y + 22, f"{pkg}  {name}", 12.5, INK, "start", mono=True)
        if bad:
            s.text(362, y + 22, "ディレクトリが無い", 12.5, RED, "start")
        else:
            s.line(350, y + 17, 560, y0 + j * dy + 17, LINE)
    for i, (pkg, name) in enumerate(tree):
        y = y0 + i * dy
        lost = i in (1, 2)
        s.box(560, y, 320, 34, AMBER_PALE if lost else PALE, AMBER if lost else SUB, rx=4)
        s.text(572, y + 22, f"{pkg}  {name}", 12.5, INK, "start", mono=True)
    s.text(30, y0 + 7 * dy + 18, "赤: 存在しないパスを指し、毎晩失敗したジョブ", 13, RED, "start")
    s.text(30, y0 + 7 * dy + 42, "黄: どのジョブも回していなかった fuzz の関数", 13, AMBER, "start")
    s.save("matrix.webp")


if __name__ == "__main__":
    retain_figure()
    loop_figure()
    row_figure()
    parquet_figure()
    matrix_figure()
    steps_figure()
