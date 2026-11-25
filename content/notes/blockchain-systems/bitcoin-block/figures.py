"""Generate the figures of the Bitcoin Block note.

Input: lab/output/blocks.json (fetch_mainnet.py, mempool.space, 2026-11-17),
heights 973,727-975,743. The period is 973,728-975,743 (2,016 blocks).

1. block_time_diff.webp (cover): header time minus the parent's header time.
2. block_header_bytes.webp: the 80 bytes of block 973,962 and its hash in both byte orders.
3. block_arrival.webp (animated): blocks 973,960-973,963. When mempool.space first saw
   each block (firstSeen) and the time written in its header. The measured times are
   played at 80x speed (80 s per second), the last frame stays 3 s.
4. block_parent_ahead.webp: the 33 backward blocks that have firstSeen for both blocks.
5. block_time_window.webp: lower bound (median of the previous 11) and header time,
   both relative to firstSeen, with the +2 h upper bound.
6. block_version_bits.webp: share of blocks with each version bit set.
7. block_size_weight.webp: size and weight of the 2,016 blocks.
8. block_fork_steps.webp: a fork at height H in 3 steps (schematic, no measured times).

Background is white (dark mode). Run: python3 figures.py
"""
import io
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / 'lab' / 'output'
IMG = HERE / 'images'

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

ROWS = json.load(open(OUT / 'blocks.json'))
BY = {b['height']: b for b in ROWS}
PERIOD = ROWS[1:]


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
def fig_time_diff():
    d = [(b['timestamp'] - BY[b['height'] - 1]['timestamp']) / 60 for b in PERIOD]
    neg = [x for x in d if x < 0]
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    bins = [i for i in range(-7, 61)]
    ax.hist([x for x in d if x >= 0], bins=bins, color=BLUE_F, edgecolor=BLUE, linewidth=0.7)
    ax.hist(neg, bins=bins, color=RED_F, edgecolor=RED, linewidth=0.9)
    ax.axvline(0, color=INK, linewidth=0.8)
    ax.set_xlim(-8, 60)
    ax.set_xlabel('直前ブロックとの時刻差（分）', color=SUB)
    ax.set_ylabel('ブロックの数', color=SUB)
    ax.annotate(f'直前ブロックより古い時刻\n{len(neg)} 個（{100 * len(neg) / len(d):.1f}%）、最も古いのは −372 秒',
                xy=(-2.5, 14), xytext=(5, 118), color=RED, fontsize=12,
                arrowprops=dict(arrowstyle='->', color=RED, lw=1))
    over = sum(x > 60 for x in d)
    ax.text(59, 60, f'60 分を超える {over} 個は省略', ha='right', color=SUB, fontsize=10)
    ax.set_title('Bitcoin の 2,016 ブロック（973,728〜975,743 番）の時刻の差', color=INK, fontsize=13, loc='left', pad=12)
    style(ax)
    save_plt(fig, 'block_time_diff.webp')


