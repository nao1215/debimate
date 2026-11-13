"""Ambassador のノートの図を作る（WebP）。

grid_figure()      : lab/output/<scenario>/ の書き込みの結果を、100ms のマスで時間に沿って並べる
concept_figure()   : アプリと ambassador が 1 つのネットワークを共有し、localhost の先で振り分ける構成
failover_animation(): 止めずに切り替えた時の、役割と「消えた書き込み」の数の移り変わり（実測の時刻）

実行: python3 content/notes/software-architecture/ambassador/figures.py
"""

import datetime
import io
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
IMG = HERE / "images"
INK, SUB, RED = "#1f1f1f", "#666666", "#e15759"
OK_C, ERR_C, REJ_C = "#d9d9d9", "#4d4d4d", "#d4a24c"
PALE, FILL = "#eaf1f5", "#f2f2f2"
plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]

WRITERS = [
    ("static", "直接 IP に繋ぐ"),
    ("sentinel", "ライブラリ（Sentinel）"),
    ("ambassador", "ambassador（接続を保つ）"),
    ("ambassador_new", "ambassador（毎回繋ぐ）"),
]


def save_webp(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def load(scenario):
    d = OUT / scenario
    ev = [json.loads(l) for l in open(d / "events.jsonl")]
    t0, tend = ev[0]["t"], ev[-1]["t"]
    res = {}
    for mode, _ in WRITERS:
        kept = {int(x) for x in (d / f"kept_{mode}.txt").read_text().split()}
        rows = [json.loads(l) for l in open(d / f"{mode}.jsonl")]
        res[mode] = [
            (r["t"] - t0, "lost" if r["res"] == "ok" and r["seq"] not in kept
             else "ok" if r["res"] == "ok"
             else "reject" if r["res"] in ("readonly", "ResponseError") else "err")
            for r in rows if t0 - 1 <= r["t"] <= tend
        ]
    events = {e["event"]: e["t"] - t0 for e in ev}
    return res, events, tend - t0


def first_readonly(scenario):
    """直接繋ぐ書き込みが最初に READONLY を受けた時刻。a が replica にされた時刻の目安"""
    d = OUT / scenario
    t0 = json.loads(open(d / "events.jsonl").readline())["t"]
    return next(json.loads(l)["t"] - t0 for l in open(d / "static.jsonl")
                if json.loads(l)["res"] == "readonly" and json.loads(l)["t"] > t0)


def log_times(scenario, pattern, name):
    """docker compose logs -t の行の時刻を、最初の出来事からの秒で返す"""
    d = OUT / scenario
    t0 = json.loads(open(d / "events.jsonl").readline())["t"]
    out = []
    for line in open(d / name):
        if re.search(pattern, line):
            m = re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6})", line)
            t = datetime.datetime.fromisoformat(m.group(1)).replace(tzinfo=datetime.timezone.utc)
            out.append(t.timestamp() - t0)
    return out


COLORS = {"ok": OK_C, "lost": RED, "err": ERR_C, "reject": REJ_C}
LABELS = {"ok": "成功（残った）", "lost": "成功と返ったが消えた", "err": "失敗（繋がらない・時間切れ）",
          "reject": "失敗（READONLY・NOREPLICAS で拒否）"}


