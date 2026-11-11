"""Generate the figures of the Differential Testing note.

Run: python3 figures.py  -> images/*.webp

The figures are built as SVG text here, rendered by headless Chrome at 2x and
saved as WebP (Pillow). Only the WebP files are kept in images/. The cover reads
lab/output/exp1_gnu_uutils.json, so rerun
`python3 lab/exp1_gnu_uutils.py lab/output/exp1_gnu_uutils.json` first when the
experiment changes.

- full_disk_figure(): `ls > list.txt` on a full disk, GNU against uutils. The cover.
- compare_scope_figure(): what experiment 1 compares (stdout, exit code, stderr).
- acl_figure(): why uutils 0.8.0 prints + for a user xattr.
- blind_spot_figure(): two implementations with the same mistake.
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


def full_disk_figure():
    """The cover: `ls > list.txt` on a full disk, GNU against uutils 0.8.0."""
    results = {r["case"]: r for r in json.loads((OUT / "exp1_gnu_uutils_0.8.0.json").read_text())}
    r = results["ls（/dev/full へ）"]
    g, u = r["gnu"], r["uutils"]
    s = Svg(880, 240)
    s.text(20, 32, "ディスクが一杯の時の  ls > list.txt", 17, INK, "start")
    s.text(20, 56, "/dev/full は、書き込むと必ず「空き容量が無い」エラーを返す", 12, SUB, "start")

    def lane(y, name, stderr, exit_code, result, bad):
        stroke, fill, color = (RED, RED_PALE, RED) if bad else (ACCENT, PALE, INK)
        s.text(20, y + 30, name, 14, INK, "start")
        s.box(150, y + 6, 150, 40, FILL, LINE)
        s.text(225, y + 31, "書き込みが失敗", 13)
        s.arrow(300, y + 26, 330, y + 26)
        s.box(332, y + 6, 250, 40, "#ffffff", LINE)
        s.text(342, y + 25, "stderr", 10, SUB, "start", mono=True)
        s.text(342, y + 40, stderr, 12, color, "start", mono=bool(stderr.strip("（）")) and not bad)
        s.box(592, y + 6, 70, 40, "#ffffff", LINE)
        s.text(602, y + 25, "終了コード", 10, SUB, "start")
        s.text(627, y + 41, str(exit_code), 15, color)
        s.arrow(662, y + 26, 690, y + 26)
        s.box(692, y + 2, 170, 48, fill, stroke)
        s.text(777, y + 22, result[0], 12, color)
        s.text(777, y + 40, result[1], 12, color)

    lane(80, "GNU 9.7", g["stderr"].strip()[:30], g["exit"], ("スクリプトは", "失敗に気付いて止まる"), False)
    lane(160, "uutils 0.8.0", "（何も出さない）", u["exit"], ("成功とみなして", "欠けた list.txt を使う"), True)
    s.save("full_disk.webp")


def compare_scope_figure():
    """What experiment 1 compares, with ls --bogus as the example."""
    results = {r["case"]: r for r in json.loads((OUT / "exp1_gnu_uutils_0.8.0.json").read_text())}
    r = results["ls --bogus"]
    g, u = r["gnu"], r["uutils"]
    s = Svg(880, 300)
    s.text(20, 30, "ls --bogus の結果を、項目ごとに比べる", 16, INK, "start")
    s.text(150, 62, "GNU", 13, SUB)
    s.text(730, 62, "uutils", 13, SUB)
    rows = [
        ("stdout", "（空）", "（空）", "そのまま比べる", "一致", INK),
        ("終了コード", str(g["exit"]), str(u["exit"]), "そのまま比べる", "一致", INK),
        ("stderr", "ls: unrecognized option …", "error: unexpected argument …",
         "何か出したかだけ比べる", "どちらも出した → 一致", AMBER),
    ]
    for i, (label, gv, uv, how, verdict, color) in enumerate(rows):
        y = 80 + i * 62
        s.text(20, y + 26, label, 13, INK, "start")
        s.box(100, y, 230, 40, FILL, LINE)
        s.text(110, y + 25, gv, 11, INK, "start", mono=True)
        s.box(620, y, 240, 40, FILL, LINE)
        s.text(630, y + 25, uv, 11, INK, "start", mono=True)
        s.line(330, y + 20, 400, y + 20, LINE)
        s.line(550, y + 20, 620, y + 20, LINE)
        s.box(400, y + 2, 150, 36, "#ffffff", color if color != INK else SUB, rx=18)
        s.text(475, y + 18, how, 11, SUB)
        s.text(475, y + 32, verdict, 11, color)
    s.text(20, 288, "raw（全てをそのまま比べる）では stderr の文面で差になり、normalized では差にならない", 12, SUB, "start")
    s.save("compare_scope.webp")


def blind_spot_figure():
    """What Differential Testing cannot see: the same mistake in both."""
    s = Svg(880, 230)
    s.text(20, 30, "2 つの実装が同じ誤りを持つと、差が出ない", 16, INK, "start")
    s.box(20, 90, 170, 56, FILL, LINE)
    s.text(105, 113, "仕様書の", 13)
    s.text(105, 132, "曖昧な記述", 13)
    for i, name in enumerate(["実装 A", "実装 B"]):
        y = 60 + i * 90
        s.arrow(190, 118, 258, y + 22)
        s.box(260, y, 170, 44, PALE, ACCENT)
        s.text(345, y + 20, name, 13)
        s.text(345, y + 36, "同じように解釈", 11, SUB)
        s.arrow(430, y + 22, 478, y + 22)
        s.box(480, y, 130, 44, RED_PALE, RED)
        s.text(545, y + 28, "誤った出力 X", 13, RED)
    s.text(640, 112, "比べると一致する", 14, INK, "start")
    s.text(640, 134, "→ テストは通る", 14, RED, "start")
    s.text(20, 218, "比べて分かるのは「2 つが違うこと」だけで、「2 つが正しいこと」は分からない", 12, SUB, "start")
    s.save("blind_spot.webp")


def sql_figure():
    s = Svg(860, 300)

    def node(x, y, label, w, fill=FILL, stroke=SUB, color=INK, size=14, mono=False):
        s.box(x, y, w, 44, fill, stroke)
        s.text(x + w / 2, y + 28, label, size, color, mono=mono)

    s.text(20, 30, "同じ SQL を 2 つの相手に渡す", 15, INK, "start")
    node(20, 112, "SELECT a, b FROM g GROUP BY b", 270, size=12, mono=True)
    node(340, 60, "SQLite（filesql が内部で使う）", 230, PALE, ACCENT, size=13)
    node(610, 60, "(1, 10) と (3, 20) を返す", 230, size=13)
    s.text(725, 124, "a はグループのどれか 1 行の値", 12, SUB)
    node(340, 170, "PostgreSQL（filesql が約束した相手）", 230, PALE, ACCENT, size=12)
    node(610, 170, "拒否する", 230, RED_PALE, RED, RED, size=13)
    s.text(725, 234, "a は GROUP BY に無く、集約もしていない", 12, SUB)
    s.arrow(290, 126, 338, 84)
    s.arrow(290, 142, 338, 190)
    s.arrow(570, 82, 608, 82)
    s.arrow(570, 192, 608, 192)
    s.text(20, 280, "修正前の filesql は SQLite の答えを返していた。約束した PostgreSQL に合わせて、拒否するように直した", 13, RED, "start")
    s.save("sql.webp")


def acl_figure():
    """Why uutils 0.8.0 prints + for a file that only has a user xattr."""
    s = Svg(880, 228)
    s.text(20, 30, "拡張属性 user.note だけを付けたファイルの ls -l", 16, INK, "start")
    s.box(20, 92, 170, 60, FILL, LINE)
    s.text(105, 116, "attr.txt", 13, INK, mono=True)
    s.text(105, 138, "user.note = 1", 12, SUB, mono=True)

    def lane(y, name, question, answer, out, bad):
        color = RED if bad else INK
        s.text(230, y - 8, name, 13, SUB, "start")
        s.box(230, y, 300, 44, PALE, ACCENT)
        s.text(380, y + 27, question, 13)
        s.arrow(530, y + 22, 568, y + 22)
        s.text(590, y + 27, answer, 13, color, "start")
        s.box(690, y, 170, 44, RED_PALE if bad else FILL, RED if bad else LINE)
        s.text(775, y + 28, out, 15, color)

    lane(60, "GNU 9.7", "ACL などのアクセス制御があるか", "無い", "-rw-rw-r--", False)
    lane(160, "uutils 0.8.0（has_acl）", "拡張属性が 1 つでもあるか", "ある", "-rw-rw-r--+", True)
    s.arrow(190, 112, 228, 86)
    s.arrow(190, 132, 228, 178)
    s.save("acl.webp")


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
    full_disk_figure()
    compare_scope_figure()
    blind_spot_figure()
    concept_figure()
    native_json_figure()
    sql_figure()
    acl_figure()