# 2 -------------------------------------------------------------------------
def fig_header_bytes():
    raw = bytes.fromhex(BY[973962]['header'])
    fields = [('バージョン', 0, 4, GRAY_F, LINE), ('直前ブロックのハッシュ値', 4, 36, BLUE_F, BLUE),
              ('merkle root', 36, 68, BLUE_F, BLUE), ('時刻', 68, 72, RED_F, RED),
              ('bits', 72, 76, OCHRE_F, OCHRE), ('nonce', 76, 80, OCHRE_F, OCHRE)]
    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.set_xlim(-1, 81)
    ax.set_ylim(-5.2, 3.2)
    ax.axis('off')
    for name, a, b, fc, ec in fields:
        ax.add_patch(Rectangle((a, 0), b - a, 1.4, facecolor=fc, edgecolor=ec, linewidth=1.2))
        n = b - a
        if n >= 32:
            ax.text((a + b) / 2, 0.95, name, ha='center', va='center', color=INK, fontsize=12)
            ax.text((a + b) / 2, 0.42, f'{n} バイト', ha='center', va='center', color=SUB, fontsize=10)
        else:
            ax.text((a + b) / 2, 0.7, str(n), ha='center', va='center', color=SUB, fontsize=10)
    # labels of the 4-byte fields
    ax.annotate('バージョン', xy=(2, 1.4), xytext=(2, 2.5), ha='center', color=INK, fontsize=11,
                arrowprops=dict(arrowstyle='-', color=LINE))
    for name, x, tx in (('時刻', 70, 63), ('bits', 74, 73), ('nonce', 78, 80)):
        ax.annotate(name, xy=(x, 1.4), xytext=(tx, 2.5), ha='center', color=INK, fontsize=11,
                    arrowprops=dict(arrowstyle='-', color=LINE))
    for x in (0, 4, 36, 68, 72, 76, 80):
        ax.text(x, -0.35, str(x), ha='center', va='top', color=SUB, fontsize=9)
    t = int.from_bytes(raw[68:72], 'little')
    when = datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    ax.text(0, -1.25, f'時刻の 4 バイト {raw[68:72].hex()} を小さい桁から読むと {t}（{when}）',
            ha='left', va='center', color=RED, fontsize=11)
    import hashlib
    h = hashlib.sha256(hashlib.sha256(raw).digest()).digest()
    ax.text(0, -2.55, '80 バイトに SHA-256 を 2 回掛けた結果（計算したままの順）', color=SUB, fontsize=10.5)
    ax.text(0, -3.2, h.hex(), color=INK, fontsize=11.5, family='DejaVu Sans Mono')
    ax.text(0, -4.05, 'エクスプローラ・RPC が表示する順（バイトを逆に並べたもの）', color=SUB, fontsize=10.5)
    ax.text(0, -4.7, h[::-1].hex(), color=INK, fontsize=11.5, family='DejaVu Sans Mono')
    ax.set_title('973,962 番のブロックヘッダ（80 バイト）とハッシュ値', color=INK, fontsize=13, loc='left')
    save_plt(fig, 'block_header_bytes.webp')


# 3 -------------------------------------------------------------------------
def pfont(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, size)


