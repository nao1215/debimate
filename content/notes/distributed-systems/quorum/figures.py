"""Quorum のノートの図（WebP）を作る。

- quorum_timeout.webp: lab/out_timeout_write.json の実測の時刻で動かす、3 台の値の移り変わり（3 倍速）
- quorum_overlap.webp: 書き込みが届いた台と読んだ台が重なる場合と重ならない場合
- quorum_aurora.webp: Aurora の 6 つのコピーが、AZ を失った時に何台残るか

実行: python3 content/notes/distributed-systems/quorum/figures.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
IMG = HERE / "images"
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
S = 2  # 2 倍で描いて縮める

INK, SUB, LINE = "#1f1f1f", "#666666", "#9a9a9a"
PALE, FILL = "#eaf1f5", "#f2f2f2"
NEW, NEW_PALE = "#c98a1c", "#f8eed8"     # 新しい値（v2）
OLD, OLD_PALE = "#5f7f95", "#e4edf3"     # 古い値（v1）
RED, RED_PALE = "#c0392b", "#fbe5e1"
SPEED = 3.0  # 再生の速さ（実時間の 3 倍速）


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, size * S)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * S, h * S), "#ffffff")
        self.d = ImageDraw.Draw(self.im)

    def text(self, x, y, s, size=16, color=INK, anchor="la", mono=False):
        self.d.text((x * S, y * S), s, font=font(size, mono), fill=color, anchor=anchor)

    def box(self, x, y, w, h, fill, outline, width=2, r=8, dash=False):
        if dash:
            self.d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), r * S, fill=fill)
            step = 10
            for xx in range(int(x), int(x + w), step * 2):
                for yy in (y, y + h):
                    self.d.line((xx * S, yy * S, min(xx + step, x + w) * S, yy * S), fill=outline, width=width * S)
            for yy in range(int(y), int(y + h), step * 2):
                for xx in (x, x + w):
                    self.d.line((xx * S, yy * S, xx * S, min(yy + step, y + h) * S), fill=outline, width=width * S)
        else:
            self.d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), r * S,
                                     fill=fill, outline=outline, width=width * S)

    def line(self, x1, y1, x2, y2, color=INK, width=2):
        self.d.line((x1 * S, y1 * S, x2 * S, y2 * S), fill=color, width=width * S)

    def circle(self, x, y, r, fill, outline, width=2):
        self.d.ellipse(((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S), fill=fill,
                       outline=outline, width=width * S)

    def cross(self, x, y, r, color=RED, width=4):
        self.line(x - r, y - r, x + r, y + r, color, width)
        self.line(x - r, y + r, x + r, y - r, color, width)

    def image(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def save_webp(im, name):
    im.save(IMG / name, "WEBP", quality=90, method=6)


# ---------------------------------------------------------------- 動く図

def load_timeline():
    data = json.loads((HERE / "lab" / "out_timeout_write.json").read_text())
    ev = data["events"]
    samples = data["samples"]

    def first(pred):
        return next(e for e in ev if pred(e))

    t = {
        "pause": first(lambda e: e["kind"] == "pause")["t"],
        "v2_start": first(lambda e: e["kind"] == "write" and e["v"] == "v2")["start"],
        "timeout": first(lambda e: e["kind"] == "write" and e["v"] == "v2")["t"],
        "read_q1": first(lambda e: e["kind"] == "read")["t"],
        "down": min(e["t"] for e in ev if e["kind"] == "down"),
        "down_q2": first(lambda e: e["kind"] == "down" and e["node"] == "q2")["t"],
        "down_q3": first(lambda e: e["kind"] == "down" and e["node"] == "q3")["t"],
        "v3": first(lambda e: e["kind"] == "write" and e["v"] == "v3")["t"],
        "unpause": first(lambda e: e["kind"] == "unpause")["t"],
        "hint": max(e["t"] for e in ev if e["kind"] == "hint"),
        "first_sample": samples[0]["t"],
    }
    # q2・q3 が v2 を返した最初の読み取りの時刻（実測）
    t["q2_new"] = next(s["t"] for s in samples if s["q2"] == "v2")
    t["q3_new"] = next(s["t"] for s in samples if s["q3"] == "v2")
    t["stale"] = samples[0]
    return t


def timeout_frame(now, t, end, final=False):
    c = Canvas(1200, 640)
    c.text(32, 22, "QUORUM の書き込みがエラーになった後、3 台が持つ値", 22)
    c.text(32, 56, f"Cassandra 5.0.6 の 3 台（レプリカ 3 つ）で実測した時刻を {SPEED:.0f} 倍速で再生", 14, SUB)
    c.text(1168, 26, f"経過 {now:5.1f} 秒", 22, anchor="ra")

    # 時間の帯
    x0, x1, yb = 32, 1168, 98
    c.box(x0, yb, x1 - x0, 14, FILL, LINE, 1, r=4)
    px = x0 + (x1 - x0) * min(now, end) / end
    c.box(x0, yb, max(px - x0, 1), 14, PALE, OLD, 1, r=4)
    marks = [("止める", t["pause"]), ("エラーになる", t["timeout"]),
             ("DOWN と判定", t["down"]), ("戻す", t["unpause"]), ("hint が届く", t["hint"])]
    for i, (label, tm) in enumerate(marks):
        mx = x0 + (x1 - x0) * tm / end
        c.line(mx, yb - 4, mx, yb + 18, INK if tm <= now else LINE, 2)
        anchor = {"止める": "la", "DOWN と判定": "ra", "戻す": "la"}.get(label, "ma")
        c.text(mx, yb + 22, label, 12, INK if tm <= now else LINE, anchor=anchor)
    for s in range(0, int(end) + 1, 5):
        c.text(x0 + (x1 - x0) * s / end, yb - 20, f"{s}s", 11, SUB, anchor="ma")

    # 3 台
    paused = t["pause"] <= now < t["unpause"]
    rows = [("q1", "coordinator"), ("q2", ""), ("q3", "")]
    for i, (name, role) in enumerate(rows):
        y = 170 + i * 120
        is_paused = paused and name != "q1"
        c.box(32, y, 470, 96, RED_PALE if is_paused else "#ffffff", RED if is_paused else LINE, 2,
              dash=is_paused)
        c.text(52, y + 14, name, 24, mono=True)
        if role:
            c.text(52, y + 56, role, 13, SUB, mono=True)
        state = "止めた（docker pause）" if is_paused else "動いている"
        c.text(130, y + 20, state, 15, RED if is_paused else SUB)
        if name == "q1":
            new = now >= t["read_q1"]
        else:
            new = now >= t[f"{name}_new"]
        val, fill, ink = ("v2", NEW_PALE, NEW) if new else ("v1", OLD_PALE, OLD)
        c.box(360, y + 18, 120, 60, fill, ink, 3)
        c.text(420, y + 48, val, 26, ink, anchor="mm", mono=True)

    # クライアントの記録
    c.box(530, 150, 638, 456, "#ffffff", LINE, 2)
    c.text(550, 164, "クライアントから見えたこと", 16, SUB)
    log = [
        (t["v2_start"], "v2 を QUORUM で書く（2 台の応答が必要）", INK),
        (t["timeout"], "WriteTimeout: 応答は 1 台だけ", RED),
        (t["read_q1"], "q1 を ONE で読む → v2", NEW),
        (t["down_q2"], "q1 が q2 を DOWN と判定", SUB),
        (t["down_q3"], "q1 が q3 を DOWN と判定", SUB),
        (t["v3"], "v3 を QUORUM で書く → Unavailable", RED),
        (t["first_sample"], "q2 を ONE で読む → v1（古い）", OLD),
        (t["first_sample"], "q2 を QUORUM で読む → v2", NEW),
        (t["q2_new"], "hint が届き、3 台とも v2", NEW),
    ]
    y = 200
    for tm, s, color in log:
        if tm <= now:
            c.text(550, y, f"{tm:4.1f}s", 15, SUB, mono=True)
            c.text(620, y - 2, s, 16, color)
            y += 40
    if final:
        c.text(550, 566, "エラーになった v2 は残り、v3 はどの台にも無い", 17, INK)
    return c.image()


def timeout_animation():
    t = load_timeline()
    end = round(t["q2_new"] + 1.0, 1)
    step = 0.75  # 1 コマで進める実時間（秒）
    frames, durs = [], []
    now = 0.0
    while now < end:
        frames.append(timeout_frame(now, t, end))
        durs.append(int(step / SPEED * 1000))
        now += step
    frames.append(timeout_frame(end, t, end, final=True))
    durs.append(3500)
    frames[0].save(IMG / "quorum_timeout.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, quality=80, method=6)
    return sum(durs) / 1000, len(frames)


# ---------------------------------------------------------------- 重なりの図

def overlap_figure():
    c = Canvas(1200, 470)
    panels = [
        (40, "QUORUM で書き、QUORUM で読む", "W = 2、R = 2（W + R = 4 > 3）",
         {0, 1}, {1, 2}, "重なった q2 が v2 を持つので、読む側は v2 を選べる", NEW),
        (620, "ONE で書き、ONE で読む", "W = 1、R = 1（W + R = 2 ≦ 3）",
         {0}, {2}, "読んだ q3 は v1 しか持たず、v1 が返る", RED),
    ]
    for x, title, sub, wset, rset, note, color in panels:
        c.box(x, 20, 540, 430, "#ffffff", LINE, 2)
        c.text(x + 24, 40, title, 20)
        c.text(x + 24, 74, sub, 15, SUB)
        for i in range(3):
            cx = x + 110 + i * 160
            cy = 250
            new = i in wset
            c.circle(cx, cy, 46, NEW_PALE if new else OLD_PALE, NEW if new else OLD, 3)
            c.text(cx, cy - 8, f"q{i + 1}", 18, anchor="mm", mono=True)
            c.text(cx, cy + 20, "v2" if new else "v1", 18, NEW if new else OLD, anchor="mm", mono=True)
        # 書き込みが届いた台（上の括弧）と読んだ台（下の括弧）
        wl, wr = x + 110 + min(wset) * 160 - 56, x + 110 + max(wset) * 160 + 56
        c.line(wl, 175, wr, 175, NEW, 4)
        c.line(wl, 175, wl, 188, NEW, 4)
        c.line(wr, 175, wr, 188, NEW, 4)
        c.text((wl + wr) / 2, 150, "書き込みが届いた台", 15, NEW, anchor="mm")
        rl, rr = x + 110 + min(rset) * 160 - 56, x + 110 + max(rset) * 160 + 56
        c.line(rl, 325, rr, 325, OLD, 4)
        c.line(rl, 312, rl, 325, OLD, 4)
        c.line(rr, 312, rr, 325, OLD, 4)
        c.text((rl + rr) / 2, 350, "読んだ台", 15, OLD, anchor="mm")
        c.text(x + 24, 400, note, 16, color)
    save_webp(c.image(), "quorum_overlap.webp")


# ---------------------------------------------------------------- Aurora の図

def aurora_figure():
    c = Canvas(1200, 430)
    cases = [
        (40, "AZ を 1 つ失う", {0, 1}, "残り 4 つ: 書き込み（4 つ）も読み取り（3 つ）もできる", INK),
        (620, "AZ 1 つと、他の AZ にあるコピー 1 つを失う", {0, 1, 2}, "残り 3 つ: 書けないが、読めて修復できる", RED),
    ]
    for x, title, lost, note, color in cases:
        c.box(x, 20, 540, 390, "#ffffff", LINE, 2)
        c.text(x + 24, 40, title, 20)
        for az in range(3):
            ax = x + 30 + az * 165
            c.box(ax, 100, 150, 200, FILL, LINE, 2)
            c.text(ax + 75, 118, f"AZ {az + 1}", 15, SUB, anchor="mm")
            for k in range(2):
                idx = az * 2 + k
                cx, cy = ax + 42 + k * 66, 200
                gone = idx in lost
                c.circle(cx, cy, 26, "#ffffff" if gone else OLD_PALE, LINE if gone else OLD, 3)
                if gone:
                    c.cross(cx, cy, 16)
        c.text(x + 24, 340, note, 16, color)
    save_webp(c.image(), "quorum_aurora.webp")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    total, n = timeout_animation()
    print(f"quorum_timeout.webp: {n} frames, {total:.1f}s")
    overlap_figure()
    aurora_figure()
