"""Generate the figures of the Bitcoin Script note (Pillow only).

1. script_race.webp (animated, cover): lab/output/race.json. Two P2WSH
   outputs are spent by Bob; a watcher polls the mempool every 0.5 s, copies
   the witness and sends a replacement that pays itself. One block is mined
   5 s after Bob's broadcast. Frames follow the measured times and are played
   at 0.5x speed (0.1 s of real time per 200 ms frame), the last frame stays 3 s.
2. script_stack.webp: the stack after each step of
   OP_SHA256 <H> OP_EQUALVERIFY <pubkey> OP_CHECKSIG (condition B).
3. script_sighash.webp: which parts of Bob's transaction the signature covers
   (BIP-143): the outpoint, the amount, the script (the last witness item,
   as scriptCode) and the outputs, not the signature and the preimage.
4. script_concat.webp: 0.3.4 and earlier joined scriptSig and scriptPubKey,
   and OP_RETURN jumped to the end (lab/output/concat_bug.txt).

Everything is drawn at 2x and reduced. Background is white (dark mode).
Run: python3 content/notes/blockchain-systems/bitcoin-script/figures.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
IMG = HERE / 'images'
JP = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
INK, SUB, LINE = '#1f1f1f', '#666666', '#9a9a9a'
BLUE, BLUE_F = '#5f8fb0', '#eaf1f5'
OCHRE, OCHRE_F = '#b98a35', '#f8eed8'
GRAY_F = '#f2f2f2'
RED = '#b0453a'
S = 2  # draw at 2x


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, round(size * 1.2 * S), index=0)  # 1.2: readable at ~820 px


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new('RGB', (w * S, h * S), '#ffffff')
        self.d = ImageDraw.Draw(self.im)

    def text(self, x, y, s, size=18, color=INK, anchor='la', mono=False):
        self.d.text((x * S, y * S), s, font=font(size, mono), fill=color, anchor=anchor)

    def box(self, x, y, w, h, fill, outline=None, width=2, r=8, dash=False):
        if dash:
            self.d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), r * S, fill=fill)
            for i in range(0, int(w), 12):
                for yy in (y, y + h):
                    self.d.line(((x + i) * S, yy * S, (x + min(i + 6, w)) * S, yy * S), fill=outline, width=width * S)
            for i in range(0, int(h), 12):
                for xx in (x, x + w):
                    self.d.line((xx * S, (y + i) * S, xx * S, (y + min(i + 6, h)) * S), fill=outline, width=width * S)
        else:
            self.d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), r * S, fill=fill,
                                     outline=outline, width=width * S if outline else 0)

    def line(self, pts, color=LINE, width=2):
        self.d.line([(x * S, y * S) for x, y in pts], fill=color, width=width * S)

    def arrow(self, x1, y1, x2, y2, color=SUB, width=2):
        self.line([(x1, y1), (x2, y2)], color, width)
        import math
        a = math.atan2(y2 - y1, x2 - x1)
        L = 10
        p1 = (x2 - L * math.cos(a - 0.45), y2 - L * math.sin(a - 0.45))
        p2 = (x2 - L * math.cos(a + 0.45), y2 - L * math.sin(a + 0.45))
        self.d.polygon([(x2 * S, y2 * S), (p1[0] * S, p1[1] * S), (p2[0] * S, p2[1] * S)], fill=color)

    def strike(self, x, y, w, h, color=RED):
        self.line([(x + 6, y + h / 2), (x + w - 6, y + h / 2)], color, 3)

    def final(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)

    def save(self, name):
        p = IMG / name
        self.final().save(p, 'WEBP', quality=90, method=6)
        print('wrote', p)


# ---------------------------------------------------------------- 1. race
def race():
    data = json.loads((HERE / 'lab/output/race.json').read_text())

    def times(case):
        ev = {e['event']: e for e in data[case]['events']}
        return ev

    A, B = times('hashlock'), times('hashsig')
    end = max(A['block_mined']['t'], B['block_mined']['t']) + 0.2
    W, H = 1000, 560
    x_pool, x_block = 290, 660
    lanes = [
        ('条件 A', 'OP_SHA256 <H> OP_EQUAL', 'プリイメージだけで使える', A, 110),
        ('条件 B', 'OP_SHA256 <H> OP_EQUALVERIFY <公開鍵> OP_CHECKSIG', 'プリイメージ ＋ Bob の署名', B, 330),
    ]

    def frame(t):
        c = Canvas(W, H)
        c.text(24, 18, '監視プログラムが Bob の送金をコピーした時、ブロックに入るのはどちらか', 21)
        c.text(24, 50, f'regtest の実測（Bitcoin Core 32.1）を 0.5 倍速で再生　経過 {t:4.1f} 秒', 15, SUB)
        # time bar
        # the clock stays in the left column so that it is not read as positions of the boxes
        bx, bw, by = 24, 220, 84
        c.box(bx, by, bw, 8, GRAY_F, r=4)
        c.box(bx, by, max(8, bw * min(t, end) / end), 8, '#c9c9c9', r=4)
        for sec in range(0, int(end) + 1):
            c.text(bx + bw * sec / end, by + 12, f'{sec} 秒', 11, SUB, 'ma')
        for title, script, sub, ev, y in lanes:
            c.text(24, y + 14, title, 18)
            c.text(24, y + 40, sub, 14, SUB)
            c.text(24, y + 182, script, 13, SUB, mono=False)
            c.box(x_pool - 20, y, 420, 170, '#fafafa', LINE, 2)
            c.text(x_pool - 10, y + 6, 'mempool（ブロック待ち）', 13, SUB)
            c.box(x_block + 60, y, 256, 170, '#fafafa', LINE, 2)
            c.text(x_block + 70, y + 6, 'ブロック', 13, SUB)
            bob_t = ev['bob_broadcast']['t']
            blk = ev['block_mined']
            winner = blk['winner']
            w_t = (ev.get('watcher_broadcast') or ev.get('watcher_rejected'))['t']
            rejected = 'watcher_rejected' in ev
            card_w, card_h = 190, 58

            def bob_card(x, yy, struck=False):
                c.box(x, yy, card_w, card_h, BLUE_F, BLUE, 2)
                c.text(x + 10, yy + 6, 'Bob 宛て', 14)
                c.text(x + 10, yy + 28, '手数料 1,000 sat', 12, SUB)
                if struck:
                    c.strike(x, yy, card_w, card_h)

            def w_card(x, yy, struck=False):
                c.box(x, yy, card_w, card_h, OCHRE_F, OCHRE, 2)
                c.text(x + 10, yy + 6, '監視プログラム宛て', 14)
                c.text(x + 10, yy + 28, '手数料 10,000 sat', 12, SUB)
                if struck:
                    c.strike(x, yy, card_w, card_h)

            mined = t >= blk['t']
            in_block_x = x_block + 92
            if t >= bob_t:
                if mined and winner == 'bob':
                    bob_card(in_block_x, y + 50)
                elif t < w_t or rejected:
                    if not mined:
                        bob_card(x_pool, y + 40)
                else:
                    if t < w_t + 0.8:   # show the replaced card briefly
                        bob_card(x_pool, y + 40, struck=True)
                        c.text(x_pool, y + 96, '置き換えられた', 12, RED)
            if t >= w_t:
                if rejected:
                    if t < w_t + 1.2:
                        w_card(24, y + 70, struck=True)
                    c.text(24, y + 132, '署名が合わず', 12, RED)
                    c.text(24, y + 150, 'mempool に入れない', 12, RED)
                elif mined:
                    w_card(in_block_x, y + 50)
                else:
                    w_card(x_pool + 205, y + 40)
            if mined:
                who = 'Bob' if winner == 'bob' else '監視プログラム'
                amt = data[case_of[title]][f'{winner}_balance_btc']
                c.text(x_block + 70, y + 124, f'{who}{" " if who == "Bob" else ""}が {amt} BTC', 13)
                c.text(x_block + 70, y + 144, f'{blk["t"]:.1f} 秒でブロックに入った', 12, SUB)
            # event ticks on the lane
            c.text(x_pool - 10, y + 140, f'Bob の送信 {bob_t:.2f} 秒　監視プログラムの送信 {w_t:.2f} 秒'
                   if t >= w_t else f'Bob の送信 {bob_t:.2f} 秒' if t >= bob_t else '', 12, SUB)
        return c.final()

    case_of = {'条件 A': 'hashlock', '条件 B': 'hashsig'}
    frames, durs = [], []
    t = 0.0
    while t < end:
        frames.append(frame(t))
        durs.append(200)    # 0.1 s of real time per 200 ms = 0.5x
        t = round(t + 0.1, 2)
    frames.append(frame(end))
    durs.append(3000)
    p = IMG / 'script_race.webp'
    frames[0].save(p, 'WEBP', save_all=True, append_images=frames[1:], duration=durs, loop=0,
                   quality=50, method=6)
    print('wrote', p, len(frames), 'frames', sum(durs) / 1000, 's', p.stat().st_size // 1024, 'KB')


# ---------------------------------------------------------------- 2. stack
def stack():
    steps = [
        ('実行前', 'witness の 2 個', ['署名', 'プリイメージ']),
        ('OP_SHA256', '一番上を SHA-256 に', ['署名', 'SHA-256 の結果']),
        ('<H>', '出力の H を積む', ['署名', 'SHA-256 の結果', 'H']),
        ('OP_EQUALVERIFY', '2 個を比べ、違えば失敗', ['署名']),
        ('<公開鍵>', 'Bob の公開鍵を積む', ['署名', '公開鍵']),
        ('OP_CHECKSIG', '署名を検証', ['1（真）']),
    ]
    W, H = 1000, 330
    c = Canvas(W, H)
    c.text(24, 16, '条件 B を実行した時のスタック（下が先に積んだもの）', 18)
    col = (W - 48) / len(steps)
    base = 250
    for i, (op, note, items) in enumerate(steps):
        x = 24 + i * col
        c.text(x + col / 2, 52, op, 15, INK, 'ma', mono=op.startswith('OP_') or op == '<H>')
        c.text(x + col / 2, 76, note, 12, SUB, 'ma')
        for j, it in enumerate(items):
            fill, edge = (BLUE_F, BLUE) if it in ('署名', '公開鍵', '1（真）') else (OCHRE_F, OCHRE)
            c.box(x + 12, base - (j + 1) * 40, col - 24, 34, fill, edge, 2, r=6)
            c.text(x + col / 2, base - (j + 1) * 40 + 7, it, 13, INK, 'ma')
        c.line([(x + 6, base + 4), (x + col - 6, base + 4)], LINE, 2)
        if i < len(steps) - 1:
            c.arrow(x + col - 8, 190, x + col + 8, 190, SUB, 2)
    c.text(24, 270, '青は署名の検査に使う値、黄土色はプリイメージの検査に使う値。最後に一番上が真なら、使って良いと判定する。', 13, SUB)
    c.text(24, 294, 'プリイメージが違えば 4 列目、署名が違えば 6 列目で失敗する。', 13, SUB)
    c.save('script_stack.webp')


# ---------------------------------------------------------------- 3. sighash
def sighash():
    W, H = 1000, 500
    c = Canvas(W, H)
    c.text(24, 16, '署名が覆う範囲：監視プログラムが出力を書き換えると、条件 B の署名は合わなくなる', 18)
    ROW0, STEP = 92, 70

    def tx(x, title, out_label, out_fill, out_edge, note, note_color):
        c.text(x, 58, title, 15)
        rows = [
            ('入力', '使う出力（txid:0）と金額 1 BTC', GRAY_F, LINE),
            ('witness の最後の要素', '条件の本体（scriptCode として計算に入る）', GRAY_F, LINE),
            ('witness の残り', '署名 ／ プリイメージ', '#fafafa', LINE),
            ('出力', out_label, out_fill, out_edge),
        ]
        for k, (h, body, fill, edge) in enumerate(rows):
            yy = ROW0 + k * STEP
            c.box(x, yy, 400, 58, fill, edge, 2)
            c.text(x + 12, yy + 6, h, 13, SUB)
            c.text(x + 12, yy + 29, body, 14)
        c.text(x, ROW0 + 4 * STEP + 10, note, 13, note_color)

    tx(24, 'Bob が送ったトランザクション', 'Bob 宛て 0.99999 BTC', BLUE_F, BLUE,
       '署名は、入力・条件の本体・出力から計算した値に付く', SUB)
    tx(560, '監視プログラムが作り直したもの', '監視プログラム宛て 0.9999 BTC', OCHRE_F, OCHRE,
       '出力が変わったので、コピーした署名は検証に失敗する', RED)
    # brackets showing the covered rows on Bob's side
    for k in (0, 1, 3):
        yy = ROW0 + k * STEP
        c.line([(436, yy + 4), (446, yy + 4), (446, yy + 54), (436, yy + 54)], BLUE, 3)
        c.text(452, yy + 10, '署名が', 13, BLUE)
        c.text(452, yy + 28, '覆う', 13, BLUE)
    c.text(452, ROW0 + 2 * STEP + 20, '覆わない', 13, SUB)
    c.arrow(522, ROW0 + STEP + 40, 556, ROW0 + STEP + 40, LINE, 2)
    c.arrow(522, ROW0 + 2 * STEP + 44, 556, ROW0 + 2 * STEP + 44, LINE, 2)
    c.arrow(514, ROW0 + 3 * STEP + 29, 556, ROW0 + 3 * STEP + 29, OCHRE, 3)
    c.text(560, ROW0 + 4 * STEP + 42, '条件 A には署名が無いので、出力を変えても検査は全て通る', 13, SUB)
    c.text(24, ROW0 + 4 * STEP + 42, '覆う範囲は BIP-143（SIGHASH_ALL）の場合', 13, SUB)
    c.text(24, ROW0 + 4 * STEP + 74, 'witness は右へそのままコピーされる。条件の本体は同じなので、変わったのは出力だけ。', 13, SUB)
    c.save('script_sighash.webp')


# ---------------------------------------------------------------- 4. concat
def concat():
    W, H = 1000, 330
    c = Canvas(W, H)
    c.text(24, 16, '0.3.4 までの実行と今の実行：攻撃者の OP_1 OP_RETURN が条件を飛ばせた', 18)
    toks = [('OP_1', OCHRE_F, OCHRE), ('OP_RETURN', OCHRE_F, OCHRE), ('OP_CODESEPARATOR', GRAY_F, LINE),
            ('<公開鍵>', BLUE_F, BLUE), ('OP_CHECKSIG', BLUE_F, BLUE)]
    widths = [80, 130, 190, 110, 140]
    # row 1: joined
    y = 70
    c.text(24, y, '0.3.4 まで：つないで 1 回実行', 15)
    x = 24
    xs = []
    for (t, f, e), w in zip(toks, widths):
        c.box(x, y + 30, w, 40, f if t in ('OP_1', 'OP_RETURN') else '#f7f7f7', e, 2, r=6, dash=t not in ('OP_1', 'OP_RETURN'))
        c.text(x + w / 2, y + 40, t, 13, INK if t in ('OP_1', 'OP_RETURN') else SUB, 'ma', mono=t.startswith('OP_'))
        xs.append((x, w))
        x += w + 10
    rx, rw = xs[1]
    c.line([(rx + rw / 2, y + 74), (rx + rw / 2, y + 92), (x + 6, y + 92)], RED, 3)
    c.arrow(x + 6, y + 92, x + 6, y + 70, RED, 3)
    c.text(x + 20, y + 40, '残ったスタック [1] → 成功', 14, RED)
    c.text(rx, y + 98, 'OP_RETURN が末尾へ飛び、点線の命令は実行されない', 12, RED)
    # row 2: separate
    y = 200
    c.text(24, y, '0.3.7 以降：使う側を実行し、残ったスタックで条件を実行', 15)
    x = 24
    for (t, f, e), w in zip(toks[:2], widths[:2]):
        c.box(x, y + 30, w, 40, f, e, 2, r=6)
        c.text(x + w / 2, y + 40, t, 13, INK, 'ma', mono=True)
        x += w + 10
    c.text(x + 6, y + 40, '← ここで失敗（OP_RETURN は 0.3.5 から失敗する命令）', 13, INK)
    c.text(24, y + 86, '出力の条件（<公開鍵> OP_CHECKSIG）は、使う側の命令に飛ばされず必ず実行される', 13, SUB)
    c.save('script_concat.webp')


if __name__ == '__main__':
    IMG.mkdir(exist_ok=True)
    race()
    stack()
    sighash()
    concat()
