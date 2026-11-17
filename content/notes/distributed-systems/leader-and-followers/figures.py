"""Leader and Followers のノートの図（WebP）を作る。

failover_figure() と raft_figure() は、lab/ の実験の出力に書かれた時刻を読んで、
コマを描く動く WebP。failover は実測の時刻を 0.2 倍速、raft は 0.5 倍速で再生する。
commit_points_figure() は synchronous_commit の設定ごとに COMMIT が返る位置を描き、
stale_read_figure() は lab/out_stale_read.json の数を棒にする。
overwrite_figure() は Raft 論文の Figure 8 の 5 台の例を段階ごとに並べる。
paxos_figure() は Paxos で提案する台が番号を競り合う様子を描く（番号は説明用の値）。

実行: python3 content/notes/distributed-systems/leader-and-followers/figures.py
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"
INK, SUB, LINE = "#1f1f1f", "#666666", "#b0b0b0"
BLUE, BLUE_PALE = "#4e79a7", "#e8eef5"
RED, RED_PALE = "#c8443f", "#f8e4e3"
GRAY_PALE = "#efefef"
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
S = 2  # 2 倍で描いて縮める


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else JP, size * S)


def events(name):
    """lab の出力の「  0.3s  メッセージ」の行を (秒, メッセージ) の列にする。"""
    out = []
    for line in (LAB / name).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([\d.]+)s\s+(.*)", line)
        if m:
            out.append((float(m.group(1)), m.group(2)))
    return out


def first(evs, word):
    return next(t for t, msg in evs if word in msg)


class Frame:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * S, h * S), "#ffffff")
        self.d = ImageDraw.Draw(self.im)

    def text(self, x, y, s, size=18, color=INK, anchor="la", mono=False):
        self.d.text((x * S, y * S), s, font=font(size, mono), fill=color, anchor=anchor)

    def box(self, x, y, w, h, fill, outline, width=2, radius=10, dash=False):
        if dash:
            self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=radius * S,
                                     fill=fill, outline=None)
            for i in range(0, int(w), 12):
                for yy in (y, y + h):
                    self.d.line([(x + i) * S, yy * S, min(x + i + 6, x + w) * S, yy * S],
                                fill=outline, width=width * S)
            for i in range(0, int(h), 12):
                for xx in (x, x + w):
                    self.d.line([xx * S, (y + i) * S, xx * S, min(y + i + 6, y + h) * S],
                                fill=outline, width=width * S)
        else:
            self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=radius * S,
                                     fill=fill, outline=outline, width=width * S)

    def line(self, x1, y1, x2, y2, color=INK, width=3, dash=False):
        if not dash:
            self.d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=color, width=width * S)
            return
        n = int(max(abs(x2 - x1), abs(y2 - y1)) // 14) or 1
        for i in range(n):
            a, b = i / n, (i + 0.5) / n
            self.d.line([(x1 + (x2 - x1) * a) * S, (y1 + (y2 - y1) * a) * S,
                         (x1 + (x2 - x1) * b) * S, (y1 + (y2 - y1) * b) * S], fill=color, width=width * S)

    def clock(self, t, t_end, speed, x=40, y=78, w=920):
        """経過時間の数字と帯。"""
        self.text(x, y, f"経過 {t:.1f} 秒", 20)
        self.text(x + w, y, f"実測の時刻を {speed} 倍速で再生", 15, SUB, anchor="ra")
        top = y + 34
        self.box(x, top, w, 12, GRAY_PALE, LINE, width=1, radius=6)
        self.box(x, top, max(12, w * min(t / t_end, 1)), 12, BLUE, BLUE, width=1, radius=6)

    def image(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def save_anim(frames, durations, name):
    frames[0].save(IMAGES / name, "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, lossless=True, method=6)


def server(f, x, y, w, h, title, rows, state, note="", cells=0, cell_color=BLUE):
    """1 台のサーバー。state は up / down / leader。"""
    fill, edge = {"up": ("#ffffff", INK), "down": (GRAY_PALE, LINE), "leader": (BLUE_PALE, BLUE)}[state]
    f.box(x, y, w, h, fill, edge, width=3 if state == "leader" else 2)
    color = SUB if state == "down" else INK
    f.text(x + w / 2, y + 22, title, 20, color, anchor="ma")
    f.text(x + w / 2, y + 62, rows, 34, color, anchor="ma")
    if note:
        note_color = SUB if state == "down" else RED
        f.text(x + w / 2, y + h - 34, note, 16, note_color, anchor="ma")
    for i in range(cells):
        cx = x + 24 + i * ((w - 48) / 10)
        f.box(cx, y + 118, (w - 48) / 10 - 4, 26, "#ffffff" if state == "down" else BLUE_PALE,
              LINE if state == "down" else cell_color, width=2, radius=4)
        f.text(cx + ((w - 48) / 10 - 4) / 2, y + 122, str(101 + i), 11, color, anchor="ma", mono=True)


def failover_figure():
    evs = events("out_failover_async.txt")
    t_cut = first(evs, "ネットワークから外した")
    t_kill = first(evs, "docker kill")
    t_promote = first(evs, "昇格させた")
    t_restart = first(evs, "起動し直した")
    t_end = t_restart
    W, H = 1000, 560
    step, speed = 0.1, 0.2
    frames, durations = [], []
    t = 0.0
    while t <= t_end + 1e-9:
        f = Frame(W, H)
        f.text(40, 26, "PostgreSQL 17 の非同期レプリケーションで、Leader を落として Follower を昇格させる", 21)
        f.clock(t, t_end, speed)
        lx, fx, y, sw, sh = 60, 560, 170, 380, 250
        cut = t >= t_cut
        f.line(lx + sw, y + 90, fx, y + 90, RED if cut else INK, 4, dash=cut)
        f.text((lx + sw + fx) / 2, y + 56, "WAL を送る", 16, SUB, anchor="ma")
        if t >= t_kill:
            f.text((lx + sw + fx) / 2, y + 104, "Leader 停止", 18, RED, anchor="ma")
        elif cut:
            f.text((lx + sw + fx) / 2, y + 104, "切断", 18, RED, anchor="ma")
        # Leader 側
        if t < t_kill:
            n = 110 if cut else 100
            server(f, lx, y, sw, sh, "Leader", f"{n} 行", "leader",
                   "id=101〜110 は COMMIT が返った" if cut else "", cells=10 if cut else 0)
        elif t < t_restart:
            server(f, lx, y, sw, sh, "Leader（docker kill で停止）", "停止", "down", "", cells=10)
        else:
            server(f, lx, y, sw, sh, "古い Leader（起動し直した）", "110 行", "leader",
                   "Leader のまま書き込みを受け付ける", cells=10, cell_color=BLUE)
        # Follower 側
        if t < t_promote:
            server(f, fx, y, sw, sh, "Follower", "100 行", "up", "")
        else:
            server(f, fx, y, sw, sh, "新しい Leader（昇格した Follower）", "100 行", "leader",
                   "id=101〜110 が無い")
        # 出来事の記録
        log = [(et, m) for et, m in evs if et <= t + 1e-9][-3:]
        for i, (et, m) in enumerate(log):
            f.text(60, 450 + i * 28, f"{et:4.1f} 秒  {m}", 16, INK if i == len(log) - 1 else SUB)
        frames.append(f.image())
        durations.append(int(step / speed * 1000))
        t = round(t + step, 3)
    # 最後のコマ: 2 台の両方に id=500 を書いた結果
    f = Frame(W, H)
    f.text(40, 26, "PostgreSQL 17 の非同期レプリケーションで、Leader を落として Follower を昇格させる", 21)
    f.clock(t_end, t_end, speed)
    server(f, 60, 170, 380, 250, "古い Leader（起動し直した）", "111 行", "leader",
           "id=500 の v=1 で COMMIT", cells=10)
    server(f, 560, 170, 380, 250, "新しい Leader（昇格した Follower）", "101 行", "leader",
           "id=500 の v=2 で COMMIT")
    f.text(500, 452, "Leader が 2 台になり、同じ id=500 に別の値が入った", 20, RED, anchor="ma")
    f.text(500, 490, "id=101〜110 は、COMMIT が返ったのに新しい Leader には無い", 18, INK, anchor="ma")
    frames.append(f.image())
    durations.append(3500)
    save_anim(frames, durations, "leader-and-followers_failover.webp")


def raft_figure():
    evs = events("out_raft.txt")
    leader0 = re.search(r"Leader は (e\d)", evs[0][1]).group(1)
    t_cut = first(evs, "ネットワークから外した")
    t_down = first(evs, "Leader を降りた")
    t_elect = first(evs, "新しい Leader")
    new_leader = re.search(r"新しい Leader (e\d)", next(m for _, m in evs if "新しい Leader" in m)).group(1)
    t_vnew = first(evs, "put k=v-new")
    t_lin = first(evs, "linearizable")
    t_ser = first(evs, "serializable")
    t_old = first(evs, "put k=v-old")
    t_back = first(evs, "を戻した")
    t_final = evs[-1][0]
    nodes = ["e1", "e2", "e3"]
    W, H = 1000, 560
    step, speed = 0.2, 0.5
    frames, durations = [], []

    def draw(t, final=False):
        f = Frame(W, H)
        f.text(40, 26, "etcd v3.5.17（Raft）の 3 台で、Leader をネットワークから外す", 21)
        if final:
            f.text(40, 78, f"経過 {t_final:.1f} 秒（{leader0} を戻してから 3 秒後）", 20)
            f.text(960, 78, "実測の時刻を 0.5 倍速で再生", 15, SUB, anchor="ra")
            f.box(40, 112, 920, 12, BLUE, BLUE, width=1, radius=6)
        else:
            f.clock(t, t_back, speed)
        xs = {n: 60 + i * 320 for i, n in enumerate(nodes)}
        cut = t >= t_cut and not final
        others = [n for n in nodes if n != leader0]
        # 残りの 2 台を結ぶ線と、外した 1 台への線
        f.line(xs[others[0]] + 260, 240, xs[others[1]], 240, INK, 3) if abs(nodes.index(others[0]) - nodes.index(others[1])) == 1 else None
        for o in others:
            a, b = sorted([xs[o], xs[leader0]])
            if abs(nodes.index(o) - nodes.index(leader0)) == 1:
                f.line(a + 260, 240, b, 240, RED if cut else INK, 3, dash=cut)
        for n in nodes:
            x = xs[n]
            if final:
                role, term = ("Leader", 3) if n == new_leader else ("Follower", 3)
                k = "v-new"
            elif n == leader0:
                role = ("Leader" if t < t_cut else
                        "外された Leader" if t < t_down else "Follower に降りた")
                term = 2
                k = "v1"
            else:
                if t >= t_elect:
                    role, term = ("Leader" if n == new_leader else "Follower"), 3
                else:
                    role, term = "Follower", 2
                k = "v-new" if t >= t_vnew else "v1"
            state = "leader" if role == "Leader" else "up"
            f.box(x, 170, 260, 150, BLUE_PALE if state == "leader" else "#ffffff",
                  BLUE if state == "leader" else INK, width=3 if state == "leader" else 2)
            f.text(x + 130, 186, f"{n}  {role}", 18, anchor="ma")
            tl = f"term {term}"
            f.text(x + 130, 224, tl, 16, SUB, anchor="ma")
            f.text(x + 130, 262, f"k = {k}", 24, INK, anchor="ma", mono=True)
        msgs = []
        if not final:
            if t >= t_cut:
                msgs.append((f"{leader0} への put k=v-old は待っている" if t < t_old else
                             f"{leader0} への put k=v-old は失敗（context deadline exceeded）",
                             SUB if t < t_old else RED))
            if t >= t_down:
                msgs.append((f"{t_down:.1f} 秒: {leader0} は過半数と話せず、自分から Leader を降りた", INK))
            if t >= t_elect:
                msgs.append((f"{t_elect:.1f} 秒: 残りの 2 台が {new_leader} を Leader に選んだ（term 3）", INK))
            if t >= t_lin:
                msgs.append((f"{leader0} から読む: 既定の linearizable は失敗、serializable は v1" if t >= t_ser
                             else f"{leader0} から読む: 既定の linearizable は失敗", RED))
        else:
            msgs = [(f"戻した {leader0} は term 3 の Follower になり、k は v-new", INK),
                    (f"{leader0} のログにあった v-old は、term 3 のエントリで上書きされた", RED)]
        for i, (m, c) in enumerate(msgs):
            f.text(60, 370 + i * 34, m, 18, c)
        return f.image()

    t = evs[0][0]
    while t <= t_back + 1e-9:
        frames.append(draw(t))
        durations.append(int(step / speed * 1000))
        t = round(t + step, 3)
    frames.append(draw(t_final, final=True))
    durations.append(3500)
    save_anim(frames, durations, "leader-and-followers_raft.webp")


def _style():
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 12,
                         "axes.edgecolor": SUB, "axes.labelcolor": INK,
                         "xtick.color": INK, "ytick.color": INK})


def _save(fig, name):
    with tempfile.TemporaryDirectory(dir=HERE) as d:
        png = Path(d) / "x.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight")
        Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)
    plt.close(fig)


def commit_points_figure():
    _style()
    fig, ax = plt.subplots(figsize=(10, 4.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.9)
    ax.axis("off")
    steps = [("Leader", "WAL を\nディスクに書く"), ("Follower", "WAL を受け取り\nOS に渡す"),
             ("Follower", "WAL を\nディスクに書く"), ("Follower", "WAL を適用し\n行が読める")]
    xs = [0.2, 2.75, 5.3, 7.85]
    for (who, what), x in zip(steps, xs):
        leader = who == "Leader"
        ax.add_patch(FancyBboxPatch((x, 1.55), 1.95, 1.15, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=BLUE_PALE if leader else "#ffffff", ec=BLUE if leader else INK, lw=1.6))
        ax.text(x + 0.975, 2.47, who, ha="center", va="center", fontsize=11, color=SUB)
        ax.text(x + 0.975, 1.98, what, ha="center", va="center", fontsize=12, color=INK, linespacing=1.3)
    for a, b in zip(xs, xs[1:]):
        ax.annotate("", xy=(b - 0.05, 2.12), xytext=(a + 2.0, 2.12),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
    # COMMIT が返る位置
    marks = [("非同期\n（既定）", 0), ("同期\nremote_write", 1), ("同期\non", 2), ("同期\nremote_apply", 3)]
    for label, i in marks:
        x = xs[i] + 0.975
        ax.annotate("", xy=(x, 2.75), xytext=(x, 3.45), arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.6))
        ax.text(x, 3.55, label, ha="center", va="bottom", fontsize=12, color=BLUE, linespacing=1.2)
    ax.text(0.2, 4.75, "COMMIT が返る所（同期の時は synchronous_commit の値で変わる）", fontsize=12, color=BLUE, va="center")
    # Follower で読めるようになる所
    ax.annotate("", xy=(xs[3] + 0.975, 1.5), xytext=(xs[3] + 0.975, 0.85),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.6))
    ax.text(xs[3] + 0.975, 0.7, "Follower から新しい値が\n読めるのはここから", ha="center", va="top",
            fontsize=12, color=RED, linespacing=1.3)
    ax.annotate("", xy=(xs[3] - 0.1, 1.05), xytext=(xs[0] + 0.975, 1.05),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=1.2, linestyle="--"))
    ax.text((xs[0] + xs[3]) / 2 + 0.5, 0.82, "この間に Follower を読むと古い値が返る", ha="center", va="top",
            fontsize=12, color=RED)
    _save(fig, "leader-and-followers_commit_points.webp")


def stale_read_figure():
    _style()
    r = json.loads((LAB / "out_stale_read.json").read_text(encoding="utf-8"))
    names = list(r)
    labels = {"async": "非同期（既定）", "sync(on)": "同期 on", "sync(remote_apply)": "同期 remote_apply",
              "async + LSN を待つ": "非同期 + LSN を待つ"}
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ys = list(range(len(names)))[::-1]
    for y, n in zip(ys, names):
        v = r[n]
        pct = v["stale"] / v["n"] * 100
        ax.barh(y, pct, color=RED if v["stale"] else BLUE, height=0.55)
        if pct > 80:
            ax.text(pct - 2, y, f"{v['stale']} / {v['n']} 回", va="center", ha="right", fontsize=12, color="#ffffff")
        else:
            ax.text(pct + 1.5, y, f"{v['stale']} / {v['n']} 回", va="center", fontsize=12, color=INK)
        ax.text(132, y, f"{v['commit_median_ms']:.2f} ms", va="center", ha="right", fontsize=12, color=INK)
        ax.text(158, y, f"{v['write_to_read_median_ms']:.2f} ms", va="center", ha="right", fontsize=12, color=INK)
    ax.text(132, len(names) - 0.35, "COMMIT まで", ha="right", va="bottom", fontsize=11, color=SUB)
    ax.text(158, len(names) - 0.35, "書いてから\n読み終えるまで", ha="right", va="bottom", fontsize=11, color=SUB, linespacing=1.2)
    ax.set_yticks(ys)
    ax.set_yticklabels([labels[n] for n in names], fontsize=12)
    ax.set_xlim(0, 160)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("COMMIT の直後に Follower が古い値を返した割合（%）")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_bounds(0, 100)
    _save(fig, "leader-and-followers_stale_read.webp")


def paxos_figure():
    """提案する台が 2 台いると、番号を競り合って何も選ばれない様子（番号は説明用の値）。"""
    _style()
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 5.6)
    ax.axis("off")
    cols = {"p1": 1.2, "acc": 4.5, "p2": 7.8}
    for key, label in [("p1", "提案する台 1"), ("acc", "受け入れる過半数の台"), ("p2", "提案する台 2")]:
        x = cols[key]
        bw = 2.7 if key == "acc" else 2.1
        ax.add_patch(FancyBboxPatch((x - bw / 2, 4.75), bw, 0.6, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc=BLUE_PALE if key == "acc" else "#ffffff", ec=BLUE if key == "acc" else INK, lw=1.4))
        ax.text(x, 5.05, label, ha="center", va="center", fontsize=12, color=INK)
        ax.plot([x, x], [0.75, 4.7], color=LINE, lw=1.2, zorder=0)
    steps = [("p1", "番号 1 で提案", None), ("p2", "番号 2 で提案", "番号 1 は選ばれない"),
             ("p1", "番号 3 で提案", "番号 2 も選ばれない"), ("p2", "番号 4 で提案", "番号 3 も選ばれない")]
    for i, (who, label, note) in enumerate(steps):
        y = 4.25 - i * 0.9
        x0 = cols[who]
        x1 = cols["acc"] + (-0.12 if who == "p1" else 0.12)
        ax.annotate("", xy=(x1, y), xytext=(x0, y), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
        ax.text((x0 + x1) / 2, y + 0.12, label, ha="center", va="bottom", fontsize=12, color=INK)
        if note:
            ax.text(cols["acc"], y - 0.32, note, ha="center", va="center", fontsize=11, color=RED,
                    bbox=dict(boxstyle="round,pad=0.25", fc=RED_PALE, ec="none"))
    ax.text(4.5, 0.45, "番号を出し合う限り、何も選ばれないまま続く", ha="center", va="center", fontsize=12, color=RED)
    _save(fig, "leader-and-followers_paxos.webp")


def overwrite_figure():
    """Raft 論文の Figure 8 の例: 過半数に届いた前の任期のエントリが、後の Leader に上書きされる。"""
    _style()
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.9)
    ax.axis("off")
    stages = [("段階 1", "任期 2 の A が B に配る", [2, 2, None, None, None]),
              ("段階 2", "任期 3 の E が自分に書く", [2, 2, None, None, 3]),
              ("段階 3", "任期 4 の A が C に配る", [2, 2, 2, None, 3]),
              ("段階 4", "任期 5 の E が上書き", [3, 3, 3, 3, 3])]
    notes = ["", "", "任期 2 が過半数に届く", "任期 2 が消える"]
    for k, (head, desc, terms) in enumerate(stages):
        ox = 0.15 + k * 2.5
        ax.text(ox + 1.15, 5.55, head, ha="center", va="center", fontsize=12, color=SUB)
        ax.text(ox + 1.15, 5.15, desc, ha="center", va="center", fontsize=11, color=INK)
        for i, (node, term) in enumerate(zip("ABCDE", terms)):
            y = 4.2 - i * 0.82
            ax.text(ox + 0.35, y + 0.3, node, ha="center", va="center", fontsize=12, color=SUB)
            if term is None:
                ax.add_patch(FancyBboxPatch((ox + 0.75, y), 1.0, 0.6, boxstyle="round,pad=0.02,rounding_size=0.08",
                                            fc="#ffffff", ec=SUB, lw=1.2, ls="--"))
                ax.text(ox + 1.25, y + 0.3, "-", ha="center", va="center", fontsize=12, color=SUB)
            else:
                fc, ec = (BLUE_PALE, BLUE) if term == 2 else (RED_PALE, RED)
                ax.add_patch(FancyBboxPatch((ox + 0.75, y), 1.0, 0.6, boxstyle="round,pad=0.02,rounding_size=0.08",
                                            fc=fc, ec=ec, lw=1.6))
                ax.text(ox + 1.25, y + 0.3, str(term), ha="center", va="center", fontsize=13, color=INK)
        if notes[k]:
            ax.text(ox + 1.15, 0.45, notes[k], ha="center", va="center", fontsize=11,
                    color=RED if k == 3 else INK)
        if k < 3:
            ax.plot([ox + 2.3, ox + 2.3], [0.8, 5.0], color=LINE, lw=1.0)
    ax.text(0.15 + 1.15, 0.45, "数字はログの同じ位置にある\nエントリの任期", ha="center", va="center",
            fontsize=10, color=SUB)
    _save(fig, "leader-and-followers_overwrite.webp")


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    failover_figure()
    raft_figure()
    commit_points_figure()
    stale_read_figure()
    paxos_figure()
    overwrite_figure()
    subprocess.run(["ls", "-la", str(IMAGES)], check=False)
