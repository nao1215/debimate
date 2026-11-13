"""Quint のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

SVG の文字列をここで組み、headless Chrome で 2 倍で描いて WebP にする（Pillow）。images/ には WebP だけを残す。
ファイルの中身と反例は lab/output/ から読むので、実験の script を回し直したら、この script も回し直す。

- cover_figure(): 表紙。a の上書きが途中で失敗する同じ順序で、0ee1d88（selfRestore）と 1742eca（touched）は a を戻し、
  3036574（rollback）は a を書き込み途中のまま残す（lab/output/exp1_verify.txt と exp1_witness.txt）。
- runtime_figure(): Go のリポジトリから Quint を使う時に、何がどの実行環境で動くか（lab/output/exp3_runtime.txt）。
- oracle_figure(): 今の sqly と、戻す範囲を 3036574・663bd7a と同じにしたミュータント（M1）で、a の上書きが
  途中で失敗した 1 回。エラー文は同じで、ファイルの中身だけが違う（lab/output/exp2_replay.txt）。
"""

import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#4f86a8", "#d64545", "#fbe3e3"
LINE = "#9a9a9a"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"

# ファイルの中身の 3 つの状態: 塗り、線、表示
STATE = {
    "old": (FILL, SUB, "元の中身"),
    "new": (PALE, ACCENT, "新しい中身"),
    "broken": (RED_PALE, RED, "書き込み途中"),
}
NAMES = {"a": "people.csv", "b": "places.csv"}


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

    def text(self, x, y, s, size=14, color=INK, anchor="middle", mono=False):
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
        render_svg("\n".join(self.p), self.w, self.h, name)


def file_box(s, x, y, w, target, state, h=30):
    fill, stroke, label = STATE[state]
    s.box(x, y, w, h, fill, stroke=stroke, rx=5, width=2 if state != "old" else 1.2)
    s.text(x + 10, y + 20, NAMES[target], size=12, anchor="start", mono=True)
    s.text(x + w - 10, y + 20, label, size=12, anchor="end", color=RED if state == "broken" else INK)


def read_block(path, name):
    """exp1 の出力から、設計 name の反例（トレース）を [(event, disk), ...] で返す。"""
    text = (OUT / path).read_text()
    block = text.split(f"== {name}:")[1].split("\n== ")[0]
    states = []
    for st in re.split(r"\[State \d+\]", block)[1:]:
        disk = dict(re.findall(r'"([ab])" -> "(\w+)"', st))
        ev = re.search(r'outcome: "(\w*)", step: "(\w+)", target: "(\w*)"', st.replace("\n", " "))
        states.append(((ev.group(2), ev.group(3), ev.group(1)), disk))
    return states


def cover_figure():
    # 3036574 の反例と、同じ順序で a を戻せる 0ee1d88・1742eca のトレース
    rollback = read_block("exp1_verify.txt", "rollback")
    self_restore = read_block("exp1_witness.txt", "selfRestore")
    touched = read_block("exp1_witness.txt", "touched")
    steps = [ev for ev, _ in rollback]
    assert [ev for ev, _ in self_restore] == steps and [ev for ev, _ in touched] == steps
    w, h = 960, 500
    s = Svg(w, h)
    s.text(24, 34, "a の上書きが途中で失敗する同じ順序で、戻せていた a が一度戻らなくなる", size=18, anchor="start")
    s.text(24, 58, "Quint の仕様を Apalache が 6 ステップまで調べた結果（上から修正の順）", size=13, anchor="start", color=SUB)
    heads = ["保存前", "a を一時ファイルに書く", "b を一時ファイルに書く", "a の上書きが途中で失敗"]
    x0, cw, gap = 200, 172, 16
    for i, hd in enumerate(heads):
        cx = x0 + i * (cw + gap)
        s.text(cx + cw / 2, 96, hd, size=13, color=RED if i == 3 else INK)
        if i:
            s.arrow(cx - gap - 6, 91, cx + 4, 91)
    rows = [
        ("0ee1d88 の設計", "失敗したファイル\n自身を戻す", self_restore, "a をバックアップから戻した"),
        ("3036574 の設計", "移し終えた分だけ戻す", rollback, "戻す範囲は空で、a は書き込み途中"),
        ("1742eca の設計", "移し終えた分と、\n失敗したファイルを戻す", touched, "a をバックアップから戻した"),
    ]
    for r, (name, sub, states, note) in enumerate(rows):
        y = 112 + r * 126
        if r:
            s.line(24, y - 4, w - 24, y - 4, color="#dddddd", width=1)
        s.text(24, y + 34, name, size=15, anchor="start")
        for li, part in enumerate(sub.split("\n")):
            s.text(24, y + 56 + li * 18, part, size=12, anchor="start", color=SUB)
        s.text(x0 - 14, y + 34, "a", size=14, color=SUB)
        s.text(x0 - 14, y + 70, "b", size=14, color=SUB)
        for i, (_, disk) in enumerate(states):
            cx = x0 + i * (cw + gap)
            file_box(s, cx, y + 14, cw, "a", disk["a"])
            file_box(s, cx, y + 50, cw, "b", disk["b"])
        ok = all(v == "old" for v in states[-1][1].values())
        s.text(x0 + 3 * (cw + gap) + cw / 2, y + 104, note, size=12, color=INK if ok else RED)
    s.save("cover.webp")


