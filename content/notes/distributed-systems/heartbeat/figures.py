"""Generate the figures of the Heartbeat note (WebP).

cover_animation() replays one trial of lab/monitor_pause.py (the "thread"
monitor) from the recorded timestamps: node-a and node-b keep sending, the
monitor is stopped for 1.5 s, and on resume it judges both nodes down before
it reads the 31 heartbeats waiting in the socket buffer. Played at 0.5x.

gray_figure() draws lab/gray_failure.json: heartbeats and request results on
one time axis, for the two places the heartbeat is sent from.

phi_figure() evaluates the phi formulas of Apache Pekko (normal distribution
plus acceptable-heartbeat-pause) and Apache Cassandra (exponential, scaled by
1/ln 10) with their default settings.

topology_figure() counts the heartbeats per period for n = 5 nodes: one\nmonitor, all-to-all, and gossip where each node sends to one peer.\n\nRun: python3 content/notes/distributed-systems/heartbeat/figures.py
"""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMG = HERE / "images"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#4f81a8", "#d64545"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#c98f2a", "#f8eed8"
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

plt.rcParams["font.family"] = "Noto Sans CJK JP"


def to_webp(png: Path, name: str):
    Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)
    png.unlink()


# ---------------------------------------------------------------- cover
S = 2               # draw at 2x, then shrink
W, H = 1200, 560


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, size * S)


def cover_animation(trial_index=2):
    r = json.load(open(LAB / "monitor_pause.json"))[trial_index]
    assert r["mode"] == "thread"
    stop, cont = r["stop"], r["cont"]
    sends = {n: sorted(s["t"] for s in r["sends"] if s["node"] == n) for n in ("node-a", "node-b")}
    recvs = {n: sorted(e["t"] for e in r["events"] if e["ev"] == "recv" and e["node"] == n)
             for n in ("node-a", "node-b")}
    deads = {e["node"]: e["t"] for e in r["events"] if e["ev"] == "dead"}
    burst = {n: sum(1 for v in recvs[n] if cont <= v < cont + 0.01) for n in recvs}
    assert sum(burst.values()) == 31
    t_lo, t_hi = 1.0, 4.3
    x0, x1 = 210, 1160

    def X(t):
        return (x0 + (t - t_lo) / (t_hi - t_lo) * (x1 - x0)) * S

    def frame(t, phase, note):
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((40 * S, 22 * S), "監視する側（monitor）を 1.5 秒止めると、動いている 2 台が落ちたと判定される",
               font=font(22), fill=INK)
        d.text((40 * S, 60 * S), f"経過 {t:4.2f} 秒（実測の時刻を 0.5 倍速で再生）", font=font(17), fill=SUB)
        # time band
        top, bot = 110, 470
        d.rectangle([X(stop), top * S, X(cont), bot * S], fill="#ececec")
        d.text((X(stop) + 10 * S, (top + 6) * S), "monitor が止まっている（SIGSTOP）", font=font(15), fill=SUB)
        for k in range(1, 5):
            d.line([X(k), (bot) * S, X(k), (bot + 8) * S], fill=SUB, width=2 * S)
            d.text((X(k) - 14 * S, (bot + 12) * S), f"{k} 秒", font=font(14), fill=SUB)
        d.line([X(t), top * S, X(t), bot * S], fill=INK, width=2 * S)
        rows = {"node-a": 170, "node-b": 230}
        for n, y in rows.items():
            d.text((40 * S, (y - 12) * S), f"{n} が送る", font=font(16), fill=INK)
            for s in sends[n]:
                if t_lo <= s <= t:
                    d.ellipse([X(s) - 5 * S, (y - 5) * S, X(s) + 5 * S, (y + 5) * S], fill=ACCENT)
        # buffer
        y_buf = 300
        waiting = sum(1 for n in sends for s in sends[n] if stop <= s <= t) if phase < 2 else 0
        if t < stop:
            waiting = 0
        d.text((40 * S, (y_buf - 12) * S), "受信バッファ", font=font(16), fill=INK)
        d.rounded_rectangle([X(stop), (y_buf - 18) * S, X(cont), (y_buf + 18) * S], radius=8 * S,
                            outline=OCHRE, width=2 * S, fill=OCHRE_PALE if waiting else "#ffffff")
        buf_note = f"届いて読まれていない ハートビート {waiting} 通"
        if phase >= 2:
            buf_note += "（monitor が読み終えた）"
        d.text((X(stop) + 14 * S, (y_buf - 11) * S), buf_note, font=font(15), fill=INK)
        # monitor rows
        mrows = {"node-a": 370, "node-b": 430}
        for n, y in mrows.items():
            d.text((40 * S, (y - 12) * S), f"monitor が読む\n（{n}）", font=font(14), fill=INK, spacing=2 * S)
            for v in recvs[n]:
                if t_lo <= v <= t and (v < cont or phase >= 2):
                    d.ellipse([X(v) - 5 * S, (y - 5) * S, X(v) + 5 * S, (y + 5) * S], fill=INK)
            if n in deads and phase >= 1:
                # the cross sits above the row so it does not hide the dots read at the same time
                xd, yc = X(deads[n]), y - 21
                d.line([xd - 8 * S, (yc - 8) * S, xd + 8 * S, (yc + 8) * S], fill=RED, width=4 * S)
                d.line([xd - 8 * S, (yc + 8) * S, xd + 8 * S, (yc - 8) * S], fill=RED, width=4 * S)
                d.text((xd + 14 * S, (yc - 11) * S), "落ちたと判定", font=font(15), fill=RED)
            if phase >= 2:
                d.text((X(cont) + 4 * S, (y + 9) * S), f"再開後、まとめて {burst[n]} 通を読んだ",
                       font=font(13), fill=INK)
        d.text((40 * S, 515 * S), note, font=font(16), fill=INK)
        return im.resize((W, H), Image.LANCZOS)

    frames, durs = [], []
    t = t_lo
    while t < cont - 1e-9:
        note = "2 台とも 100 ms ごとに送り続けている" if t < stop else \
            "monitor は止まっているが、ハートビートは届いて受信バッファに溜まる"
        frames.append(frame(t, 0, note))
        durs.append(200)
        t = round(t + 0.1, 3)
    frames.append(frame(cont, 1, "再開した直後、判定のスレッドが先に動いた。最後に読んだのは 1.5 秒前なので、2 台とも落ちたと判定"))
    durs.append(2000)
    frames.append(frame(cont + 0.001, 2, "1 ms も経たないうちに受信のスレッドが 31 通を読み、2 台とも生き返ったと判定し直す"))
    durs.append(2000)
    t = round(cont + 0.1, 3)
    while t <= t_hi:
        frames.append(frame(t, 2, "1 ms も経たないうちに受信のスレッドが 31 通を読み、2 台とも生き返ったと判定し直す"))
        durs.append(200)
        t = round(t + 0.1, 3)
    durs[-1] = 3000
    frames[0].save(IMG / "heartbeat_monitor_pause.webp", "WEBP", save_all=True,
                   append_images=frames[1:], duration=durs, loop=0, quality=80, method=6)
    print("cover", len(frames), "frames", sum(durs) / 1000, "s")


