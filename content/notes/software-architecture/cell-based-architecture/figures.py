"""Generate the figures of the Cell-based Architecture note (WebP).

poison_figure() and timeline_figure() read lab/results/*.json (written by lab/run.py).
remap_figure() recomputes lab/remap.py for the first 100 customers.

Run: python3 content/notes/software-architecture/cell-based-architecture/figures.py
"""

import json
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
import remap  # noqa: E402
import run  # noqa: E402

INK, SUB, RED, RED_PALE = "#1f1f1f", "#666666", "#e15759", "#fbe3e3"
FILL, PALE, ACCENT, LINE = "#f2f2f2", "#eaf1f5", "#7aa6c2", "#bdbdbd"
FONT = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"
MODES = [("shared", "1 つの群（GET）"), ("shared_post", "1 つの群（POST）"),
         ("cells", "4 つのセル"), ("shuffle", "Shuffle Sharding")]


def load(mode):
    return json.loads((HERE / "lab" / "results" / f"{mode}.json").read_text())


class Svg:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="5" markerHeight="5" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=22, color=INK, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                          f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=2.5, arrow=False, dash=""):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                          f'stroke-width="{sw}"{m}{d}/>')

    def save_webp(self, name):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def crashed(res):
    return {i for _, i, kind in res["events"] if kind == "down"}


def failed_customers(res):
    return len({c for _, c, s in res["records"] if s != 200})


def groups(mode):
    if mode == "cells":
        return [(0, 1), (2, 3), (4, 5), (6, 7)]
    return [tuple(range(8))]


def poison_figure():
    """表紙。ポイズンピル 1 回で落ちた台（赤）と、要求が失敗した顧客の数。"""
    s = Svg(1200, 590)
    s.text(40, 50, "ポイズンピルを 1 回送った後", 24, anchor="start")
    s.text(580, 50, "8 台（赤は落ちた台）", 20, SUB)
    s.text(1050, 50, "要求が失敗した顧客", 20, SUB)
    y = 90
    for mode, label in MODES:
        res = load(mode)
        down = crashed(res)
        s.text(40, y + 62, label, 23, anchor="start")
        x = 290
        for g in groups(mode):
            gx = x
            for i in g:
                red = i in down
                s.box(x, y + 20, 64, 64, RED_PALE if red else FILL, RED if red else LINE, sw=3 if red else 2)
                s.text(x + 32, y + 59, f":{run.PORTS[i]}", 17, RED if red else SUB)
                x += 72
            if mode == "cells":
                s.box(gx - 6, y + 12, 72 * len(g) + 4, 80, "none", ACCENT, sw=2, dash="6 4")
                s.text(gx + 68, y + 110, f"cell{g[0] // 2}", 18, ACCENT)
                x += 18
        if mode == "shuffle":
            s.text(290 + 4 * 72, y + 110, "c007 の組は :9002 と :9003", 18, SUB)
        n = failed_customers(res)
        s.text(1050, y + 64, f"{n} / {len(run.CUSTOMERS) - 1} 人", 26, RED if n else INK)
        y += 118
    s.save_webp("cell_poison_cover.webp")


