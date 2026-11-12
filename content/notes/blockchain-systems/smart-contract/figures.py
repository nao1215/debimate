#!/usr/bin/env python3
"""Smart Contract ノートの図を lab/output/results.json から作る。

Run: python3 content/notes/blockchain-systems/smart-contract/figures.py
出力: images/ の WebP 3 枚（lottery、replay、storage）。
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "images")
RES = json.load(open(os.path.join(HERE, "lab", "output", "results.json")))

JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
INK, SUB, LINE = "#1f1f1f", "#666666", "#bdbdbd"
FILL, PALE = "#f2f2f2", "#eaf1f5"
WIN = "#3a5a6e"
RED, RED_PALE = "#d1495b", "#fbe3e3"
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

    def rect(self, x, y, w, h, fill="#ffffff", outline=LINE, width=1):
        self.d.rectangle([x * S, y * S, (x + w) * S, (y + h) * S],
                         fill=rgb(fill) if fill else None, outline=rgb(outline) if outline else None, width=width * S)

    def box(self, x, y, w, h, fill="#ffffff", outline=LINE, width=1, r=8):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S,
                                 fill=rgb(fill) if fill else None, outline=rgb(outline), width=width * S)

    def final(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def save_webp(im, name):
    im.save(os.path.join(IMG, name), "WEBP", quality=90, method=6)


def lottery():
    """表紙: 適当に選んだ番号と Predictor の当たりの数。1 回を 1 マスで描く。"""
    s = RES["lottery"]["summary"]
    grid = RES["replay"]["grid"]
    rows = [("適当に選ぶ", "アカウントから play を呼ぶ", s["guess"], grid["guess"]["A"]),
            ("計算してから選ぶ", "Predictor が同じトランザクションで", s["predictor"], grid["predictor"]["A"])]
    c = Canvas(1000, 360)
    c.text(30, 22, "ブロックの値で当たり番号を作る抽選に、100 回ずつ参加", 26)
    c.text(30, 64, "1 マスが 1 回で、左から参加した順。濃いマスが当たり、白いマスが外れ", 17, SUB)
    x0, cell = 300, 5.4
    for i, (title, sub, r, st) in enumerate(rows):
        y = 112 + i * 100
        c.text(30, y, title, 22)
        c.text(30, y + 34, sub, 15, SUB)
        wins = r["wins"]
        assert sum(st) == wins and len(st) == 100
        for k, v in enumerate(st):
            c.rect(x0 + k * cell, y, cell - 1, 58, fill=WIN if v else "#ffffff", outline=None if v else LINE)
        c.text(x0 + 100 * cell + 16, y + 2, f"{wins} 回", 28)
        c.text(x0 + 100 * cell + 16, y + 40, "当たり", 15, SUB)
    c.text(30, 318, f"外れた {100 - s['guess']['wins']} 回は取り消されたが、手数料は払った（手元の anvil で実行）", 17, SUB)
    save_webp(c.final(), "smart-contract_lottery.webp")


def replay():
    """ブロックの時刻だけを変えて、適当に選んだ 100 回を実行し直した当たり外れを並べる。"""
    g = RES["replay"]["grid"]["guess"]
    a = g["A"]
    rows = [("ノード A", "元のブロック", g["A"]),
            ("ノード B", "時刻を A に揃える", g["B"]),
            ("ノード C", "時刻を 1 秒ずらす", g["C"])]
    c = Canvas(1000, 452)
    c.text(30, 22, "ブロックの時刻だけを変えて、同じトランザクションを実行し直す", 24)
    c.text(30, 62, "濃いマスが当たり（適当に選んだ 100 回）。赤い枠は、時刻を変えて当たり外れが変わった回", 17, SUB)
    x0, cell = 250, 5.6
    for i, (name, sub, st) in enumerate(rows):
        y = 108 + i * 92
        c.text(30, y, name, 22)
        c.text(30, y + 34, sub, 15, SUB)
        for k, v in enumerate(st):
            diff = v != a[k]
            c.rect(x0 + k * cell, y, cell - 1.2, 56, fill=WIN if v else "#ffffff",
                   outline=RED if diff else (None if v else LINE), width=2 if diff else 1)
        nd = sum(1 for k, v in enumerate(st) if v != a[k])
        c.text(x0 + 100 * cell + 16, y, f"当たり {sum(st)} 回", 20)
        c.text(x0 + 100 * cell + 16, y + 32, "A と同じ" if nd == 0 else f"時刻で変わった {nd} 回", 16, RED if nd else SUB)
    for k in (0, 49, 99):
        c.text(x0 + k * cell + cell / 2, 386, f"{k + 1}", 15, SUB, anchor="ma")
    c.text(x0 - 12, 386, "回目", 15, SUB, anchor="ra")
    c.text(30, 420, "手元の anvil で時刻を指定した実験。実際のノードは受け取ったブロックの時刻で実行するので、結果は揃う", 15, SUB)
    save_webp(c.final(), "smart-contract_replay.webp")


def storage():
    """Quiz の slot 1 の 32 バイトに、private の answer がそのまま入っている様子。"""
    q = RES["quiz"]
    slot1 = bytes.fromhex(q["slot1"][2:])
    n = len(q["decoded"])
    c = Canvas(1000, 330)
    c.text(30, 22, "eth_getStorageAt で読んだ Quiz の slot 1（private の answer）", 24)
    c.text(30, 62, "1 マスが 1 バイト。31 バイト以下の文字列は、先頭に中身、末尾に長さ × 2", 17, SUB)
    x0, y0, cell = 30, 112, 29.4
    for i, b in enumerate(slot1):
        used = i < n
        fill = RED_PALE if used else (PALE if i == 31 else FILL)
        c.rect(x0 + i * cell, y0, cell - 3, 48, fill=fill, outline=RED if used else LINE)
        c.text(x0 + i * cell + (cell - 3) / 2, y0 + 14, f"{b:02x}", 15, INK, mono=True, anchor="ma")
        if used:
            c.text(x0 + i * cell + (cell - 3) / 2, y0 + 62, chr(b), 24, RED, mono=True, anchor="ma")
    c.text(x0, y0 + 112, f"先頭の {n} バイト: 文字列 \"{q['decoded']}\"", 18, RED)
    right = x0 + 31 * cell + (cell - 3)
    c.text(right, y0 + 62, f"0x{slot1[-1]:02x} = {slot1[-1]}", 17, SUB, anchor="ra")
    c.text(right, y0 + 90, f"長さ {n} × 2", 17, SUB, anchor="ra")
    c.text(x0, y0 + 160, "private を付けても、ノードに問い合わせれば誰でもこの 32 バイトを読める", 18, SUB)
    save_webp(c.final(), "smart-contract_storage.webp")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    lottery()
    replay()
    storage()