# ---------------------------------------------------------------- gray failure
def gray_figure():
    data = json.load(open(LAB / "gray_failure.json"))
    labels = {"thread": "別のスレッドから送る", "inloop": "処理のループから送る"}
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.6), sharex=True)
    for ax, mode in zip(axes, ("thread", "inloop")):
        ev = data[mode]
        hb = [e["t"] for e in ev if e["ev"] == "hb"]
        ok = [e["t"] for e in ev if e["ev"] == "ok"]
        to = [e["sent"] for e in ev if e["ev"] == "timeout"]
        dead = [e["t"] for e in ev if e["ev"] == "dead"]
        ax.scatter(hb, [1] * len(hb), s=14, color=ACCENT, label="monitor に届いたハートビート")
        ax.scatter(ok, [0] * len(ok), s=14, color=INK, label="300 ms 以内に返った要求")
        ax.scatter(to, [0] * len(to), s=40, color=RED, marker="x", label="返らなかった要求")
        for t in dead:
            ax.axvline(t, color=RED, lw=1.5)
            ax.text(t + 0.05, 1.35, f"{t:.2f} 秒に落ちたと判定", color=RED, fontsize=10)
        ax.axvline(2.0, color=SUB, lw=1, ls="--")
        ax.set_yticks([1, 0], ["ハートビート", "要求"])
        ax.set_ylim(-0.6, 1.7)
        ax.set_title(f"ハートビートを{labels[mode]}", loc="left", fontsize=12)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].text(2.03, 1.35, "2.0 秒に処理のループがデッドロック", color=SUB, fontsize=10)
    axes[1].text(1.97, 0.45, "2.0 秒に処理のループがデッドロック", color=SUB, fontsize=10, ha="right")
    axes[1].set_xlabel("開始からの時間（秒）")
    axes[1].set_xlim(0, 5)
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=3, frameon=False, fontsize=9.5)
    fig.tight_layout()
    png = IMG / "gray.png"
    fig.savefig(png, dpi=200, facecolor="#ffffff")
    plt.close(fig)
    to_webp(png, "heartbeat_gray_failure.webp")


# ---------------------------------------------------------------- phi
def pekko_phi(t, mean, sd):
    y = (t - mean) / sd
    if y < -8:
        return 0.0
    if y > 8:
        return 99.0  # far above every threshold drawn
    e = math.exp(-y * (1.5976 + 0.070566 * y * y))
    return -math.log10(e / (1 + e)) if t > mean else -math.log10(1 - 1 / (1 + e))


