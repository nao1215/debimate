"""Figures of the UTXO note, drawn from the numbers the lab wrote.

Run lab/utxo_lab.py and lab/fee_history.py first, then:
    python3 content/notes/blockchain-systems/utxo/figures.py

1. utxo_fee_same_balance.webp (cover): fee of a 0.9 BTC payment from 1 coin vs 200 coins.
2. utxo_tx_shape.webp: the 1-coin payment as coins consumed and created.
3. utxo_double_spend.webp: the UTXO set before and after, and the second spend that finds nothing.
4. utxo_small_coins.webp: what 100 coins of 1,000 sat can actually send at each fee rate.
5. utxo_fee_history.webp: median block fee rate over 3 years against the break-even rate.
"""
import csv
import datetime as dt
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
IMG = HERE / 'images'
OUT = HERE / 'lab' / 'output'
INK, SUB, GRID = '#1f1f1f', '#666666', '#dddddd'
ACCENT, ACCENT_PALE = '#4e79a7', '#eaf1f5'
RED, RED_PALE = '#c0392b', '#fbe3e3'
OCHRE, OCHRE_PALE = '#b07d1f', '#f8eed8'
SPENT = '#bbbbbb'

plt.rcParams.update({
    'font.family': ['Noto Sans CJK JP', 'DejaVu Sans'],
    'font.size': 11, 'axes.edgecolor': SUB, 'axes.labelcolor': INK,
    'xtick.color': INK, 'ytick.color': INK, 'text.color': INK,
    'figure.facecolor': '#ffffff', 'axes.facecolor': '#ffffff',
})
RES = json.loads((OUT / 'results.json').read_text())


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=200, facecolor='#ffffff', bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert('RGB').save(IMG / name, 'WEBP', quality=90, method=6)


def comma(n):
    return f'{n:,}'


def cover():
    p = RES['payment']
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    names = ['UTXO 200 個\n（0.005 BTC ずつ）', 'UTXO 1 個\n（1 BTC）']
    rows = [p['many'], p['one']]
    colors = [RED, ACCENT]
    ax.barh(names, [r['fee_sat'] for r in rows], color=colors, height=0.55)
    for y, r in enumerate(rows):
        ax.text(r['fee_sat'] + 2500, y, f"{comma(r['fee_sat'])} sat", va='center', fontsize=13)
        ax.text(r['fee_sat'] + 2500, y - 0.3, f"入力 {r['inputs']} 個・見積もり {comma(r['fee_sat'] // 10)} vB",
                va='center', fontsize=10, color=SUB)
    ratio = p['many']['fee_sat'] / p['one']['fee_sat']
    ax.set_xlim(0, 190_000)
    ax.set_ylim(-0.65, 1.45)
    ax.set_xlabel('手数料（sat）')
    ax.set_title(f'残高はどちらも 1 BTC。0.9 BTC を手数料率 10 sat/vB で送ると、手数料は {ratio:.0f} 倍', fontsize=12)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: comma(int(v))))
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='x', color=GRID)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, 'utxo_fee_same_balance.webp')


def coin(ax, x, y, sat, label, sub, face, edge, scale=0.55, ls='-'):
    r = scale * (sat / 1e8) ** 0.5
    r = max(r, 0.09)
    ax.add_patch(Circle((x, y), r, facecolor=face, edgecolor=edge, lw=2, ls=ls))
    ax.text(x, y - r - 0.12, label, ha='center', va='top', fontsize=11)
    ax.text(x, y - r - 0.42, sub, ha='center', va='top', fontsize=10, color=SUB)
    return r


