"""Mutation Testing のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

SVG の文字列をここで組み、headless Chrome で 2 倍で描いて WebP にする（Pillow）。
images/ には WebP だけを残す。数値は lab/output/ から読むので、実験を回し直したらこの script も回し直す。

- cover_figure(): 表紙。width_bucket の正しい計算と、x-low を x+low にしたミュータントが、
  値を範囲のどこに置くか。公式文書の例（下限 0.024）では同じ 3 番、下限 10 では 3 番と 13 番に分かれる
  （lab/output/width_bucket.txt、postgresql_width_bucket.txt）。
- packages_figure(): gremlins が filesql の dialect に作ったミュータントを、パッケージごとに
  キル・生き残り・未カバー・時間切れで積んだ横棒（lab/output/gremlins_dialect_*.txt）。
- gleam_figure(): metamon の relation.gleam のミュータントごとに、どのテストのモジュールが落ちたか
  （lab/output/gleam_relation.json）。
"""

import json
import re
import subprocess
import tempfile
from collections import Counter
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE, GREEN = "#7aa6c2", "#d64545", "#fbe3e3", "#5b9a68"
LINE = "#9a9a9a"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"


def render_svg(svg_text, w, h, name):
    """SVG の文字列 -> PNG（headless Chrome、2 倍）-> images/<name>（WebP）。"""
    work = HERE.parents[3] / ".note-review" / "work"   # /tmp が RAM の環境向け。無ければ既定の場所
    with tempfile.TemporaryDirectory(dir=work if work.exists() else None) as tmp:
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
                  '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
                  f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
                  '<marker id="r" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
                  f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
                  f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def box(self, x, y, bw, bh, fill, stroke=SUB, dash=False, rx=6, width=1.2):
        d = ' stroke-dasharray="6 4"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{width}"{d}/>')

    def text(self, x, y, s, size=15, color=INK, anchor="middle", mono=False):
        cls = ' class="m"' if mono else ""
        self.p.append(f'<text{cls} x="{x}" y="{y}" font-size="{size}" fill="{color}" '
                      f'text-anchor="{anchor}" style="fill:{color}" xml:space="preserve">{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, color=LINE, dash=False, width=1.5, arrow=None):
        d = ' stroke-dasharray="5 4"' if dash else ""
        m = f' marker-end="url(#{arrow})"' if arrow else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{width}"{d}{m}/>')

    def circle(self, x, y, r, fill, stroke=None):
        s = f' stroke="{stroke}" stroke-width="1.5"' if stroke else ""
        self.p.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"{s}/>')

    def done(self):
        return "\n".join(self.p + ["</svg>"])


def bucket(x, low, high, n, mutant):
    """width_bucket の式。mutant=True は x-low を x+low にしたミュータント（lab の L219）。"""
    pos = n * ((x + low) if mutant else (x - low)) / (high - low)
    return pos, int(pos) + 1


def cover_figure():
    lines = (OUT / "postgresql_width_bucket.txt").read_text()
    pg = {m.group(1): int(m.group(2)) for m in re.finditer(r"width_bucket\(([^)]*)\) = (\d+)", lines)}
    w, h = 1100, 470
    s = Svg(w, h)
    s.text(40, h - 22, "青い区画は範囲を 5 等分した番号。点線は範囲の外で、実際の関数は 6 番にまとめる"
           "（ミュータントは範囲の中だと計算するので、式の値がそのまま返る）", 13, SUB, anchor="start")
    x0, unit = 90, 62            # 範囲の割合 0〜1 を 5 区画にした目盛り（1 区画 = unit px）
    cases = [("公式文書の例: width_bucket(5.35, 0.024, 10.06, 5)", (5.35, 0.024, 10.06, 5), 70),
             ("下限を 10 にした例: width_bucket(15, 10, 20, 5)", (15, 10, 20, 5), 255)]
    for title, (x, low, high, n), y in cases:
        s.text(40, y, title, 18, anchor="start")
        base = y + 80
        for i in range(n):
            s.box(x0 + i * unit, base - 22, unit, 44, PALE, stroke=ACCENT)
            s.text(x0 + i * unit + unit / 2, base + 6, f"{i + 1}", 16, SUB)
        for i in range(n, 13):
            s.box(x0 + i * unit, base - 22, unit, 44, "#ffffff", stroke=LINE, dash=True)
            s.text(x0 + i * unit + unit / 2, base + 6, f"{i + 1}", 16, "#aaaaaa")
        pos_ok, b_ok = bucket(x, low, high, n, False)
        pos_mu, b_mu = bucket(x, low, high, n, True)
        key = f"{x}, {low}, {high}, {n}".replace("15, 10, 20, 5", "15, 10, 20, 5")
        assert pg.get(key) == b_ok, (key, pg.get(key), b_ok)
        ok_x, mu_x = x0 + pos_ok * unit, x0 + pos_mu * unit
        s.line(ok_x, base - 52, ok_x, base - 26, ACCENT, width=2.5, arrow="a")
        s.text(ok_x - 8, base - 58, f"正しい計算（x − low）: {b_ok} 番", 15, INK, anchor="end")
        s.line(mu_x, base + 62 - 30, mu_x, base + 26, RED, width=2.5, arrow="r")
        if b_mu == b_ok:
            s.text(mu_x + 8, base + 58, f"ミュータント（x + low）: {b_mu} 番", 15, RED, anchor="start")
        else:
            s.text(mu_x - 8, base + 58, f"ミュータント（x + low）: {b_mu} 番", 15, RED, anchor="end")
        if b_mu == b_ok:
            s.text(w - 40, y, "同じ番号になり、テストは通る", 17, SUB, anchor="end")
        else:
            s.text(w - 40, y, "番号が分かれ、テストが落ちる", 17, RED, anchor="end")
    render_svg(s.done(), w, h, "cover.webp")


def packages_figure():
    per = {}
    tsv = (OUT / "gremlins_dialect_by_package.tsv").read_text().splitlines()
    head = tsv[0].split("\t")
    for l in tsv[1:]:
        cells = l.split("\t")
        per[cells[0]] = Counter({head[i]: int(cells[i]) for i in range(1, len(head))})
    rows = sum(per.values(), Counter())
    summary = (OUT / "gremlins_dialect_summary.txt").read_text()
    k = int(re.search(r"Killed: (\d+)", summary).group(1))
    lv = int(re.search(r"Lived: (\d+)", summary).group(1))
    nc = int(re.search(r"Not covered: (\d+)", summary).group(1))
    assert (rows["KILLED"], rows["LIVED"], rows["NOT COVERED"]) == (k, lv, nc)
    order = ["internal/runtime", "internal/parser", "internal/lower", "internal/token", "internal/render"]
    colors = [("KILLED", "キル", ACCENT), ("LIVED", "生き残り", RED), ("TIMED OUT", "時間切れ", "#c9a227"),
              ("NOT COVERED", "未カバー（実行しない）", "#d9d9d9")]
    w, h = 820, 400
    s = Svg(w, h)
    s.text(20, 32, "dialect 配下のパッケージごとのミュータント", 17, anchor="start")
    lx = 20
    for _, name, c in colors:
        s.box(lx, 52, 15, 15, c, stroke=c, rx=2)
        s.text(lx + 21, 65, name, 14, anchor="start")
        lx += 36 + len(name) * 14
    x0, maxw, top, bh, gap = 100, 470, 92, 32, 16
    total = max(sum(per[p].values()) for p in order)
    for i, p in enumerate(order):
        y = top + i * (bh + gap)
        s.text(x0 - 10, y + 22, p.replace("internal/", ""), 14, anchor="end", mono=True)
        x = x0
        for key, _, c in colors:
            v = per[p][key]
            bw = maxw * v / total
            if bw > 0:
                s.box(x, y, bw, bh, c, stroke="#ffffff", rx=0, width=1)
                if bw > 34:
                    s.text(x + bw / 2, y + 22, f"{v}", 13, "#ffffff" if key in ("KILLED", "LIVED") else INK)
            x += bw
        kk, ll = per[p]["KILLED"], per[p]["LIVED"]
        s.text(x + 10, y + 22, f"キル率 {100 * kk / (kk + ll):.1f}%", 14, SUB, anchor="start")
    s.text(20, h - 36, f"全体: キル {k}・生き残り {lv}・未カバー {nc}。キル率はキル ÷（キル + 生き残り）", 13, SUB, anchor="start")
    s.text(20, h - 16, "ミュータントが 10 個に満たない 2 つのパッケージと、最上位の dialect.go は図から外した", 13, SUB, anchor="start")
    render_svg(s.done(), w, h, "packages.webp")


def gleam_figure():
    rs = [r for r in json.loads((OUT / "gleam_relation.json").read_text()) if r["status"] != "COMPILE_ERROR"]
    rs.sort(key=lambda r: r["line"])
    cols = ["relation_test", "metamon_self_property_test", "morph_n_test"]
    label = {"relation_test": "例を並べた\nテスト",
             "metamon_self_property_test": "metamon 自身の\nPBT",
             "morph_n_test": "N 項の関係の\nテスト", "その他": "その他の\nテスト"}
    reach = dict(re.findall(r"^L(\d+): (.*)$", (OUT / "gleam.txt").read_text(), re.M))
    # 生き残った行の分岐を panic にしてもテストが全部通るなら、テストはその行に届いていない
    note = {int(k): ("テストが届かない" if "no failures" in v else "等価ミュータント") for k, v in reach.items()}
    rowh, x0, cw, top = 22, 380, 112, 104
    allc = cols + ["その他"]
    w, h = x0 + cw * len(allc) + 20, top + rowh * len(rs) + 52
    s = Svg(w, h)
    s.text(20, 32, "relation.gleam のミュータントごとに、落ちたテストの数", 17, anchor="start")
    for j, c in enumerate(allc):
        cx = x0 + j * cw + cw / 2
        for k2, part in enumerate(label[c].split("\n")):
            s.text(cx, 70 + k2 * 18, part, 14, INK)
    for i, r in enumerate(rs):
        y = top + i * rowh
        lived = r["status"] == "LIVED"
        if lived:
            s.box(12, y, w - 24, rowh, RED_PALE, stroke=RED_PALE, rx=0)
        color = RED if lived else INK
        s.text(20, y + 16, f"L{r['line']:<4}{r['mutator']}", 13, color, anchor="start", mono=True)
        s.text(x0 - 10, y + 16, r["function"], 13, SUB, anchor="end", mono=True)
        if lived:
            s.text(x0 + cw * len(allc) / 2, y + 16, f"生き残り（{note.get(r['line'], '')}）", 14, RED)
            continue
        cnt = Counter(t.split(".")[0] for t in r["killed_by"])
        other = sum(v for m, v in cnt.items() if m not in cols)
        for j, c in enumerate(allc):
            v = other if c == "その他" else cnt.get(c, 0)
            cx = x0 + j * cw + cw / 2
            if v:
                s.box(cx - 20, y + 3, 40, rowh - 6, ACCENT, stroke=ACCENT, rx=3)
                s.text(cx, y + 16, str(v), 13, "#ffffff")
    s.text(20, h - 18, "数字は、そのミュータントで落ちたテスト関数の数（gleam test 1 回分）", 13, SUB, anchor="start")
    render_svg(s.done(), w, h, "gleam.webp")


if __name__ == "__main__":
    cover_figure()
    packages_figure()
    gleam_figure()
