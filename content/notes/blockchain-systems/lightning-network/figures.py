"""Lightning Network のノートの図。lab/run.py が書いた lab/result.json の数値から描く。

    python3 lab/run.py        # regtest の LND 3 台で測る（docker が要る）
    python3 figures.py

1. ln_cover.webp: チャネルの残高と、送れる額・受け取れる額（表紙）
2. ln_route.webp: alice から bob 経由で carol へ 150,000 sat ずつ払った時の 2 本のチャネル
3. ln_close.webp: 協調クローズと強制クローズで、資金を使えるまでのブロック数
4. ln_breach.webp: 古い状態を出した bob と、戻ってきた alice（動く WebP、1 ブロックを 0.5 秒）
"""
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
IMG = HERE / 'images'
RES = json.loads((HERE / 'lab' / 'result.json').read_text())

INK, SUB, GRID = '#1f1f1f', '#666666', '#dddddd'
ACCENT, ACCENT_PALE = '#4e79a7', '#eaf1f5'
RED, RED_PALE = '#c0392b', '#fbe3e3'
OCHRE, OCHRE_PALE = '#b07d1f', '#f8eed8'
GREEN = '#3b7d4f'
GREY = '#bbbbbb'

plt.rcParams.update({
    'font.family': ['Noto Sans CJK JP', 'DejaVu Sans'],
    'font.size': 11, 'axes.edgecolor': SUB, 'axes.labelcolor': INK,
    'xtick.color': INK, 'ytick.color': INK, 'text.color': INK,
    'figure.facecolor': '#ffffff', 'axes.facecolor': '#ffffff',
})


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=200, facecolor='#ffffff', bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert('RGB').save(IMG / name, 'WEBP', quality=90, method=6)


def comma(n):
    return f'{n:,}'


def cover():
    o = RES['open']
    b = RES['bob_after_10000']
    rows = [
        ('alice', '開いた直後の alice', o['local_balance'], RES['alice_max_send'], 0),
        ('bob', '10,000 sat を受け取った bob', b['local_balance'], RES['bob_max_send'], None),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.3), gridspec_kw={'wspace': 0.55})
    for ax, (_, title, bal, send, recv) in zip(axes, rows):
        labels = ['チャネルの残高', '送れる額']
        vals = [bal, send]
        colors = [GREY, ACCENT]
        if recv is not None:
            labels.append('受け取れる額')
            vals.append(recv)
            colors.append(ACCENT)
        y = [2, 1, 0][:len(labels)]
        ax.barh(y, vals, color=colors, height=0.55)
        top = max(vals)
        for yy, v in zip(y, vals):
            if v == 0:
                ax.text(top * 0.02, yy, '0 sat', va='center', fontsize=13, color=RED)
            else:
                ax.text(v + top * 0.02, yy, f'{comma(v)} sat', va='center', fontsize=12)
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.set_xlim(0, top * 1.45)
        ax.set_ylim(-0.5, 2.5)
        ax.set_xticks([])
        ax.spines[['top', 'right', 'bottom']].set_visible(False)
        ax.set_title(title, fontsize=12, loc='left')
    fig.suptitle('容量 1,000,000 sat のチャネル（regtest の LND で実測）', fontsize=12, x=0.02, ha='left', y=1.04)
    save(fig, 'ln_cover.webp')


