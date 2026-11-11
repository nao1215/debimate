"""Generate the figures of the Sidecar note (WebP).

concept_figure() draws one execution unit (Pod / Task). The main container
and the sidecar overlap: what they share (volume and network) sits in the
overlap, and what each keeps for itself (image and resource limit) appears
once on each side. The Ambassador and Adapter notes use the same frame.

jobs_figure() reads the timestamps in lab/output.txt.

Run: python3 content/notes/software-architecture/sidecar/figures.py
"""

import re
import subprocess
import tempfile
from datetime import datetime
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=4, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def db(self, cx, top, w, h, fill, stroke):
        rx, ry = w / 2, 10
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')

    def save_webp(self, name, width, height):
        """SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={width},{height}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "同じ実行単位の main と sidecar が共有するものと分けるもの")

    # The execution unit (Pod / Task).
    f.box(180, 40, 560, 470, FILL, SUB, sw=2.5, dash="10 7", rx=24)
    f.text(204, 82, "実行単位（Pod）", 26, SUB, "normal", "start")

    # Two containers overlapping in the middle, shifted vertically so the
    # overlap reads as the intersection of two boxes, not a third box.
    w, h = 340, 360
    main_x, main_y, side_x, side_y = 200, 100, 380, 140  # overlap: 380..540
    for x, y, fill in ((main_x, main_y, PALE), (side_x, side_y, OCHRE_PALE)):
        f.box(x, y, w, h, fill, INK, sw=0, rx=18)
    # Shared area: the intersection of the two containers.
    f.box(side_x, side_y, main_x + w - side_x, main_y + h - side_y, "#ffffff", ACCENT, sw=0, rx=0)
    for x, y, stroke in ((main_x, main_y, ACCENT), (side_x, side_y, OCHRE)):
        f.box(x, y, w, h, "none", stroke, sw=3, rx=18)

    f.text(290, 142, "main", 28, weight="normal")
    f.text(290, 178, "Web サーバー", 24, SUB)
    f.text(630, 190, "sidecar", 28, weight="normal")
    f.text(630, 226, "log-shipper", 24, SUB)

    # Shared: volume and network.
    f.text(460, 186, "共有", 26, INK, "normal")
    f.db(460, 230, 110, 60, FILL, INK)
    f.text(460, 276, "volume", 24)
    f.box(388, 326, 144, 56, FILL, INK, rx=8)
    f.text(460, 362, "ネットワーク", 19)
    f.text(460, 438, "1 つずつ", 24, INK, "normal")

    # Kept per container: image and resource limit.
    for cx, y in ((290, 240), (630, 280)):
        f.box(cx - 75, y, 150, 52, "#ffffff", SUB, sw=2)
        f.text(cx, y + 35, "イメージ", 24, SUB)
        f.box(cx - 75, y + 68, 150, 52, "#ffffff", SUB, sw=2)
        f.text(cx, y + 103, "資源の上限", 24, SUB)
        f.text(cx, y + 168, "別々", 24, SUB, "normal")

    # Outside: the client calls main, the sidecar sends logs out.
    f.box(6, 175, 160, 70, "#ffffff", INK, sw=2.5)
    f.text(86, 219, "クライアント", 24)
    f.line(168, 210, 214, 210, INK, 4, arrow=True)
    f.db(860, 230, 150, 80, "#ffffff", INK)
    f.text(860, 290, "ストレージ", 24)
    f.line(706, 265, 768, 265, INK, 4, arrow=True)

    f.save_webp("sidecar_concept.webp", 960, 540)


def _ts(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00"))


def _style():
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff"})


def _save(fig, name):
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def jobs_figure():
    """lab/output.txt の時刻から、3 つの Job で main と sidecar がいつ終わり、Job がいつ完了したかを並べる。"""
    out = (HERE / "lab" / "output.txt").read_text()
    blk1 = out.split("== 1.")[1].split("== 2.")[0]
    s0 = _ts(re.search(r"start: (\S+)", blk1).group(1))
    main1 = (_ts(re.search(r'main: \{"terminated".*?"finishedAt":"([^"]+)"', blk1).group(1)) - s0).seconds
    rows = [(main1, None, None, None)]
    for job in ("job-native", "job-native-term"):
        blk = out.split(f"（{job}）")[1]
        js = re.search(r"start: (\S+)\s+completion: (\S+)", blk)
        me = re.search(r"main: finished (\S+)", blk).group(1)
        se = re.search(r"log-shipper: finished (\S+) exit (\d+)", blk)
        st = _ts(js.group(1))
        rows.append(((_ts(me) - st).seconds, (_ts(se.group(1)) - st).seconds,
                     (_ts(js.group(2)) - st).seconds, se.group(2)))
    _style()
    fig, ax = plt.subplots(figsize=(7.6, 3.3))
    labels = ["普通のコンテナとして同居", "Sidecar Containers\n（SIGTERM を無視）", "Sidecar Containers\n（SIGTERM で止まる）"]
    for i, r in enumerate(rows):
        y = 2 - i
        ax.barh(y + 0.17, r[0], height=0.3, color=ACCENT, label="main（処理）" if i == 0 else None)
        if i == 0:
            ax.barh(y - 0.17, 30, height=0.3, color=OCHRE, label="log-shipper（sidecar）")
            ax.annotate("", xy=(40, y - 0.17), xytext=(30, y - 0.17),
                        arrowprops=dict(arrowstyle="->", color=OCHRE, lw=2, ls="--"))
            ax.text(41, y, "30 秒後も動いていて、\nJob は未完了のまま", va="center", fontsize=8.5, color=RED)
        else:
            ax.barh(y - 0.17, r[1], height=0.3, color=OCHRE)
            ax.plot([r[2]], [y], marker="v", color=INK, ms=8)
            ax.text(r[2] + 1, y + 0.05, f"Job 完了 {r[2]} 秒（exit {r[3]}）", va="center", fontsize=8.5)
    ax.set_yticks([2, 1, 0], labels)
    ax.set_xlim(0, 60)
    ax.set_xlabel("Job の開始からの秒数")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    _save(fig, "sidecar_jobs.webp")


def startup_figure():
    """プロキシを普通のコンテナとして並べた場合と、Sidecar Containers にした場合の起動を、実測の時刻で動かす（動く WebP）。"""
    from PIL import ImageDraw, ImageFont
    out = (HERE / "lab" / "output.txt").read_text()
    b3 = out.split("== 3.")[1].split("== 4.")[0]
    b4 = out.split("== 4.")[1]
    c3 = _ts(re.search(r"pod created (\S+)", b3).group(1))
    m3 = re.search(r"main last started (\S+) last finished (\S+) now started (\S+)", b3)
    p3 = _ts(re.search(r"proxy last started\s+last finished\s+now started (\S+)", b3).group(1))
    c4 = _ts(re.search(r"pod created (\S+)", b4).group(1))
    p4 = _ts(re.search(r"proxy started (\S+)", b4).group(1))
    m4 = _ts(re.search(r"main started (\S+)", b4).group(1))
    t = lambda a, c: (a - c).total_seconds()  # noqa: E731
    LISTEN = 3  # プロキシは起動から 3 秒後に待ち受ける（マニフェストの sleep 3）
    lanes = [
        {"title": "普通のコンテナとして並べる", "proxy": t(p3, c3),
         "fails": [0.0, t(_ts(m3.group(1)), c3)], "ok": t(_ts(m3.group(3)), c3), "wait": True},
        {"title": "Sidecar Containers ＋ startupProbe", "proxy": t(p4, c4),
         "fails": [], "ok": t(m4, c4), "wait": False},
    ]
    T, STEP, SPEED = 20.0, 0.5, 2.0
    S = 2
    W, H = 960, 430
    font = lambda n: ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", n * S)  # noqa: E731
    x0, x1 = 300, 920
    X = lambda sec: (x0 + (x1 - x0) * sec / T) * S  # noqa: E731
    frames = []
    n = int(T / STEP) + 1
    for k in range(n):
        now = k * STEP
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((20 * S, 14 * S), "Pod を作ってから、main がプロキシに繋がるまで", font=font(20), fill=INK)
        d.text((20 * S, 44 * S), f"経過 {now:4.1f} 秒（{SPEED:.0f} 倍速。開始と接続は実測、待ち受けは sleep 3 から計算）", font=font(16), fill=SUB)
        # 時間の帯
        d.line([(X(0), 380 * S), (X(T), 380 * S)], fill=SUB, width=2 * S)
        for sec in range(0, 21, 5):
            d.line([(X(sec), 375 * S), (X(sec), 385 * S)], fill=SUB, width=2 * S)
            d.text((X(sec) - 8 * S, 390 * S), f"{sec}", font=font(14), fill=SUB)
        d.text((X(T) - 30 * S, 405 * S), "秒", font=font(14), fill=SUB)
        for li, ln in enumerate(lanes):
            y = 110 + li * 135
            d.text((20 * S, (y - 30) * S), ln["title"], font=font(17), fill=INK)
            d.text((230 * S, (y + 2) * S), "proxy", font=font(15), fill=SUB)
            d.text((230 * S, (y + 52) * S), "main", font=font(15), fill=SUB)
            # proxy の帯: 起動前は無し、準備中は灰、待ち受け中は黄
            ps = ln["proxy"]
            if now > ps:
                d.rectangle([X(ps), (y) * S, X(min(now, ps + LISTEN)), (y + 26) * S], fill="#e6e6e6", outline=SUB)
            if now > ps + LISTEN:
                d.rectangle([X(ps + LISTEN), y * S, X(now), (y + 26) * S], fill=OCHRE)
                d.text((X(ps + LISTEN) + 6 * S, (y + 1) * S), "待ち受け中", font=font(14), fill=INK)
            elif now > ps:
                d.text((X(ps) + 4 * S, (y + 1) * S), "準備中", font=font(14), fill=INK)
            # main の出来事
            my = y + 50
            for f in ln["fails"]:
                if now >= f:
                    cx = X(f) + 8 * S
                    d.line([(cx - 9 * S, (my + 4) * S), (cx + 9 * S, (my + 22) * S)], fill=RED, width=4 * S)
                    d.line([(cx - 9 * S, (my + 22) * S), (cx + 9 * S, (my + 4) * S)], fill=RED, width=4 * S)
            if ln["wait"] and ln["fails"] and now > ln["fails"][-1] + 0.5:
                end = min(now, ln["ok"])
                xs = X(ln["fails"][-1]) + 20 * S
                xx = xs
                while xx < X(end):
                    d.line([(xx, (my + 13) * S), (min(xx + 8 * S, X(end)), (my + 13) * S)], fill=RED, width=2 * S)
                    xx += 14 * S
                if now < ln["ok"]:
                    d.text((xs, (my + 30) * S), "接続を拒否されて落ち、再起動を待たされている（back-off）", font=font(14), fill=RED)
            if not ln["wait"] and now < ln["ok"] and now > ps:
                d.text((X(ps) + 4 * S, (my + 2) * S), "startupProbe が通るまで起動しない", font=font(14), fill=SUB)
            if now >= ln["ok"]:
                d.rectangle([X(ln["ok"]), my * S, X(now) if now > ln["ok"] else X(ln["ok"]) + 2 * S, (my + 26) * S], fill=ACCENT)
                d.text((X(ln["ok"]) + 6 * S, (my + 30) * S), f"{ln['ok']:.0f} 秒で接続", font=font(14), fill=INK)
        # 今の時刻の線
        d.line([(X(now), 80 * S), (X(now), 380 * S)], fill=INK, width=2 * S)
        frames.append(im.resize((W, H), Image.LANCZOS))
    dur = int(STEP / SPEED * 1000)
    durations = [dur] * (len(frames) - 1) + [3000]
    frames[0].save(HERE / "images" / "sidecar_startup.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=75, method=6)


def per_node_figure():
    """プロキシを Pod ごとに置く場合と、ノード（マシン）ごとに 1 つ置く場合。"""
    f = Svg(960, 400, "左は Pod 4 つのそれぞれに proxy がある。右は同じ 4 つの Pod が、ノードに 1 つだけ置いた proxy を共有する")

    def node(x0, title, per_pod):
        f.box(x0, 70, 420, 270, FILL, SUB, sw=2.5, dash="10 7", rx=18)
        f.text(x0 + 20, 100, title, 22, SUB, "normal", "start")
        for k in range(4):
            x = x0 + 25 + k * 98
            f.box(x, 120, 88, 120 if per_pod else 70, "#ffffff", ACCENT, sw=2.5, rx=10)
            f.text(x + 44, 150, "Pod", 20)
            f.text(x + 44, 180, "アプリ", 18, SUB)
            if per_pod:
                f.box(x + 8, 196, 72, 36, OCHRE_PALE, OCHRE, sw=2, rx=6)
                f.text(x + 44, 221, "proxy", 18)
        if not per_pod:
            f.box(x0 + 60, 260, 300, 50, OCHRE_PALE, OCHRE, sw=2, rx=8)
            f.text(x0 + 210, 293, "proxy（ノードに 1 つ）", 20)
            for k in range(4):
                f.line(x0 + 69 + k * 98, 190, x0 + 210, 260, SUB, 2)

    node(30, "ノード（マシン）", True)
    node(510, "ノード（マシン）", False)
    f.text(240, 50, "Pod ごとに置く（sidecar）", 22)
    f.text(720, 50, "ノードごとに 1 つ置く", 22)
    f.text(240, 375, "Pod の数だけ proxy が動き、資源を予約する", 18, SUB)
    f.text(720, 375, "proxy は 1 つ。Pod ごとの分離は弱まる", 18, SUB)
    f.save_webp("sidecar_per_node.webp", 960, 400)


if __name__ == "__main__":
    concept_figure()
    jobs_figure()
    startup_figure()
    per_node_figure()