def structure_figure():
    """セルルーター・セル・コントロールプレーンの関係。"""
    s = Svg(1200, 530)
    s.box(40, 200, 150, 90, FILL, LINE)
    s.text(115, 240, "顧客", 22)
    s.text(115, 270, "c000〜c279", 15, SUB)
    s.box(260, 150, 250, 190, PALE, ACCENT)
    s.text(385, 185, "セルルーター", 22)
    rows = [("c000", "cell1"), ("c001", "cell3"), ("c002", "cell0"), ("c007", "cell3")]
    for k, (c, cell) in enumerate(rows):
        yy = 220 + 28 * k
        s.text(345, yy, c, 16, RED if c == "c007" else INK)
        s.text(425, yy, cell, 16, RED if c == "c007" else INK)
    s.text(385, 330, "顧客 → セルの表を引くだけ", 15, SUB)
    s.line(190, 245, 255, 245, arrow=True)
    for k in range(4):
        y = 40 + 115 * k
        red = k == 3
        s.box(600, y, 340, 95, RED_PALE if red else "#ffffff", RED if red else INK, sw=3 if red else 2)
        s.text(640, y + 55, f"cell{k}", 18, RED if red else INK, anchor="start")
        for j in range(2):
            s.box(720 + 70 * j, y + 25, 60, 45, FILL, LINE)
            s.text(750 + 70 * j, y + 54, "app", 15, SUB)
        s.box(870, y + 25, 55, 45, FILL, LINE)
        s.text(897, y + 54, "DB", 15, SUB)
        s.line(510, 245, 595, y + 47, color=RED if red else INK, arrow=True, sw=2)
    s.box(260, 400, 250, 110, "#ffffff", SUB, dash="6 4")
    s.text(385, 435, "コントロールプレーン", 20)
    s.text(385, 465, "セルを作る・消す", 15, SUB)
    s.text(385, 490, "顧客を移す・表を書く", 15, SUB)
    s.line(385, 400, 385, 346, color=SUB, dash="6 4", arrow=True, sw=2)
    s.text(1070, 255, "要求は表が指す", 16, SUB)
    s.text(1070, 280, "1 つのセルの中で", 16, SUB)
    s.text(1070, 305, "完結する", 16, SUB)
    s.save_webp("cell_structure.webp")


