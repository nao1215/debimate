"""Transactional Outbox のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

図は lab/output/*.json（lab/outbox_lab.py の実験の出力）を読んで描く。環境を変えたら先に
lab の実験を走らせ直す。matplotlib の図は PNG（dpi 200、白背景）を Pillow で WebP にし、
仕組みの図と動く図は Pillow の ImageDraw で 2 倍の大きさに描いてから縮める。

- load_figure(): relay の読み方ごとの送らなかった行の数（表紙）
- crash_figure(): コミットと送信の間で落ちた時に残るもの（3 通りの書き方）
- overtake_animation(): id の順に読む relay が、遅れてコミットした id 1 を飛ばす様子（動く図）
- stall_animation(): トランザクション ID で読む relay が、無関係な長いトランザクションの間は何も送らない様子（動く図）
- ordering_animation(): relay 2 個が 10 行ずつ取り、注文 4 の支払いが確定より先に届く様子（動く図）
- ordering_figure(): relay の数ごとの、順番が入れ替わった注文の数（5 回の中央値と範囲）
- wal_order_figure(): WAL から読んだ順に並べた outbox の id
"""

import io
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
IMG = HERE / "images"
INK, SUB, LINE, FILL = "#1f1f1f", "#666666", "#bdbdbd", "#f2f2f2"
ACCENT, RED, RED_PALE = "#7aa6c2", "#e15759", "#fbe3e3"
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP",
    "font.size": 11,
    "axes.edgecolor": SUB,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": SUB,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
S = 2  # 2 倍で描いてから縮める


def load(name):
    return json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))


def save_plot(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    IMG.mkdir(exist_ok=True)
    Image.open(buf).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, int(size * S))


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


RELAY_NAMES = {"id": "id の順に読む\n（WHERE id > 前回の最大）",
               "flag": "未送信の印で読む\n（published = false）",
               "xmin": "トランザクション ID で読む\n（xid8 と pg_snapshot_xmin）"}


