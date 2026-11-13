"""Anticorruption Layer のノートの図を作る（Pillow だけを使う）。

図の中の動き（どの関数が何を返したか）は、lab/ の no_acl.py と acl.py を import して
その場で計算する。本文の出力（lab/output.txt）と図が食い違わないようにするため。

実行: python3 content/notes/software-architecture/anti-corruption-layer/figures.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
import acl  # noqa: E402
import no_acl  # noqa: E402

S = 2  # 2 倍で描いて縮める
INK, SUB, RED, LINE = "#1f1f1f", "#666666", "#c62828", "#9a9a9a"
FILL, PALE, RED_PALE, WHITE = "#f2f2f2", "#eaf1f5", "#fbe9e7", "#ffffff"
ACCENT = "#4f7ea8"
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

PLACES = ["shipping", "mail", "sales", "stock"]
LABEL = {"shipping": "出荷", "mail": "メール", "sales": "売上", "stock": "在庫"}
EXPECTED = {"shipping": "出荷を待つ", "mail": "送らない", "sales": "計上しない", "stock": "引当を保つ"}
REVIEW = {"payment_id": "pay_0042", "status": "REVIEW", "amount": 3980}
V1 = ["PAID", "PENDING", "FAILED"]


def font(n, mono=False):
    return ImageFont.truetype(MONO if mono else JP, n * S)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w * S, h * S), WHITE)
        self.d = ImageDraw.Draw(self.img)

    def text(self, x, y, s, size=16, color=INK, anchor="la", mono=False):
        self.d.text((x * S, y * S), s, font=font(size, mono), fill=color, anchor=anchor)

    def box(self, x, y, w, h, fill=FILL, outline=LINE, width=2, r=8):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S,
                                 fill=fill, outline=outline, width=width * S)

    def line(self, pts, color=LINE, width=2):
        self.d.line([(x * S, y * S) for x, y in pts], fill=color, width=width * S)

    def arrow(self, x1, y1, x2, y2, color=LINE, width=2):
        self.line([(x1, y1), (x2, y2)], color, width)
        self.d.polygon([(x2 * S, y2 * S), ((x2 - 9) * S, (y2 - 5) * S), ((x2 - 9) * S, (y2 + 5) * S)], fill=color)

    def save_webp(self, name):
        out = self.img.resize((self.w, self.h), Image.LANCZOS)
        out.save(HERE / "images" / name, "WEBP", quality=90, method=6)


def like_v1(i, got):
    """v1 のどの値と同じ動きか。A の 4 か所が REVIEW を何として読んだかを出す。"""
    hits = [st for st in V1 if no_acl_actions({"payment_id": "x", "status": st, "amount": 1})[i] == got]
    return hits


def no_acl_actions(p):
    return [getattr(no_acl, f)(p) for f in PLACES]


def acl_actions(p):
    s = acl.translate(p)
    return [getattr(acl, f)(s) for f in PLACES]


def panel(c, y0, title, actions, with_acl):
    """1 つの実装の図。左に届いた値、真ん中に 4 か所、右に動き。y0 は panel の上端。"""
    x0 = 24
    c.text(x0, y0, title, 20)
    ys = [y0 + 44 + i * 74 for i in range(4)]
    mid = (ys[0] + ys[-1]) / 2 + 28
    # 届いた値
    c.box(x0, mid - 36, 130, 72, fill=RED_PALE, outline=RED)
    c.text(x0 + 65, mid - 13, "status", 15, SUB, "mm", mono=True)
    c.text(x0 + 65, mid + 13, "REVIEW", 19, RED, "mm", mono=True)
    fan_x = x0 + 130
    if with_acl:
        c.box(x0 + 160, mid - 74, 140, 148, fill=PALE, outline=ACCENT, width=3)
        c.text(x0 + 230, mid - 42, "ACL", 20, ACCENT, "mm")
        c.text(x0 + 230, mid - 8, "translate()", 15, SUB, "mm", mono=True)
        c.text(x0 + 230, mid + 26, "→ 確認中", 18, INK, "mm")
        c.text(x0 + 230, mid + 54, "ログに 1 行", 14, SUB, "mm")
        c.arrow(fan_x, mid, x0 + 158, mid)
        fan_x = x0 + 300
    place_x = x0 + 360
    for i, f in enumerate(PLACES):
        y = ys[i] + 28
        c.line([(fan_x, mid), (fan_x + 16, mid), (fan_x + 16, y), (place_x - 2, y)])
        c.d.polygon([(place_x * S, y * S), ((place_x - 9) * S, (y - 5) * S), ((place_x - 9) * S, (y + 5) * S)], fill=LINE)
        c.box(place_x, ys[i], 96, 56)
        c.text(place_x + 48, y, LABEL[f], 18, INK, "mm")
        ok = actions[i] == EXPECTED[f]
        rx = place_x + 126
        c.arrow(place_x + 96, y, rx - 2, y)
        c.box(rx, ys[i] - 4, 330, 64, fill=WHITE if ok else RED_PALE, outline=LINE if ok else RED, width=2)
        sub = "確認中として扱う" if with_acl else "・".join(like_v1(i, actions[i])) + " と同じ扱い"
        c.text(rx + 14, ys[i] + 5, sub, 15, SUB)
        c.text(rx + 14, ys[i] + 29, actions[i] + ("（誤り）" if not ok else ""), 18, INK if ok else RED)
    wrong = sum(a != EXPECTED[f] for a, f in zip(actions, PLACES))
    c.text(x0 + 360, ys[-1] + 74, f"誤り {wrong}/4 か所、例外 0 件", 18, RED if wrong else INK)


def cover_figure():
    c = Canvas(880, 860)
    c.text(24, 18, "status が REVIEW の支払い 1 件を、4 か所がどう扱ったか（lab/run.py の実測）", 16, SUB)
    panel(c, 60, "A: ACL なし（4 か所が上流の値をそのまま読む）", no_acl_actions(REVIEW), False)
    c.line([(24, 452), (856, 452)], "#d0d0d0", 2)
    panel(c, 474, "C: ACL あり（知らない値は「確認中」に翻訳）", acl_actions(REVIEW), True)
    c.save_webp("acl_review_cover.webp")


# 分岐の作り。no_acl.py の if と else の並びを、そのまま箱にしたもの
BRANCHES = {
    "shipping": [(["PAID"], "出荷する"), (["FAILED"], "取り消す"), (["PENDING"], "出荷を待つ")],
    "mail": [(["PAID"], "お礼のメール"), (["FAILED"], "失敗のメール"), (["PENDING"], "入金案内のメール")],
    "sales": [(["PENDING", "FAILED"], "計上しない"), (["PAID"], "計上する")],
    "stock": [(["PAID", "PENDING"], "引当を保つ"), (["FAILED"], "引当を外す")],
}


def else_figure():
    """各関数の分岐を、v1 の値の箱として並べる。最後の箱が else で、REVIEW はそこに落ちる。"""
    # 図の箱が no_acl.py の動きと合っているかを、v1 の値で照合してから描く
    for f, branches in BRANCHES.items():
        for values, action in branches:
            for v in values:
                assert getattr(no_acl, f)({"payment_id": "x", "status": v, "amount": 1}) == action, (f, v)
        assert getattr(no_acl, f)(REVIEW) == branches[-1][1], f
    c = Canvas(960, 470)
    c.text(24, 22, "no_acl.py の分岐。右端の箱が else で、REVIEW は書いた時に残っていた値と同じ箱に入る", 17, SUB)
    for i, f in enumerate(PLACES):
        y = 70 + i * 98
        c.box(24, y, 80, 70)
        c.text(64, y + 35, LABEL[f], 17, INK, "mm")
        x = 140
        for j, (values, action) in enumerate(BRANCHES[f]):
            last = j == len(BRANCHES[f]) - 1
            w = 300 if len(values) == 2 or last else 230
            c.box(x, y, w, 70, fill=WHITE, outline=RED if last else LINE, width=2)
            head = "else" if last else ("if " if j == 0 else "elif ")
            c.text(x + 10, y + 8, head, 13, RED if last else SUB, mono=True)
            vx = x + 10
            for v in values:
                c.box(vx, y + 32, 14 + len(v) * 10, 28, fill=FILL, outline=LINE, width=1, r=5)
                c.text(vx + 7 + len(v) * 5, y + 46, v, 13, INK, "mm", mono=True)
                vx += 22 + len(v) * 10
            if last:
                c.box(vx, y + 32, 14 + 6 * 10, 28, fill=RED_PALE, outline=RED, width=2, r=5)
                c.text(vx + 7 + 30, y + 46, "REVIEW", 13, RED, "mm", mono=True)
            c.text(x + w - 10, y + 8, f"→ {action}", 14, RED if last else INK, "ra")
            x += w + 16
    c.save_webp("acl_else_branches.webp")


def placement_figure():
    """ACL を置く位置。左が決済サービスの語、右が通販の語で、境目に translate() を置く。"""
    c = Canvas(1100, 430)
    c.text(24, 18, "実験のコードに当てはめた、ACL と業務規則を置く位置", 17, SUB)
    c.box(20, 60, 330, 340, fill=FILL, outline=LINE, width=2, r=12)
    c.text(185, 88, "決済サービスの語", 20, SUB, "mm")
    c.box(500, 60, 580, 340, fill=PALE, outline=ACCENT, width=2, r=12)
    c.text(790, 88, "通販の語", 20, ACCENT, "mm")
    # 上流側
    c.box(60, 120, 250, 70, fill=WHITE)
    c.text(185, 145, "決済サービスの API", 18, INK, "mm")
    c.text(185, 170, "status: PAID / PENDING / …", 15, SUB, "mm", mono=True)
    c.box(60, 250, 250, 70, fill=WHITE)
    c.text(185, 275, "SDK の型", 18, INK, "mm")
    c.text(185, 300, "上流のモデルをそのまま写す", 15, SUB, "mm")
    c.line([(185, 190), (185, 247)])
    c.d.polygon([(185 * S, 250 * S), (180 * S, 241 * S), (190 * S, 241 * S)], fill=LINE)
    # ACL
    c.box(380, 200, 150, 120, fill=WHITE, outline=ACCENT, width=3)
    c.text(455, 232, "ACL", 20, ACCENT, "mm")
    c.text(455, 262, "translate()", 16, INK, "mm", mono=True)
    c.text(455, 292, "語を置き換える", 15, SUB, "mm")
    c.arrow(310, 285, 378, 285, ACCENT, 3)
    # 下流側
    c.box(570, 210, 170, 100, fill=WHITE)
    c.text(655, 245, "PaymentState", 17, INK, "mm", mono=True)
    c.text(655, 275, "4 つで閉じた状態", 15, SUB, "mm")
    c.arrow(530, 260, 568, 260, ACCENT, 3)
    c.box(780, 120, 270, 70, fill=WHITE)
    c.text(915, 145, "業務規則（ACTIONS の表）", 17, INK, "mm")
    c.text(915, 170, "確認中なら出荷を待つ", 15, SUB, "mm")
    c.arrow(740, 240, 778, 165)
    labels = ["出荷", "メール", "売上", "在庫"]
    for k, lab in enumerate(labels):
        x = 790 + k * 66
        c.box(x, 300, 56, 44, fill=WHITE)
        c.text(x + 28, 322, lab, 16, INK, "mm")
    c.line([(915, 190), (915, 265)])
    c.line([(818, 265), (1016, 265)])
    for k in range(4):
        x = 790 + k * 66 + 28
        c.line([(x, 265), (x, 290)])
        c.d.polygon([(x * S, 299 * S), ((x - 5) * S, 290 * S), ((x + 5) * S, 290 * S)], fill=LINE)
    c.save_webp("acl_placement.webp")


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    cover_figure()
    else_figure()
    placement_figure()
