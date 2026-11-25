"""WAL のノートの図を作る（WebP）。

kill_figure()      lab/killtest_output.txt から、設定ごとの 1 秒あたりのコミット数と、止めた後に消えた行数。
layers_figure()    コミットの記録が通る 3 つの置き場と、設定ごとに成功を返す位置、障害ごとに消える範囲。
async_animation()  lab/killtest_async_timeline.json の実測の時刻で、成功が返った行と OS に渡した行を動かす。
group_animation()  グループコミットで、fsync を待つグループと次の fsync に乗るグループが入れ替わる様子（推測した仕組みの模式図）。
group_figure()     lab/groupcommit_output.txt から、同時に送る数とコミット数・fsync の回数。
slot_figure()      lab/slot_output.txt・slot_cap_output.txt から、書いた WAL の量と pg_wal の大きさ。
positions_figure() 1 本のログの上の 3 つの位置（消して良い位置・見せて良い位置・末尾）。
leader_change_figure() Leader の交代で、High-Water Mark より後ろの記録が残るか消えるか。

再生成: python3 content/notes/distributed-systems/write-ahead-log/figures.py
"""

import json
import re
import statistics
import subprocess
import tempfile
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMG = HERE / "images"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#4e79a7", "#e15759"
FILL, PALE, RED_PALE = "#f2f2f2", "#eaf1f5", "#fbe3e3"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Noto Sans CJK JP',sans-serif"
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def _style():
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff"})