def route():
    bc = RES['bc_open']
    ab_bob0 = RES['bob_after_10000']['local_balance']
    states = [('支払い前', ab_bob0, bc['local_balance'], 0, None)]
    for i, p in enumerate(RES['ac_pays'], 1):
        if p['status'] == 'SUCCEEDED':
            states.append((f'{i} 回目：成功', p['ab_bob_local'], p['bc_bob_local'], p['bc_carol_local'], True))
        else:
            prev = states[-1]
            states.append((f'{i} 回目：失敗', prev[1], prev[2], prev[3], False))
    cap_ab, cap_bc = RES['open']['capacity'], bc['capacity']
    n = len(states)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.4), gridspec_kw={'width_ratios': [2, 1.55], 'wspace': 0.08})
    for k, (label, ab_bob, bc_bob, bc_carol, ok) in enumerate(states):
        y = n - 1 - k
        a1.barh(y, cap_ab - ab_bob, height=0.5, color=ACCENT_PALE, edgecolor=ACCENT)
        a1.barh(y, ab_bob, left=cap_ab - ab_bob, height=0.5, color=OCHRE_PALE, edgecolor=OCHRE)
        a1.text(cap_ab + 15_000, y, f'bob {comma(ab_bob)}', va='center', fontsize=10, color=OCHRE)
        a2.barh(y, bc_bob, height=0.5, color=OCHRE_PALE, edgecolor=OCHRE)
        a2.barh(y, cap_bc - bc_bob, left=bc_bob, height=0.5, color='#eef5ee', edgecolor=GREEN)
        a2.text(cap_bc + 10_000, y, f'bob {comma(bc_bob)}', va='center', fontsize=10, color=OCHRE)
        a1.text(-20_000, y, label, ha='right', va='center', fontsize=11, color=RED if ok is False else INK)
    a2.text(cap_bc + 10_000, -0.75, '4 回目の 150,000 sat は\nbob の残高が足りず届かない', fontsize=10, color=RED, va='center')
    a1.set_title('alice と bob のチャネル（容量 1,000,000 sat）\n左が alice 側、右が bob 側', fontsize=10, color=SUB)
    a2.set_title('bob と carol のチャネル（容量 500,000 sat）\n左が bob 側、右が carol 側', fontsize=10, color=SUB)
    for ax, cap in ((a1, cap_ab), (a2, cap_bc)):
        ax.set_xlim(0, cap * 1.3)
        ax.set_ylim(-1.2, n - 0.4)
        ax.axis('off')
    save(fig, 'ln_route.webp')


def close():
    c = RES['close']
    h0 = c['start_height']
    s = c['series']
    st = c['start_onchain']

    def first(node, cond):
        for row in s:
            if cond(row[node]):
                return row['height'] - h0
        return None
    coop = first('carol', lambda v: v > st['carol'])
    later = [r for r in s if r['carol'] > s[0]['carol']]
    force_remote = later[0]['height'] - h0 if later else None
    bob_done = first('bob', lambda v: v > st['bob'])
    rows = [('carol：協調クローズ（自分の分）', coop, ACCENT),
            ('carol：bob の強制クローズ（相手の分）', force_remote, ACCENT),
            ('bob：強制クローズした側（自分の分）', bob_done, RED)]
    fig, ax = plt.subplots(figsize=(9.2, 2.8))
    for i, (label, blk, color) in enumerate(rows[::-1]):
        ax.barh(i, blk, color=color, height=0.5)
        ax.text(blk + 2, i, f'{blk} ブロック', va='center', fontsize=11)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows[::-1]])
    ax.set_xlim(0, 175)
    ax.set_xlabel('閉じる指示を出してから、オンチェーンの残高に入るまでのブロック数')
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='x', color=GRID)
    ax.set_axisbelow(True)
    save(fig, 'ln_close.webp')
    return coop, force_remote, bob_done


# ---- 動く図 ----
W, H = 960, 470
S = 2
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def font(px):
    return ImageFont.truetype(FONT, px * S)