def fig_arrival():
    S = 2
    W, H = 1100, 470
    hs = [973960, 973961, 973962, 973963]
    x0t, x1t = 1793440080, 1793441280       # 20 minutes on both axes
    L, R = 110, W - 50
    ya, yh = 200, 360                        # arrival axis, header-time axis
    start, end = 1793440140, 1793441200
    speed = 80
    step = 20                                # 20 s of real time per 250 ms frame
    frames, durs = [], []

    def X(t):
        return L + (t - x0t) / (x1t - x0t) * (R - L)

    def hm(t):
        return datetime.fromtimestamp(t, timezone.utc).strftime('%H:%M')

    times = list(range(start, end + 1, step))
    for now in times:
        im = Image.new('RGB', (W * S, H * S), '#ffffff')
        d = ImageDraw.Draw(im)

        def t(x, y, s, size, color=INK, anchor='la', mono=False):
            d.text((x * S, y * S), s, fill=color, font=pfont(size * S, mono), anchor=anchor)

        def line(x0, y0, x1, y1, color=LINE, w=1):
            d.line([(x0 * S, y0 * S), (x1 * S, y1 * S)], fill=color, width=w * S)

        t(24, 18, 'ブロックを受け取った時刻と、ヘッダに書かれた時刻（973,960〜973,963 番）', 17)
        t(24, 48, '上の線は mempool.space がブロックを最初に受け取った時刻、下の線はヘッダの時刻（UTC、2026-10-31）', 12.5, SUB)
        t(W - 24, 74, f'経過 {now - start:4d} 秒（実時間の {speed} 倍速）', 13, SUB, anchor='ra')
        # progress band
        line(24, 100, W - 24, 100, '#dddddd', 6)
        px = 24 + (now - start) / (end - start) * (W - 48)
        line(24, 100, px, 100, BLUE, 6)
        for y, name in ((ya, '受け取った時刻'), (yh, 'ヘッダの時刻')):
            line(L, y, R, y, LINE, 1)
            t(L - 10, y, name, 12, SUB, anchor='rm')
            for m in range(0, 21, 2):
                tx = x0t + m * 60
                line(X(tx), y - 4, X(tx), y + 4, LINE, 1)
                t(X(tx), y + 10, hm(tx), 10.5, SUB, anchor='ma')
        # the clock of the observer on the arrival axis
        line(X(now), ya - 50, X(now), ya, BLUE, 1)
        t(X(now), ya - 54, '今', 11, BLUE, anchor='md')
        seen = [h for h in hs if BY[h]['firstSeen'] <= now]
        crossed = 973961 in seen and 973962 in seen
        for h in seen:
            b = BY[h]
            xa, xh = X(b['firstSeen']), X(b['timestamp'])
            red = crossed and h in (973961, 973962)
            c = RED if red else BLUE
            line(xa, ya, xh, yh, c, 2)
            r = 6
            for x, y in ((xa, ya), (xh, yh)):
                d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=c)
            # 973,961 and 973,962 arrived 32 s apart: label them left and right
            if h == 973961:
                t(xa - 8, ya - 10, f'{h:,}', 12, c, anchor='rd')
            elif h == 973962:
                t(xa + 8, ya - 10, f'{h:,}', 12, c, anchor='ld')
            else:
                t(xa, ya - 26, f'{h:,}', 12, c, anchor='ma')
        if 973961 in seen:
            b = BY[973961]
            t(X(b['timestamp']) + 8, yh + 30, f'973,961 番: 受け取った時刻より {b["timestamp"] - b["firstSeen"]:.0f} 秒先', 11.5, RED if crossed else BLUE, anchor='ma')
        if crossed:
            t(W / 2, H - 28, '973,962 番の時刻は 973,961 番より 372 秒前。線が交差するのは、前のブロックが先の時刻を書いたため', 13, RED, anchor='mm')
        frames.append(im.resize((W, H), Image.LANCZOS))
        durs.append(int(step / speed * 1000))
    durs[-1] = 3000
    frames[0].save(IMG / 'block_arrival.webp', 'WEBP', save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, quality=80, method=6)


# 4 -------------------------------------------------------------------------
def fig_parent_ahead():
    pairs = []
    for b in PERIOD:
        p = BY[b['height'] - 1]
        if b['timestamp'] < p['timestamp'] and b['firstSeen'] and p['firstSeen']:
            pairs.append((p['timestamp'] - p['firstSeen'], b['timestamp'] - b['firstSeen']))
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for a, c in pairs:
        ax.plot([0, 1], [a, c], color=LINE, linewidth=0.8)
    ax.scatter([0] * len(pairs), [a for a, _ in pairs], color=RED, s=18, zorder=3)
    ax.scatter([1] * len(pairs), [c for _, c in pairs], color=BLUE, s=18, zorder=3)
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks([0, 1], ['前のブロック', '時刻が前より古いブロック'])
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylabel('ヘッダの時刻 − 受け取った時刻（秒）', color=SUB)
    ax.text(0.5, 500, f'{len(pairs)} 組の全てで、前のブロックの時刻が\n受け取った時刻より先（0 より上）', ha='center', color=INK, fontsize=11)
    ax.set_ylim(-120, 600)
    ax.set_title(f'時刻が逆転した {len(pairs)} 組の、受け取った時刻との差', color=INK, fontsize=12.5, loc='left')
    style(ax)
    save_plt(fig, 'block_parent_ahead.webp')