# ---------------------------------------------------------------- 表紙
def load_figure():
    data = load("load")
    works = ["0", "5", "20"]
    xlabels = ["0 ms", "0〜5 ms", "0〜20 ms"]
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    width = 0.26
    colors = {"id": RED, "flag": ACCENT, "xmin": "#9aa5ad"}
    for j, name in enumerate(["id", "flag", "xmin"]):
        for i, w in enumerate(works):
            runs = [r[name]["missed"] for r in data[w]]
            med, lo, hi = statistics.median(runs), min(runs), max(runs)
            x = i + (j - 1) * width
            ax.bar(x, med, width * 0.9, color=colors[name], label=RELAY_NAMES[name].replace("\n", "") if i == 0 else None)
            if hi > lo:
                ax.plot([x, x], [lo, hi], color=INK, lw=1)
            ax.text(x, max(med, hi) + 8, f"{med:g}", ha="center", va="bottom", fontsize=10, color=INK)
    ax.set_xticks(range(3), xlabels)
    ax.set_xlabel("1 件の注文のトランザクションで、INSERT からコミットまでに掛かる処理時間")
    ax.set_ylabel("送られなかった行（4,000 行のうち）")
    ax.set_ylim(0, 470)
    ax.set_title("8 並列で注文 4,000 件を書いた時に relay が送らなかった outbox の行（5 回の中央値と範囲）",
                 fontsize=11, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    save_plot(fig, "outbox_load.webp")


# ---------------------------------------------------------------- 落ちる位置
def crash_figure():
    c = load("crash")
    W, H = 640, 400
    im = Image.new("RGB", (W * S, H * S), "#ffffff")
    d = ImageDraw.Draw(im)

    def box(x, y, w, text, fill=FILL, color=INK):
        d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + 40) * S], radius=6 * S, fill=rgb(fill),
                            outline=rgb(LINE), width=S)
        tw = d.textlength(text, font=font(14))
        d.text(((x + w / 2) * S - tw / 2, (y + 9) * S), text, font=font(14), fill=rgb(color))

    def window(x, y, w):
        d.rectangle([x * S, (y + 6) * S, (x + w) * S, (y + 34) * S], fill=rgb(RED_PALE))
        d.line([(x * S, (y + 20) * S), ((x + w) * S, (y + 20) * S)], fill=rgb(RED), width=2 * S)
        tw = d.textlength("ここで落ちる", font=font(12))
        d.text(((x + w / 2) * S - tw / 2, (y - 14) * S), "ここで落ちる", font=font(12), fill=rgb(RED))

    rows = [
        ("コミットしてから送る", [("注文をコミット", 160), ("ブローカーへ送る", 160)],
         f"注文はあるのに、イベントが届かない（{c['dual_write']['lost']} 件）"),
        ("送ってからコミットする", [("ブローカーへ送る", 160), ("注文をコミット", 160)],
         f"注文が無いのに、イベントが届く（{c['send_first']['ghost']} 件）"),
        ("outbox を使う（relay 側）", [("outbox の行を送る", 160), ("送った印を付ける", 160)],
         f"同じイベントが 2 回届く（{c['outbox']['duplicated']} 件）"),
    ]
    d.text((20 * S, 14 * S), f"アプリケーションを SIGKILL で {c['dual_write']['rounds']} 回止めた時に残ったもの",
           font=font(15), fill=rgb(INK))
    for i, (label, steps, result) in enumerate(rows):
        y = 70 + i * 108
        d.text((20 * S, (y + 9) * S), label, font=font(14), fill=rgb(INK))
        x = 220
        box(x, y, steps[0][1], steps[0][0])
        window(x + steps[0][1] + 6, y, 58)
        box(x + steps[0][1] + 70, y, steps[1][1], steps[1][0])
        d.text((222 * S, (y + 50) * S), "→ " + result, font=font(14), fill=rgb(RED if i < 2 else SUB))
    d.text((20 * S, (H - 34) * S),
           "outbox では、注文と outbox の行を同じトランザクションでコミットするので、片方だけは残らない",
           font=font(12), fill=rgb(SUB))
    IMG.mkdir(exist_ok=True)
    im.resize((W * 3 // 2, H * 3 // 2), Image.LANCZOS).save(IMG / "outbox_crash.webp", "WEBP", quality=90, method=6)


# ---------------------------------------------------------------- 動く図の共通部分
def chip(d, x, y, text, color, dashed=False, fill="#ffffff", w=96):
    if dashed:
        for k in range(0, w, 10):
            d.line([((x + k) * S, y * S), ((x + min(k + 5, w)) * S, y * S)], fill=rgb(color), width=2 * S)
            d.line([((x + k) * S, (y + 30) * S), ((x + min(k + 5, w)) * S, (y + 30) * S)], fill=rgb(color), width=2 * S)
        for k in range(0, 30, 10):
            d.line([(x * S, (y + k) * S), (x * S, (y + min(k + 5, 30)) * S)], fill=rgb(color), width=2 * S)
            d.line([((x + w) * S, (y + k) * S), ((x + w) * S, (y + min(k + 5, 30)) * S)], fill=rgb(color), width=2 * S)
    else:
        d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + 30) * S], radius=5 * S, fill=rgb(fill),
                            outline=rgb(color), width=2 * S)
    tw = d.textlength(text, font=font(14, mono=True))
    d.text(((x + w / 2) * S - tw / 2, (y + 5) * S), text, font=font(14, mono=True), fill=rgb(color))


def clock(d, t, t_end, marks, band=None, speed=0.5, x0=430, x1=880, yb=34):
    d.text((20 * S, 12 * S), f"経過 {t:.1f} 秒", font=font(20), fill=rgb(INK))
    d.text((20 * S, 42 * S), f"実測した時刻を {speed:g} 倍速で再生", font=font(11), fill=rgb(SUB))
    if band:
        b0, b1, blabel = band
        bx0, bx1 = x0 + (x1 - x0) * b0 / t_end, x0 + (x1 - x0) * b1 / t_end
        d.rectangle([bx0 * S, (yb - 7) * S, bx1 * S, (yb + 7) * S], fill=rgb(RED_PALE))
        d.text((bx0 * S, (yb - 28) * S), blabel, font=font(11), fill=rgb(RED))
    d.line([(x0 * S, yb * S), (x1 * S, yb * S)], fill=rgb("#cfcfcf"), width=3 * S)
    for mt, color in marks:
        xx = x0 + (x1 - x0) * mt / t_end
        d.line([(xx * S, (yb - 6) * S), (xx * S, (yb + 6) * S)], fill=rgb(color), width=S)
    d.text(((x0 - 4) * S, (yb + 9) * S), "0 秒", font=font(11), fill=rgb(SUB))
    d.text(((x1 - 22) * S, (yb + 9) * S), f"{t_end:g} 秒", font=font(11), fill=rgb(SUB))
    xx = x0 + (x1 - x0) * min(t, t_end) / t_end
    d.ellipse([((xx - 6) * S, (yb - 6) * S), ((xx + 6) * S, (yb + 6) * S)], fill=rgb(INK))


