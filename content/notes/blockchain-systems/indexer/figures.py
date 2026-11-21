#!/usr/bin/env python3
"""インデクサーのノートの図を lab/output/results.json から作る。

Run: python3 content/notes/blockchain-systems/indexer/figures.py
出力: images/ の WebP 3 枚（reorg.webp は動く WebP）。
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
GREEN, GREEN_PALE = "#3b7d4f", "#e3f1e6"
GHOST = "#b0b0b0"
S = 2  # 2 倍で描いて縮める
NAMES = ["alice", "bob", "carol", "dave"]


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


def step(prefix):
    return next(s for s in RES["steps"] if s["label"].startswith(prefix))


# ---------------------------------------------------------------- 1. 全体像（表紙）

def overview_figure():
    W, H = 980, 400
    c = Canvas(W, H)
    c.text(20, 14, "ノードはブロック単位で答え、インデクサーは問いに合わせた表で答える", size=17)

    # ノード: ブロックの列
    c.box(20, 60, 220, 300, FILL)
    c.text(36, 74, "ノード", size=15)
    c.text(36, 98, "ブロックを番号順に持つ", size=12, color=SUB)
    chain = step("block 4")["chain"]
    for i, b in enumerate(chain):
        y = 130 + i * 44
        c.box(36, y, 188, 36, "#ffffff")
        c.text(46, y + 8, f"block {b['number']}", size=12)
        c.text(214, y + 9, b["hash"], size=11, color=SUB, mono=True, anchor="ra")
    c.text(36, 318, "聞ける: block 3 の中身は？", size=12, color=SUB)

    # インデクサー: 取得・変換・保存
    c.arrow(244, 210, 282, 210)
    c.box(286, 60, 200, 300, PALE)
    c.text(302, 74, "インデクサー", size=15)
    for i, (head, sub) in enumerate([("取得", "ブロックとログを取る"), ("変換", "ABI で意味のある値に"),
                                     ("保存", "DB に行として入れる")]):
        y = 112 + i * 76
        c.box(302, y, 168, 60, "#ffffff")
        c.text(314, y + 8, head, size=14)
        c.text(314, y + 32, sub, size=12, color=SUB)
        if i < 2:
            c.line([(386, y + 61), (386, y + 70)], SUB, 2)
            c.d.polygon([(386 * S, (y + 76) * S), (381 * S, (y + 68) * S), (391 * S, (y + 68) * S)], fill=rgb(SUB))
    c.text(302, 340, "どこまで取り込んだかを記録", size=12, color=SUB)

    # DB: 送金の表
    c.arrow(490, 210, 528, 210)
    c.box(532, 60, 250, 300, "#ffffff")
    c.text(548, 74, "DB の表（transfers）", size=15)
    c.text(548, 98, "Transfer ログ 1 件が 1 行", size=12, color=SUB)
    rows = [("block", "from", "to", "量")] + [("1", "-", "alice", "1000"), ("2", "alice", "bob", "100"),
                                               ("3", "alice", "carol", "50"), ("4", "bob", "carol", "30")]
    for i, r in enumerate(rows):
        y = 130 + i * 34
        col = SUB if i == 0 else INK
        for x, v in zip((548, 600, 664, 766), r):
            c.text(x, y, v, size=12, color=col, anchor="ra" if x == 766 else "la")
        if i == 0:
            c.line([(548, y + 24), (766, y + 24)], LINE, 1)
    for y in (196, 264):  # bob が出てくる行
        c.box(544, y, 230, 30, None, RED, 2, 6)

    # アプリ
    c.arrow(786, 210, 824, 210)
    c.box(828, 60, 132, 300, FILL)
    c.text(844, 74, "アプリ", size=15)
    c.text(844, 98, "API で問い合わせる", size=12, color=SUB)
    c.box(844, 150, 100, 110, "#ffffff")
    c.text(854, 160, "bob の履歴", size=12)
    c.text(854, 190, "+100 alice", size=11, mono=True)
    c.text(854, 214, "-30  carol", size=11, mono=True)
    c.text(844, 300, "聞ける: bob の", size=12, color=SUB)
    c.text(844, 320, "送金の一覧は？", size=12, color=SUB)
    save_webp(c.final(), "overview.webp")


# ---------------------------------------------------------------- 2. ログが出る送金と出ない送金

def logs_figure():
    et = RES["eth_transfer"]
    W, H = 980, 330
    c = Canvas(W, H)
    c.text(20, 14, "同じ block 3 に入った 2 つの送金と、それぞれのレシートのログ", size=17)
    panels = [
        ("トークンの送金", "Token.transfer(carol, 50)", ["Transfer(alice, carol, 50)"], PALE, LINE),
        ("ETH の送金", "to: carol, value: 1 ETH", [], RED_PALE, RED),
    ]
    for i, (title, call, logs, fill, edge) in enumerate(panels):
        x = 20 + i * 480
        c.box(x, 60, 460, 200, fill, edge, 2 if i else 1)
        c.text(x + 16, 74, title, size=15)
        c.text(x + 16, 104, call, size=13, mono=True)
        c.text(x + 16, 140, f"status: {et['status'] if i else '0x1'}（成功）", size=12, color=SUB)
        c.box(x + 16, 170, 428, 74, "#ffffff")
        c.text(x + 28, 180, "logs", size=12, color=SUB, mono=True)
        if logs:
            c.text(x + 28, 206, logs[0], size=13, mono=True)
        else:
            c.text(x + 28, 206, "[]", size=13, mono=True, color=RED)
            c.text(x + 52, 204, "空", size=13, color=RED)
    c.text(20, 284, f"Transfer のログを集めると {RES['log_count']} 件。右の 1 ETH は、成功していてもその中に現れない", size=14)
    save_webp(c.final(), "logs_vs_eth.webp")


# ---------------------------------------------------------------- 3. reorg（動く WebP）

def block_row(c, x0, y, chain, color_of):
    for i, b in enumerate(chain):
        x = x0 + i * 150
        fill, edge, ink = color_of(b)
        c.box(x, y, 130, 56, fill, edge, 2 if edge == RED else 1)
        c.text(x + 10, y + 6, f"block {b['number']}  {b['hash']}", size=11, color=ink, mono=True)
        txt = (b["txs"][0] if b["txs"] else "（空）").replace("トークンを作る（alice に 1000）", "alice に 1000")
        c.text(x + 10, y + 30, txt, size=12, color=ink)
        if i:
            c.line([(x - 20, y + 28), (x, y + 28)], ink if ink == GHOST else SUB, 2)


def reorg_frame(s, old_chain, message, note):
    W, H = 980, 470
    c = Canvas(W, H)
    c.text(20, 14, "reorg の前後で、2 つのインデクサーが持つ残高", size=17)
    c.text(960, 18, s["label"].split(":")[0].replace("reorg", "reorg の直後"), size=13, color=SUB, anchor="ra")

    chain = s["chain"]
    c.text(20, 56, "ノードが持つチェーン", size=13, color=SUB)
    if old_chain:
        # 捨てられたブロックを上の段に薄く描く
        ghosts = [b for b in old_chain if b["number"] >= 3]
        block_row(c, 20 + 2 * 150, 78, ghosts, lambda b: ("#ffffff", "#dddddd", GHOST))
        c.text(20 + 4 * 150 + 10, 98, "捨てられたブロック", size=12, color=GHOST)
        c.line([(300, 168), (320, 106)], GHOST, 2)
    replaced = {b["number"] for b in chain} if old_chain else set()
    block_row(c, 20, 140, chain, lambda b: (GREEN_PALE if old_chain and b["number"] >= 3 else "#ffffff",
                                             LINE, INK))

    # 残高の表
    y0 = 230
    c.text(20, y0, "トークンの残高", size=13, color=SUB)
    xs = [380, 520, 660, 800]
    for x, n in zip(xs, NAMES):
        c.text(x, y0 + 30, n, size=13, color=SUB, anchor="ra")
    rows = [("ノード（balanceOf の値）", s["truth"]), ("素朴なインデクサー", s["naive"]),
            ("ハッシュを記録するインデクサー", s["careful"])]
    for i, (label, vals) in enumerate(rows):
        y = y0 + 60 + i * 42
        wrong = i and any(vals.get(n, 0) != s["truth"][n] for n in NAMES)
        c.box(20, y - 6, 800, 34, RED_PALE if wrong else (FILL if i == 0 else "#ffffff"),
              RED if wrong else LINE, 1, 6)
        c.text(32, y, label, size=13)
        for x, n in zip(xs, NAMES):
            v = vals.get(n, 0)
            bad = i and v != s["truth"][n]
            c.text(x, y, f"{v}", size=13, color=RED if bad else INK, anchor="ra")
        if i:
            c.text(836, y, "ずれている" if wrong else "一致", size=13, color=RED if wrong else GREEN)
    c.text(20, 424, message, size=14)
    c.text(20, 448, note, size=12, color=SUB)
    return c.final()


def reorg_figure():
    s4, sr, s5 = step("block 4"), step("reorg"), step("block 5")
    frames = [
        (reorg_frame(s4, None, "block 4 まで取り込んだ。3 つの値は一致している",
                     "1 段階を 3〜5 秒ずつ表示（時刻の実測ではなく、実験の段階ごとのコマ）"), 3000),
        (reorg_frame(sr, s4["chain"], "block 3 と 4 が別の中身に置き換わった。最新の番号は 4 のままで、どちらも気付かない",
                     "ノードの値だけが変わり、2 つのインデクサーは捨てられたブロックの内容を持ち続ける"), 4500),
        (reorg_frame(s5, s4["chain"], "block 5 の取り込みで、親のハッシュが記録した block 4 と違うので、記録した方は 4 と 3 を巻き戻した",
                     "素朴な方は番号だけを見て block 5 を足し、dave の残高が負になった"), 5000),
    ]
    ims = [f for f, _ in frames]
    ims[0].save(os.path.join(IMG, "reorg.webp"), "WEBP", save_all=True, append_images=ims[1:],
                duration=[d for _, d in frames], loop=0, quality=80, method=6)


# ---------------------------------------------------------------- 4. 戻せる深さと Polygon の reorg

def depth_figure():
    # Ponder のウィンドウは 180 秒。2023 年当時の Polygon PoS は 2 秒間隔（0xPolygon/bor の genesis-mainnet-v1.json の period）なので 90 ブロック。
    # 値は 2026-11-21 に手元で確認した既定の値（.note-review/work/indexer/results-all.md）。Rivet だけは報道の値。
    rows = [("Shovel v1.6", 10), ("Ponder（2 秒間隔）", 90), ("Fulcrum", 100), ("Rivet（報道）", 125),
            ("Envio HyperIndex", 199), ("Substreams（RPC から）", 200), ("Blockbook（Bitcoin）", 300),
            ("rindexer（Polygon）", 400)]
    W, H = 860, 520
    c = Canvas(W, H)
    c.text(20, 14, "reorg で戻せる深さ（OSS は既定の値）と、Polygon で起きた reorg", size=18)
    x0, x1, vmax = 230, 830, 420
    sx = lambda v: x0 + (x1 - x0) * v / vmax
    xp = sx(157)
    step_y = 46
    for i, (name, v) in enumerate(rows):
        y = 64 + i * step_y
        short = v < 157
        c.text(20, y + 4, name, size=16)
        c.box(x0, y, max(sx(v) - x0, 4), 30, RED_PALE if short else PALE, RED if short else LINE, 1, 4)
        label = f"約 {v} ブロック" if name.startswith("Rivet") else f"{v} ブロック"
        if sx(v) - x0 < 120:
            c.text(sx(v) + 8, y + 4, str(v), size=15, color=RED if short else INK)
        elif v <= 200:
            c.text(sx(v) + 8, y + 4, label, size=15, color=INK)
        else:
            c.text(sx(v) - 10, y + 4, label, size=15, color=RED if short else INK, anchor="ra")
    y = 64 + len(rows) * step_y
    c.text(20, y + 4, "上限なし", size=16)
    c.box(x0, y, x1 - x0 - 10, 30, GREEN_PALE, GREEN, 1, 4)
    c.d.polygon([((x1 - 10) * S, (y - 4) * S), ((x1 + 6) * S, (y + 15) * S), ((x1 - 10) * S, (y + 34) * S)], fill=rgb(GREEN))
    c.text(x0 + 12, y + 5, "electrs・Blockstream electrs・Blockscout・Graph Node（全履歴）", size=14)
    c.line([(xp, 42), (xp, y + 44)], RED, 2)
    c.text(xp + 6, 40, "157（Polygon の reorg）", size=15, color=RED)
    for v in (0, 100, 200, 300, 400):
        c.text(sx(v), y + 50, str(v), size=14, color=SUB, anchor="ma")
    save_webp(c.final(), "depth.webp")


# ---------------------------------------------------------------- 6. 上限を超えた時の 4 つの型（模式図）

def types_figure():
    # 実測（.note-review/work/indexer/results-all.md）の振る舞いを模式的に描く。数値の軸は持たない
    W, H = 940, 700
    c = Canvas(W, H)
    c.text(20, 14, "戻せる深さを超えた reorg の後、取り込んだ番号と表の値がどう動くか（模式図）", size=17)
    panels = [
        ("上限が無く正しく戻す", "electrs・Blockstream electrs・Blockscout・Graph Node（全履歴）",
         "same", [(0.0, 0.08, False), (0.08, 1.0, True)], "表を戻す間だけずれる", "不要"),
        ("落ちる", "Fulcrum・Substreams",
         "dead", [(0.0, 0.32, None), (0.32, 1.0, "down")], "帯は Fulcrum。Substreams の表は古い値で DB に残る", "プロセスの終了（終了コード 0 の例あり）"),
        ("止まるが、正常と答える", "Ponder・SQD・Shovel・Blockbook・Graph Node（刈り込み）",
         "flat", [(0.0, 1.0, False)], "ヘルスチェックは正常のまま", "取り込んだ番号とノードの最新の差"),
        ("ずれたまま進み、正常と答える", "rindexer・Envio HyperIndex",
         "track", [(0.0, 1.0, False)], "ヘルスチェックは正常のまま", "古いブロックのハッシュの照合"),
    ]
    pw, ph = 440, 316
    for i, (title, names, mode, spans, health, clue) in enumerate(panels):
        px = 20 + (i % 2) * (pw + 20)
        py = 52 + (i // 2) * (ph + 14)
        c.box(px, py, pw, ph, "#ffffff", LINE, 1, 8)
        c.text(px + 16, py + 12, title, size=16)
        c.text(px + 16, py + 38, names, size=12, color=SUB)
        # 折れ線の枠
        gx0, gx1, gy0, gy1 = px + 30, px + pw - 24, py + 70, py + 180
        c.line([(gx0, gy0 - 4), (gx0, gy1), (gx1, gy1)], LINE, 1)
        c.text(gx0 - 6, gy0 - 8, "番号", size=11, color=SUB, anchor="ra")
        c.text(gx1, gy1 + 4, "時間", size=11, color=SUB, anchor="ra")
        xr = gx0 + 40  # reorg の時刻
        c.line([(xr, gy0 - 4), (xr, gy1)], RED, 1)
        c.text(xr + 4, gy0 - 8, "reorg", size=11, color=RED)
        node = lambda x: gy1 - 12 - (x - gx0) * 0.22
        c.line([(gx0, node(gx0)), (gx1, node(gx1))], GHOST, 3)
        c.text(gx1 - 4, node(gx1) - 22, "ノードの最新", size=11, color=SUB, anchor="ra")
        if mode in ("same", "track"):
            off = 6
            if mode == "same":
                pts = [(gx0, node(gx0) + off), (xr, node(xr) + off), (xr + 8, node(xr) + 18), (xr + 22, node(xr + 22) + off), (gx1, node(gx1) + off)]
            else:
                pts = [(gx0, node(gx0) + off), (xr, node(xr) + off), (xr + 8, node(xr) + 18), (xr + 22, node(xr + 22) + off), (gx1, node(gx1) + off)]
            c.line(pts, INK, 2)
        elif mode == "flat":
            c.line([(gx0, node(gx0) + 6), (xr, node(xr) + 6), (gx1, node(xr) + 6)], INK, 2)
            c.d.line([(gx1 - 6) * S, (node(gx1) + 4) * S, (gx1 - 6) * S, (node(xr) + 2) * S], fill=rgb(RED), width=2 * S)
            c.text(gx1 - 12, (node(gx1) + node(xr)) / 2 - 2, "差が開く", size=11, color=RED, anchor="ra")
        elif mode == "dead":
            xd = xr + 60
            c.line([(gx0, node(gx0) + 6), (xd, node(xd) + 6)], INK, 2)
            yd = node(xd) + 6
            c.line([(xd - 7, yd - 7), (xd + 7, yd + 7)], RED, 3)
            c.line([(xd - 7, yd + 7), (xd + 7, yd - 7)], RED, 3)
            c.text(xd + 12, yd - 6, "終了", size=12, color=RED)
        c.text(gx0 + 4, gy1 + 4, "黒: インデクサーが取り込んだ番号", size=11, color=SUB)
        # 表の値の帯
        by = py + 206
        c.text(px + 16, by + 2, "表", size=12, color=SUB)
        bx0, bx1 = gx0, gx1
        for t0, t1, ok in spans:
            a, b = bx0 + (bx1 - bx0) * t0, bx0 + (bx1 - bx0) * t1
            if ok is None:
                fill, edge = GREEN_PALE, GREEN
            elif ok == "down":
                fill, edge = FILL, GHOST
            else:
                fill, edge = (GREEN_PALE, GREEN) if ok else (RED_PALE, RED)
            c.box(a, by, max(b - a, 3), 22, fill, edge, 1, 3)
        c.text(px + 16, by + 34, health, size=13, color=INK)
        c.text(px + 16, by + 62, "気付く手がかり: " + clue, size=13, color=RED if mode == "track" else INK)
    y = 52 + 2 * (ph + 14) + 2
    c.box(20, y, 26, 18, GREEN_PALE, GREEN, 1, 3)
    c.text(54, y, "表がノードと一致", size=13, color=SUB)
    c.box(210, y, 26, 18, RED_PALE, RED, 1, 3)
    c.text(244, y, "表がずれている", size=13, color=SUB)
    c.box(390, y, 26, 18, FILL, GHOST, 1, 3)
    c.text(424, y, "応答なし", size=13, color=SUB)
    save_webp(c.final(), "types.webp")


# ---------------------------------------------------------------- 5. Ponder に当てた reorg

def ponder_figure():
    res = json.load(open(os.path.join(HERE, "lab", "ponder", "output", "results.json")))
    sc = {x["label"]: x for x in res["scenarios"]}
    W, H = 880, 420
    c = Canvas(W, H)
    c.text(20, 14, "Ponder 0.18.9 に reorg を当てた後、表がノードの値と一致するか", size=17)

    def lane(y, title, sub, tmax, ticks, spans, notes):
        c.text(20, y, title, size=17)
        c.text(20, y + 26, sub, size=13, color=SUB)
        x0, x1 = 270, 850
        sx = lambda t: x0 + (x1 - x0) * min(t, tmax) / tmax
        for t0, t1, ok in spans:
            c.box(sx(t0), y + 4, max(sx(t1) - sx(t0), 3), 34, GREEN_PALE if ok else RED_PALE,
                  GREEN if ok else RED, 1, 4)
        for t, label, color in notes:
            c.line([(sx(t), y - 2), (sx(t), y + 44)], color, 2)
            c.text(sx(t) + 4, y + 48, label, size=14, color=color)
        for t in ticks:
            c.text(sx(t), y + 74, f"{t:g} 秒", size=13, color=SUB, anchor="ma")

    ins = sc["inside"]
    m = ins["first_match_seconds"]
    lane(64, "ウィンドウの内側", "3 ブロック（36 秒分）を置き換え", 6, [0, 2, 4, 6],
         [(0, m, False), (m, 6, True)], [(0, "reorg", INK), (m, f"{m:g} 秒で一致", GREEN)])
    out = sc["outside"]
    watch = res["after_outside"]
    tmax = 12 + watch[-1]["t"]
    lane(220, "ウィンドウの外側", "30 ブロック（360 秒分）を置き換え", tmax, [0, 20, 40, 60],
         [(0, tmax, False)], [(0, "reorg", INK), (6, "次のブロック", INK)])
    last = watch[-1]
    c.text(20, 330, f"{tmax:.0f} 秒たっても古い値のまま。プロセスは動き、/ready は 200 を返し続けた", size=15, color=RED)
    c.text(20, 354, f"/status の取り込み済みのブロックは {last['status_block']} で止まり、ノードの最新は {last['node_head']} まで進んだ", size=15, color=RED)
    c.box(20, 388, 26, 18, GREEN_PALE, GREEN, 1, 3)
    c.text(54, 388, "表がノードと一致", size=13, color=SUB)
    c.box(220, 388, 26, 18, RED_PALE, RED, 1, 3)
    c.text(254, 388, "表がずれている", size=13, color=SUB)
    save_webp(c.final(), "ponder.webp")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    overview_figure()
    logs_figure()
    reorg_figure()
    depth_figure()
    ponder_figure()
    types_figure()
