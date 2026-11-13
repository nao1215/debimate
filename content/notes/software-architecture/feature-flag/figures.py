"""Generate the figures of the Feature Flag note (WebP).

flicker_figure() and timeline_animation() read lab/output.txt (lab/run.py).
bucket_figure() puts real hash values of 30 users on a 0-99 line.
overlap_figure() uses the two rules in lab/overlap.py.
knight_figure() draws the stages in the SEC order on Knight Capital (2013).

Run: python3 content/notes/software-architecture/feature-flag/figures.py
"""

import io
import re
import subprocess
import sys
import zlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
sys.path.insert(0, str(HERE / "lab"))
from overlap import per_flag, shared  # noqa: E402

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#4e86ad", "#e15759"
PALE, OCHRE, LINE = "#eaf1f5", "#d4a24c", "#cccccc"
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _style():
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
                         "axes.edgecolor": SUB, "text.color": INK})


def _save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    Image.open(buf).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def _sections():
    text = (HERE / "lab" / "output.txt").read_text()
    return {m.group(1): m.group(2) for m in re.finditer(r"^== (.+)\n((?:  .*\n?)*)", text, re.M)}


def flicker_figure():
    sec = _sections()
    rows = [
        ("3 台のサーバー、hash()", "3 pods (uvicorn x3, round robin), builtin"),
        ("uvicorn --workers 3、hash()", "uvicorn --workers 3 (spawn), builtin"),
        ("gunicorn -w 3、hash()", "gunicorn -w 3 (fork), builtin"),
        ("3 台のサーバー、crc32", "3 pods (uvicorn x3, round robin), crc32"),
        ("uvicorn --workers 3、crc32", "uvicorn --workers 3 (spawn), crc32"),
    ]
    _style()
    fig, (left, right) = plt.subplots(1, 2, figsize=(8.2, 3.0), gridspec_kw={"width_ratios": [1, 1.5]})
    for i, (label, key) in enumerate(rows):
        body = sec[key]
        ons = [float(v) for v in re.findall(r"on ([\d.]+)%", body)]
        changed = float(re.search(r"changed: \d+ \(([\d.]+)%\)", body).group(1))
        y = len(rows) - 1 - i
        left.scatter(ons, [y] * len(ons), s=36, color=INK, zorder=3)
        color = RED if changed > 0 else SUB
        right.barh(y, changed, color=color, height=0.55)
        right.text(changed + 0.8, y, f"{changed:.1f}%", va="center", fontsize=9.5,
                   color=RED if changed > 0 else INK)
    labels = [r[0] for r in rows][::-1]
    left.set_yticks(range(len(rows)), labels)
    left.set_xlim(0, 20)
    left.axvline(10, color=LINE, lw=1, zorder=1)
    left.set_xlabel("プロセスごとの有効の割合（%）")
    left.set_title("どのプロセスも約 10% を有効にする", fontsize=10, loc="left")
    right.set_yticks([])
    right.set_xlim(0, 35)
    right.set_xlabel("6 回の中で答えが変わったユーザー（%）")
    right.set_title("それでも答えが変わるユーザーがいる", fontsize=10, loc="left")
    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(-0.6, len(rows) - 0.4)
    fig.tight_layout(w_pad=1.0)
    _save(fig, "feature-flag_flicker.webp")


def _builtin_buckets(users, seed):
    code = "import sys\nfor u in sys.argv[1:]: print(hash(u) % 100)"
    out = subprocess.run([sys.executable, "-c", code, *users], check=True,
                         capture_output=True, text=True, env={"PYTHONHASHSEED": str(seed)}).stdout
    return [int(x) for x in out.split()]


