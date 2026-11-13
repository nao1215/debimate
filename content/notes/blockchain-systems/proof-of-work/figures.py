"""Generate the figures of the Proof of Work note.

1. pow_wait.webp (cover): lab/output/trials.csv and wait.json (mine.py, wait.py).
   Block intervals of a toy chain mined with double SHA-256 at a 16-bit target,
   65,536 trials read as 10 minutes, and the wait of a transaction sent at a
   random moment.
2. pow_hashes.webp: the genesis hash (lab/output/genesis.txt) and the hash of
   block 975640 (lab/output/tip.json) with the zeros the target asks for.
3. pow_retarget.webp: every difficulty change of Bitcoin mainnet
   (lab/output/difficulty_adjustments.json, mempool.space, 2026-11-13).
4. pow_fork.webp (animated): fork at height 26 in lab/output/fork_60s.json
   (fork.py, 60 s delay). The measured ticks are played at 60x speed
   (1 minute of the simulation per 1 second), the last frame stays 3 s.
5. pow_attack.webp: the white paper's formula (lab/attack.py).
6. pow_double_spend.webp (animated): attempt 65 in lab/output/double_spend.json
   (double_spend.py, q = 40%, the shop waits 2 confirmations). The measured
   ticks are played at 150x speed (0.5 minute per 200 ms frame), the last
   frame stays 3 s.
7. pow_inspection.webp: 40 intervals (heights 1,121-1,160) of lab/output/trials.csv as a
   strip, with random send times falling on them (wait.py's rule).

Background is white (dark mode). Run: python3 figures.py
"""
import csv
import io
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
LAB = HERE / 'lab'
OUT = LAB / 'output'
IMG = HERE / 'images'
sys.path.insert(0, str(LAB))
from attack import whitepaper  # noqa: E402

JP = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
font_manager.fontManager.addfont(JP)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 12
INK, SUB, LINE = '#1f1f1f', '#666666', '#9a9a9a'
BLUE, BLUE_F = '#5f8fb0', '#eaf1f5'
OCHRE, OCHRE_F = '#b98a35', '#f8eed8'
RED, RED_F = '#b0453a', '#f6e3e0'
GRAY_F = '#f2f2f2'


