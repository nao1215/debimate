#!/usr/bin/env python3
"""ERC-20 ノートの図を lab/output/results.json から作る。

Run: python3 content/notes/blockchain-systems/erc-20/figures.py
出力: images/ の WebP 3 枚（approve_race.webp は動く WebP）。
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
RED, RED_PALE = "#e15759", "#fbe3e3"
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
                                 fill=rgb(fill) if fill else None, outline=rgb(outline), width=width * S)

    def line(self, pts, color=SUB, width=2):
        self.d.line([(x * S, y * S) for x, y in pts], fill=rgb(color), width=width * S)

    def arrow(self, x1, y1, x2, y2, color=SUB):
        self.line([(x1, y1), (x2, y2)], color)
        self.d.polygon([(x2 * S, y2 * S), ((x2 - 9) * S, (y2 - 5) * S), ((x2 - 9) * S, (y2 + 5) * S)], fill=rgb(color))

    def final(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def save_webp(im, name):
    im.save(os.path.join(IMG, name), "WEBP", quality=90, method=6)


# ---------------------------------------------------------------- 1. 承認の付け替えの割り込み（動く WebP）

def lane_txs(race):
    """events から、トランザクションごとに送った時刻・ブロックに入った時刻・順番・成否を組み立てる。"""
    txs, pending = [], []
    for e in race["events"]:
        if e["kind"] == "owner_sent":
            label = {"approve": "approve(50)", "decrease": "decreaseAllowance(50)",
                     "zero_then": "approve(0)", "approve_50_after_zero": "approve(50)"}[e["change"]]
            t = {"who": "owner", "label": label, "sent": e["t"]}
            txs.append(t)
            pending.append(t)
        elif e["kind"] == "attacker_sent":
            t = {"who": "spender", "label": f"transferFrom({e['amount']})", "amount": e["amount"], "sent": e["t"]}
            txs.append(t)
            pending.append(t)
        elif e["kind"] == "block_mined":
            for o in e["order"]:
                # order の名前から、待っているトランザクションのどれかを決める
                who = "spender" if o["tx"].startswith("spender") else "owner"
                t = next(p for p in pending if p["who"] == who)
                pending.remove(t)
                t.update(mined=e["t"], block=e["block"], index=o["index"], ok=o["status"] == 1)
    return txs


def lane_state(txs, t):
    """時刻 t までにブロックに入ったトランザクションを順に当て、許可の残りと spender の受け取りを返す。"""
    allowance, got = 100, 0
    for x in sorted([x for x in txs if x.get("mined", 1e9) <= t], key=lambda x: (x["mined"], x["index"])):
        if not x["ok"]:
            continue
        lab = x["label"]
        if x["who"] == "spender":
            allowance -= x["amount"]
            got += x["amount"]
        elif lab.startswith("approve("):
            allowance = int(lab[8:-1])
        elif lab.startswith("decrease"):
            allowance -= 50
    return allowance, got


def race_figure(speed=0.5, step=0.1, hold=3.0):
    lanes = [("approve(50) で上書き", RES["race_approve"]),
             ("approve(0) の後に\napprove(50)", RES["race_zero_then"]),
             ("decreaseAllowance(50)\nで 50 を引く", RES["race_decrease"])]
    lanes = [(name, lane_txs(r)) for name, r in lanes]
    t_end = max(x["mined"] for _, txs in lanes for x in txs) + 0.3
    blocks = sorted({round(x["mined"], 1) for _, txs in lanes for x in txs})
    W, row_h, top = 1000, 172, 118
    H = top + row_h * len(lanes) + 10
    x_pool, x_blk, x_res = 230, 470, 820

    def frame(t):
        c = Canvas(W, H)
        c.text(20, 12, "許可を 100 から 50 に下げるトランザクションを、spender が見て割り込む", size=17)
        c.text(20, 42, f"経過 {t:.1f} 秒", size=20)
        c.text(20, 74, f"ローカルの Anvil で実測。2 秒ごとにブロックを作る。{speed:g} 倍速で再生", size=13, color=SUB)
        # 時間の帯
        bx0, bx1, by = 560, 970, 56
        c.line([(bx0, by), (bx1, by)], "#cfcfcf", 3)
        for b in blocks:
            xx = bx0 + (bx1 - bx0) * b / t_end
            c.line([(xx, by - 7), (xx, by + 7)], SUB, 1)
        c.text(bx0 - 4, by + 10, "0 秒", size=12, color=SUB)
        c.text(bx1 - 34, by + 10, f"{t_end:.1f} 秒", size=12, color=SUB)
        c.text(bx0 + (bx1 - bx0) * blocks[0] / t_end - 50, by - 32, "ブロックを作った時刻", size=12, color=SUB)
        xx = bx0 + (bx1 - bx0) * min(t, t_end) / t_end
        c.d.ellipse([(xx - 7) * S, (by - 7) * S, (xx + 7) * S, (by + 7) * S], fill=rgb(INK))
        c.text(x_pool, top - 26, "待っているトランザクション（mempool）", size=14, color=SUB)
        c.text(x_blk, top - 26, "ブロックに入った順", size=14, color=SUB)
        c.text(x_res, top - 26, "spender の受け取り", size=14, color=SUB)
        for i, (name, txs) in enumerate(lanes):
            y = top + i * row_h
            for k, part in enumerate(name.split("\n")):
                c.text(20, y + 40 + k * 24, part, size=15)
            c.box(x_pool, y, 220, row_h - 20, FILL)
            c.box(x_blk, y, 330, row_h - 20, "#ffffff")
            c.arrow(x_pool + 222, y + (row_h - 20) / 2, x_blk - 4, y + (row_h - 20) / 2)
            waiting = [x for x in txs if x["sent"] <= t and x.get("mined", 1e9) > t]
            for k, x in enumerate(waiting[:3]):
                col = RED if x["who"] == "spender" else INK
                c.box(x_pool + 10, y + 10 + k * 36, 200, 28, "#ffffff", col, 2, 6)
                c.text(x_pool + 16, y + 15 + k * 36, x["label"], size=12, color=col, mono=True)
            mined = sorted([x for x in txs if x.get("mined", 1e9) <= t], key=lambda x: (x["mined"], x["index"]))
            for k, x in enumerate(mined[:4]):
                col = RED if x["who"] == "spender" else INK
                yy = y + 10 + k * 36
                c.text(x_blk + 8, yy + 5, f"#{x['block']}", size=13, color=SUB)
                c.box(x_blk + 50, yy, 200, 28, "#ffffff" if x["ok"] else FILL, col if x["ok"] else LINE, 2, 6)
                c.text(x_blk + 56, yy + 5, x["label"], size=12, color=col if x["ok"] else SUB, mono=True)
                if not x["ok"]:
                    c.line([(x_blk + 56, yy + 14), (x_blk + 244, yy + 14)], SUB, 1)
                    c.text(x_blk + 258, yy + 5, "失敗", size=12, color=SUB)
            allowance, got = lane_state(txs, t)
            over = got > 100
            c.box(x_res, y, 160, row_h - 20, RED_PALE if over else "#ffffff", RED if over else LINE, 2 if over else 1)
            c.text(x_res + 80, y + 22, str(got), size=34, color=RED if over else INK, anchor="ma")
            c.text(x_res + 80, y + 78, f"残りの許可 {allowance}", size=14, color=SUB, anchor="ma")
        return c.final()

    frames, durs = [], []
    n = int(t_end / step) + 1
    for i in range(n):
        frames.append(frame(i * step))
        durs.append(int(step / speed * 1000))
    durs[-1] = int(hold * 1000)
    frames[0].save(os.path.join(IMG, "approve_race.webp"), "WEBP", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, quality=55, method=6)
    return sum(durs) / 1000


# ---------------------------------------------------------------- 2. 残高の置き場所

def storage_figure():
    st = RES["storage"]
    eth_b, eth_a = st["receiver_eth_before_wei"] / 10**18, st["receiver_eth_after_wei"] / 10**18
    tok_b, tok_a = st["storage_before"] / 10**18, st["storage_after"] / 10**18
    W, H = 980, 380
    c = Canvas(W, H)
    c.text(20, 14, "100 STU を送った前後で、受取人の何が変わったか", size=17)
    # 左: アカウントの状態
    c.box(20, 60, 300, 290, FILL)
    c.text(36, 74, "受取人のアカウント", size=15)
    c.text(36, 100, "Ethereum 自体が持つ状態", size=12, color=SUB)
    c.box(36, 140, 268, 70, "#ffffff")
    c.text(50, 152, "ETH の残高（eth_getBalance）", size=12, color=SUB)
    c.text(50, 176, f"{eth_b:,.0f} → {eth_a:,.0f} ETH", size=16)
    c.text(36, 228, "変わらない。トークンの残高は", size=13, color=SUB)
    c.text(36, 250, "ここには無い", size=13, color=SUB)
    # 右: トークンのコントラクト
    c.box(360, 60, 600, 290, PALE)
    c.text(376, 74, "STU のコントラクト（1 つのアドレス）", size=15)
    c.text(376, 100, "コントラクトのストレージにある 2 つの表", size=12, color=SUB)
    # balanceOf
    c.box(376, 135, 280, 200, "#ffffff")
    c.text(390, 145, "balanceOf", size=14, mono=True)
    c.text(390, 172, "アドレス → 残高", size=12, color=SUB)
    c.text(390, 210, "送った人", size=13)
    c.text(640, 210, "1,000 → 900", size=13, anchor="ra")
    c.box(384, 240, 264, 34, RED_PALE, RED, 2, 6)
    c.text(392, 247, "受取人", size=13)
    c.text(640, 247, f"{tok_b:,.0f} → {tok_a:,.0f}", size=13, color=RED, anchor="ra")
    c.text(390, 292, "transfer が書き換える", size=12, color=SUB)
    # allowance
    c.box(670, 135, 276, 200, "#ffffff")
    c.text(684, 145, "allowance", size=14, mono=True)
    c.text(684, 172, "所有者 → spender → 上限", size=12, color=SUB)
    c.text(684, 210, "所有者が approve で書き、", size=12, color=SUB)
    c.text(684, 232, "spender の transferFrom が減らす", size=12, color=SUB)
    c.text(684, 292, "この実験では空のまま", size=12, color=SUB)
    save_webp(c.final(), "balance_storage.webp")


# ---------------------------------------------------------------- 3. 規格から外れたトークンと預け入れの書き方

def matrix_figure():
    rows = [("StandardToken", "EIP-20 の書き方どおり", "成功で true、失敗で revert"),
            ("NoReturnToken", "戻り値なし（USDT 型）", "関数が何も返さない"),
            ("FalseToken", "失敗で false（ZRX 型）", "残高 0 の人が 100 を預ける"),
            ("FeeToken", "手数料で減る（STA 型）", "実験は 2%、100 を送ると 98 が届く")]
    cols = [("depositRequire", "1. 戻り値を require"), ("depositIgnore", "2. 戻り値を見ない"),
            ("depositSafe", "3. SafeERC20 の判定"), ("depositMeasured", "4. SafeERC20 + 残高の差")]
    cell = {(r["token"], r["style"]): r for r in RES["matrix"]}
    W, x0, cw, top, rh = 1000, 250, 185, 96, 78
    H = top + rh * len(rows) + 50
    c = Canvas(W, H)
    c.text(20, 14, "Vault に 100 を預けた結果: 記帳した額 / 実際に届いた額", size=17)
    for j, (_, lab) in enumerate(cols):
        c.text(x0 + j * cw + cw / 2, top - 30, lab, size=13, color=SUB, anchor="ma")
    for i, (tok, lab, sub) in enumerate(rows):
        y = top + i * rh
        c.text(20, y + 16, lab, size=14)
        c.text(20, y + 42, sub, size=11, color=SUB)
        for j, (style, _) in enumerate(cols):
            r = cell[(tok, style)]
            x = x0 + j * cw
            bad = r["status"] == 1 and r["credited"] != r["vault_received"]
            if r["status"] == 0:
                c.box(x + 6, y + 6, cw - 12, rh - 12, "#e9e9e9", "#c8c8c8")
                c.text(x + cw / 2, y + 26, "取り消し（revert）", size=13, color=SUB, anchor="ma")
            else:
                c.box(x + 6, y + 6, cw - 12, rh - 12, RED_PALE if bad else "#ffffff", RED if bad else "#c8c8c8", 2 if bad else 1)
                c.text(x + cw / 2, y + 16, f"記帳 {r['credited']:g}", size=14, color=RED if bad else INK, anchor="ma")
                c.text(x + cw / 2, y + 40, f"届いた {r['vault_received']:g}", size=14, color=RED if bad else INK, anchor="ma")
    c.box(20, H - 36, 18, 18, RED_PALE, RED, 2, 3)
    c.text(46, H - 36, "トランザクションは成功したのに、記帳と届いた額が食い違う", size=12, color=SUB)
    c.box(420, H - 36, 18, 18, "#e9e9e9", "#c8c8c8", 1, 3)
    c.text(446, H - 36, "トランザクションごと取り消された", size=12, color=SUB)
    save_webp(c.final(), "deposit_matrix.webp")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    print("approve_race.webp", race_figure(), "秒")
    storage_figure()
    matrix_figure()
