#!/usr/bin/env python3
"""オンチェーン監視のノートの図を lab の実験結果から作る。

Run: python3 content/notes/blockchain-systems/onchain-monitoring/figures.py
入力: lab/oz/output/v170/results.json、lab/oz/timelines/、lab/rindexer/output/results.json、
      lab/silverback/output/results.json
出力: images/ の WebP（restart.webp と reorg.webp は動く WebP）。
動く WebP の時刻は実測の値で、restart は 10 倍速で再生する。reorg は 1 段階を 3〜4 秒で表示する。
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "images")
LAB = os.path.join(HERE, "lab")
OZ = json.load(open(os.path.join(LAB, "oz", "output", "v170", "results.json")))
RI = json.load(open(os.path.join(LAB, "rindexer", "output", "results.json")))
SB = json.load(open(os.path.join(LAB, "silverback", "output", "results.json")))

JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
INK, SUB, LINE = "#1f1f1f", "#666666", "#bdbdbd"
FILL, PALE = "#f2f2f2", "#eaf1f5"
RED, RED_PALE = "#d64545", "#fbe3e3"
GREEN, GREEN_PALE = "#3b7d4f", "#e3f1e6"
BLUE, BLUE_PALE = "#2f6690", "#e2edf5"
AMBER, AMBER_PALE = "#b7791f", "#fbf0dc"
GHOST = "#c8c8c8"
S = 2  # 2 倍で描いて縮める


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, size * S)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * S, h * S), "#ffffff")
        self.d = ImageDraw.Draw(self.im)

    def text(self, x, y, s, size=14, color=INK, mono=False, anchor="la"):
        self.d.text((x * S, y * S), s, font=font(size, mono), fill=rgb(color), anchor=anchor)

    def box(self, x, y, w, h, fill="#ffffff", outline=LINE, width=1, r=8):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S,
                                 fill=rgb(fill) if fill else None,
                                 outline=rgb(outline) if outline else None, width=width * S)

    def rect(self, x, y, w, h, fill, outline=None):
        self.d.rectangle([x * S, y * S, (x + w) * S, (y + h) * S], fill=rgb(fill),
                         outline=rgb(outline) if outline else None, width=S)

    def line(self, pts, color=SUB, width=2):
        self.d.line([(x * S, y * S) for x, y in pts], fill=rgb(color), width=width * S)

    def arrow(self, x1, y1, x2, y2, color=SUB, width=2):
        self.line([(x1, y1), (x2, y2)], color, width)
        if x2 != x1:
            k = 1 if x2 > x1 else -1
            self.d.polygon([(x2 * S, y2 * S), ((x2 - 9 * k) * S, (y2 - 5) * S), ((x2 - 9 * k) * S, (y2 + 5) * S)],
                           fill=rgb(color))
        else:
            k = 1 if y2 > y1 else -1
            self.d.polygon([(x2 * S, y2 * S), ((x2 - 5) * S, (y2 - 9 * k) * S), ((x2 + 5) * S, (y2 - 9 * k) * S)],
                           fill=rgb(color))

    def badge(self, x, y, n, color=RED):
        self.d.ellipse([(x - 11) * S, (y - 11) * S, (x + 11) * S, (y + 11) * S], fill=rgb(color))
        self.text(x, y + 1, str(n), size=13, color="#ffffff", anchor="mm")

    def final(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def save_webp(im, name):
    im.save(os.path.join(IMG, name), "WEBP", quality=90, method=6)


def save_anim(frames, durations, name):
    frames[0].save(os.path.join(IMG, name), "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=80, method=6)


def oz_ok(run):
    """OZ の結果で、通知先が 200 を返した量（500 だけの試行は除く）。"""
    return {d["amount"] for d in run["delivered"] if 200 in d["statuses"]}


def timeline(rel):
    rows = [json.loads(l) for l in open(os.path.join(LAB, "oz", "timelines", rel, "timeline.jsonl"))]
    t0 = rows[0]["t"]
    for r in rows:
        r["t"] -= t0
    return rows


# ---------------------------------------------------------------- 0. ICON の時系列（事後報告の時刻、UTC）

def icon_figure():
    # 時刻は ICON Foundation の事後報告（2026-08-30 公開）の Timeline の値
    events = [
        ("02:01", 2 * 60 + 1, "悪用が始まる", RED),
        ("02:08", 2 * 60 + 8, "監視のアラートが鳴る", AMBER),
        ("03:40 頃", 3 * 60 + 40, "担当者が調べ始める", BLUE),
        ("03:53", 3 * 60 + 53, "コントラクトを止める", GREEN),
    ]
    W, H = 980, 250
    c = Canvas(W, H)
    c.text(20, 14, "ICON の事件で、アラートが鳴ってから止めるまで（2026 年 8 月 27 日、UTC）", size=17)
    x0, x1, t0, t1 = 60, 920, 2 * 60 - 5, 4 * 60 + 5
    X = lambda m: x0 + (x1 - x0) * (m - t0) / (t1 - t0)
    y = 140
    c.rect(X(2 * 60 + 1), y - 6, X(2 * 60 + 21) - X(2 * 60 + 1), 12, RED_PALE)
    c.text(X(2 * 60 + 21) + 6, y - 16, "使い回しが続いた 20 分", size=11, color=RED)
    c.rect(X(2 * 60 + 8), y + 26, X(3 * 60 + 40) - X(2 * 60 + 8), 10, AMBER_PALE)
    c.text((X(2 * 60 + 8) + X(3 * 60 + 40)) / 2, y + 42, "アラートは当番を呼ばない重要度だった（約 90 分）", size=12, color=AMBER, anchor="ma")
    c.line([(x0, y), (x1, y)], LINE, 2)
    for h in range(2, 5):
        for mm in (0, 30):
            m = h * 60 + mm
            if t0 <= m <= t1:
                c.line([(X(m), y - 4), (X(m), y + 4)], LINE, 1)
                c.text(X(m), y + 70, f"{h:02d}:{mm:02d}", size=11, color=SUB, anchor="ma")
    for i, (label, m, what, col) in enumerate(events):
        c.d.ellipse([(X(m) - 6) * S, (y - 6) * S, (X(m) + 6) * S, (y + 6) * S], fill=rgb(col))
        ty = 60 if i % 2 == 0 else 84
        c.line([(X(m), y - 8), (X(m), ty + 18)], col, 1)
        if i >= 2:
            c.text(X(m) - 4, ty, f"{label} {what}", size=12, color=col, anchor="ra")
        else:
            c.text(X(m) + 4, ty, f"{label} {what}", size=12, color=col)
    save_webp(c.final(), "icon.webp")


# ---------------------------------------------------------------- 1. 表紙: RPC を 5 分止めた OZ Monitor

def rpc_down_figure():
    r = OZ["S5"]
    tl = timeline("v170_S5")
    samples = [x for x in tl if x["ev"] == "sample" and x["alive"]]
    ctl = [x for x in r["control_events"] if x["ev"] == "proxy_control"]
    down0, down1 = ctl[0]["t"], ctl[1]["t"]
    metrics = [m for m in r["metrics_timeline"] if m.get("alive") and "error" not in m]
    lag_key = 'block_checkpoint_lag{network="anvil_local"}'
    delivered = oz_ok(r)
    mined = {int(k): v for k, v in r["mined_times"].items()}

    W, H = 980, 470
    c = Canvas(W, H)
    c.text(20, 14, "RPC を 5 分止めた OpenZeppelin Monitor（既定の設定）", size=17)
    c.text(20, 40, "プロセスは動き続け、遅れの指標は 0 のまま。戻った後、止まっていた間の送金の通知は送られなかった", size=13, color=SUB)

    x0, x1, tmax = 90, 940, 345.0
    X = lambda t: x0 + (x1 - x0) * t / tmax
    # 上: 遅れ（ブロック数）
    y0, y1, vmax = 90, 300, 320.0
    Y = lambda v: y1 - (y1 - y0) * v / vmax
    c.rect(X(down0), y0, X(down1) - X(down0), y1 - y0, "#f6f6f6")
    c.text(X(down0) + 8, y0 + 6, "RPC が応答しない 5 分", size=12, color=SUB)
    for v in (0, 100, 200, 300):
        c.line([(x0, Y(v)), (x1, Y(v))], "#ececec", 1)
        c.text(x0 - 10, Y(v), str(v), size=11, color=SUB, anchor="rm")
    c.text(20, y0 - 4, "遅れ（ブロック）", size=11, color=SUB)
    c.line([(x0, y1), (x1, y1)], LINE, 1)
    pts = [(X(s["t"]), Y(s["head"] - s["checkpoint"])) for s in samples if s["t"] <= tmax]
    c.line(pts, RED, 3)
    mpts = [(X(m["t"]), Y(m[lag_key])) for m in metrics if m["t"] <= tmax]
    c.line(mpts, BLUE, 3)
    for x, y in mpts:
        c.d.ellipse([(x - 3.5) * S, (y - 3.5) * S, (x + 3.5) * S, (y + 3.5) * S], fill=rgb(BLUE))
    peak = max(samples, key=lambda s: s["head"] - s["checkpoint"])
    c.text(X(peak["t"]) - 10, Y(peak["head"] - peak["checkpoint"]) - 10,
           f"実際の遅れ（最新の番号 − チェックポイント）最大 {peak['head'] - peak['checkpoint']}", size=12, color=RED, anchor="rb")
    c.text(X(150), Y(0) - 12, "block_checkpoint_lag の値（10 秒ごとに取得）: 0 のまま", size=12, color=BLUE, anchor="lb")

    # 下: 送金ごとの通知
    yb = 350
    c.text(20, yb - 2, "通知", size=11, color=SUB)
    c.text(20, yb + 14, "（送金 1 件）", size=10, color=SUB)
    for a, t in mined.items():
        if t > tmax:
            continue
        col = GREEN if a in delivered else RED
        c.rect(X(t) - 1.1, yb, 2.2, 34, col)
    c.line([(x0, yb + 44), (x1, yb + 44)], LINE, 1)
    for t in range(0, 341, 60):
        c.line([(X(t), yb + 44), (X(t), yb + 49)], LINE, 1)
        c.text(X(t), yb + 52, f"{t} 秒", size=11, color=SUB, anchor="ma")
    lost = sum(1 for a in mined if a not in delivered)
    c.rect(x0, H - 30, 12, 12, GREEN)
    c.text(x0 + 18, H - 31, f"届いた {len(delivered)} 件", size=12)
    c.rect(x0 + 130, H - 30, 12, 12, RED)
    c.text(x0 + 148, H - 31, f"届かなかった {lost} 件", size=12)
    c.text(x1, H - 31, "Anvil で 1 秒に 1 ブロック、各ブロックに通知の対象の送金を 1 件", size=11, color=SUB, anchor="ra")
    save_webp(c.final(), "rpc_down.webp")


# ---------------------------------------------------------------- 2. 監視ツールの 1 周と、欠けが入る 5 か所

def loop_figure():
    W, H = 980, 430
    c = Canvas(W, H)
    c.text(20, 14, "監視ツールの 1 周と、通知が欠ける 5 か所", size=17)

    # ノード（チェーン）
    c.box(20, 60, 230, 300, FILL)
    c.text(36, 72, "ノード", size=15)
    c.text(36, 96, "RPC で問い合わせを受ける", size=12, color=SUB)
    bx = 40
    for i, n in enumerate(range(101, 106)):
        y = 128 + i * 40
        last = i >= 3
        c.box(bx, y, 120, 30, "#ffffff" if not last else AMBER_PALE, LINE if not last else AMBER, r=4)
        c.text(bx + 60, y + 15, f"block {n}", size=12, mono=True, anchor="mm")
    c.text(bx + 130, 128 + 3 * 40 + 15, "まだ置き換わる", size=11, color=AMBER, anchor="lm")
    c.text(bx + 130, 128 + 3 * 40 + 31, "かもしれない", size=11, color=AMBER, anchor="lm")
    c.text(bx, 330, "承認数 2: 103 までを処理する", size=11, color=SUB)
    c.badge(232, 300, 3)

    # 監視ツール
    c.box(300, 60, 430, 300, "#ffffff", SUB)
    c.text(316, 72, "監視ツール（一定の間隔で繰り返す）", size=15)
    steps = [
        ("新しいブロックとログを取得", "前回の続きから、承認数だけ手前まで"),
        ("条件に合うものを選ぶ", "例: Transfer で受け手が bob"),
        ("通知を送る", "webhook・Slack・メール"),
        ("チェックポイントを保存", "どのブロックまで処理したか"),
    ]
    for i, (a, b) in enumerate(steps):
        y = 110 + i * 60
        c.box(330, y, 360, 46, PALE, LINE, r=6)
        c.text(346, y + 8, a, size=13)
        c.text(346, y + 27, b, size=11, color=SUB)
        if i < 3:
            c.arrow(510, y + 46, 510, y + 60, SUB)
    c.line([(330, 110 + 3 * 60 + 23), (314, 110 + 3 * 60 + 23), (314, 133), (328, 133)], SUB, 2)
    c.d.polygon([(330 * S, 133 * S), (321 * S, 128 * S), (321 * S, 138 * S)], fill=rgb(SUB))
    c.badge(690, 110, 1)
    c.badge(690, 290, 2)

    # 通知先
    c.box(780, 170, 180, 90, FILL)
    c.text(796, 182, "通知先", size=15)
    c.text(796, 208, "当番のスマートフォン", size=11, color=SUB)
    c.text(796, 226, "チャット・自動の停止", size=11, color=SUB)
    c.arrow(690, 133 + 120 - 10, 780, 215, SUB)
    c.badge(770, 196, 4)

    # RPC の矢印
    c.arrow(300, 133, 250, 133, SUB)
    c.arrow(250, 150, 300, 150, SUB)
    c.text(275, 120, "RPC", size=11, color=SUB, anchor="ms")
    c.badge(275, 175, 5)

    notes = [
        (1, "1 ブロックだけ取得に失敗する"),
        (2, "監視が止まり、後で再起動する"),
        (3, "処理したブロックが reorg で置き換わる"),
        (4, "通知先がエラーを返す"),
        (5, "RPC がしばらく応答しない"),
    ]
    for i, (n, s) in enumerate(notes):
        x = 32 + (i % 3) * 320
        y = 378 + (i // 3) * 26
        c.badge(x, y + 9, n)
        c.text(x + 18, y, s, size=12)
    save_webp(c.final(), "loop.webp")


# ---------------------------------------------------------------- 3. 実験の作り

def setup_figure():
    W, H = 980, 300
    c = Canvas(W, H)
    c.text(20, 14, "実験の作り: 監視ツールと Anvil の間に、失敗を混ぜる中継を置く", size=17)
    boxes = [
        (20, "Anvil", ["手元のノード", "1 秒に 1 ブロック"]),
        (270, "faultproxy.py", ["JSON-RPC の中継", "指定したブロックや全部を", "エラーにする"]),
        (520, "監視ツール", ["OZ Monitor・rindexer・", "Silverback を 1 つずつ"]),
        (770, "sink.py", ["webhook の受け口", "受けた時刻と本文を記録", "500 を返すこともできる"]),
    ]
    for x, t, lines in boxes:
        c.box(x, 70, 190, 120, PALE if t != "監視ツール" else "#ffffff", LINE if t != "監視ツール" else SUB)
        c.text(x + 16, 82, t, size=14, mono=t.endswith(".py"))
        for i, s in enumerate(lines):
            c.text(x + 16, 110 + i * 20, s, size=11, color=SUB)
    c.arrow(520, 115, 460, 115)
    c.arrow(270, 115, 210, 115)
    c.arrow(710, 130, 770, 130)
    c.box(20, 222, 940, 60, FILL, None)
    c.text(36, 232, "各ブロックに alice → bob の送金を 1 件入れ、量はそのブロックの番号にする", size=13)
    c.text(36, 254, "受け口に届いた量を数えれば、どのブロックの通知が届き、どれが消えたかが分かる", size=12, color=SUB)
    save_webp(c.final(), "setup.webp")


# ---------------------------------------------------------------- 4. 1 ブロックだけ取れない時の 3 つの型

def strip(c, x, y, order, delivered, fail_idx, cell=19, gap=3):
    for i, a in enumerate(order):
        cx = x + i * (cell + gap)
        if a in delivered:
            c.rect(cx, y, cell, cell, GREEN)
        else:
            c.rect(cx, y, cell, cell, RED_PALE, RED)
        if i == fail_idx:
            c.line([(cx + cell / 2, y - 8), (cx + cell / 2, y - 2)], RED, 2)


def one_block_figure():
    W, H = 980, 420
    c = Canvas(W, H)
    c.text(20, 14, "1 ブロックだけ、取得がエラーを返し続けた時", size=17)
    c.text(20, 40, "40 件の送金のうち 14 件目のブロックで失敗させた。マスは送金 1 件、緑が届いた通知、薄い赤は届かなかった送金", size=13, color=SUB)
    rows = [
        ("黙って飛ばす", "OpenZeppelin Monitor v1.7.0", OZ["S1a_logs"]["expected"],
         oz_ok(OZ["S1a_logs"]),
         "その 1 件だけ消え、続きは届く。ERROR が 1 行出るが、ブロックの番号は書かれない"),
        ("止まって待つ", "rindexer 1.0.0", RI["S1-a"]["expected"], {d["amount"] for d in RI["S1-a"]["delivered"]},
         "13 件の後で進まない。7 分たっても /health は 200、遅れの指標は 0"),
        ("終了する", "Silverback 0.7.39（ポーリング）", SB["S1-a-poll"]["expected"],
         {d["amount"] for d in SB["S1-a-poll"]["delivered"]},
         "13 件の後で、プロセスが終了コード 0 で終わる"),
    ]
    for k, (kind, tool, exp, dl, note) in enumerate(rows):
        y = 84 + k * 108
        c.text(20, y, kind, size=15)
        c.text(150, y + 2, tool, size=12, color=SUB)
        strip(c, 20, y + 34, exp, dl, 13)
        c.text(20, y + 62, note, size=12)
    c.text(20 + 13 * 22 + 10, 74, "失敗させたブロック", size=11, color=RED, anchor="ls")
    save_webp(c.final(), "one_block.webp")


# ---------------------------------------------------------------- 5. 止めて再起動した時（動く WebP、10 倍速）

def restart_frames():
    oz = OZ["S2_term_default"]
    tl = timeline("v170_S2_term_default")
    ev = {x["ev"]: x["t"] for x in tl if x["ev"] in ("monitor_signal", "monitor_exit")}
    starts = [x["t"] for x in tl if x["ev"] == "monitor_start"]
    oz_mined = {int(k): v for k, v in oz["mined_times"].items()}
    oz_got = {d["amount"]: d["first_ok_t"] for d in oz["delivered"] if d["first_ok_t"] is not None}
    oz_stop, oz_restart = ev["monitor_signal"], starts[1]
    first_after = min(t for a, t in oz_got.items() if t > oz_restart)

    ri = RI["S2-term-none"]
    ri_mined = {e["amount"]: e["t"] for e in ri["emitted"]}
    ri_got = {d["amount"]: d["t"] for d in ri["delivered"]}
    ri_stop = next(x["t"] for x in ri["controls"] if "stopped" in x["what"])
    ri_restart = [x["t"] for x in ri["controls"] if "start" in x["what"] and "stopped" not in x["what"]][1]

    # 揃えるため、止めた時刻を 0 とずらさず、それぞれ実測の時刻で描く
    lanes = [
        ("OpenZeppelin Monitor（既定）", oz_mined, oz_got, oz_stop, oz_restart, first_after, True),
        ("rindexer", ri_mined, ri_got, ri_stop, ri_restart, None, False),
    ]
    tmax = 110.0
    W, H = 980, 520
    frames, durs = [], []
    step = 4.0
    ts = [i * step for i in range(int(tmax / step) + 1)]
    for t in ts:
        c = Canvas(W, H)
        c.text(20, 14, "監視を 60 秒止めて再起動した時、止まっていた間の通知はどうなるか", size=17)
        c.text(20, 40, "実測した時刻を 10 倍速で再生。マスは送金 1 件（1 秒に 1 件）", size=13, color=SUB)
        # 時計と帯
        c.text(W - 46, 14, f"{t:5.0f}", size=20, mono=True, anchor="ra")
        c.text(W - 20, 18, "秒", size=16, anchor="ra")
        bx0, bx1 = 20, 960
        c.rect(bx0, 70, bx1 - bx0, 8, FILL)
        c.rect(bx0, 70, (bx1 - bx0) * min(t, tmax) / tmax, 8, SUB)
        for k, (name, mined, got, stop, restart, skip_t, lossy) in enumerate(lanes):
            y = 100 + k * 200
            state = "動いている" if t < stop or t >= restart else "止まっている"
            col = GREEN if state == "動いている" else RED
            c.text(20, y, name, size=15)
            c.box(300, y - 2, 120, 26, GREEN_PALE if state == "動いている" else RED_PALE, col, r=12)
            c.text(360, y + 11, state, size=12, color=col, anchor="mm")
            cell, gap, per = 17, 3, 46
            amounts = sorted(mined)
            for i, a in enumerate(amounts):
                cx = 20 + (i % per) * (cell + gap)
                cy = y + 40 + (i // per) * (cell + gap)
                if mined[a] > t:
                    continue
                if a in got and got[a] <= t:
                    c.rect(cx, cy, cell, cell, GREEN)
                elif lossy and skip_t is not None and t >= skip_t and a not in got:
                    c.rect(cx, cy, cell, cell, RED_PALE, RED)
                else:
                    c.rect(cx, cy, cell, cell, "#ffffff", GHOST)
            n_got = sum(1 for a in amounts if a in got and got[a] <= t)
            n_lost = sum(1 for a in amounts if lossy and skip_t is not None and t >= skip_t and a not in got and mined[a] <= t)
            msg = f"届いた {n_got} 件"
            if n_lost:
                msg += f"　捨てられた {n_lost} 件（ログは INFO の skipped {n_lost} blocks の 1 行）"
            c.text(20, y + 120, msg, size=13, color=INK)
        c.rect(20, H - 30, 12, 12, "#ffffff", GHOST)
        c.text(38, H - 31, "まだ通知されていない", size=12)
        c.rect(210, H - 30, 12, 12, GREEN)
        c.text(228, H - 31, "届いた", size=12)
        c.rect(300, H - 30, 12, 12, RED_PALE, RED)
        c.text(318, H - 31, "再起動の後、遡らずに捨てられた", size=12)
        frames.append(c.final())
        durs.append(400)
    durs[-1] = 3500
    return frames, durs


def restart_figure():
    f, d = restart_frames()
    save_anim(f, d, "restart.webp")


# ---------------------------------------------------------------- 6. reorg と承認数（動く WebP、1 段階を 3〜4 秒で表示）

def chain(c, x, y, blocks, note=None):
    for i, (label, kind) in enumerate(blocks):
        bx = x + i * 112
        fill, out = {"old": ("#ffffff", LINE), "gone": ("#f4f4f4", GHOST), "new": (AMBER_PALE, AMBER)}[kind]
        c.box(bx, y, 96, 34, fill, out, r=4)
        c.text(bx + 48, y + 17, label, size=12, mono=True, color=GHOST if kind == "gone" else INK, anchor="mm")
        if i:
            c.line([(bx - 16, y + 17), (bx, y + 17)], LINE, 2)


def reorg_frames():
    r1, r5 = OZ["S3_c1"], OZ["S3_c5"]
    got1 = oz_ok(r1)
    got5 = oz_ok(r5)
    stages = [
        ("1. 承認数 1 の監視は、最新の 1 つ手前の block 23 まで通知した",
         [("21", "old"), ("22", "old"), ("23", "old"), ("24", "old")], {21, 22, 23}, 23, None, 3500),
        ("2. reorg で block 22〜24 が、量 1022〜1024 の送金を持つブロックに置き換わる",
         [("21", "old"), ("22→1022", "new"), ("23→1023", "new"), ("24→1024", "new")], {21, 22, 23}, 23, None, 3500),
        ("3. 監視はチェックポイントの続きの block 24 から処理するので、1024 だけを通知する",
         [("21", "old"), ("22→1022", "new"), ("23→1023", "new"), ("24→1024", "new")], {21, 22, 23, 1024}, 24, None, 3500),
        ("4. 消えたブロックの通知は残り、置き換わった 2 件は届かない。承認数 5 なら新しい 3 件だけが届く",
         [("21", "old"), ("22→1022", "new"), ("23→1023", "new"), ("24→1024", "new")], {21, 22, 23, 1024}, 24, True, 4500),
    ]
    W, H = 980, 430
    frames, durs = [], []
    for title, blocks, notified, cp, show5, dur in stages:
        c = Canvas(W, H)
        c.text(20, 14, "深さ 3 の reorg と承認数（OpenZeppelin Monitor v1.7.0 の実測）", size=17)
        c.text(20, 40, "1 段階を 3〜4 秒で表示", size=12, color=SUB)
        c.text(20, 72, title, size=14)
        chain(c, 40, 112, blocks)
        cx = 40 + (cp - 21) * 112 + 48
        c.text(cx, 160, "▲ チェックポイント", size=12, color=BLUE, anchor="ma")
        c.text(20, 206, "承認数 1 で届いた通知", size=13, color=SUB)
        x = 20
        for a in sorted(notified):
            stale = a in (22, 23) and len(blocks[1][0]) > 2
            fill, out, col = (RED_PALE, RED, RED) if stale else (GREEN_PALE, GREEN, GREEN)
            c.box(x, 232, 92, 30, fill, out, r=6)
            c.text(x + 46, 247, f"量 {a}", size=12, color=col, anchor="mm")
            x += 104
        if len(blocks[1][0]) > 2 and cp == 24:
            for a in (1022, 1023):
                if a not in got1:
                    c.box(x, 232, 112, 30, "#ffffff", RED, r=6)
                    c.text(x + 56, 247, f"量 {a} 届かず", size=12, color=RED, anchor="mm")
                    x += 124
        if show5:
            ev = {e["ev"]: e for e in r5["control_events"] if e["ev"] in ("reorg_before", "reorg")}
            rep, new_amounts = ev["reorg_before"]["replaced"], ev["reorg"]["new_amounts"]
            c.text(20, 290, f"承認数 5 の回（block {rep[0]}〜{rep[-1]} を置き換え）で届いた通知", size=13, color=SUB)
            x = 20
            for a in new_amounts:
                ok = a in got5
                c.box(x, 316, 92, 30, GREEN_PALE if ok else "#ffffff", GREEN if ok else RED, r=6)
                c.text(x + 46, 331, f"量 {a}", size=12, color=GREEN if ok else RED, anchor="mm")
                x += 104
            old_sent = [a for a in rep if a in got5]
            c.text(x + 10, 331, "置き換わる前の" + ("通知は無し" if not old_sent else str(old_sent)), size=12, color=SUB, anchor="lm")
            c.text(20, 366, "5 ブロック待ってから処理するので、置き換わる前のブロックはまだ通知していなかった", size=12, color=SUB)
            c.text(20, 388, "赤の塗り: チェーンから消えたブロックの通知（取り消しは送られない）。赤い枠: 届かなかった通知", size=12, color=RED)
        frames.append(c.final())
        durs.append(dur)
    return frames, durs


def reorg_figure():
    f, d = reorg_frames()
    save_anim(f, d, "reorg.webp")


# ---------------------------------------------------------------- 7. 通知先が 60 秒 500 を返した時

def sink_figure():
    rows = []
    o = OZ["S4"]
    o_start = next(e["t"] for e in o["control_events"] if e["ev"] == "sink_control" and e["fail"])
    o_end = next(e["t"] for e in o["control_events"] if e["ev"] == "sink_control" and not e["fail"])
    o_m = {int(k): v - o_start for k, v in o["mined_times"].items()}
    rows.append(("OpenZeppelin Monitor", o_m, oz_ok(o), None,
                 "10 秒ごとにまとめて通知し、各件を約 1 秒で 4 回送って捨てる。捨てた数の指標は無い"))
    r = RI["S4-none"]
    r_start = next(x["t"] for x in r["controls"] if x["what"] == "sink fail=True")
    rows.append(("rindexer", {e["amount"]: e["t"] - r_start for e in r["emitted"]},
                 {d["amount"] for d in r["delivered"]}, None,
                 "3 回試して捨てる。rindexer_stream_publish_dropped_total に 59 と出る"))
    for key, label, note in (("S4-noraise", "Silverback（例外を投げないハンドラ）", "失敗を数えず、そのまま消える"),
                             ("S4-raise", "Silverback（失敗で例外を投げるハンドラ）", "4 回目の例外で、縦線の時刻にプロセスが終了コード 0 で終わる")):
        s = SB[key]
        s_start = next(x["t"] for x in s["controls"] if x["what"] == "sink fail=True")
        ex = next((x["t"] - s_start for x in s["controls"] if "exited" in x["what"]), None)
        rows.append((label, {e["amount"]: e["t"] - s_start for e in s["emitted"]},
                     {d["amount"] for d in s["delivered"]}, ex, note))

    W, H = 980, 540
    c = Canvas(W, H)
    c.text(20, 14, "通知先が 60 秒間 500 を返した時、その間の通知は後から届くか", size=17)
    c.text(20, 40, "マスは送金 1 件。横軸はそのブロックが作られた時刻で、通知先が 500 を返し始めた時を 0 秒とする", size=13, color=SUB)
    x0, x1, tmin, tmax = 40, 940, -12.0, 84.0
    X = lambda t: x0 + (x1 - x0) * (t - tmin) / (tmax - tmin)
    c.rect(X(0), 70, X(60) - X(0), 400, "#f6f6f6")
    c.text(X(0) + 6, 74, "通知先が 500 を返す 60 秒", size=12, color=SUB)
    for k, (name, mined, got, ex, note) in enumerate(rows):
        y = 104 + k * 92
        c.text(x0, y, name, size=14)
        for a, t in mined.items():
            if not tmin <= t <= tmax:
                continue
            c.rect(X(t) - 3.5, y + 26, 7, 22, GREEN if a in got else RED)
        if ex is not None:
            c.line([(X(ex), y + 22), (X(ex), y + 52)], INK, 3)
        c.text(x0, y + 56, note, size=12, color=SUB)
    c.line([(x0, 474), (x1, 474)], LINE, 1)
    for t in (0, 20, 40, 60, 80):
        c.text(X(t), 480, f"{t} 秒", size=11, color=SUB, anchor="ma")
    c.rect(x0, H - 22, 12, 12, GREEN)
    c.text(x0 + 18, H - 23, "届いた", size=12)
    c.rect(x0 + 90, H - 22, 12, 12, RED)
    c.text(x0 + 108, H - 23, "届かなかった", size=12)
    save_webp(c.final(), "sink.webp")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    rpc_down_figure()
    icon_figure()
    loop_figure()
    setup_figure()
    one_block_figure()
    restart_figure()
    reorg_figure()
    sink_figure()
