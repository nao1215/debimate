"""Generate the figures of the Soft Delete note (WebP).

join_figure() draws the rows of lab/join.sql: where the deleted_at
condition is written (WHERE or ON) decides whether the product whose only
reservation was canceled survives the LEFT JOIN.

unique_figure() draws the index entries of lab/unique_pg.sql for each way
of writing the unique constraint, and which entries collide.

places_figure() draws where a deleted row lives for each design.

The SVG is rendered by headless Chrome at 2x and saved as WebP. Temporary
files go to .note-review/work/soft-delete/ (not /tmp).

Run: python3 content/notes/database-systems/soft-delete/figures.py
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
WORK = REPO / ".note-review" / "work" / "soft-delete"
INK, SUB, LINE = "#1f1f1f", "#666666", "#9a9a9a"
FILL, PALE, ACCENT = "#f2f2f2", "#eaf1f5", "#5f8fae"
RED, RED_PALE = "#d04a4c", "#fbe9e9"
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .m{{font-family:{MONO}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="5" markerHeight="5" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=20, color=INK, anchor="middle", mono=False):
        cls = ' class="m"' if mono else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{cls} '
            f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=3, arrow=False, dash=""):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}{d}/>')

    def save_webp(self, name):
        WORK.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=WORK) as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def row(s, x, y, cells, widths, fill=FILL, stroke=LINE, colors=None, dash="", strike=False):
    """表の 1 行を描く。cells はマスの文字、widths はマスの幅。"""
    total = sum(widths)
    s.box(x, y, total, 40, fill, stroke, dash=dash, rx=4)
    cx = x
    for i, (c, w) in enumerate(zip(cells, widths)):
        if i:
            s.line(cx, y + 6, cx, y + 34, color=LINE, sw=1)
        color = (colors[i] if colors else INK)
        s.text(cx + w / 2, y + 27, c, size=18, color=color, mono=c.isascii() and c != "")
        cx += w
    if strike:
        s.line(x + 6, y + 20, x + total - 6, y + 20, color=RED, sw=3)


def join_figure():
    s = Svg(1200, 620, "LEFT JOIN と取り消した予約の条件の置き場所")
    widths = [110, 90, 140]
    head = ["商品", "予約", "取り消し"]
    # 上の段: WHERE に書いた場合
    s.text(30, 44, "(A) WHERE r.deleted_at IS NULL に書いた場合", size=22, anchor="start")
    s.text(195, 92, "結合した直後", size=18, color=SUB)
    row(s, 25, 104, head, widths, fill="#ffffff", colors=[SUB] * 3)
    row(s, 25, 148, ["カメラ", "NULL", "NULL"], widths, colors=[INK, SUB, SUB])
    row(s, 25, 192, ["三脚", "10", "NULL"], widths)
    row(s, 25, 236, ["レンズ", "11", "済み"], widths, colors=[INK, INK, RED])
    s.line(385, 192, 505, 192, arrow=True)
    s.text(445, 178, "WHERE", size=16, color=SUB, mono=True)
    s.text(780, 92, "結果: 2 行", size=18, color=SUB)
    w2 = [150, 120]
    row(s, 645, 104, ["商品", "予約数"], w2, fill="#ffffff", colors=[SUB, SUB])
    row(s, 645, 148, ["カメラ", "0"], w2)
    row(s, 645, 192, ["三脚", "1"], w2)
    row(s, 645, 236, ["レンズ", "0"], w2, fill="#ffffff", stroke=RED, dash="6 5",
        colors=[RED, RED], strike=True)
    s.text(935, 261, "取り消した予約しか無い", size=18, color=RED, anchor="start")
    s.text(935, 285, "商品が結果から消える", size=18, color=RED, anchor="start")
    s.text(935, 173, "予約が 1 件も無い", size=18, color=SUB, anchor="start")
    s.text(935, 197, "カメラは残る", size=18, color=SUB, anchor="start")
    s.line(20, 318, 1180, 318, color="#dddddd", sw=2)
    # 下の段: ON に書いた場合
    s.text(30, 362, "(B) ON ... AND r.deleted_at IS NULL に書いた場合", size=22, anchor="start")
    s.text(195, 410, "結合した直後", size=18, color=SUB)
    row(s, 25, 422, head, widths, fill="#ffffff", colors=[SUB] * 3)
    row(s, 25, 466, ["カメラ", "NULL", "NULL"], widths, colors=[INK, SUB, SUB])
    row(s, 25, 510, ["三脚", "10", "NULL"], widths)
    row(s, 25, 554, ["レンズ", "NULL", "NULL"], widths, colors=[INK, SUB, SUB])
    s.line(385, 510, 505, 510, arrow=True)
    s.text(445, 496, "WHERE", size=16, color=SUB, mono=True)
    s.text(780, 410, "結果: 3 行", size=18, color=SUB)
    row(s, 645, 422, ["商品", "予約数"], w2, fill="#ffffff", colors=[SUB, SUB])
    row(s, 645, 466, ["カメラ", "0"], w2)
    row(s, 645, 510, ["三脚", "1"], w2)
    row(s, 645, 554, ["レンズ", "0"], w2, fill=PALE, stroke=ACCENT)
    s.text(935, 567, "取り消した予約は", size=18, color=SUB, anchor="start")
    s.text(935, 591, "結合の前に外れる", size=18, color=SUB, anchor="start")
    s.save_webp("soft-delete_join.webp")


def unique_figure():
    s = Svg(1200, 520, "一意制約の書き方ごとに、インデックスに入る値と衝突する値")
    cols = [
        ("UNIQUE (email)", "", [("a", ""), ("a", ""), ("b", ""), ("b", "")],
         [0, 1], [2, 3], "再登録できない", "重複を止める", False, True),
        ("UNIQUE", "(email, deleted_at)", [("a", "日時"), ("a", "NULL"), ("b", "NULL"), ("b", "NULL")],
         [], [], "再登録できる", "重複が通る", True, False),
        ("部分インデックス", "WHERE deleted_at IS NULL", [None, ("a", ""), ("b", ""), ("b", "")],
         [], [2, 3], "再登録できる", "重複を止める", True, True),
        ("UNIQUE NULLS NOT DISTINCT", "(email, deleted_at)", [("a", "日時"), ("a", "NULL"), ("b", "NULL"), ("b", "NULL")],
         [], [2, 3], "再登録できる", "重複を止める", True, True),
    ]
    s.text(120, 82, "インデックスに", size=15, color=SUB, anchor="end")
    s.text(120, 102, "入る値", size=15, color=SUB, anchor="end")
    labels = ["退会した a", "再登録の a", "有効な b", "有効な b"]
    for i, lab in enumerate(labels):
        s.text(120, 142 + i * 58, lab, size=18, color=SUB, anchor="end")
    x0, cw = 145, 262
    for c, (title, sub, entries, bad_a, dup_b, re_ok, dup_ok, re_good, dup_good) in enumerate(cols):
        x = x0 + c * cw
        s.text(x + cw / 2 - 8, 50, title, size=16, mono=title.isascii())
        s.text(x + cw / 2 - 8, 78, sub, size=15, color=SUB, mono=True)
        for i, e in enumerate(entries):
            y = 114 + i * 58
            if e is None:
                s.box(x + 20, y, cw - 56, 42, "#ffffff", LINE, dash="5 5", rx=4)
                s.text(x + cw / 2 - 8, y + 28, "入らない", size=16, color=SUB)
                continue
            em, d = e
            label = f"{em}@" if not d else f"({em}@, {d})"
            collide = (i in bad_a and i == 1) or (i in dup_b and i == 3)
            fill, stroke = (RED_PALE, RED) if collide else (FILL, LINE)
            s.box(x + 20, y, cw - 56, 42, fill, stroke, rx=4)
            s.text(x + cw / 2 - 8, y + 28, label, size=17, mono=True, color=RED if collide else INK)
        # 結果
        for j, (txt, good) in enumerate([(re_ok, re_good), (dup_ok, dup_good)]):
            y = 380 + j * 52
            s.box(x + 20, y, cw - 56, 40, PALE if good else RED_PALE, ACCENT if good else RED, rx=20)
            s.text(x + cw / 2 - 8, y + 27, txt, size=17, color=INK if good else RED)
    s.text(120, 406, "退会者と同じ", size=16, color=SUB, anchor="end")
    s.text(120, 426, "アドレス", size=16, color=SUB, anchor="end")
    s.text(120, 458, "有効どうしの", size=16, color=SUB, anchor="end")
    s.text(120, 478, "重複", size=16, color=SUB, anchor="end")
    s.text(600, 362, "赤い枠は、上の値と衝突して INSERT が拒否された値", size=15, color=SUB)
    s.save_webp("soft-delete_unique.webp")


def places_figure():
    s = Svg(1200, 440, "使わなくなった会員のレコードが残る場所")
    panels = [
        ("論理削除", "members", [("佐藤", "deleted_at = 日時", True), ("鈴木", "deleted_at = NULL", False)],
         None, "読む SQL が全部、条件を書く"),
        ("削除したレコードの表", "members", [("鈴木", "", False)],
         ("deleted_record", ['{"name": "佐藤", ...}']), "現行の表には有効な会員だけ"),
        ("状態のカラムと履歴", "members", [("佐藤", "status = 退会済み", True), ("鈴木", "status = 有効", False)],
         ("member_status_changes", ["有効 → 退会済み"]), "いつ何に変わったかが残る"),
        ("匿名化", "members", [("退会者 1", "email = NULL", True), ("鈴木", "email = s@...", False)],
         None, "個人データだけ消え、注文は辿れる"),
    ]
    pw = 285
    for i, (title, table, rows, side, note) in enumerate(panels):
        x = 20 + i * (pw + 10)
        s.box(x, 20, pw, 400, "#ffffff", "#dddddd", rx=10)
        s.text(x + pw / 2, 58, title, size=21)
        s.text(x + 22, 100, table, size=16, color=SUB, anchor="start", mono=True)
        for j, (name, attr, dead) in enumerate(rows):
            y = 112 + j * 62
            s.box(x + 18, y, pw - 36, 52, FILL if dead else PALE, LINE if dead else ACCENT, rx=4)
            s.text(x + 34, y + 23, name, size=17, anchor="start", color=SUB if dead else INK)
            if attr:
                s.text(x + 34, y + 44, attr, size=15, anchor="start", color=SUB)
        if side:
            st, items = side
            s.line(x + pw / 2, 248, x + pw / 2, 280, arrow=True)
            s.text(x + 22, 302, st, size=15, color=SUB, anchor="start", mono=True)
            for j, it in enumerate(items):
                s.box(x + 18, 312 + j * 50, pw - 36, 42, FILL, LINE, rx=4)
                s.text(x + pw / 2, 339 + j * 50, it, size=15, mono=it.isascii())
        s.text(x + pw / 2, 404, note, size=16, color=SUB)
    s.save_webp("soft-delete_places.webp")


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    join_figure()
    unique_figure()
    places_figure()