def tx_shape():
    p = RES['payment']['one']
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.5, 2.5)
    ax.set_aspect('equal')
    ax.axis('off')
    r = coin(ax, 1.4, 0.9, 100_000_000, 'Alice が受け取った出力', '1 BTC = 100,000,000 sat\n入力で丸ごと使う', '#eeeeee', SPENT, ls='--')
    ax.text(1.4, 0.9, '使用済み\nになる', ha='center', va='center', fontsize=10, color=SUB)
    ax.add_patch(FancyBboxPatch((3.8, 0.45), 2.2, 0.9, boxstyle='round,pad=0.05', facecolor='#ffffff', edgecolor=INK, lw=1.6))
    ax.text(4.9, 0.9, 'トランザクション', ha='center', va='center', fontsize=11)
    ax.add_patch(FancyArrowPatch((1.4 + r + 0.05, 0.9), (3.75, 0.9), arrowstyle='-|>', mutation_scale=16, color=SUB, lw=1.6))
    ax.text(2.6, 1.02, '入力 0', ha='center', va='bottom', fontsize=10, color=SUB)
    r1 = coin(ax, 8.0, 1.55, 90_000_000, '出力 0：Bob 宛て', '90,000,000 sat', ACCENT_PALE, ACCENT, scale=0.42)
    r2 = coin(ax, 8.0, -0.25, p['change_sat'], '出力 1：Alice へのお釣り', f"{comma(p['change_sat'])} sat", ACCENT_PALE, ACCENT, scale=0.42)
    ax.add_patch(FancyArrowPatch((6.05, 1.1), (8.0 - r1 - 0.05, 1.55), arrowstyle='-|>', mutation_scale=16, color=ACCENT, lw=1.6))
    ax.add_patch(FancyArrowPatch((6.05, 0.7), (8.0 - r2 - 0.05, -0.25), arrowstyle='-|>', mutation_scale=16, color=ACCENT, lw=1.6))
    ax.text(4.9, 0.1, f"入力 − 出力 = {comma(p['fee_sat'])} sat\nこの差が手数料", ha='center', va='top', fontsize=10.5, color=OCHRE,
            bbox=dict(boxstyle='round,pad=0.35', facecolor=OCHRE_PALE, edgecolor=OCHRE))
    ax.text(5.0, 2.3, '使った出力は消え、新しい出力 2 つが UTXO になる', ha='center', va='top', fontsize=12)
    save(fig, 'utxo_tx_shape.webp')


def double_spend():
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 5.2)
    ax.axis('off')

    def table(x, title, rows):
        ax.text(x + 1.6, 4.85, title, ha='center', va='top', fontsize=11.5)
        ax.add_patch(FancyBboxPatch((x, 0.5), 3.2, 3.85, boxstyle='round,pad=0.04', facecolor='#fafafa', edgecolor=SUB, lw=1.2))
        for i, (text, face, edge) in enumerate(rows):
            y = 3.65 - i * 0.85
            ax.add_patch(FancyBboxPatch((x + 0.2, y - 0.3), 2.8, 0.6, boxstyle='round,pad=0.02', facecolor=face, edgecolor=edge, lw=1.4))
            ax.text(x + 1.6, y, text, ha='center', va='center', fontsize=10)

    table(0.3, 'UTXO セット（使う前）', [('one:0　Alice　1 BTC', ACCENT_PALE, ACCENT), ('many:0〜199　Carol', ACCENT_PALE, ACCENT)])
    table(4.4, 'トランザクション 1 を適用した後', [('tx1:0　Bob　0.9 BTC', ACCENT_PALE, ACCENT),
                                         ('tx1:1　Alice　お釣り', ACCENT_PALE, ACCENT),
                                         ('many:0〜199　Carol', ACCENT_PALE, ACCENT)])
    ax.text(6.0, 0.95, 'one:0 は削除された', ha='center', va='center', fontsize=10, color=SUB)
    ax.add_patch(FancyArrowPatch((3.55, 2.4), (4.35, 2.4), arrowstyle='-|>', mutation_scale=16, color=SUB, lw=1.6))
    ax.text(3.95, 2.55, 'tx1', ha='center', va='bottom', fontsize=10, color=SUB)
    ax.add_patch(FancyBboxPatch((8.2, 2.5), 3.9, 1.3, boxstyle='round,pad=0.05', facecolor=RED_PALE, edgecolor=RED, lw=1.6))
    ax.text(10.15, 3.45, 'トランザクション 2（tx2）', ha='center', va='center', fontsize=11)
    ax.text(10.15, 2.9, '入力 one:0 → お店宛て', ha='center', va='center', fontsize=10)
    ax.add_patch(FancyArrowPatch((8.25, 2.7), (7.7, 2.2), arrowstyle='-|>', mutation_scale=14, color=RED, lw=1.4, ls='--'))
    ax.text(10.15, 1.9, '拒否：入力が\nUTXO セットに無い', ha='center', va='center', fontsize=10.5, color=RED)
    save(fig, 'utxo_double_spend.webp')