def draw_grid(ax, res, xmax, marks, title=None):
    for i, (mode, label) in enumerate(WRITERS):
        y = len(WRITERS) - 1 - i
        rows = res[mode]
        for j, (t, kind) in enumerate(rows):
            # 次の書き込みを始めるまでを 1 マスにする（時間切れの 0.5 秒もそのまま幅になる）
            w = min(rows[j + 1][0] - t, 1.0) if j + 1 < len(rows) else 0.1
            ax.add_patch(Rectangle((t, y + 0.12), w + 0.004, 0.76, color=COLORS[kind], lw=0))
        lost = sum(1 for _, k in res[mode] if k == "lost")
        ax.text(xmax + 0.3, y + 0.5, f"消えた {lost}", va="center", fontsize=9,
                color=RED if lost else SUB)
    for x, text in marks:
        ax.axvline(x, color=INK, lw=0.8, ls=(0, (3, 2)))
        ax.text(x, len(WRITERS) + 0.05, text, ha="center", va="bottom", fontsize=8.5, color=INK,
                bbox=dict(fc="#ffffff", ec="none", pad=1.0))
    ax.set_xlim(-1, xmax)
    ax.set_ylim(0, len(WRITERS) + 0.75)
    ax.set_yticks([len(WRITERS) - 1 - i + 0.5 for i in range(len(WRITERS))])
    ax.set_yticklabels([w[1] for w in WRITERS], fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=8.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    if title:
        ax.set_title(title, loc="left", fontsize=10.5, color=INK, pad=16)


def legend(fig, y):
    handles = [Rectangle((0, 0), 1, 1, color=COLORS[k]) for k in LABELS]
    fig.legend(handles, LABELS.values(), loc="lower center", ncol=4, frameon=False,
               fontsize=9, bbox_to_anchor=(0.5, y), handlelength=1.2)


def stop_figure():
    res, ev, xmax = load("stop")
    conv = first_readonly("stop")
    fig, ax = plt.subplots(figsize=(10, 3.0))
    draw_grid(ax, res, xmax, [(0, "a を停止"), (ev["start-a"], "a が戻る"), (conv, "a が replica に")])
    ax.set_xlabel("a を止めてからの秒（100ms ごとに 1 回書く）", fontsize=9)
    legend(fig, 0.0)
    fig.subplots_adjust(left=0.2, right=0.91, top=0.93, bottom=0.3)
    save_webp(fig, "ambassador_stop.webp")


def failover_figure():
    runs = [("failover", "HAProxy の設定のまま"),
            ("failover-kill", "HAProxy に on-marked-down shutdown-sessions"),
            ("failover-minrep", "Redis に min-replicas-to-write 1")]
    fig, axes = plt.subplots(3, 1, figsize=(10, 7.6), sharex=True)
    for ax, (sc, title) in zip(axes, runs):
        res, ev, xmax = load(sc)
        conv = first_readonly(sc)
        draw_grid(ax, res, xmax, [(0, "切り替えの指示"), (conv, "a が replica に")], title)
    axes[-1].set_xlabel("SENTINEL FAILOVER からの秒（100ms ごとに 1 回書く）", fontsize=9)
    legend(fig, 0.0)
    fig.subplots_adjust(left=0.2, right=0.91, top=0.95, bottom=0.11, hspace=0.6)
    save_webp(fig, "ambassador_failover.webp")


def box(ax, x, y, w, h, text, fc=FILL, ec=INK, fs=10, color=INK, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=color)


def arrow(ax, x1, y1, x2, y2, text=None, color=INK, ls="-", tx=None, ty=None):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2, ls=ls, shrinkA=2, shrinkB=2))
    if text:
        ax.text(tx if tx is not None else (x1 + x2) / 2, ty if ty is not None else (y1 + y2) / 2 + 0.12,
                text, ha="center", va="bottom", fontsize=8.5, color=color)


def concept_figure():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    # 1 つのネットワークを共有する枠（Pod・Task・compose の network_mode: service）
    ax.add_patch(FancyBboxPatch((0.2, 0.5), 4.6, 3.2, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=PALE, ec=SUB, lw=1.0, ls=(0, (4, 3))))
    ax.text(0.4, 3.45, "同じネットワークを共有する単位（Pod など）", fontsize=9, color=SUB, va="center")
    box(ax, 0.5, 1.3, 1.8, 1.4, "アプリ\n\n宛先は\n127.0.0.1:6380", fc="#ffffff", fs=9.5)
    box(ax, 2.9, 1.3, 1.7, 1.4, "ambassador\n（HAProxy）\n\nどれが master\nかを見て送る", fc="#ffffff", fs=9.5)
    arrow(ax, 2.3, 2.0, 2.9, 2.0, "localhost", ty=2.08)
    # Redis
    ys = [3.0, 1.85, 0.7]
    for y, (name, role) in zip(ys, [("a", "master"), ("b", "replica"), ("c", "replica")]):
        box(ax, 6.0, y, 1.6, 0.75, f"redis-{name}\n{role}", fc="#ffffff", fs=9.5)
    arrow(ax, 4.6, 2.2, 6.0, 3.35, "書き込み", tx=5.15, ty=2.95)
    for y in ys:
        arrow(ax, 4.6, 1.75, 6.0, y + 0.3, color=SUB, ls=(0, (3, 2)))
    ax.text(5.3, 0.55, "1 秒ごとの\nrole:master の確認", fontsize=8.5, color=SUB, ha="center", va="top")
    # Sentinel
    box(ax, 8.3, 1.5, 1.5, 1.4, "Sentinel × 3\n\n落ちたと決め\n昇格させる", fc=FILL, fs=9.5)
    for y in ys:
        arrow(ax, 8.3, 2.2, 7.6, y + 0.375, color=SUB)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
    save_webp(fig, "ambassador_concept.webp")