def breach():
    b = RES['breach']
    h_bc = b['broadcast_height']
    h_back = b['alice_back_height']
    tl = {r['height']: r for r in b['timeline']}
    gain = b['alice_onchain_after'] - b['alice_onchain_before']
    csv = b['bob_csv_delay']
    h_justice = min(h for h, r in tl.items() if r['alice_onchain'] > b['alice_onchain_before'])
    first_h = h_bc - 2
    last_h = h_justice + 2

    def frame(h, note, bob_amt, alice_amt, alice_online, final=False):
        im = Image.new('RGB', (W * S, H * S), '#ffffff')
        d = ImageDraw.Draw(im)
        d.text((24 * S, 14 * S), '古い状態を出した bob と、あとから戻った alice', font=font(20), fill=INK)
        d.text((24 * S, 44 * S), 'regtest で掘ったブロック高。1 ブロック（本番は約 10 分）を 0.5 秒で再生（約 1,200 倍速）',
               font=font(13), fill=SUB)
        # ブロックの列
        x = 24
        for hh in range(first_h, last_h + 1):
            col = '#ffffff'
            edge = GRID
            if hh <= h:
                col, edge = '#f2f2f2', SUB
            if hh == h_bc and h >= h_bc:
                col, edge = RED_PALE, RED
            if hh == h_justice and h >= h_justice:
                col, edge = '#eef5ee', GREEN
            d.rectangle([x * S, 80 * S, (x + 52) * S, 120 * S], fill=col, outline=edge, width=S)
            d.text(((x + 8) * S, 90 * S), str(hh), font=font(14), fill=INK if hh <= h else GRID)
            x += 60
        d.text((24 * S, 128 * S), f'今のブロック高 {h}', font=font(15), fill=INK)
        if h_bc <= h < h_justice:
            left = csv - (h - h_bc)
            d.text((260 * S, 128 * S), f'bob が自分の分を使えるまで あと {left} ブロック', font=font(15), fill=RED)
        elif h >= h_justice:
            d.text((260 * S, 128 * S), 'bob の分は、使えるようになる前に alice が持っていった', font=font(15), fill=RED)
        d.text((640 * S, 166 * S), '赤い枠：古い状態　緑の枠：ペナルティ', font=font(12), fill=SUB)
        # alice の状態
        st = 'alice：オンライン' if alice_online else 'alice：オフライン（チェーンを見ていない）'
        d.text((24 * S, 168 * S), st, font=font(16), fill=GREEN if alice_online else SUB)
        d.text((24 * S, 198 * S), note, font=font(16), fill=INK)
        # 取り分
        maxv = 1_000_000
        for i, (name, amt, color) in enumerate([('bob', bob_amt, OCHRE), ('alice', alice_amt, ACCENT)]):
            y = 260 + i * 70
            d.text((24 * S, y * S), name, font=font(16), fill=INK)
            d.rectangle([110 * S, y * S, (110 + 600) * S, (y + 34) * S], outline=GRID, width=S)
            if amt:
                d.rectangle([110 * S, y * S, int((110 + 600 * amt / maxv) * S), (y + 34) * S], fill=color)
            d.text((725 * S, (y + 4) * S), f'{comma(amt)} sat', font=font(16), fill=RED if (final and name == 'bob') else INK)
        d.text((110 * S, 400 * S), 'チャネルから手にした額（容量 1,000,000 sat）', font=font(13), fill=SUB)
        if final:
            d.text((24 * S, 428 * S), f'最新の状態での bob の残高は {comma(b["honest_bob_local"])} sat だった',
                   font=font(14), fill=RED)
        return im.resize((W, H), Image.LANCZOS)

    frames, durs = [], []
    old, honest = b['old_bob_local'], b['honest_bob_local']
    frames.append(frame(first_h, f'bob が channel.db を写す（bob の残高 {comma(old)} sat の時点）', 0, 0, True))
    durs.append(2000)
    frames.append(frame(first_h, f'bob が alice へ 200,000 sat 払う（最新は bob {comma(honest)} sat）', 0, 0, True))
    durs.append(2000)
    for h in range(first_h + 1, last_h + 1):
        if h < h_bc:
            note = 'alice が止まる。bob は写しておいた channel.db に戻す'
        elif h == h_bc:
            note = f'bob が古い状態（bob {comma(old)} sat）で強制クローズ'
        elif h < h_back:
            note = '古い状態がチェーンに載った。alice はまだ気づいていない'
        elif h < h_justice:
            note = 'alice が戻り、チェーンを読み直す'
        else:
            note = 'alice のペナルティトランザクションが bob の分まで持っていく'
        alice_amt = gain if h >= h_justice else 0
        frames.append(frame(h, note, 0, alice_amt, h >= h_back))
        durs.append(500)
    frames.append(frame(last_h, 'alice のペナルティトランザクションが bob の分まで持っていく', 0, gain, True, final=True))
    durs.append(3500)
    frames[0].save(IMG / 'ln_breach.webp', 'WEBP', save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, quality=80, method=6)
    return sum(durs)


if __name__ == '__main__':
    IMG.mkdir(exist_ok=True)
    cover()
    route()
    print('close', close())
    print('breach ms', breach())