def _save(fig, name):
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)
    plt.close(fig)


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=20, color=INK, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                          f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=3, arrow=False, dash=""):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                          f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save_webp(self, name):
        """SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def _kill_runs():
    runs = {}
    for ln in (LAB / "killtest_output.txt").read_text().splitlines():
        m = re.match(r"setting=(\S+) acked=(\d+) survived=(\d+) lost=(\d+) last_ack_ms=(\d+)", ln)
        if m:
            runs.setdefault(m.group(1), []).append(
                (int(m.group(2)), int(m.group(4)), int(m.group(5))))
    return runs


def kill_figure():
    runs = _kill_runs()
    order = [("default", "既定\n（両方 on）"), ("synchronous_commit=off", "synchronous_commit\n= off"),
             ("fsync=off", "fsync\n= off")]
    _style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.2, 3.2), gridspec_kw={"width_ratios": [1, 1.15]})
    ys = [2, 1, 0]
    rates = [statistics.median(a / ms * 1000 for a, _, ms in runs[k]) for k, _ in order]
    a1.barh(ys, rates, height=0.5, color=[SUB, ACCENT, ACCENT])
    for y, r in zip(ys, rates):
        a1.text(r + 300, y, f"{r:,.0f}", va="center", fontsize=9.5)
    a1.set_yticks(ys, [lbl for _, lbl in order])
    a1.set_xlim(0, 22000)
    a1.set_xlabel("1 秒あたりに成功が返った INSERT（5 回の中央値）")
    a1.spines[["top", "right"]].set_visible(False)
    for y, (k, _) in zip(ys, order):
        lost = [lo for _, lo, _ in runs[k]]
        a2.scatter(lost, [y] * len(lost), s=46, color=RED if max(lost) else INK, zorder=3)
        if max(lost) == 0:
            a2.text(300, y + 0.22, "5 回とも 0 行", fontsize=9.5)
        else:
            a2.text(300, y + 0.22, f"5 回とも消えた（{min(lost):,}〜{max(lost):,} 行）", fontsize=9.5, color=RED)
    a2.set_yticks(ys, ["", "", ""])
    a2.set_ylim(-0.5, 2.6)
    a1.set_ylim(-0.5, 2.6)
    a2.set_xlim(-200, 7000)
    a2.set_xlabel("docker kill の後に消えていた、成功が返った行")
    a2.spines[["top", "right"]].set_visible(False)
    a2.grid(axis="x", color="#e5e5e5")
    _save(fig, "wal_kill_result.webp")


def layers_figure():
    s = Svg(1040, 440, "コミットの記録が通る 3 つの置き場")
    cols = [(40, "PostgreSQL のメモリ", "WAL バッファ"), (380, "OS のメモリ", "ページキャッシュ"),
            (720, "ディスク", "WAL のファイル")]
    for x, top, name in cols:
        s.box(x, 60, 280, 130, PALE if x < 700 else FILL, INK)
        s.text(x + 140, 105, top, 20, SUB)
        s.text(x + 140, 150, name, 24)
    s.line(320, 125, 376, 125, arrow=True)
    s.text(348, 108, "write", 16, SUB)
    s.line(660, 125, 716, 125, arrow=True)
    s.text(688, 108, "fsync", 16, SUB)
    s.text(40, 36, "成功を返す時に、コミットの記録がある所", 18, SUB, "start")
    # 設定ごとに成功を返す位置
    for label, cx in [("synchronous_commit = off", 180), ("fsync = off", 520), ("既定（両方 on）", 860)]:
        s.line(cx, 194, cx, 222, SUB, 1.5, dash="3,4")
        s.box(cx - 135, 226, 270, 76, "#ffffff", ACCENT, 2, rx=14)
        s.text(cx, 258, label, 17, ACCENT)
        s.text(cx, 286, "ここまで届いたら成功を返す", 15, ACCENT)
    # 障害ごとに消える範囲
    s.box(40, 330, 280, 46, RED_PALE, RED, 2, rx=8)
    s.text(180, 360, "PostgreSQL が落ちると消える", 17, RED)
    s.box(40, 384, 620, 46, RED_PALE, RED, 2, dash="6,5", rx=8)
    s.text(350, 414, "OS が落ちる・電源が切れると消える", 17, RED)
    s.box(720, 330, 280, 100, "#ffffff", INK, 2, rx=8)
    s.text(860, 374, "どちらでも残る", 17)
    s.text(860, 402, "ディスク自体が壊れない限り", 14, SUB)
    s.save_webp("wal_layers.webp")


def _lsn(x):
    hi, lo = x.split("/")
    return (int(hi, 16) << 32) + int(lo, 16)


def async_animation():
    r = json.loads((LAB / "killtest_async_timeline.json").read_text())
    acks = [(a["at_ms"], a["id"], _lsn(a["lsn"])) for a in r["acks"]]
    polls = [(p["at_ms"], _lsn(p["write_lsn"])) for p in r["polls"]]
    end = acks[-1][0]
    window = 1000.0
    t0 = end - window
    id0 = max(i for t, i, _ in acks if t <= t0)
    id1 = acks[-1][1]
    survived_last = r["lost_first_id"] - 1
    speed = 0.2
    S = 2
    W, H = 900, 370
    font = lambda n: ImageFont.truetype(CJK, n * S)  # noqa: E731
    X0, X1 = 60, 840

    def X(i):
        return (X0 + (X1 - X0) * max(0, i - id0) / (id1 - id0)) * S

    def state(t):
        acked = max([i for tt, i, _ in acks if tt <= t] or [id0])
        wl = max([w for tt, w in polls if tt <= t] or [polls[0][1]])
        written = max([i for _, i, lsn in acks if lsn <= wl] or [id0])
        return acked, written

    frames, durs = [], []
    step = 20.0  # ms（実時間）
    t = t0
    while t <= end + 0.01:
        frames.append(("run", t))
        durs.append(int(step / speed))
        t += step
    frames.append(("kill", end))
    durs.append(3500)
    imgs = []
    for kind, t in frames:
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((20 * S, 14 * S), "synchronous_commit = off で 1 行ずつ INSERT し、docker kill で止める",
               font=font(19), fill=INK)
        left = end - t
        d.text((20 * S, 46 * S), f"止める {left:5.0f} ms 前（実測の時刻を {speed} 倍速で再生）"
               if kind == "run" else "止めた後（起動し直して数えた）", font=font(16), fill=SUB)
        # 時間の帯
        d.rectangle([X0 * S, 78 * S, X1 * S, 86 * S], fill=FILL)
        d.rectangle([X0 * S, 78 * S, (X0 + (X1 - X0) * (t - t0) / window) * S, 86 * S], fill=SUB)
        acked, written = state(t)
        rows = [("成功が返った行", 120, acked, ACCENT), ("OS に渡した行", 210, written, INK)]
        for label, y, upto, color in rows:
            d.text((X0 * S, (y - 4) * S), label, font=font(17), fill=INK)
            d.rectangle([X0 * S, (y + 24) * S, X1 * S, (y + 54) * S], outline="#cccccc", width=S)
            if kind == "kill" and label.startswith("成功"):
                d.rectangle([X0 * S, (y + 24) * S, X(survived_last), (y + 54) * S], fill=color)
                d.rectangle([X(survived_last), (y + 24) * S, X(id1), (y + 54) * S], fill=RED_PALE,
                            outline=RED, width=S)
            else:
                d.rectangle([X0 * S, (y + 24) * S, X(upto), (y + 54) * S], fill=color)
        if kind == "kill":
            lost = id1 - survived_last
            d.text((X0 * S, 300 * S),
                   f"成功が返ったのに消えた {lost:,} 行", font=font(18), fill=RED)
            d.text((X0 * S, 330 * S), "消えた行は、OS に渡した位置より後ろの行と一致した",
                   font=font(16), fill=SUB)
        else:
            gap = acked - written
            d.text((X0 * S, 300 * S), f"成功を返したが、まだ PostgreSQL のメモリにしか無い行: {gap:,}",
                   font=font(16), fill=RED if gap else SUB)
        d.text((X0 * S, 268 * S), f"行番号 {id0:,}", font=font(13), fill=SUB)
        d.text(((X1 - 110) * S, 268 * S), f"行番号 {id1:,}", font=font(13), fill=SUB)
        imgs.append(im.resize((W, H), Image.LANCZOS))
    imgs[0].save(IMG / "wal_async_loss.webp", "WEBP", save_all=True, append_images=imgs[1:],
                 duration=durs, loop=0, quality=80, method=6)


def group_animation():
    """8 クライアントが 2 つのグループに分かれ、交互に fsync に乗る様子。時刻は持たない模式図で、1 コマずつ秒で表示する。"""
    S = 2
    W, H = 900, 470
    font = lambda n: ImageFont.truetype(CJK, n * S)  # noqa: E731
    A, B = range(1, 5), range(5, 9)
    # (fsync の番号, その fsync に乗るグループ, 成功を返したグループ, 待つグループ, 説明)
    frames = [
        (1, A, None, B, "クライアント 1〜4 の記録を乗せて fsync #1 が始まる。5〜8 はその後に記録を書き、待つ"),
        (2, B, A, None, "fsync #1 が終わり、1〜4 に成功を返す。待っていた 5〜8 の記録で fsync #2 が始まる"),
        (2, B, None, A, "1〜4 は次の記録を書くが、fsync #2 はもう始まっているので、次の fsync を待つ"),
        (3, A, B, None, "fsync #2 が終わり、5〜8 に成功を返す。待っていた 1〜4 の記録で fsync #3 が始まる"),
        (3, A, None, B, "5〜8 は次の記録を書き、次の fsync を待つ"),
        (4, B, A, None, "fsync #3 が終わり、1〜4 に成功を返す。待っていた 5〜8 の記録で fsync #4 が始まる"),
        (4, B, None, A, "1〜4 は次の記録を書き、次の fsync を待つ"),
        (None, None, B, A, "fsync #4 が終わり、5〜8 に成功を返す。1 回の fsync に乗るのは、いつも 8 クライアントの半分"),
    ]
    per = 1.6
    durs = [int(per * 1000)] * (len(frames) - 1) + [3500]
    imgs = []
    done_k, done_c = 0, 0
    carried = {}
    for k, cur, acked, wait, text in frames:
        if acked is not None:
            done_k += 1
            done_c += 4
        if k is not None:
            carried[k] = cur
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((20 * S, 14 * S), "8 クライアントが同時にコミットする時のグループコミット（推測した仕組みの模式図）",
               font=font(18), fill=INK)
        d.text((20 * S, 44 * S), f"1 コマ {per} 秒で表示", font=font(14), fill=SUB)
        # fsync の帯（時間の流れ）
        for i in range(1, 5):
            x = 40 + (i - 1) * 205
            on = k == i
            past = i in carried and (k is None or i < k)
            fill = PALE if on else (FILL if past else "#ffffff")
            d.rectangle([x * S, 76 * S, (x + 190) * S, 112 * S], fill=fill,
                        outline=ACCENT if on else "#cccccc", width=S * (2 if on else 1))
            lab = f"fsync #{i}"
            if i in carried:
                g = carried[i]
                lab += f"：{g[0]}〜{g[-1]} の記録"
            d.text(((x + 10) * S, 83 * S), lab, font=font(15), fill=INK if (on or past) else "#bbbbbb")
        # 時間の向きは fsync の並びにだけ掛かるので、その真上に置く
        d.line([40 * S, 68 * S, 840 * S, 68 * S], fill=SUB, width=S)
        d.polygon([(846 * S, 68 * S), (836 * S, 63 * S), (836 * S, 73 * S)], fill=SUB)
        d.text((790 * S, 46 * S), "時間", font=font(13), fill=SUB)
        # クライアントの行
        for c in range(1, 9):
            y = 146 + (c - 1) * 30
            d.text((40 * S, y * S), f"クライアント {c}", font=font(15), fill=INK)
            if cur is not None and c in cur:
                st, fill, edge = "記録が fsync でディスクへ向かう", PALE, ACCENT
            elif acked is not None and c in acked:
                st, fill, edge = "成功が返る", "#e3f0e5", "#59a14f"
            elif wait is not None and c in wait:
                st, fill, edge = "記録を書いて、次の fsync を待つ", OCHRE_PALE, OCHRE
            else:
                st, fill, edge = "", "#ffffff", "#ffffff"
            if st:
                d.rectangle([180 * S, (y - 2) * S, 520 * S, (y + 24) * S], fill=fill, outline=edge, width=S)
                d.text((192 * S, y * S), st, font=font(14), fill=INK)
        d.text((560 * S, 160 * S), f"終わった fsync: {done_k} 回", font=font(16), fill=INK)
        d.text((560 * S, 192 * S), f"成功を返したコミット: {done_c} 件", font=font(16), fill=INK)
        if done_k:
            d.text((560 * S, 224 * S), f"fsync 1 回あたり: {done_c / done_k:.0f} 件", font=font(16), fill=ACCENT)
        d.text((40 * S, 400 * S), text, font=font(15), fill=INK)
        imgs.append(im.resize((W, H), Image.LANCZOS))
    imgs[0].save(IMG / "wal_group_commit_cycle.webp", "WEBP", save_all=True, append_images=imgs[1:],
                 duration=durs, loop=0, quality=80, method=6)


def _group_blocks():
    blocks, cur = {}, None
    for ln in (LAB / "groupcommit_output.txt").read_text().splitlines():
        if ln.startswith("# PGOPTIONS="):
            cur = "off" if "synchronous_commit=off" in ln else "on"
            blocks[cur] = []
            continue
        p = ln.split()
        if cur and len(p) == 6 and p[0].isdigit():
            blocks[cur].append(tuple(float(v) for v in p))
    return blocks


def group_figure():
    blocks = _group_blocks()
    rows, off = blocks["on"], blocks["off"]
    n = [r[0] for r in rows]
    _style()
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.plot(n, [r[2] for r in off], marker="^", color=SUB, ls="--", label="1 秒あたりのコミット（synchronous_commit = off）")
    ax.plot(n, [r[2] for r in rows], marker="o", color=ACCENT, label="1 秒あたりのコミット（既定）")
    ax.plot(n, [r[4] for r in rows], marker="s", color=INK, label="1 秒あたりの WAL の fsync（既定）")
    for r in rows:
        ax.text(r[0], r[2] * 0.62, f"{r[5]:.0f}" if r[5] >= 2 else f"{r[5]:.1f}", ha="center",
                fontsize=8.5, color=ACCENT)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(n, [f"{int(v)}" for v in n])
    ax.set_ylim(300, 2000000)
    ax.set_xlabel("同時に INSERT を送るクライアントの数（青い数字は既定での fsync 1 回あたりのコミット）")
    ax.set_ylabel("回数（対数）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    _save(fig, "wal_group_commit.webp")


def _slot_series(path, mode):
    xs, ys = [], []
    for ln in (LAB / path).read_text().splitlines():
        m = re.match(rf"{mode} step=(\d+) written_mb=([\d.]+) pg_wal_mb=([\d.]+)", ln)
        if m:
            xs.append(float(m.group(2)))
            ys.append(float(m.group(3)))
    return xs, ys


def slot_figure():
    _style()
    fig, ax = plt.subplots(figsize=(7.4, 3.5))
    x, y = _slot_series("slot_output.txt", "slot")
    ax.plot(x, y, marker="o", color=RED, label="使われていない slot がある")
    x, y = _slot_series("slot_cap_output.txt", "cap")
    ax.plot(x, y, marker="^", color=OCHRE, label="同じ slot と max_slot_wal_keep_size = 256MB")
    ax.annotate("slot が lost になる", xy=(x[4], y[4]), xytext=(x[4] + 40, y[4] + 120),
                arrowprops=dict(arrowstyle="->", color=OCHRE), color=OCHRE, fontsize=9)
    x, y = _slot_series("slot_output.txt", "no_slot")
    ax.plot(x, y, marker="s", color=INK, label="slot が無い")
    ax.set_xlabel("書いた WAL の量（MB）。1 段ごとに 20 万行を足して CHECKPOINT")
    ax.set_ylabel("pg_wal の大きさ（MB）")
    ax.set_xlim(-10, 700)
    ax.set_ylim(0, 720)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    _save(fig, "wal_slot.webp")


def positions_figure():
    s = Svg(1040, 290, "1 本のログの上の 3 つの位置")
    x0, x1, y = 60, 940, 150
    lw, hw = x0 + 220, x0 + 600
    s.box(x0, y, lw - x0, 56, FILL, "#999999", 1.5, rx=4)
    s.box(lw, y, hw - lw, 56, PALE, "#999999", 1.5, rx=0)
    s.box(hw, y, x1 - hw, 56, OCHRE_PALE, "#999999", 1.5, rx=4)
    s.text((x0 + lw) / 2, y + 35, "消して良い", 16, SUB)
    s.text((lw + hw) / 2, y + 35, "確定した。成功を返した記録はここに入る", 16)
    s.text((hw + x1) / 2, y + 35, "まだ確定していない。見せない", 16)
    marks = [(lw, "Low-Water Mark", "ここより前は消して良い", RED),
             (hw, "High-Water Mark", "確定した最後の位置", ACCENT),
             (x1, "末尾", "最後に追記した位置", INK)]
    for x, name, desc, color in marks:
        s.line(x, y - 40, x, y + 70, color, 3)
        s.text(x, y - 74, name, 18)
        s.text(x, y - 50, desc, 14, SUB)
    s.text(x0, y + 108, "古い", 15, SUB, "start")
    s.text(x1, y + 108, "新しい", 15, SUB, "end")
    s.line(x0 + 50, y + 103, x1 - 60, y + 103, SUB, 1.5, arrow=True)
    s.save_webp("wal_positions.webp")


def leader_change_figure():
    """High-Water Mark より後ろの記録は、新しい Leader が持っていれば残る。"""
    s = Svg(960, 520, "Leader の交代で High-Water Mark より後ろの記録がどうなるか")
    cell, x0 = 104, 300
    idx = [40, 41, 42, 43, 44, 45]
    rows = [(70, "旧 Leader", 6), (210, "新 Leader", 4)]
    for y, name, n in rows:
        s.text(40, y + (48 if n == 6 else 34), name, 24, anchor="start")
        for i in range(n):
            v = idx[i]
            if v <= 42:
                fill, stroke = FILL, SUB
            elif v == 43:
                fill, stroke = PALE, ACCENT
            else:
                fill, stroke = OCHRE_PALE, OCHRE
            s.box(x0 + i * cell, y, cell - 12, 76, fill, stroke)
            s.text(x0 + i * cell + (cell - 12) / 2, y + 48, str(v), 24)
    s.text(40, 274, "（元 Follower）", 20, SUB, anchor="start")
    hx = x0 + 3 * cell - 6
    s.line(hx, 40, hx, 320, INK, 5)
    s.text(hx, 30, "High-Water Mark = 42", 20)
    s.box(40, 380, 420, 110, PALE, ACCENT, sw=3)
    s.text(250, 428, "43 は新 Leader にある", 22)
    s.text(250, 464, "後から確定する", 20, SUB)
    s.box(500, 380, 420, 110, OCHRE_PALE, OCHRE, sw=3)
    s.text(710, 428, "44・45 は新 Leader に無い", 22)
    s.text(710, 464, "上書きされて消える", 20, SUB)
    s.save_webp("wal_leader_change.webp")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    kill_figure()
    layers_figure()
    async_animation()
    group_animation()
    group_figure()
    slot_figure()
    positions_figure()
    leader_change_figure()