def failover_animation():
    res, ev, _ = load("failover")
    conv = first_readonly("failover")
    # redis-b が master として書き込みを受け始めた時刻。+promoted-slave（1.2 秒）は
    # Sentinel が昇格を確認した時刻で、SLAVEOF NO ONE の後の wait-promotion（0.3 秒）の方が実際に近い
    promoted = log_times("failover", r"\+failover-state-wait-promotion", "sentinel-1.log")[0]
    switch = log_times("failover", r"\+switch-master", "sentinel-1.log")[0]
    b_up = [t for t in log_times("failover", r"redis-b is UP", "ambassador.log") if t > 0][0]
    a_down = [t for t in log_times("failover", r"redis-a is DOWN", "ambassador.log") if t > 0][0]
    tmax, step = 15.0, 0.2
    frames = []
    ts = [round(-1 + i * step, 2) for i in range(int((tmax + 1) / step) + 1)]
    for now in ts:
        fig, ax = plt.subplots(figsize=(8, 4.6))
        ax.set_xlim(0, 8)
        ax.set_ylim(0, 4.6)
        ax.axis("off")
        ax.text(0.2, 4.35, "止めずに master を切り替えた時（実測の時刻を等倍速で再生）", fontsize=10.5, va="center")
        # 時間の帯
        ax.add_patch(Rectangle((0.2, 3.85), 7.6, 0.16, color=FILL))
        frac = (min(now, tmax) + 1) / (tmax + 1)
        ax.add_patch(Rectangle((0.2, 3.85), 7.6 * frac, 0.16, color=SUB))
        ax.text(7.8, 3.68, f"経過 {max(now, 0):4.1f} 秒", ha="right", va="top", fontsize=10)
        # Redis の役割
        roles = [("a", "master" if now < conv else "replica", now >= 0 and now < conv),
                 ("b", "master" if now >= promoted else "replica", False),
                 ("c", "replica", False)]
        for i, (name, role, stale) in enumerate(roles):
            x = 0.4 + i * 1.5
            ec = RED if stale and now >= promoted else INK
            label = f"redis-{name}\n{role}" + ("（古い）" if ec == RED else "")
            box(ax, x, 2.45, 1.3, 0.8, label, fc="#ffffff", ec=ec, fs=9, lw=1.6 if ec == RED else 1.0)
        # 誰が何を master と見ているか
        sent = "b" if now >= switch else "a"
        hap = "+".join(n for n, up in [("a", now < a_down), ("b", now >= b_up)] if up)
        ax.text(5.1, 3.05, f"Sentinel が知らせる master: {sent}", fontsize=9.5, va="center")
        ax.text(5.1, 2.65, f"HAProxy が送る先: {hap}", fontsize=9.5, va="center",
                color=RED if "+" in hap else INK)
        # 書き込みの数
        ax.text(0.4, 2.05, "成功と返った書き込みのうち、消えた数（0 秒から）", fontsize=9.5, va="center", color=SUB)
        for i, (mode, label) in enumerate(WRITERS):
            y = 1.55 - i * 0.42
            lost = sum(1 for t, k in res[mode] if 0 <= t <= now and k == "lost")
            ax.text(0.4, y, label, fontsize=9.5, va="center")
            ax.add_patch(Rectangle((3.2, y - 0.11), lost * 0.03, 0.22, color=RED, lw=0))
            ax.text(3.25 + lost * 0.03, y, str(lost), fontsize=9.5, va="center", color=RED if lost else SUB)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, facecolor="#ffffff")
        plt.close(fig)
        buf.seek(0)
        frames.append(Image.open(buf).convert("RGB"))
    durations = [int(step * 1000)] * (len(frames) - 1) + [3000]
    frames[0].save(IMG / "ambassador_failover_anim.webp", "WEBP", save_all=True,
                   append_images=frames[1:], duration=durations, loop=0, quality=70, method=6)


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    stop_figure()
    failover_figure()
    concept_figure()
    failover_animation()