def save_plt(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=200, facecolor='#ffffff', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert('RGB').save(IMG / name, 'WEBP', quality=90, method=6)


def style(ax):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.spines['left'].set_color(LINE)
    ax.spines['bottom'].set_color(LINE)
    ax.tick_params(colors=SUB)


# 1 -------------------------------------------------------------------------
def fig_wait():
    gaps = [int(r['trials']) * 10 / 65536 for r in csv.DictReader(open(OUT / 'trials.csv'))]
    w = json.load(open(OUT / 'wait.json'))
    fig, (a, b) = plt.subplots(1, 2, figsize=(10.5, 4.0), gridspec_kw={'width_ratios': [1.35, 1]})
    a.hist(gaps, bins=[i * 2.5 for i in range(25)], color=BLUE_F, edgecolor=BLUE, linewidth=0.8)
    xs = [i / 10 for i in range(0, 601)]
    scale = 2.5 * len(gaps)
    a.plot(xs, [scale * math.exp(-x / 10) / 10 for x in xs], color=INK, linewidth=1.2)
    a.text(24, 260, '平均 10 分の指数分布', color=INK, fontsize=10)
    a.set_xlim(0, 60)
    a.set_xlabel('ブロックの間隔（分）', color=INK)
    a.set_ylabel('ブロックの数（3,000 個のうち）', color=INK)
    a.set_title('間隔は短いものほど多く、20 分を超えるのが 14%', color=INK, fontsize=11, loc='left')
    style(a)
    labels = ['ブロックの間隔', '送ってから次の\nブロックまで', '送った時刻を\n含む間隔']
    vals = [w['mean_gap'], w['mean_wait'], w['mean_gap_containing_send']]
    bars = b.bar(range(3), vals, color=[BLUE_F, OCHRE_F, OCHRE_F], edgecolor=[BLUE, OCHRE, OCHRE], width=0.6)
    for i, v in enumerate(vals):
        b.text(i, v + 0.5, f'{v:.1f} 分', ha='center', color=INK, fontsize=11)
    b.axhline(5, color=RED, linestyle='--', linewidth=1)
    b.text(2.45, 5.4, '間隔の半分（5 分）', color=RED, fontsize=9, ha='right')
    b.set_xticks(range(3), labels, fontsize=9.5)
    b.set_ylim(0, 24)
    b.set_ylabel('平均（分）', color=INK)
    b.set_title('ランダムな時刻に送ったトランザクション', color=INK, fontsize=11, loc='left')
    style(b)
    fig.tight_layout()
    save_plt(fig, 'pow_wait.webp')


# 2 -------------------------------------------------------------------------
S = 2


def pfont(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, round(size * S), index=0)


def fig_hashes():
    genesis = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'
    tip = json.load(open(OUT / 'tip.json'))
    rows = [
        ('ジェネシスブロック（2009 年 1 月、高さ 0）', genesis, 32, 43, '期待される試行 約 43 億回（2³²）'),
        (f'2026 年 11 月 13 日のブロック（高さ {tip["height"]:,}）', tip['id'], 79, 80, '期待される試行 約 6.4 × 10²³ 回'),
    ]
    W, H = 1180, 330
    im = Image.new('RGB', (W * S, H * S), '#ffffff')
    d = ImageDraw.Draw(im)
    cw = 15.6
    x0 = 40
    y = 22
    for title, h, need_bits, zero_bits, trials in rows:
        d.text((x0 * S, y * S), title, font=pfont(17), fill=INK)
        y += 34
        for i, ch in enumerate(h):
            x = x0 + i * cw
            if ch == '0' and h[:i].strip('0') == '':
                d.rectangle((x * S, (y - 2) * S, (x + cw - 1) * S, (y + 26) * S), fill=GRAY_F)
            part = min(max(need_bits - 4 * i, 0), 4) / 4      # one hex digit is 4 bits
            if part:
                d.rectangle((x * S, (y - 2) * S, (x + (cw - 1) * part) * S, (y + 26) * S), fill=OCHRE_F)
            d.text(((x + 1.5) * S, y * S), ch, font=pfont(20, True), fill=INK if h[:i + 1].strip('0') == '' else SUB)
        y += 38
        d.text((x0 * S, y * S), f'ターゲットが求める 0 は {need_bits} ビット（茶色）、実際に先頭に並ぶ 0 は {zero_bits} ビット　{trials}　検証は 1 回', font=pfont(14.5), fill=SUB)
        y += 64
    d.text((x0 * S, (H - 30) * S), '表示は Bitcoin のブロックエクスプローラーと同じ向き（大きい桁が左）の 16 進数', font=pfont(13), fill=SUB)
    im.resize((W, H), Image.LANCZOS).save(IMG / 'pow_hashes.webp', 'WEBP', quality=90, method=6)


# 3 -------------------------------------------------------------------------
def fig_retarget():
    data = [x for x in json.load(open(OUT / 'difficulty_adjustments.json')) if x[3] > 0 and x[1] > 0]
    data.sort(key=lambda x: x[1])
    dates = [datetime.fromtimestamp(x[0], timezone.utc) for x in data]
    ratio = [x[3] for x in data]
    fig, ax = plt.subplots(figsize=(10.5, 3.9))
    ax.axhline(1, color=LINE, linewidth=0.8)
    ax.axhline(4, color=RED, linestyle='--', linewidth=1)
    ax.axhline(0.25, color=RED, linestyle='--', linewidth=1)
    ax.text(dates[-1], 4.3, '上限 4 倍', color=RED, ha='right', fontsize=10)
    ax.text(dates[-1], 0.27, '下限 1/4', color=RED, ha='right', va='bottom', fontsize=10)
    ax.scatter(dates, ratio, s=9, color=BLUE, zorder=3)
    for x, dt, r in zip(data, dates, ratio):
        if x[1] == 68544:
            ax.annotate('2010 年 7 月 16 日\n4.00 倍（上限に当たった）', (dt, r), xytext=(40, -48), textcoords='offset points',
                        fontsize=9.5, color=INK, arrowprops={'arrowstyle': '-', 'color': SUB})
        if x[1] == 689472:
            ax.annotate('2021 年 7 月 3 日\n0.72 倍（最大の下げ）', (dt, r), xytext=(-150, -28), textcoords='offset points',
                        fontsize=9.5, color=INK, arrowprops={'arrowstyle': '-', 'color': SUB})
    ax.set_yscale('log')
    ax.set_yticks([0.25, 0.5, 1, 2, 4], ['1/4', '1/2', '1', '2', '4'])
    ax.minorticks_off()
    ax.set_ylim(0.18, 6)
    ax.set_ylabel('1 回の調整で変わった倍率', color=INK)
    ax.set_title(f'Bitcoin の難易度が変わった調整 {len(data)} 回（2009〜2026 年 11 月）', color=INK, fontsize=11, loc='left')
    style(ax)
    fig.tight_layout()
    save_plt(fig, 'pow_retarget.webp')


# 4 -------------------------------------------------------------------------
def fig_fork():
    d = json.load(open(OUT / 'fork_60s.json'))
    ts = d['tick_s']
    B = {b['hash']: b for b in d['blocks']}
    main = set(d['main'])
    start, end = 285.5, 295.5            # minutes of the simulation
    ev = [e for e in d['events'] if start * 60 <= e['tick'] * ts <= end * 60]
    W, H = 1100, 520
    lanes = {'A': 120, 'B': 300}
    color = {'A': (BLUE, BLUE_F), 'B': (OCHRE, OCHRE_F)}
    base_h = 25
    bw, gap = 104, 30
    xs = lambda h: 210 + (h - base_h) * (bw + gap)

    def frame(now, state, last=False):
        im = Image.new('RGB', (W * S, H * S), '#ffffff')
        dr = ImageDraw.Draw(im)
        t = lambda x, y, s, size=16, c=INK, mono=False, anchor='la': dr.text((x * S, y * S), s, font=pfont(size, mono), fill=c, anchor=anchor)
        t(24, 16, '2 人のマイナーが同じ高さのブロックを見つけた時に残る方（相手に届くまで 60 秒）', 17)
        # time bar
        bx, by, bwid = 24, 52, W - 48
        dr.rectangle((bx * S, by * S, (bx + bwid) * S, (by + 8) * S), fill=GRAY_F)
        frac = (now - start) / (end - start)
        dr.rectangle((bx * S, by * S, (bx + bwid * frac) * S, (by + 8) * S), fill=SUB)
        t(W - 24, 66, f'経過 {now - start:4.1f} 分（実時間の 60 倍速）', 14, SUB, anchor='ra')
        for name, y in lanes.items():
            share = '計算能力 60%' if name == 'A' else '計算能力 40%'
            t(24, y + 12, f'マイナー {name}', 17, color[name][0])
            t(24, y + 38, share, 13, SUB)
            t(24, y + 58, 'が知っている列', 13, SUB)
            for h, owner, status in state[name]:
                x = xs(h)
                y0 = y + (0 if status == 'main' else 74)
                out, fill = color[owner]
                if status == 'stale':
                    fill, out = RED_F, RED
                dr.rounded_rectangle((x * S, y0 * S, (x + bw) * S, (y0 + 56) * S), 8 * S, fill=fill, outline=out, width=2 * S)
                t(x + bw / 2, y0 + 10, f'高さ {h}', 15, INK, anchor='ma')
                t(x + bw / 2, y0 + 32, f'{owner} が作成', 13, SUB, anchor='ma')
            # parent arrows
            hs = sorted(state[name], key=lambda s: (s[0], s[2] != 'main'))
            for h, owner, status in hs:
                if h == base_h:
                    continue
                x = xs(h)
                y0 = y + (0 if status == 'main' else 74)
                px = xs(h - 1) + bw
                dr.line((px * S, (y + 28) * S, x * S, (y0 + 28) * S), fill=LINE, width=2 * S)
        note = state.get('note', '')
        if note:
            t(24, H - 40, note, 15, RED if last else INK)
        return im

    # rebuild what each miner knows at each moment
    know = {'A': {}, 'B': {}}
    tip = {'A': None, 'B': None}
    for b in d['blocks']:
        if b['height'] == base_h and b['hash'] in main:
            for m in know:
                know[m][b['hash']] = b
                tip[m] = b['hash']
    frames, durs = [], []
    notes = {
        'found A 26': 'A が高さ 26 を見つけた。B に届くのは 60 秒後',
        'found B 26': 'B も A の 26 を受け取る前に、自分の高さ 26 を見つけた',
        'recv B 26': 'B に A の 26 が届く。同じ高さなので先に見た自分の 26 のまま',
        'recv A 26': 'A に B の 26 が届く。A も自分の 26 のまま。列が 2 本に分かれた',
        'found A 27': 'A が自分の 26 の上に 27 を見つけた',
        'recv B 27': 'B に 27 が届き、長い方へ乗り換える。B の 26 は列から外れた',
    }
    note = '高さ 25 までは 2 人とも同じ列'
    step = 0.2                             # minutes per 200 ms frame = 60x
    now = start
    i = 0
    while now <= end + 1e-9:
        while i < len(ev) and ev[i]['tick'] * ts / 60 <= now:
            e = ev[i]
            b = B[e['hash']]
            m = e['miner']
            know[m][b['hash']] = b
            if e['type'] == 'found' or e.get('switched'):
                tip[m] = b['hash']
            key = f"{e['type']} {m} {b['height']}"
            note = notes.get(key, note)
            i += 1
        state = {'note': note}
        for m in know:
            onchain = set()
            h = tip[m]
            while h in know[m]:
                onchain.add(h)
                h = know[m][h]['parent']
            items = []
            for hh, b in know[m].items():
                if b['height'] < base_h:
                    continue
                if hh in onchain:
                    st = 'main'
                else:                       # off the chain: a competitor at the tip, or left behind
                    st = 'stale' if B[tip[m]]['height'] > b['height'] else 'side'
                items.append((b['height'], b['miner'], st))
            state[m] = items
        frames.append(frame(now, state))
        durs.append(200)
        now += step
    frames.append(frame(end, state, last=True))
    durs.append(3000)
    frames = [f.resize((W, H), Image.LANCZOS) for f in frames]
    frames[0].save(IMG / 'pow_fork.webp', 'WEBP', save_all=True, append_images=frames[1:], duration=durs,
                   loop=0, quality=80, method=6)


# 5 -------------------------------------------------------------------------
def fig_attack():
    fig, ax = plt.subplots(figsize=(10.5, 4.0))
    zs = list(range(0, 11))
    marks = {0.1: BLUE, 0.2: '#4a7a5a', 0.3: OCHRE, 0.4: '#8a5aa0', 0.45: RED}
    for q, c in marks.items():
        ps = [whitepaper(q, z) for z in zs]
        ax.plot(zs, ps, color=c, marker='o', markersize=3.5, linewidth=1.3)
        ax.text(10.2, ps[-1] * {0.45: 0.95, 0.4: 0.7}.get(q, 1), f'q = {q:.0%}', color=c, fontsize=10, va='center')
    ax.plot(zs, [1] * len(zs), color=INK, linewidth=1.6)
    ax.text(10.2, 1.75, 'q = 50% 以上', color=INK, fontsize=10, va='center')
    ax.axvline(6, color=LINE, linestyle='--', linewidth=1)
    ax.text(6.1, 2e-7, '6 承認', color=SUB, fontsize=10)
    ax.set_yscale('log')
    ax.set_ylim(1e-7, 3)
    ax.set_xlim(0, 11.6)
    ax.set_xticks(range(0, 11))
    ax.set_xlabel('待った承認数 z', color=INK)
    ax.set_ylabel('攻撃者が追い付く確率', color=INK)
    ax.set_title('攻撃者が握る計算能力の割合 q ごとに見た、承認数と追い付く確率（ホワイトペーパーの式）', color=INK, fontsize=11, loc='left')
    style(ax)
    fig.tight_layout()
    save_plt(fig, 'pow_attack.webp')


# 6 -------------------------------------------------------------------------
def fig_double_spend():
    d = json.load(open(OUT / 'double_spend.json'))
    ts = d['tick_s']
    run = d['runs'][65]
    assert run['success']
    ev = run['events']
    end = math.ceil(run['end'] * ts / 60 * 2) / 2
    W, H = 900, 470
    lanes = {'honest': 120, 'attacker': 280}
    color = {'honest': (BLUE, BLUE_F), 'attacker': (OCHRE, OCHRE_F)}
    bw, gap = 104, 30
    base_x = 230
    xs = lambda h: base_x + h * (bw + gap)
    paid_min = run['paid'] * ts / 60

    def frame(now, hh, ah, note, done):
        im = Image.new('RGB', (W * S, H * S), '#ffffff')
        dr = ImageDraw.Draw(im)
        t = lambda x, y, s, size=16, c=INK, anchor='la': dr.text((x * S, y * S), s, font=pfont(size), fill=c, anchor=anchor)
        t(24, 16, '二重使用：攻撃者が隠した列が、公開されている列を追い越すまで（攻撃者の計算能力 40%）', 17)
        bx, by, bwid = 24, 52, W - 48
        dr.rectangle((bx * S, by * S, (bx + bwid) * S, (by + 8) * S), fill=GRAY_F)
        dr.rectangle((bx * S, by * S, (bx + bwid * min(now / end, 1)) * S, (by + 8) * S), fill=SUB)
        t(W - 24, 66, f'経過 {now:4.1f} 分（実時間の 150 倍速）', 14, SUB, anchor='ra')
        labels = {'honest': ('公開されている列', '正直なマイナー 60%'), 'attacker': ('攻撃者が隠している列', '攻撃者 40%')}
        # the block both chains build on
        my = (lanes['honest'] + lanes['attacker'] + 56) / 2 - 28
        dr.rounded_rectangle(((base_x - bw - 20) * S, my * S, (base_x - 20) * S, (my + 56) * S), 8 * S, fill=GRAY_F, outline=LINE, width=2 * S)
        t(base_x - 20 - bw / 2, my + 10, '分岐の元', 15, INK, anchor='ma')
        t(base_x - 20 - bw / 2, my + 32, '共通のブロック', 13, SUB, anchor='ma')
        for who, y in lanes.items():
            name, share = labels[who]
            if done and who == 'attacker':
                name = '攻撃者が公開した列'
            t(24, y + 8, name, 15, color[who][0])
            t(24, y + 32, share, 13, SUB)
            n = hh if who == 'honest' else ah
            for h in range(1, n + 1):
                x = xs(h) - bw
                out, fill = color[who]
                if done and who == 'honest':
                    fill, out = RED_F, RED
                dr.rounded_rectangle((x * S, y * S, (x + bw) * S, (y + 56) * S), 8 * S, fill=fill, outline=out, width=2 * S)
                t(x + bw / 2, y + 10, f'{h} 個目', 15, INK, anchor='ma')
                if h == 1:
                    t(x + bw / 2, y + 32, '店への送金' if who == 'honest' else '自分宛てに送る', 13, RED if who == 'honest' else SUB, anchor='ma')
                px = base_x - 20 if h == 1 else xs(h - 1)
                py = my + 28 if h == 1 else y + 28
                dr.line((px * S, py * S, x * S, (y + 28) * S), fill=LINE, width=2 * S)
            if who == 'attacker' and not done:
                t(xs(max(n, 0)) + 16 if n else base_x + 4, y + 18, '（隠している）', 13, SUB)
        t(24, H - 70, f'公開されている列 {hh} 個　{"攻撃者の列" if done else "隠している列"} {ah} 個', 15, SUB)
        t(24, H - 40, note, 15, RED if done else INK)
        return im

    frames, durs = [], []
    now, step = 0.0, 0.5
    while now <= end + 1e-9:
        hh = max([e['height'] for e in ev if e['who'] == 'honest' and e['tick'] * ts / 60 <= now] or [0])
        ah = max([e['height'] for e in ev if e['who'] == 'attacker' and e['tick'] * ts / 60 <= now] or [0])
        if now < paid_min:
            note = '店への送金を公開する一方で、攻撃者は同じコインを自分宛てに送る列を隠れて伸ばす'
        elif ah <= hh:
            note = f'送金が 2 承認になり（{paid_min:.1f} 分）、店は商品を渡した。攻撃者は列を伸ばし続ける'
        else:
            note = ''
        done = ah > hh
        if done:
            note = f'{run["end"] * ts / 60:.1f} 分、隠した列が {ah} 個で公開の {hh} 個を追い越して公開される。ノードは乗り換え、店への送金は消える'
        frames.append(frame(now, hh, ah, note, done))
        durs.append(200)
        now += step
    durs[-1] = 3000
    frames = [f.resize((W, H), Image.LANCZOS) for f in frames]
    frames[0].save(IMG / 'pow_double_spend.webp', 'WEBP', save_all=True, append_images=frames[1:], duration=durs,
                   loop=0, quality=80, method=6)


# 7 -------------------------------------------------------------------------
def fig_inspection():
    import random
    rows = list(csv.DictReader(open(OUT / 'trials.csv')))[1120:1160]   # heights 1,121-1,160
    gaps = [int(r['trials']) / 65536 * 10 for r in rows]
    ends = []
    acc = 0
    for g in gaps:
        acc += g
        ends.append(acc)
    random.seed(1)
    sends = sorted(random.uniform(0, ends[-1]) for _ in range(60))
    import bisect
    hit = [0] * len(gaps)
    for s_ in sends:
        hit[bisect.bisect_right(ends, s_)] += 1
    fig, ax = plt.subplots(figsize=(10.5, 2.6))
    start = 0
    for i, g in enumerate(gaps):
        long_ = g >= 20
        ax.barh(0, g, left=start, height=0.5, color=OCHRE_F if long_ else BLUE_F, edgecolor=OCHRE if long_ else BLUE, linewidth=0.8)
        if long_:
            ax.text(start + g / 2, 0, f'{g:.0f} 分', ha='center', va='center', fontsize=9.5, color=INK)
        start += g
    ax.scatter(sends, [0.48] * len(sends), marker='v', s=22, color=INK, zorder=3)
    long_hits = sum(h for h, g in zip(hit, gaps) if g >= 20)
    long_len = sum(g for g in gaps if g >= 20)
    ax.set_ylim(-0.4, 0.75)
    ax.set_yticks([])
    ax.set_xlim(0, ends[-1])
    ax.set_xlabel('時間（分）', color=INK)
    ax.set_title(f'手元のブロック 40 個（高さ 1,121〜1,160）の間隔（帯）と、ランダムに選んだ送信の時刻 60 回（▼）。'
                 f'20 分以上の間隔（茶）は {sum(g >= 20 for g in gaps)} 個で、▼ の {long_hits} 回が落ちた',
                 color=INK, fontsize=10.5, loc='left')
    style(ax)
    ax.spines['left'].set_visible(False)
    fig.tight_layout()
    save_plt(fig, 'pow_inspection.webp')
    print('inspection: gaps', len(gaps), 'long', sum(g >= 20 for g in gaps), 'long_share_of_time',
          round(long_len / ends[-1], 3), 'hits_long', long_hits, 'of', len(sends))


if __name__ == '__main__':
    IMG.mkdir(exist_ok=True)
    fig_wait()
    fig_hashes()
    fig_retarget()
    fig_fork()
    fig_attack()
    fig_double_spend()
    fig_inspection()