def phi_figure():
    ts = [i / 100 for i in range(0, 2101)]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    curves = [
        ("Pekko、間隔の平均 1 秒・標準偏差 0.1 秒", lambda t: pekko_phi(t, 1.0 + 3.0, 0.1), ACCENT, "-"),
        ("Pekko、間隔の平均 1 秒・標準偏差 1 秒", lambda t: pekko_phi(t, 1.0 + 3.0, 1.0), ACCENT, "--"),
        ("Cassandra、間隔の平均 1 秒", lambda t: t / 1.0 / math.log(10), OCHRE, "-"),
    ]
    for label, f, color, ls in curves:
        ys = [f(t) if f(t) <= 12 else float("nan") for t in ts]
        ax.plot(ts, ys, color=color, ls=ls, lw=2, label=label)
        cross = next(t for t in ts if f(t) >= 8)
        ax.plot([cross], [8], "o", color=color)
        ax.annotate(f"{cross:.1f} 秒", (cross, 8), xytext=(cross + 0.35, 7.0), color=color, fontsize=11)
    ax.axhline(8, color=RED, lw=1, ls=":")
    ax.text(0.2, 8.25, "閾値 8（どちらも既定）", color=RED, fontsize=10)
    ax.annotate("Pekko は平均に猶予の 3 秒を足すので、\n4 秒近くまで φ はほぼ 0", (3.6, 0.08), xytext=(9.6, 0.5),
                color=ACCENT, fontsize=10, arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1))
    ax.set_xlim(0, 21)
    ax.set_ylim(0, 12)
    ax.set_xlabel("最後のハートビートからの経過時間（秒）")
    ax.set_ylabel("φ")
    ax.legend(loc="upper right", frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    png = IMG / "phi.png"
    fig.savefig(png, dpi=200, facecolor="#ffffff")
    plt.close(fig)
    to_webp(png, "heartbeat_phi.webp")

# ---------------------------------------------------------------- topology
def topology_figure(n=5):
    """Messages per period with n nodes: one monitor, all-to-all, gossip (1 peer each)."""
    from matplotlib.patches import Circle, FancyArrowPatch
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.2))
    R, r = 1.0, 0.27

    def ring():
        return [(R * math.sin(2 * math.pi * i / n), R * math.cos(2 * math.pi * i / n)) for i in range(n)]

    def arrow(ax, a, b, both=False, color=SUB, shrink_b=24):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>", mutation_scale=12,
                                     shrinkA=24, shrinkB=shrink_b, color=color, lw=1.4, zorder=5))

    def nodes(ax, pts, label=None):
        for k, (x, y) in enumerate(pts):
            ax.add_patch(Circle((x, y), r, facecolor=PALE, edgecolor=ACCENT, lw=2, zorder=3))
            if label:
                ax.text(x, y, label(k), ha="center", va="center", fontsize=10, zorder=4)

    pts = ring()
    # 1) one monitor
    ax = axes[0]
    for pt in pts:
        arrow(ax, pt, (0, 0), shrink_b=34)
    ax.add_patch(Circle((0, 0), 0.4, facecolor=OCHRE_PALE, edgecolor=OCHRE, lw=2, zorder=3))
    ax.text(0, 0, "monitor", ha="center", va="center", fontsize=10.5, zorder=4)
    nodes(ax, pts)
    ax.set_title("1 台の monitor が全てを見る", fontsize=15)
    ax.text(0, -1.55, f"1 周期に n = {n} 本", ha="center", color=SUB, fontsize=14)
    # 2) all-to-all
    ax = axes[1]
    for i in range(n):
        for j in range(i + 1, n):
            arrow(ax, pts[i], pts[j], both=True)
    nodes(ax, pts)
    ax.set_title("全てのノードが送り合う", fontsize=15)
    ax.text(0, -1.55, f"1 周期に n × (n−1) = {n * (n - 1)} 本", ha="center", color=SUB, fontsize=14)
    # 3) gossip: each node picks one peer (fixed here for the drawing)
    ax = axes[2]
    for i in range(n):
        arrow(ax, pts[i], pts[(i + 2) % n], color=ACCENT)
    nodes(ax, pts, label=lambda k: f"{n} 台分")
    ax.set_title("gossip（送る相手を 1 台に絞った例）", fontsize=15)
    ax.text(0, -1.55, f"1 周期に {n} 本、1 通に {n} 台分の記録", ha="center", color=SUB, fontsize=14)
    for ax in axes:
        ax.set_xlim(-1.4, 1.4)
        ax.set_ylim(-1.75, 1.35)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.tight_layout()
    png = IMG / "topology.png"
    fig.savefig(png, dpi=200, facecolor="#ffffff")
    plt.close(fig)
    to_webp(png, "heartbeat_topology.webp")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    cover_animation()
    gray_figure()
    phi_figure()
    topology_figure()