# 5 -------------------------------------------------------------------------
def fig_time_window():
    low, hdr = [], []
    for b in PERIOD:
        if b['firstSeen']:
            low.append((BY[b['height'] - 1]['mediantime'] - b['firstSeen']) / 60)
            hdr.append((b['timestamp'] - b['firstSeen']) / 60)
    import random
    rnd = random.Random(1)
    fig, ax = plt.subplots(figsize=(10.5, 3.6))
    ax.axvspan(max(low), 120, color='#f4f7f2')
    ax.scatter(low, [1 + rnd.uniform(-0.18, 0.18) for _ in low], s=5, color=OCHRE, alpha=0.6)
    ax.scatter(hdr, [0 + rnd.uniform(-0.18, 0.18) for _ in hdr], s=5, color=BLUE, alpha=0.6)
    ax.text((max(low) + 120) / 2, 0.62, '全てのブロックで許される範囲\n（最も遅い下限〜上限）', ha='center', va='center', color=SUB, fontsize=10.5)
    ax.axvline(120, color=RED, linestyle='--', linewidth=1)
    ax.axvline(0, color=INK, linewidth=0.6)
    ax.text(118, 1.45, '上限: 受け取ったノードの時計 + 2 時間', ha='right', color=RED, fontsize=10.5)
    ax.text(statistics.median(low), 1.38, '下限: 直前 11 個の時刻の中央値', ha='center', color=OCHRE, fontsize=10.5)
    ax.text(10, -0.42, f'ヘッダの時刻: {min(hdr):.1f}〜+{max(hdr):.1f} 分', ha='left', color=BLUE, fontsize=10.5)
    ax.set_yticks([0, 1], ['ヘッダの時刻', '下限'])
    ax.set_ylim(-0.6, 1.65)
    ax.set_xlim(-190, 130)
    ax.set_xlabel('mempool.space が受け取った時刻との差（分）', color=SUB)
    ax.set_title(f'許される範囲と、実際に書かれた時刻（受け取った時刻の記録がある {len(hdr):,} 個）', color=INK, fontsize=12.5, loc='left')
    style(ax)
    save_plt(fig, 'block_time_window.webp')


# 6 -------------------------------------------------------------------------
def fig_version_bits():
    n = len(PERIOD)
    share = [sum((b['version'] >> i) & 1 for b in PERIOD) / n for i in range(32)]
    fig, ax = plt.subplots(figsize=(11, 2.6))
    for col, bit in enumerate(range(31, -1, -1)):
        s = share[bit]
        fc = RED if bit == 29 else (BLUE if s > 0 else '#ffffff')
        alpha = 1 if bit == 29 else (0.25 + 0.75 * s if s > 0 else 1)
        ax.add_patch(Rectangle((col, 0), 1, 1, facecolor=fc, alpha=alpha, edgecolor=LINE, linewidth=0.8))
        ax.text(col + 0.5, -0.25, str(bit), ha='center', va='top', color=SUB, fontsize=8.5)
        if s > 0:
            ax.text(col + 0.5, 0.5, f'{round(100 * s)}', ha='center', va='center',
                    color='#ffffff' if bit == 29 or s > 0.4 else INK, fontsize=8.5)
    ax.annotate('', xy=(2.9, 1.25), xytext=(19.1, 1.25), arrowprops=dict(arrowstyle='<->', color=BLUE))
    ax.text(11, 1.45, '13〜28 番目のビット: マイナーが nonce の代わりに変える範囲', ha='center', color=BLUE, fontsize=10.5)
    ax.text(2.5, -0.75, '29 番目は常に 1', ha='center', color=RED, fontsize=10.5)
    ax.text(32, 1.45, 'ビットが 1 だったブロックの割合（%）', ha='right', color=SUB, fontsize=10)
    ax.set_xlim(-0.2, 32.2)
    ax.set_ylim(-1.05, 1.8)
    ax.axis('off')
    ax.set_title(f'バージョンの 32 ビット（2,016 個のブロック、値は {len({b["version"] for b in PERIOD}):,} 通り）', color=INK, fontsize=12.5, loc='left')
    save_plt(fig, 'block_version_bits.webp')