def bucket_figure():
    users = [f"u-{i:05d}" for i in range(30)]
    crc = [zlib.crc32(u.encode()) % 100 for u in users]
    # Two interpreter starts. The seeds are fixed only so that the figure can be regenerated.
    before, after = _builtin_buckets(users, 11), _builtin_buckets(users, 12)
    rows = [
        ("crc32、10%", crc, 10, None),
        ("crc32、20% に上げる", crc, 20, crc),
        ("hash()、10%", before, 10, None),
        ("hash()、10%（再起動の後）", after, 10, before),
    ]
    _style()
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    for i, (label, vals, pct, prev) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.add_patch(Rectangle((-0.5, y - 0.28), pct, 0.56, color=PALE, zorder=1))
        ax.plot([-0.5, 99.5], [y, y], color=LINE, lw=1, zorder=2)
        ax.plot([pct - 0.5] * 2, [y - 0.34, y + 0.34], color=ACCENT, lw=2, zorder=3)
        ax.text(pct + 0.6, y + 0.3, f"{pct} 未満は有効", fontsize=10, color=ACCENT, va="bottom")
        was_on = set()
        if prev is not None:
            was_on = {k for k, v in enumerate(prev) if v < 10}
        placed = []
        for k, v in enumerate(vals):
            on = v < pct
            edge = RED if k in was_on and not on else INK
            # Users whose numbers are equal or adjacent would hide each other, so stack them.
            near = sum(1 for w in placed if abs(w - v) <= 1)
            placed.append(v)
            dy = (0, 0.17, -0.17, 0.34)[near]
            ax.scatter(v, y + dy, s=46, zorder=4, facecolor=INK if on else "#ffffff", edgecolor=edge,
                       linewidth=1.8 if edge == RED else 1.1)
        ax.text(-3, y, label, ha="right", va="center", fontsize=11)
    ax.set_xlim(-0.5, 99.5)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_yticks([])
    ax.set_xticks([0, 10, 20, 50, 99])
    ax.set_xlabel("ユーザーに付いた番号（0〜99）。黒は有効、白は無効、赤い縁は前の段で有効だった人", fontsize=10.5)
    ax.spines[["top", "right", "left"]].set_visible(False)
    _save(fig, "feature-flag_bucket.webp")


