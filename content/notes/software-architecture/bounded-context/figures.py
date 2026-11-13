"""Bounded Context のノートの図を作る（WebP）。

race_figure(): lab/race.py の実測の時刻（lab/events.json）で動く図。税の計算の途中で
  別の処理が注文を触った場面を、total 列を共有する設計と base_total 列に分ける設計で並べる。
  実測の時刻を 0.5 倍速で再生する。
writers_figure(): Saleor の PR #19801 の前と後で、Order の合計の列に誰が書くかを並べる。
columns_figure(): Saleor の Order に「合計」の列が足されてきた年表（migration と PR の日付）。
contexts_figure(): 「合計」の意味ごとに境界を分けた場合。各コンテキストが自分の合計を持ち、注文 ID で対応付ける。
contextmap_figure(): 3 つのコンテキストに、渡すもの（ID・翻訳した値・起きた事実）と関係の名前を書き込んだコンテキストマップ（説明用の一例）。
copies_figure(): 弁護士ドットコムの振り返り記事の構図。機能で分けたサービスのそれぞれに、カテゴリ管理のコピーを持たせた。

実行: python3 content/notes/software-architecture/bounded-context/lab/race.py \
        content/notes/software-architecture/bounded-context/lab/events.json
      python3 content/notes/software-architecture/bounded-context/figures.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
INK, SUB, LINE = (31, 31, 31), (102, 102, 102), (190, 190, 190)
BLUE, BLUE_PALE = (74, 128, 163), (230, 239, 245)
RED, RED_PALE = (200, 60, 60), (250, 228, 228)
FILL = (242, 242, 242)
S = 2  # 2 倍で描いて縮める
SPEED = 0.5  # 再生の速さ（実時間の 0.5 倍速）


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, size * S, index=0)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w * S, h * S), "white")
        self.d = ImageDraw.Draw(self.img)

    def text(self, x, y, s, size=16, color=INK, anchor="la", mono=False):
        self.d.text((x * S, y * S), s, font=font(size, mono), fill=color, anchor=anchor)

    def rect(self, x, y, w, h, fill=None, outline=INK, width=2, r=8):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S,
                                 fill=fill, outline=outline, width=width * S)

    def line(self, x1, y1, x2, y2, color=INK, width=2):
        self.d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=color, width=width * S)

    def arrow(self, x1, y1, x2, y2, color=INK, width=2):
        self.line(x1, y1, x2, y2, color, width)
        import math
        a = math.atan2(y2 - y1, x2 - x1)
        p = [(x2, y2), (x2 - 11 * math.cos(a - 0.4), y2 - 11 * math.sin(a - 0.4)),
             (x2 - 11 * math.cos(a + 0.4), y2 - 11 * math.sin(a + 0.4))]
        self.d.polygon([(px * S, py * S) for px, py in p], fill=color)

    def dot(self, x, y, r, fill):
        self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill)

    def image(self):
        return self.img.resize((self.w, self.h), Image.LANCZOS)


def save_webp(img, name):
    IMAGES.mkdir(exist_ok=True)
    img.save(IMAGES / name, "WEBP", quality=90, method=6)


# ---------------------------------------------------------------- 動く図
SHORT = {
    "値引きの判定用に税抜きの合計を書く": "① 税抜きの 80 を書く",
    "別の処理が注文の備考を変える": "② 別の処理が備考を変える",
    "他の処理が注文を変えていたので、税込みの合計の保存をやめる": "③ 税込みの 88 の保存をやめる",
    "保存されていない計算があるので、確定を拒否する": "④ 確定を拒否する（再試行を待つ）",
}


def short(what, design):
    if what.startswith("値引きの判定用"):
        return "① 税抜きの 80 を " + ("total" if design == "shared" else "base_total") + " に書く"
    if what.startswith("注文を確定する"):
        return "④ " + what.replace("注文を確定する（", "確定（").replace("）", "）")
    return SHORT.get(what)


def race_frame(runs, now, end):
    W, H = 1200, 560
    c = Canvas(W, H)
    c.text(40, 26, "税の計算の途中で、別の処理が注文を触った場合", 26)
    c.text(40, 60, f"lab/race.py で実測した時刻を {SPEED} 倍速で再生", 17, SUB)
    # 時間の帯
    x0, x1, tmax = 330, 860, 2.2
    tx = lambda t: x0 + (x1 - x0) * min(t, tmax) / tmax
    c.text(1160, 30, f"経過 {min(now, end):.2f} 秒", 20, INK, anchor="ra", mono=False)
    c.rect(x0, 92, x1 - x0, 14, fill=FILL, outline=LINE, width=1, r=4)
    c.rect(x0, 92, max(tx(now) - x0, 1), 14, fill=BLUE, outline=BLUE, width=1, r=4)
    for t in (0, 0.5, 1.0, 1.5, 2.0):
        c.text(tx(t), 112, f"{t:.1f} 秒", 15, SUB, anchor="ma")
    titles = {"shared": ("total 列を共有する", "値引きの判定も税の計算も total に書く"),
              "split": ("base_total 列に分ける", "値引きの判定は base_total、税は total")}
    for i, run in enumerate(runs):
        top = 150 + i * 200
        c.rect(20, top, W - 40, 180, fill=None, outline=LINE, width=1, r=10)
        name, sub = titles[run["design"]]
        c.text(40, top + 16, name, 22)
        c.text(40, top + 50, sub, 15, SUB)
        # 税の計算の棒
        ev = run["events"]
        start = next(e["t"] for e in ev if e["what"] == "税の計算を始める")
        stop = next((e["t"] for e in ev if "保存" in e["what"]), 2.0)
        if now > start:
            c.rect(tx(start), top + 20, max(tx(min(now, stop)) - tx(start), 2), 22,
                   fill=BLUE_PALE, outline=BLUE, width=1, r=4)
            c.text(tx(start) + 8, top + 22, "税の計算（外部のアプリ）", 15, BLUE)
        c.line(tx(min(now, end)), top + 10, tx(min(now, end)), top + 170, SUB, 1)
        # 出来事
        shown = [e for e in ev if e["t"] <= now and short(e["what"], run["design"])]
        for k, e in enumerate(shown):
            y = top + 64 + k * 27
            label = short(e["what"], run["design"])
            bad = "確定（total=80）" in label
            color = RED if bad else INK
            c.dot(tx(e["t"]), y + 9, 5, color)
            anchor = "ra" if tx(e["t"]) > 700 else "la"
            off = -12 if anchor == "ra" else 12
            c.text(tx(e["t"]) + off, y - 2, label, 17, color, anchor=anchor)
        # 列の値
        cur = [e for e in ev if e["t"] <= now]
        total = cur[-1]["total"] if cur else 88
        base = cur[-1]["base_total"] if cur else 0
        bx = 900
        for j, (col, val) in enumerate((("total", total), ("base_total", base))):
            y = top + 30 + j * 62
            untaxed = col == "total" and val == 80
            c.rect(bx, y, 260, 50, fill=RED_PALE if untaxed else FILL,
                   outline=RED if untaxed else LINE, width=2 if untaxed else 1)
            c.text(bx + 14, y + 12, col, 18, INK, mono=True)
            note = "税抜き" if untaxed else ("税込み" if col == "total" else ("税抜き・判定用" if val else "未使用"))
            c.text(bx + 246, y + 2, str(val), 24, RED if untaxed else INK, anchor="ra", mono=True)
            c.text(bx + 246, y + 31, note, 14, RED if untaxed else SUB, anchor="ra")
    return c.image()


def race_figure():
    data = json.loads((HERE / "lab" / "events.json").read_text())
    runs = [r for r in data if r["scene"] == "edit"]
    end = max(e["t"] for r in runs for e in r["events"])
    frames, durations = [], []
    step = 0.1
    t = -step
    while t < end:
        t = min(t + step, end)
        frames.append(race_frame(runs, t, end))
        durations.append(int(step / SPEED * 1000))
    durations[-1] = 3500  # 最後の状態で止める
    IMAGES.mkdir(exist_ok=True)
    frames[0].save(IMAGES / "race.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=80, method=6)


# ---------------------------------------------------------------- 書き手の図
def writers_panel(c, x, title, sub, cols):
    c.text(x, 28, title, 20)
    c.text(x, 60, sub, 13, SUB)
    writers = [("値引きの判定", 130), ("税の計算", 250)]
    for name, y in writers:
        c.rect(x, y, 170, 56, fill=FILL, outline=LINE, width=1)
        c.text(x + 85, y + 28, name, 16, anchor="mm")
    for col, y, bad in cols:
        c.rect(x + 300, y, 200, 56, fill=RED_PALE if bad else BLUE_PALE,
               outline=RED if bad else BLUE, width=2)
        c.text(x + 400, y + 18, col, 17, anchor="mm", mono=True)
        c.text(x + 400, y + 40, "税抜きと税込みが交互に入る" if bad else
               ("税抜き（判定用）" if col == "base_total" else "税込みだけ"), 12,
               RED if bad else SUB, anchor="mm")


def writers_figure():
    W, H = 1200, 360
    c = Canvas(W, H)
    # 左: 直す前
    writers_panel(c, 40, "直す前（Order）", "2 つの処理が同じ total に書く", [("total", 190, True)])
    c.arrow(210, 158, 338, 205, RED)
    c.arrow(210, 278, 338, 230, RED)
    # 右: 直した後
    writers_panel(c, 640, "直した後（PR #19801）", "書く列を処理ごとに分ける", [("base_total", 130, False), ("total", 250, False)])
    c.arrow(810, 158, 938, 158, BLUE)
    c.arrow(810, 278, 938, 278, BLUE)
    c.line(600, 30, 600, 330, LINE, 1)
    c.text(40, 334, "値引きの判定は税抜きの合計を SQL で比べるため、税の計算より前に DB へ書く必要がある", 13, SUB)
    save_webp(c.image(), "writers.webp")


# ---------------------------------------------------------------- 年表
def columns_figure():
    W, H = 1200, 470
    c = Canvas(W, H)
    c.text(40, 26, "Saleor の Order に「合計」の列が増えた順", 21)
    c.text(40, 58, "saleor/order/migrations と PR の日付から", 13, SUB)
    x0, x1, y = 90, 1130, 300
    tx = lambda yr: x0 + (x1 - x0) * (yr - 2015) / (2027 - 2015)
    c.line(x0, y, x1, y, INK, 2)
    for yr in range(2015, 2027):
        c.line(tx(yr), y - 6, tx(yr), y + 6, INK, 2)
        c.text(tx(yr), y + 14, str(yr), 13, SUB, anchor="ma")
    # (年, 列, 意味, 出典, 置く高さ)。高さは負なら軸の上、正なら軸の下
    items = [
        (2015.5, ["total"], "税抜き・税込み", "最初の migration", -110),
        (2021.2, ["undiscounted_total"], "値引き前", "#6930 注文に値引き", 50),
        (2021.35, ["total_paid"], "入金済み", "#7283", -110, "ra"),
        (2022.4, ["total_authorized", "total_charged"], "与信済みを追加、total_paid を改名", "#9795 決済の状態", -210),
        (2023.95, ["subtotal"], "送料を除いた小計", "#14887", 50),
        (2026.75, ["base_subtotal", "base_total"], "値引きの判定用", "#19801", -130),
    ]
    for yr, cols, mean, src, off, *side in items:
        x = tx(yr)
        top = y + off
        height = 26 * len(cols) + 56
        c.line(x, y, x, top + (height if off < 0 else 0), LINE, 1)
        c.dot(x, y, 6, RED if yr > 2026 else BLUE)
        anchor = side[0] if side else ("ra" if x > 900 else "la")
        bx = x - 8 if anchor == "ra" else x + 8
        for k, col in enumerate(cols):
            c.text(bx, top + k * 26, col, 15, INK, anchor=anchor, mono=True)
        c.text(bx, top + 26 * len(cols) + 4, mean, 14, INK, anchor=anchor)
        c.text(bx, top + 26 * len(cols) + 30, src, 12, SUB, anchor=anchor)
    save_webp(c.image(), "columns.webp")

# ---------------------------------------------------------------- コンテキストの図
def contexts_figure():
    W, H = 1200, 400
    c = Canvas(W, H)
    boxes = [
        (40, "値引き", ["合計 = カタログの値引き後", "税は含まない", "条件の判定に使う"]),
        (430, "税と請求", ["合計 = 小計 + 送料 + 税", "請求書と確定に使う", "値引きの結果を受け取る"]),
        (820, "決済", ["合計 = 入金済みの額", "与信済みの額は別に持つ", "請求額と比べる"]),
    ]
    for x, name, lines in boxes:
        c.rect(x, 40, 340, 230, fill=BLUE_PALE, outline=BLUE, width=2, r=14)
        c.text(x + 20, 54, name, 23)
        for k, ln in enumerate(lines):
            c.text(x + 20, 104 + k * 42, ln, 20)
    c.arrow(382, 155, 428, 155, INK)
    c.arrow(772, 155, 818, 155, INK)
    c.text(405, 120, "値引き額", 14, SUB, anchor="ma")
    c.text(795, 120, "請求額", 14, SUB, anchor="ma")
    c.rect(40, 310, 1120, 56, fill=FILL, outline=LINE, width=1)
    c.text(600, 338, "どのコンテキストも同じ注文 ID で対応付ける。合計という語の意味は枠ごとに 1 つ", 19, anchor="mm")
    for x in (210, 600, 990):
        c.line(x, 270, x, 310, LINE, 2)
    save_webp(c.image(), "contexts.webp")


# ---------------------------------------------------------------- コンテキストマップ
def contextmap_figure():
    W, H = 1200, 430
    c = Canvas(W, H)
    c.text(40, 24, "本記事の 3 つのコンテキストに当てはめたコンテキストマップ（説明用の一例）", 19)
    boxes = [(40, "値引き"), (400, "税と請求"), (760, "決済")]
    for x, name in boxes:
        c.rect(x, 150, 180, 110, fill=BLUE_PALE, outline=BLUE, width=2, r=14)
        c.text(x + 90, 205, name, 22, anchor="mm")
    # 外部の決済代行
    c.rect(1040, 150, 120, 110, fill=FILL, outline=SUB, width=2, r=14)
    c.text(1100, 192, "決済代行", 18, anchor="mm")
    c.text(1100, 224, "外部", 14, SUB, anchor="mm")
    # 渡すもの（矢印の上）と関係・上流と下流（矢印の下）
    links = [
        (220, 400, ["注文 ID", "値引き額"], "Customer/Supplier"),
        (580, 760, ["注文 ID", "請求額", "「注文が確定した」"], "Published Language"),
    ]
    for xa, xb, gives, rel in links:
        mid = (xa + xb) / 2
        c.arrow(xa + 4, 205, xb - 4, 205, INK)
        for k, g in enumerate(gives):
            c.text(mid, 192 - (len(gives) - k) * 24, g, 14, INK, anchor="ma")
        c.text(mid, 216, rel, 13, BLUE, anchor="ma", mono=True)
        c.text(xa + 6, 244, "上流", 13, SUB)
        c.text(xb - 6, 244, "下流", 13, SUB, anchor="ra")
    # 決済代行 → 決済（ACL）
    c.rect(944, 150, 16, 110, fill=RED_PALE, outline=RED, width=2, r=4)
    c.arrow(1036, 205, 964, 205, INK)
    c.text(1000, 180, "状態", 14, INK, anchor="ma")
    c.text(966, 244, "下流", 13, SUB)
    c.text(1034, 244, "上流", 13, SUB, anchor="ra")
    c.text(1000, 276, "Anticorruption Layer", 13, RED, anchor="ma", mono=True)
    c.text(1000, 298, "決済代行の語を決済の語に直す", 13, RED, anchor="ma")
    c.rect(40, 340, 1120, 56, fill=FILL, outline=LINE, width=1)
    c.text(600, 368, "矢印は情報が流れる向き。上流は判断が相手の成否を左右する側、下流は左右される側", 17, anchor="mm")
    save_webp(c.image(), "contextmap.webp")


# ---------------------------------------------------------------- コピーの図
def copies_figure():
    W, H = 1200, 360
    c = Canvas(W, H)
    c.text(40, 26, "見かけの機能で分けたサービスと、全体に入り込んだカテゴリ", 20)
    c.text(40, 58, "弁護士ドットコムの振り返り記事（2022-11-29）の記述から", 13, SUB)
    names = ["認証・決済", "ニュース", "他のサービス"]
    for k, n in enumerate(names):
        x = 40 + k * 390
        c.rect(x, 100, 340, 210, fill=FILL, outline=INK, width=2, r=14)
        c.text(x + 170, 130, n, 18, anchor="mm")
        c.rect(x + 30, 180, 280, 100, fill=RED_PALE, outline=RED, width=2, r=10)
        c.text(x + 170, 212, "カテゴリ管理のコピー", 16, RED, anchor="mm")
        c.text(x + 170, 248, "800 以上のカテゴリ", 14, SUB, anchor="mm")
    c.text(600, 336, "改修のたびに他のサービスへコピーしてテストし、デプロイの順序にも気を付ける", 14, SUB, anchor="mm")
    save_webp(c.image(), "copies.webp")



if __name__ == "__main__":
    race_figure()
    writers_figure()
    columns_figure()
    contexts_figure()
    contextmap_figure()
    copies_figure()
