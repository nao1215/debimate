"""Generate the figures of the Differential Testing note.

Run: python3 figures.py  -> images/*.webp

The figures are built as SVG text here, rendered by headless Chrome at 2x and
saved as WebP (Pillow). Only the WebP files are kept in images/. The cover reads
lab/output/exp1_gnu_uutils.json, so rerun
`python3 lab/exp1_gnu_uutils.py lab/output/exp1_gnu_uutils.json` first when the
experiment changes.

- gnu_uutils_figure(): 32 cases given to GNU coreutils and uutils. The cover.
- concept_figure(): Metamorphic Testing (one implementation, two inputs) next to
  Differential Testing (two implementations, one input).
- sql_figure(): the same SQL given to SQLite and PostgreSQL (lab/output/exp3_group_by.txt).
- native_json_figure(): the values of one veth row, jz against `ip -j`, before
  and after the fix (lab/output/exp2_native_json.txt).
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


def describe(r):
    """One cell of the cover table: exit code and what was printed."""
    if r["exit"] < 0:
        return f"panic（シグナル {-r['exit']}）"
    out = r["stdout"].split("\n")[0]
    if out:
        return out.split(" 1 ")[0]
    if r["stderr"]:
        return f"{r['exit']}、エラーを表示"
    return f"{r['exit']}、何も表示しない"


def gnu_uutils_figure():
    results = json.loads((OUT / "exp1_gnu_uutils_0.8.0.json").read_text())
    n = len(results)
    same = sum(not r["raw_diff"] for r in results)
    noise = sum(r["raw_diff"] and not r["normalized_diff"] for r in results)
    diff = sum(r["normalized_diff"] for r in results)
    s = Svg(840, 356)
    s.text(20, 30, f"同じ {n} ケースを GNU coreutils 9.7 と uutils 0.8.0 に渡した結果", 16, INK, "start")
    # 1 ケース 1 マスの帯
    x = 20
    for r in sorted(results, key=lambda r: (r["normalized_diff"], r["raw_diff"])):
        if r["normalized_diff"]:
            fill, stroke = RED_PALE, RED
        elif r["raw_diff"]:
            fill, stroke = AMBER_PALE, AMBER
        else:
            fill, stroke = FILL, LINE
        s.box(x, 46, 20, 20, fill, stroke, rx=3, width=1.2)
        x += 24
    s.text(20, 88, f"一致 {same}", 13, SUB, "start")
    s.text(110, 88, f"エラーの文面だけ違う {noise}", 13, AMBER, "start")
    s.text(290, 88, f"出力か終了コードが違う {diff}", 13, RED, "start")
    # 違いの表
    cols = [20, 270, 560]
    y = 124
    s.text(cols[0], y, "ケース", 13, SUB, "start")
    s.text(cols[1], y, "GNU 9.7（出力、または終了コード）", 13, SUB, "start")
    s.text(cols[2], y, "uutils 0.8.0（同）", 13, SUB, "start")
    s.line(20, y + 10, 820, y + 10, LINE)
    rows = [r for r in results if r["raw_diff"]]
    rows.sort(key=lambda r: not r["normalized_diff"])
    for i, r in enumerate(rows):
        yy = y + 36 + i * 32
        if not r["normalized_diff"]:
            yy += 12
            s.line(20, yy - 24, 820, yy - 24, LINE, dash=True)
        color = RED if r["normalized_diff"] else AMBER
        s.text(cols[0], yy, r["case"], 13, INK, "start")
        g, u = r["gnu"], r["uutils"]
        if r["normalized_diff"]:
            gl, ul = describe(g), describe(u)
        else:
            gl, ul = "2、ls: unrecognized option", "2、error: unexpected argument"
        s.text(cols[1], yy, gl, 13, INK, "start")
        s.text(cols[2], yy, ul, 13, color, "start")
    s.save("gnu_uutils.webp")


def versions_figure():
    old = json.loads((OUT / "exp1_gnu_uutils_0.8.0.json").read_text())
    new = {r["case"]: r for r in json.loads((OUT / "exp1_gnu_uutils_0.10.0.json").read_text())}
    rows = [r for r in old if r["normalized_diff"]]
    s = Svg(840, 70 + 32 * len(rows) + 16)
    cols = [20, 250, 450, 650]
    y = 30
    for c, label in zip(cols, ["ケース", "GNU 9.7", "uutils 0.8.0", "uutils 0.10.0"]):
        s.text(c, y, label, 13, SUB, "start")
    s.line(20, y + 10, 820, y + 10, LINE)
    for i, r in enumerate(rows):
        yy = y + 40 + i * 32
        n = new[r["case"]]
        s.text(cols[0], yy, r["case"], 13, INK, "start")
        s.text(cols[1], yy, describe(r["gnu"]), 13, INK, "start")
        for c, rr in ((cols[2], r), (cols[3], n)):
            if rr["normalized_diff"]:
                color = RED
            elif rr["raw_diff"]:
                color = AMBER
            else:
                color = INK
            s.text(c, yy, describe(rr["uutils"]), 13, color, "start")
    s.text(820, y + 40 + 32 * len(rows) + 2, "赤: GNU と出力か終了コードが違う　黄: エラーの文面だけ違う", 12, SUB, "end")
    s.save("versions.webp")


def sql_figure():
    s = Svg(860, 300)

    def node(x, y, label, w, fill=FILL, stroke=SUB, color=INK, size=14, mono=False):
        s.box(x, y, w, 44, fill, stroke)
        s.text(x + w / 2, y + 28, label, size, color, mono=mono)

    s.text(20, 30, "同じ SQL を 2 つの相手に渡す", 15, INK, "start")
    node(20, 112, "SELECT a, b FROM g GROUP BY b", 270, size=12, mono=True)
    # 上: filesql が内部で使う SQLite
    node(340, 60, "SQLite（filesql が内部で使う）", 230, PALE, ACCENT, size=13)
    node(610, 60, "(1, 10) と (3, 20) を返す", 230, size=13)
    s.text(725, 124, "a はグループのどれか 1 行の値", 12, SUB)
    # 下: filesql が書き方を約束した PostgreSQL
    node(340, 170, "PostgreSQL（filesql が約束した相手）", 230, PALE, ACCENT, size=12)
    node(610, 170, "拒否する", 230, RED_PALE, RED, RED, size=13)
    s.text(725, 234, "a は GROUP BY に無く、集約もしていない", 12, SUB)
    s.arrow(290, 126, 338, 84)
    s.arrow(290, 142, 338, 190)
    s.arrow(570, 82, 608, 82)
    s.arrow(570, 192, 608, 192)
    s.text(20, 280, "修正前の filesql は SQLite の答えを返していた。約束した PostgreSQL に合わせて、拒否するように直した", 13, RED, "start")
    s.save("sql.webp")


def concept_figure():
    s = Svg(900, 245)

    def node(x, y, label, w=130, fill=FILL, stroke=SUB, mono=False):
        s.box(x, y, w, 40, fill, stroke)
        s.text(x + w / 2, y + 26, label, 14, INK, mono=mono)

    # 左: Metamorphic
    s.text(20, 30, "Metamorphic Testing（前のノート）", 15, INK, "start")
    s.text(20, 52, "1 つの実装に、変えた 2 つの入力", 12, SUB, "start")
    node(20, 80, "入力 x", 110)
    node(20, 170, "変えた入力 x′", 110)
    node(170, 125, "実装 P", 100, PALE, ACCENT)
    s.arrow(130, 100, 168, 138)
    s.arrow(130, 190, 168, 152)
    node(310, 80, "P(x)", 90, mono=True)
    node(310, 170, "P(x′)", 90, mono=True)
    s.arrow(270, 138, 308, 102)
    s.arrow(270, 152, 308, 188)
    s.text(355, 150, "関係を満たすか", 13, RED)
    # 区切り
    s.line(450, 20, 450, 260, LINE, dash=True)
    # 右: Differential
    s.text(480, 30, "Differential Testing（本記事）", 15, INK, "start")
    s.text(480, 52, "2 つの実装に、同じ入力", 12, SUB, "start")
    node(480, 125, "入力 x", 100)
    node(620, 80, "実装 A", 100, PALE, ACCENT)
    node(620, 170, "実装 B", 100, PALE, ACCENT)
    s.arrow(580, 138, 618, 102)
    s.arrow(580, 152, 618, 188)
    node(760, 80, "A(x)", 90, mono=True)
    node(760, 170, "B(x)", 90, mono=True)
    s.arrow(720, 100, 758, 100)
    s.arrow(720, 190, 758, 190)
    s.text(805, 150, "一致するか", 13, RED)
    s.save("concept.webp")


def native_json_figure():
    s = Svg(900, 392)

    def chip(x, y, key, value, w, fill=FILL, stroke=LINE, color=INK, below=False):
        s.text(x + 4, y + 46 if below else y - 6, key, 11, SUB, "start", mono=True)
        s.box(x, y, w, 30, fill, stroke, rx=5, width=1.3)
        s.text(x + w / 2, y + 20, value, 13, color, mono=True)

    def row(y0, title, ours, native, links):
        """ours/native: [(key, value, width, kind)]; links: [(i, j, kind)]"""
        s.text(20, y0, title, 15, INK, "start")
        s.text(20, y0 + 54, "jz", 12, SUB, "start")
        s.text(20, y0 + 124, "ip -j", 12, SUB, "start")
        xs, xn = [], []
        x = 80
        for key, value, w, kind in ours:
            fill, stroke, color = {"bad": (RED_PALE, RED, RED), "rep": (AMBER_PALE, AMBER, AMBER)}.get(
                kind, (FILL, LINE, INK))
            chip(x, y0 + 34, key, value, w, fill, stroke, color)
            xs.append(x + w / 2)
            x += w + 14
        x = 80
        for key, value, w, kind in native:
            if kind == "left":
                chip(x, y0 + 104, key, value, w, FILL, RED, INK, below=True)
            else:
                chip(x, y0 + 104, key, value, w, below=True)
            xn.append(x + w / 2)
            x += w + 14
        for i, j, kind in links:
            color = AMBER if kind == "rep" else LINE
            s.line(xs[i], y0 + 64, xn[j], y0 + 104, color, dash=kind == "rep")

    native = [("ifname", "veth3a8eedd", 130, ""), ("link_index", "2", 90, ""),
              ("operstate", "UP", 90, ""), ("address", "MAC", 90, ""), ("flags", "4 個", 110, "")]
    left = [("ifname", "veth3a8eedd", 130, "left"), ("link_index", "2", 90, "left")] + native[2:]
    row(28, "修正前の jz",
        [("interface", "veth3a8eedd@if2", 170, "bad"), ("state", "UP", 90, ""),
         ("lladdr", "MAC", 90, ""), ("flags", "4 個", 110, "")],
        left, [(1, 2, ""), (2, 3, ""), (3, 4, "")])
    s.text(670, 86, "jz にだけある値", 13, RED, "start")
    s.text(670, 156, "ip -j にだけある値", 13, RED, "start")
    row(216, "修正後の jz（v0.9.1）",
        [("interface", "veth3a8eedd", 130, ""), ("peer", "if2", 90, "rep"), ("state", "UP", 90, ""),
         ("lladdr", "MAC", 90, ""), ("flags", "4 個", 110, "")],
        native, [(0, 0, ""), (1, 1, "rep"), (2, 2, ""), (3, 3, ""), (4, 4, "")])
    s.text(670, 296, "peer の if2 と link_index の 2", 13, AMBER, "start")
    s.text(670, 316, "は表現の違い", 13, AMBER, "start")
    s.save("native_json.webp")


if __name__ == "__main__":
    gnu_uutils_figure()
    versions_figure()
    concept_figure()
    native_json_figure()
    sql_figure()