def overlap_figure():
    users = [f"u-{i:06d}" for i in range(400)]
    text = (HERE / "lab" / "overlap_output.txt").read_text()
    both = re.findall(r"both on (\d+) \(([\d.]+)% of users", text)
    panels = [("同じ番号を全てのフラグで使う", shared, both[0]),
              ("フラグの名前を混ぜて番号を出す", per_flag, both[1])]
    colors = {(True, True): RED, (True, False): ACCENT, (False, True): OCHRE, (False, False): "#ffffff"}
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.4))
    for ax, (title, rule, (n, pct)) in zip(axes, panels):
        for k, u in enumerate(users):
            a, b = rule("new-checkout", u, 10), rule("new-search", u, 10)
            x, y = k % 20, 19 - k // 20
            ax.add_patch(Rectangle((x + 0.06, y + 0.06), 0.88, 0.88, facecolor=colors[(a, b)],
                                   edgecolor=LINE, lw=0.6))
        ax.set_xlim(0, 20)
        ax.set_ylim(0, 20)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=10.5)
        ax.text(10, -1.2, f"10 万人のうち両方が有効: {int(n):,} 人（{pct}%）", ha="center", fontsize=9.5,
                color=RED if float(pct) > 5 else INK)
    handles = [Rectangle((0, 0), 1, 1, facecolor=c, edgecolor=LINE) for c in (ACCENT, OCHRE, RED)]
    fig.legend(handles, ["new-checkout だけ有効", "new-search だけ有効", "両方が有効"],
               loc="lower center", ncol=3, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _save(fig, "feature-flag_overlap.webp")


def knight_figure():
    stages = [
        ("7 月 27 日から: 新しいコードを順に配布する", ["new"] * 7 + ["old"],
         "8 台目には配布されなかった"),
        ("8 月 1 日: 同じフラグを付けた注文が届く", ["ok"] * 7 + ["bad"],
         "8 台目は Power Peg を動かす"),
        ("対処: 7 台から新しいコードを外す", ["bad"] * 8,
         "8 台全てが Power Peg を動かす"),
    ]
    look = {"new": ("#ffffff", ACCENT, "RLP"), "ok": (PALE, ACCENT, "RLP"),
            "old": ("#ffffff", SUB, "古い\nコード"), "bad": ("#fbe3e3", RED, "Power\nPeg")}
    _style()
    fig, axes = plt.subplots(3, 1, figsize=(7.0, 3.8))
    for ax, (title, kinds, note) in zip(axes, stages):
        for k, kind in enumerate(kinds):
            fill, edge, label = look[kind]
            ax.add_patch(FancyBboxPatch((k * 1.1 + 0.05, 0.1), 0.95, 0.8, boxstyle="round,pad=0.02,rounding_size=0.08",
                                        facecolor=fill, edgecolor=edge, lw=1.6))
            ax.text(k * 1.1 + 0.52, 0.5, label, ha="center", va="center", fontsize=9.5,
                    color=RED if kind == "bad" else INK, linespacing=1.35)
        ax.text(0.05, 1.12, title, fontsize=11, va="bottom")
        ax.text(9.0, 0.5, note, fontsize=10.5, va="center", color=RED if "Power" in note else INK)
        ax.set_xlim(0, 12.6)
        ax.set_ylim(0, 1.5)
        ax.axis("off")
    fig.tight_layout(h_pad=0.6)
    _save(fig, "feature-flag_knight.webp")


def timeline_animation():
    body = _sections()
    key = next(k for k in body if k.startswith("timeline"))
    user = re.search(r"user (u-\d+)", key).group(1)
    reqs = [(float(t), int(w), on == "True") for t, w, on in
            re.findall(r"t=([\d.]+) worker=(\d) on=(\w+)", body[key])]
    S, W, H = 2, 900, 400
    f = lambda n: ImageFont.truetype(CJK, n * S)  # noqa: E731
    mono = ImageFont.truetype(MONO, 13 * S)
    T = 8.0
    X0, X1 = 150, 600
    X = lambda t: (X0 + (X1 - X0) * t / T) * S  # noqa: E731
    lane_y = {1: 150, 2: 210, 3: 270}
    STEP, SPEED = 0.125, 0.5
    frames = []
    times = [i * STEP for i in range(int(reqs[-1][0] / STEP) + 2)]
    for now in times:
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((20 * S, 14 * S), f"同じユーザー {user} が 0.5 秒ごとに開いた時の答え（uvicorn --workers 3、hash()）",
               font=f(17), fill=INK)
        d.text((20 * S, 44 * S), f"経過 {now:4.2f} 秒（実測の時刻を {SPEED} 倍速で再生）", font=f(15), fill=SUB)
        d.rectangle([X(0), 84 * S, X(T), 96 * S], fill="#eeeeee")
        d.rectangle([X(0), 84 * S, X(min(now, T)), 96 * S], fill=ACCENT)
        for sec in range(0, 9, 2):
            d.text((X(sec) - 4 * S, 100 * S), str(sec), font=f(12), fill=SUB)
        d.text((X(T) + 8 * S, 98 * S), "秒", font=f(12), fill=SUB)
        for w, y in lane_y.items():
            d.text((20 * S, (y - 12) * S), f"worker {w}", font=f(15), fill=INK)
            d.line([X(0), y * S, X(T), y * S], fill="#dddddd", width=2 * S)
        shown = [r for r in reqs if r[0] <= now]
        for t, w, on in shown:
            y = lane_y[w]
            box = [X(t) - 9 * S, (y - 9) * S, X(t) + 9 * S, (y + 9) * S]
            d.rectangle(box, fill=RED if on else "#ffffff", outline=INK, width=2 * S)
        n_on = sum(1 for r in shown if r[2])
        d.text((20 * S, 318 * S), f"新しい画面 {n_on} 回、今の画面 {len(shown) - n_on} 回", font=f(15), fill=INK)
        d.rectangle([150 * S, 352 * S, 168 * S, 370 * S], fill=RED, outline=INK, width=2 * S)
        d.text((176 * S, 350 * S), "有効（新しい画面）", font=f(13), fill=INK)
        d.rectangle([330 * S, 352 * S, 348 * S, 370 * S], fill="#ffffff", outline=INK, width=2 * S)
        d.text((356 * S, 350 * S), "無効（今の画面）", font=f(13), fill=INK)
        # the screen the user sees now
        d.rounded_rectangle([650 * S, 130 * S, 880 * S, 300 * S], radius=10 * S, outline=INK, width=2 * S)
        d.text((662 * S, 106 * S), "ユーザーの画面", font=f(14), fill=SUB)
        if shown:
            on = shown[-1][2]
            fill = "#fbe3e3" if on else "#f2f2f2"
            d.rounded_rectangle([662 * S, 142 * S, 868 * S, 288 * S], radius=8 * S, fill=fill)
            d.text((680 * S, 196 * S), "新しい決済画面" if on else "今の決済画面", font=f(20),
                   fill=RED if on else INK)
            d.text((680 * S, 240 * S), f"worker {shown[-1][1]} が答えた", font=f(13), fill=SUB)
        d.text((660 * S, 318 * S), "hash(user) % 100 < 10", font=mono, fill=SUB)
        frames.append(im.resize((W, H), Image.LANCZOS))
    durations = [int(STEP * 1000 / SPEED)] * len(frames)
    durations[-1] = 3000
    frames[0].save(IMAGES / "feature-flag_timeline.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=80, method=6)


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    flicker_figure()
    bucket_figure()
    overlap_figure()
    knight_figure()
    timeline_animation()