# 7 -------------------------------------------------------------------------
def fig_size_weight():
    s = [b['size'] / 1e6 for b in PERIOD]
    w = [b['weight'] / 1e6 for b in PERIOD]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.scatter(s, w, s=6, color=BLUE, alpha=0.5)
    ax.axhline(4.0, color=RED, linestyle='--', linewidth=1)
    ax.axvline(1.0, color=LINE, linestyle=':', linewidth=1)
    ax.text(4.05, 4.04, '上限: weight 4,000,000', ha='right', va='bottom', color=RED, fontsize=10.5)
    ax.text(1.03, 0.3, '1,000,000 バイト', ha='left', color=SUB, fontsize=10)
    ax.set_xlim(0, 4.1)
    ax.set_ylim(0, 4.4)
    ax.set_xlabel('ブロックの大きさ（100 万バイト）', color=SUB)
    ax.set_ylabel('weight（100 万）', color=SUB)
    ax.set_title('ブロックの大きさと weight（2,016 個）', color=INK, fontsize=12.5, loc='left')
    style(ax)
    save_plt(fig, 'block_size_weight.webp')


# 8 -------------------------------------------------------------------------
def fig_fork_steps():
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    titles = ['1. 末尾が 2 本に分かれる', '2. B の後ろに次のブロックが付く', '3. B の列が選ばれ、t は mempool へ']
    W, H = 1.9, 1.15

    def block(ax, x, y, name, height, tx=False, gone=False):
        ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle='round,pad=0.02',
                                    facecolor=GRAY_F if gone else BLUE_F, edgecolor=LINE if gone else BLUE, linewidth=1.2))
        c = SUB if gone else INK
        ax.text(x + W / 2, y + 0.85, name, ha='center', va='center', color=c, fontsize=11.5)
        ax.text(x + W / 2, y + 0.52, height, ha='center', va='center', color=SUB, fontsize=9.5)
        if tx:
            ax.text(x + W / 2, y + 0.2, '送金 t', ha='center', va='center', color=SUB if gone else RED, fontsize=10)

    def arrow(ax, x0, y0, x1, y1, color=LINE):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='->', mutation_scale=12, color=color, lw=1.1))

    for i, ax in enumerate(axes):
        ax.set_xlim(0, 7.3)
        ax.set_ylim(-0.3, 3.6)
        ax.axis('off')
        ax.set_title(titles[i], loc='left', color=INK, fontsize=12)
        block(ax, 0.05, 1.15, '直前', '高さ H−1')
        block(ax, 2.5, 2.3, 'A', '高さ H', tx=True, gone=(i == 2))
        block(ax, 2.5, 0.0, 'B', '高さ H')
        arrow(ax, 2.5, 2.85, 1.95, 2.0)
        arrow(ax, 2.5, 0.55, 1.95, 1.4)
        if i >= 1:
            block(ax, 5.0, 0.0, 'C', '高さ H+1')
            arrow(ax, 5.0, 0.57, 4.4, 0.57)
        if i == 0:
            ax.text(4.7, 2.85, 't の承認数: 1', color=RED, fontsize=10.5, va='center')
        if i == 1:
            ax.text(4.6, 2.85, 'B の列の方が\n計算量の合計が大きい', color=SUB, fontsize=10, va='center')
        if i == 2:
            ax.add_patch(FancyBboxPatch((4.85, 2.3), 2.4, H, boxstyle='round,pad=0.02',
                                        facecolor=OCHRE_F, edgecolor=OCHRE, linewidth=1.2))
            ax.text(6.05, 3.1, 'mempool', ha='center', va='center', color=INK, fontsize=10.5)
            ax.text(6.05, 2.65, '送金 t（承認数 0）', ha='center', va='center', color=RED, fontsize=10)
            arrow(ax, 4.4, 2.85, 4.85, 2.85, RED)
    fig.tight_layout()
    save_plt(fig, 'block_fork_steps.webp')

if __name__ == '__main__':
    IMG.mkdir(exist_ok=True)
    fig_time_diff()
    fig_header_bytes()
    fig_arrival()
    fig_parent_ahead()
    fig_time_window()
    fig_version_bits()
    fig_size_weight()
    fig_fork_steps()