def mib(du):
    """du -h の 43M・2.1M を 43 MiB・2.1 MiB にする。"""
    return re.sub(r"^([\d.]+)M$", r"\1 MiB", du)


def runtime_figure():
    rt = (OUT / "exp3_runtime.txt").read_text()
    nm = re.search(r"node_modules: (\S+), packages: (\d+)", rt)
    binsize = re.search(r"quint-linux-amd64: (\S+)", rt).group(1)
    ev = re.search(r"downloaded: rust-evaluator-(\S+)\s+(\S+)", rt)
    ap = re.search(r"downloaded: (apalache-dist-\S+) .* (\S+)$", rt, re.M)
    w, h = 960, 430
    s = Svg(w, h)
    s.text(24, 34, "Go のリポジトリから Quint を使う時に、どこで何が動くか", size=18, anchor="start")
    # 左: Go
    s.box(24, 66, 250, 330, "#ffffff", stroke=SUB)
    s.text(149, 92, "Go のリポジトリ（go test）", size=14)
    s.box(44, 112, 210, 46, FILL, rx=6)
    s.text(149, 141, "save.qnt（仕様）", size=13)
    s.box(44, 300, 210, 76, PALE, stroke=ACCENT, rx=6)
    s.text(149, 326, "savemodel_test.go", size=13, mono=True)
    s.text(149, 348, "ITF を読む部分は自分で書く", size=12)
    s.text(149, 366, "（Go の Quint Connect は無い）", size=12, color=SUB)
    # 中: quint CLI
    s.box(330, 66, 270, 120, FILL, stroke=SUB)
    s.text(465, 92, "quint（TypeScript 製の CLI）", size=14)
    s.text(465, 120, f"npm: Node.js 18 以上、{mib(nm.group(1))}・{nm.group(2)} パッケージ", size=12)
    s.text(465, 144, f"または Node 同梱の実行ファイル {mib(binsize)}", size=12)
    s.text(465, 170, "書く・型を調べる・trace を書き出す", size=12, color=SUB)
    s.arrow(254, 135, 328, 120)
    # 右上: Rust の評価器
    s.box(660, 66, 276, 100, PALE, stroke=ACCENT)
    s.text(798, 92, "quint run（シミュレーター）", size=14)
    s.text(798, 118, f"Rust 製の評価器 {mib(ev.group(2))}", size=12)
    s.text(798, 140, "初回に GitHub から ~/.quint へダウンロード", size=12, color=SUB)
    s.arrow(600, 110, 658, 110)
    # 右中: Apalache
    s.box(660, 190, 276, 110, RED_PALE, stroke=RED)
    s.text(798, 216, "quint verify（有界モデル検査）", size=14)
    s.text(798, 242, f"Apalache {mib(ap.group(2))}（Z3 を同梱）", size=12)
    s.text(798, 264, "JDK 21 以上。JDK 17 では起動しない", size=12, color=RED)
    s.text(798, 286, "初回に GitHub から ~/.quint へダウンロード", size=12, color=SUB)
    s.arrow(600, 160, 658, 235)
    # 下: ITF
    s.box(330, 300, 270, 76, FILL, stroke=SUB, dash=True)
    s.text(465, 328, "traces/*.itf.json", size=13, mono=True)
    s.text(465, 350, "quint run --mbt が書き出す JSON", size=12)
    s.arrow(465, 186, 465, 298)
    s.arrow(330, 338, 256, 338)
    s.save("runtime.webp")


def oracle_figure():
    rep = (OUT / "exp2_replay.txt").read_text()
    runs = {}
    for key in ("original", "M1_failed_target_not_restored"):
        disk = re.search(rf"^{key} one run: disk: people.csv=(\w+) places.csv=(\w+)", rep, re.M)
        err = re.search(rf"^{key} one run: error: (.+)$", rep, re.M).group(1)
        runs[key] = ({"a": disk.group(1), "b": disk.group(2)}, err)
    assert runs["original"][1] == runs["M1_failed_target_not_restored"][1]
    w, h = 960, 330
    s = Svg(w, h)
    s.text(24, 34, "a の上書きが途中で失敗した 1 回: エラー文は同じで、ファイルだけが違う", size=18, anchor="start")
    cols = [("original", "今の sqly（1742eca の設計）"), ("M1_failed_target_not_restored", "M1: 書き込み途中のファイルを戻さない（3036574 の戻す範囲）")]
    for i, (key, title) in enumerate(cols):
        x = 24 + i * 468
        disk, _ = runs[key]
        s.box(x, 60, 444, 150, "#ffffff", stroke=SUB)
        s.text(x + 222, 88, title, size=14)
        file_box(s, x + 40, 108, 364, "a", disk["a"], h=34)
        file_box(s, x + 40, 152, 364, "b", disk["b"], h=34)
        s.arrow(x + 222, 212, x + 222, 246)
    s.box(24, 248, 912, 58, FILL, stroke=SUB, rx=6)
    s.text(480, 271, "どちらも返すエラー文", size=12, color=SUB)
    s.text(480, 293, runs["original"][1], size=13, mono=True)
    s.save("oracle.webp")


if __name__ == "__main__":
    cover_figure()
    runtime_figure()
    oracle_figure()