def small_coins():
    s = RES['small_coins']
    rates = [r['fee_rate'] for r in s['curve']]
    allin = [r['all']['received'] for r in s['curve']]
    best = [r['send_max']['received'] if r['send_max'] else 0 for r in s['curve']]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.axhline(s['balance'], color=SUB, ls='--', lw=1.2)
    ax.text(30, s['balance'] + 3000, f"表示上の残高 {comma(s['balance'])} sat", ha='right', color=SUB, fontsize=10)
    ax.axhline(0, color=INK, lw=0.8)
    ax.plot(rates, allin, color=SUB, lw=1.6, marker='o', ms=4, ls=':', label='100 個すべてを入力にした時')
    ax.plot(rates, best, color=RED, lw=2.4, marker='o', ms=4, label='受け取れる額（赤字の UTXO を外した時）')
    be = s['break_even_rate']
    ax.axvline(be, color=OCHRE, lw=1.4)
    ax.text(be - 0.4, -75_000, f'{be:.1f} sat/vB\n1 個の額 = 1 個を\n使う手数料', color=OCHRE, fontsize=10, ha='right')
    ax.set_xlim(0, 30.5)
    ax.set_ylim(-110_000, 115_000)
    ax.set_xlabel('手数料率（sat/vB）')
    ax.set_ylabel('送り先が受け取る額（sat）')
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: comma(int(v))))
    ax.set_title('1,000 sat の UTXO 100 個を 1 つの出力にまとめて送る', fontsize=12)
    ax.legend(loc='upper right', bbox_to_anchor=(1.0, 0.86), fontsize=10, frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, 'utxo_small_coins.webp')


def fee_history():
    times, med = [], []
    with (OUT / 'fee_rates_3y.csv').open() as f:
        for row in csv.DictReader(f):
            times.append(dt.datetime.strptime(row['utc'], '%Y-%m-%dT%H:%M'))
            med.append(max(int(row['median_sat_per_vb']), 1))
    be = RES['small_coins']['break_even_rate']
    fig, ax = plt.subplots(figsize=(7.8, 3.8))
    ax.fill_between(times, be, [max(m, be) for m in med], color=RED_PALE, step='mid')
    ax.plot(times, med, color=INK, lw=0.9, drawstyle='steps-mid')
    ax.axhline(be, color=OCHRE, lw=1.4)
    ax.text(times[-1], be * 1.25, f'{be:.1f} sat/vB（1,000 sat の UTXO が赤字になる境目）', ha='right', color=OCHRE, fontsize=10)
    peak = max(range(len(med)), key=med.__getitem__)
    ax.annotate(f'{times[peak]:%Y-%m-%d}\n{comma(med[peak])} sat/vB', (times[peak], med[peak]), xytext=(25, -8),
                textcoords='offset points', fontsize=10, arrowprops=dict(arrowstyle='-', color=SUB))
    ax.set_yscale('log')
    ax.set_ylim(0.8, 3000)
    ax.set_yticks([1, 10, 100, 1000])
    ax.set_yticklabels(['1', '10', '100', '1,000'])
    ax.set_ylabel('手数料率（ブロックごとの中央値、sat/vB）')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.set_title('2023-11 から 2026-11 までの手数料率（mempool.space の API、約 12 時間ごとの平均）', fontsize=11)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', color=GRID)
    fig.tight_layout()
    save(fig, 'utxo_fee_history.webp')


if __name__ == '__main__':
    IMG.mkdir(exist_ok=True)
    cover()
    tx_shape()
    double_spend()
    small_coins()
    fee_history()