def panel(d, x, y, w, h, title, fill="#ffffff"):
    d.text((x * S, (y - 24) * S), title, font=font(14), fill=rgb(SUB))
    d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=8 * S, fill=rgb(fill),
                        outline=rgb(LINE), width=S)


def save_anim(frames, name, fps, speed, hold):
    durations = [int(1000 / fps / speed)] * len(frames)
    durations[-1] = int(hold * 1000)
    small = [f.resize((f.width * 3 // 4, f.height * 3 // 4), Image.LANCZOS) for f in frames]
    IMG.mkdir(exist_ok=True)
    small[0].save(IMG / name, "WEBP", save_all=True, append_images=small[1:], duration=durations,
                  loop=0, quality=80, method=6)


# ---------------------------------------------------------------- 追い越し
def overtake_animation(fps=10, speed=0.5, hold=3.0):
    log = load("overtake")["log"]
    t_end = 3.2
    ins = {e["id"]: e["t"] for e in log if e["what"] == "insert"}
    com = {e["id"]: e["t"] for e in log if e["what"] == "commit"}
    polls = [e for e in log if e["what"] == "poll"]
    marks = [(p["t"], SUB) for p in polls] + [(com[1], RED)]
    W, H = 900, 400
    frames = []
    for k in range(int(round(t_end * fps)) + 1):
        t = k / fps
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        clock(d, t, t_end, marks)
        done = [p for p in polls if p["t"] <= t + 1e-9]
        sent = sorted({i for p in done for i in p["ids"]})
        cursor = max([i for p in done for i in p["ids"]], default=0)
        panel(d, 20, 110, 400, 150, "outbox の表")
        panel(d, 480, 110, 400, 150, "ブローカーに届いた行")
        for n, i in enumerate(sorted(ins)):
            if ins[i] > t + 1e-9:
                continue
            x, y = 40 + n * 190, 130
            label = f"id {i}"
            if com[i] > t + 1e-9:
                chip(d, x, y, label, "#9a9a9a", dashed=True)
                d.text((x * S, (y + 38) * S), "未コミット", font=font(12), fill=rgb(SUB))
            else:
                missed = i not in sent and cursor >= i
                chip(d, x, y, label, RED if missed else INK)
                note = "送った" if i in sent else ("コミット済み・未送信" if not missed else "コミット済み・読まれない")
                d.text((x * S, (y + 38) * S), note, font=font(12), fill=rgb(RED if missed else SUB))
            who = "トランザクション A（注文 1）" if i == 1 else "トランザクション B（注文 2）"
            d.text((x * S, (y + 62) * S), who, font=font(12), fill=rgb(SUB))
        for n, i in enumerate(sent):
            chip(d, 500 + n * 110, 130, f"id {i}", INK)
        d.text((20 * S, 290 * S), "relay は 0.5 秒ごとに読む:", font=font(14), fill=rgb(INK))
        d.text((210 * S, 290 * S), f"SELECT ... WHERE id > {cursor}", font=font(15, mono=True), fill=rgb(INK))
        if done:
            last = done[-1]
            d.text((20 * S, 318 * S), f"{last['t']:.2f} 秒に読んだ行: {last['ids'] or 'なし'}",
                   font=font(13), fill=rgb(SUB))
        if t >= com[1] and any(p["t"] > com[1] for p in done):
            d.text((20 * S, 350 * S),
                   f"id 1 はコミット済みだが、id > {cursor} の条件に入らないので、この先も送られない",
                   font=font(14), fill=rgb(RED))
        frames.append(im)
    save_anim(frames, "outbox_overtake.webp", fps, speed, hold)


# ---------------------------------------------------------------- 長いトランザクションで止まる
def stall_animation(fps=10, speed=0.5, hold=3.0):
    log = load("stall")["log"]
    t_end = round(max(e["t"] for e in log) + 0.2, 1)
    b0 = next(e["t"] for e in log if e["who"] == "batch" and e["what"] == "begin")
    b1 = next(e["t"] for e in log if e["who"] == "batch" and e["what"] == "commit")
    com = {e["id"]: e["t"] for e in log if e["who"] == "app"}
    snd = {e["id"]: e["t"] for e in log if e["who"] == "relay"}
    marks = [(v, SUB) for v in com.values()]
    W, H = 900, 360
    frames = []
    for k in range(int(round(t_end * fps)) + 1):
        t = k / fps
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        clock(d, t, t_end, marks, band=(b0, b1, "outbox と無関係な集計のトランザクションが開いている"))
        waiting = [i for i in sorted(com) if com[i] <= t + 1e-9 and snd.get(i, 99) > t + 1e-9]
        got = [i for i in sorted(snd) if snd[i] <= t + 1e-9]
        panel(d, 20, 110, 400, 150, "コミット済みで、まだ送っていない行",
              fill=RED_PALE if waiting else "#ffffff")
        panel(d, 480, 110, 400, 150, "ブローカーに届いた行")
        for n, i in enumerate(waiting):
            chip(d, 34 + (n % 4) * 96, 126 + (n // 4) * 42, f"id {i}", RED, w=86)
        for n, i in enumerate(got):
            chip(d, 494 + (n % 4) * 96, 126 + (n // 4) * 42, f"id {i}", INK, w=86)
        open_ = b0 <= t < b1
        msg = ("集計のトランザクションが終わるまで、relay が読める行は増えない" if open_ else
               "集計のトランザクションが終わると、溜まった行がまとめて送られる" if t >= b1 else
               "注文は 0.5 秒ごとに 1 件コミットされる")
        d.text((20 * S, 290 * S), msg, font=font(15), fill=rgb(RED if open_ else INK))
        d.text((20 * S, 322 * S), "relay の条件:", font=font(13), fill=rgb(SUB))
        d.text((112 * S, 323 * S), "tx < pg_snapshot_xmin(pg_current_snapshot())",
               font=font(13, mono=True), fill=rgb(SUB))
        frames.append(im)
    save_anim(frames, "outbox_stall.webp", fps, speed, hold)


# ---------------------------------------------------------------- relay 2 個で順番が入れ替わる
TYPE_JP = {"OrderPlaced": "確定", "OrderPaid": "支払い", "OrderShipped": "発送"}


def chip_jp(d, x, y, text, color, fill="#ffffff", w=78, dashed=False):
    if dashed:
        d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + 30) * S], radius=5 * S, fill=rgb("#ffffff"),
                            outline=rgb("#c8c8c8"), width=S)
    else:
        d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + 30) * S], radius=5 * S, fill=rgb(fill),
                            outline=rgb(color), width=2 * S)
    tw = d.textlength(text, font=font(12))
    d.text(((x + w / 2) * S - tw / 2, (y + 6) * S), text, font=font(12), fill=rgb(color))


def ordering_animation(fps=10, speed=0.5, hold=3.0):
    data = load("ordering_trace")
    log = data["log"]
    take = {e["who"]: (e["t"], e["ids"]) for e in log if e["what"] == "take"}
    sends = [e for e in log if e["what"] == "send"]
    info = {e["id"]: (e["order"], e["type"]) for e in sends}
    sent_at = {e["id"]: e["t"] for e in sends}
    t_end = round(max(sent_at.values()) + 0.2, 1)
    marks = [(e["t"], RED if info[e["id"]][0] == 4 else SUB) for e in sends]
    W, H = 900, 400
    frames = []
    for k in range(int(round(t_end * fps)) + 1):
        t = k / fps
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        clock(d, t, t_end, marks)
        for row, who in enumerate(("A", "B")):
            tt, ids = take[who]
            y = 110 + row * 80
            if t + 1e-9 >= tt:
                d.text((30 * S, (y - 24) * S), f"relay {who} が {tt:.2f} 秒に取った行（id {ids[0]}〜{ids[-1]}。灰色は送り終えた行）",
                       font=font(13), fill=rgb(SUB))
                for n, i in enumerate(ids):
                    o, ty = info[i]
                    color = RED if o == 4 else INK
                    done = sent_at[i] <= t + 1e-9
                    chip_jp(d, 30 + n * 84, y, f"{o}・{TYPE_JP[ty]}", color if not done else "#b0b0b0",
                            fill="#ffffff" if not done else FILL)
            else:
                d.text((30 * S, (y - 24) * S), f"relay {who}: まだ取っていない", font=font(13), fill=rgb(SUB))
        d.text((30 * S, 246 * S), "ブローカーに届いた順（数字は注文の番号）", font=font(13), fill=rgb(SUB))
        got = [e for e in sends if e["t"] <= t + 1e-9]
        for n, e in enumerate(got):
            o, ty = info[e["id"]]
            chip_jp(d, 30 + (n % 9) * 94, 270 + (n // 9) * 40, f"{o}・{TYPE_JP[ty]}", RED if o == 4 else INK,
                    fill=RED_PALE if o == 4 else "#ffffff", w=86)
        got4 = [info[e["id"]][1] for e in got if info[e["id"]][0] == 4]
        if "OrderPlaced" in got4:
            msg = f"注文 4 の確定は {len(got)} 番目。支払い・発送より後に届いた"
        elif got4:
            msg = "注文 4 の支払いが、確定より先に届いた（確定は relay A の最後の行）"
        else:
            msg = "注文ごとに 確定 → 支払い → 発送 の順で書いた 18 行を、2 つの relay が 10 行ずつ取る"
        d.text((30 * S, 360 * S), msg, font=font(15), fill=rgb(RED if got4 else INK))
        frames.append(im)
    save_anim(frames, "outbox_ordering_swap.webp", fps, speed, hold)


# ---------------------------------------------------------------- relay の数と順番
def ordering_figure():
    data = load("ordering")
    keys = ["1", "2", "4", "2_by_order", "4_by_order"]
    labels = ["relay 1 個", "relay 2 個", "relay 4 個", "relay 2 個\n注文で分担", "relay 4 個\n注文で分担"]
    vals = [data[k]["out_of_order"] for k in keys]
    lo = [v - min(data[k]["runs"]) for k, v in zip(keys, vals)]
    hi = [max(data[k]["runs"]) - v for k, v in zip(keys, vals)]
    total = data["1"]["orders"]
    fig, ax = plt.subplots(figsize=(8.0, 3.2))
    bars = ax.bar(range(len(keys)), vals, 0.55, color=[ACCENT, RED, RED, ACCENT, ACCENT],
                  yerr=[lo, hi], error_kw=dict(ecolor=SUB, capsize=4, lw=1))
    for b, k, v, h in zip(bars, keys, vals, hi):
        runs = data[k]["runs"]
        label = f"{v}" if min(runs) == max(runs) else f"{v}（{min(runs)}〜{max(runs)}）"
        ax.text(b.get_x() + b.get_width() / 2, v + h + 3, label, ha="center", va="bottom", fontsize=9.5)
    ax.set_xticks(range(len(keys)), labels, fontsize=10)
    ax.set_ylabel("順番が入れ替わった注文の数")
    ax.set_ylim(0, max(v + h for v, h in zip(vals, hi)) * 1.3 + 5)
    ax.set_title(f"注文 {total} 件のうち、確定 → 支払い → 発送 の順で届かなかった注文（5 回の中央値と範囲）",
                 fontsize=10, color=INK, loc="left")
    save_plot(fig, "outbox_ordering.webp")


# ---------------------------------------------------------------- WAL の順
def wal_order_figure(n=40):
    data = load("wal_order")
    ids = data["head"][:n]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    xs = list(range(1, len(ids) + 1))
    ax.plot(xs, xs, ls="--", color=LINE, lw=1, label="id の順に届いた場合")
    ax.plot(xs, ids, marker="o", ms=4, color=INK, lw=1, label="WAL から読んだ順（コミットの順）")
    for x, i in zip(xs, ids):
        if i == 1:
            ax.annotate("id 1 は 8 番目" if x == 8 else f"id 1 は {x} 番目", (x, i), xytext=(x + 2, i - 1),
                        fontsize=10, color=RED, arrowprops=dict(arrowstyle="-", color=RED))
    ax.set_xlabel("WAL から読んだ順番")
    ax.set_ylabel("outbox の id")
    ax.set_title(f"8 並列で書いた outbox の行の、最初の {n} 行（全 {data['total']:,} 行で取りこぼし 0）",
                 fontsize=10.5, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    save_plot(fig, "outbox_wal_order.webp")


if __name__ == "__main__":
    load_figure()
    crash_figure()
    overtake_animation()
    stall_animation()
    ordering_animation()
    ordering_figure()
    wal_order_figure()