def timeline_figure():
    """台の状態と、失敗した要求の割合を実測の時刻で動かす（動く WebP）。

    落ちて起動し直す 2〜5 秒は 0.5 倍速、それ以外は 1 倍速で再生する。
    nginx が台を外している時間は、台が落ちた時刻から fail_timeout の 10 秒とする（設定からの値で、実測ではない）。
    """
    S = 2
    W, H = 1200, 630
    font = lambda n: ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", n * S)  # noqa: E731
    data = {m: load(m) for m, _ in MODES}
    t_start, t_end, step = 1.5, 13.5, 0.5
    FAIL_TIMEOUT = 10.0
    x0, x1 = 300, 1150
    X = lambda sec: (x0 + (x1 - x0) * sec / 14.0) * S  # noqa: E731

    def alive(res, t):
        state = [True] * 8
        for at, i, kind in res["events"]:
            if at <= t:
                state[i] = kind == "up"
        return state

    def excluded(res, t):
        out = [False] * 8
        for at, i, kind in res["events"]:
            if kind == "down" and at <= t < at + FAIL_TIMEOUT:
                out[i] = True
        return out

    def fail_rate(res, a, b):
        rec = [r for r in res["records"] if a <= r[0] < b]
        return (sum(1 for r in rec if r[2] != 200) / len(rec)) if rec else 0.0

    frames = []
    t = t_start
    while t <= t_end + 1e-9:
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((40 * S, 22 * S), "ポイズンピルの後の 8 台と、失敗した要求の割合（2〜5 秒は 0.5 倍速、他は 1 倍速）", font=font(22), fill=INK)
        d.text((40 * S, 60 * S), f"経過 {t:4.1f} 秒", font=font(22), fill=INK)
        # 時間の帯
        d.rectangle([X(0), 66 * S, X(14), 82 * S], fill=FILL, outline=LINE)
        d.rectangle([X(0), 66 * S, X(t), 82 * S], fill=ACCENT)
        for sec in range(0, 15, 2):
            d.text((X(sec) - 6 * S, 86 * S), f"{sec}", font=font(14), fill=SUB)
        d.line([X(2.0), 60 * S, X(2.0), 88 * S], fill=RED, width=3 * S)
        y = 130
        for mode, label in MODES:
            res = data[mode]
            st = alive(res, t)
            ex = excluded(res, t)
            d.text((40 * S, (y + 22) * S), label, font=font(20), fill=INK)
            x = x0
            for i in range(8):
                if mode == "cells" and i % 2 == 0 and i:
                    x += 16
                ok = st[i]
                if not ok:
                    d.rounded_rectangle([x * S, y * S, (x + 50) * S, (y + 50) * S], radius=6 * S,
                                        fill=RED, outline=RED, width=2 * S)
                    d.text(((x + 25) * S, (y + 25) * S), f":{run.PORTS[i]}", font=font(13), anchor="mm", fill="#ffffff")
                elif ex[i]:
                    d.rounded_rectangle([x * S, y * S, (x + 50) * S, (y + 50) * S], radius=6 * S,
                                        fill=RED_PALE, outline=RED, width=2 * S)
                    d.text(((x + 25) * S, (y + 17) * S), f":{run.PORTS[i]}", font=font(13), anchor="mm", fill=RED)
                    d.text(((x + 25) * S, (y + 35) * S), "外す", font=font(12), anchor="mm", fill=RED)
                else:
                    d.rounded_rectangle([x * S, y * S, (x + 50) * S, (y + 50) * S], radius=6 * S,
                                        fill=FILL, outline=LINE, width=2 * S)
                    d.text(((x + 25) * S, (y + 25) * S), f":{run.PORTS[i]}", font=font(13), anchor="mm", fill=SUB)
                x += 58
            r = fail_rate(res, t - step, t) if t > 0 else 0.0
            bx = x0 + 8 * 58 + 16 * 3 + 40
            d.text((bx * S, (y - 4) * S), "直前 0.5 秒に失敗した要求", font=font(13), fill=SUB)
            d.rectangle([bx * S, (y + 20) * S, (bx + 180) * S, (y + 44) * S], outline=LINE, width=S)
            d.rectangle([bx * S, (y + 20) * S, (bx + 180 * r) * S, (y + 44) * S], fill=RED)
            d.text(((bx + 190) * S, (y + 18) * S), f"{r:.0%}", font=font(18), fill=RED if r else INK)
            y += 105
        d.text((40 * S, (H - 62) * S), "濃い赤は落ちている台。薄い赤の「外す」は、起動し直したが nginx が使わない台（落ちてから fail_timeout の 10 秒）",
               font=font(15), fill=SUB)
        d.text((40 * S, (H - 36) * S), "2 秒目に c007 がポイズンピルを 1 回送り、落ちた台は 2 秒後に起動し直す", font=font(15), fill=SUB)
        frames.append(im.resize((W, H), Image.LANCZOS))
        t += step
    times = [t_start + step * k for k in range(len(frames))]
    durations = [1000 if 2.0 < tt <= 5.0 + 1e-9 else 500 for tt in times[:-1]] + [3000]
    frames[0].save(HERE / "images" / "cell_timeline.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=80, method=6)


def remap_figure():
    """セルを 4 → 5 にした時、先頭の 100 人のうち誰がセルを移るか。"""
    cust = remap.CUSTOMERS[:100]
    r4, r5 = remap.ring(4), remap.ring(5)
    panels = [
        ("剰余（hash % セルの数）", [remap.modulo(c, 4) != remap.modulo(c, 5) for c in cust]),
        ("コンシステントハッシュ法", [r4(c) != r5(c) for c in cust]),
        ("割り当て表", [False for _ in cust]),
    ]
    s = Svg(1200, 470)
    for k, (title, moved) in enumerate(panels):
        ox = 50 + 390 * k
        s.text(ox + 160, 45, title, 21)
        for i, m in enumerate(moved):
            x, y = ox + 30 * (i % 10) + 15, 75 + 30 * (i // 10)
            s.box(x, y, 24, 24, RED if m else FILL, RED if m else LINE, sw=1.5, rx=4)
        s.text(ox + 160, 410, f"先頭の 100 人では {sum(moved)} 人", 20, RED if sum(moved) else INK)
    s.text(600, 455, "マス 1 つが顧客 1 人（10,000 人の先頭 100 人）。赤は、セルを 4 つから 5 つにした時に別のセルへ移る顧客", 16, SUB)
    s.save_webp("cell_remap.webp")


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    poison_figure()
    structure_figure()
    timeline_figure()
    remap_figure()
