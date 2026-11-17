"""2PC ノートの図を作る（WebP）。

stuck_animation() は lab/output_postgres.txt の「== 2.」の時刻を読み、
コーディネータが止まった後のポイントの DB と、待たされる UPDATE を動く図にする。
protocol_figure() はコーディネータと参加者 2 つのやり取りと、参加者が自分で決められない区間。
indoubt_figure() は全員が準備済みの時に、参加者からは区別できない 2 つの場合。
vacuum_figure() は lab/output_postgres.txt の「== 3.」の VACUUM の結果を読む。

実行: python3 content/notes/distributed-systems/two-phase-commit/figures.py
"""

import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "images"
INK, SUB, LINE = "#1f1f1f", "#666666", "#9a9a9a"
RED, RED_PALE = "#c0392b", "#f6dcd8"
BLUE, BLUE_PALE = "#4a7fa8", "#dde9f2"
GRAY_PALE = "#ececec"
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
S = 2  # 2 倍で描いて縮める


def font(n):
    return ImageFont.truetype(CJK, int(n * S))


def read_events():
    text = (HERE / "lab" / "output_postgres.txt").read_text()
    part = text.split("== 2.")[1].split("== 3.")[0]
    ev = {}
    for sec, msg in re.findall(r"\[\s*([\d.]+)\] (.+)", part):
        ev[msg.strip()] = float(sec)

    def find(prefix):
        return next(v for k, v in ev.items() if k.startswith(prefix))

    return {
        "prep_orders": find("準備: orders"),
        "prep_points": find("準備: points"),
        "commit_orders": find("決定: orders"),
        "coord_stop": find("コーディネータが停止"),
        "b1_start": find("別のアプリの UPDATE を開始"),
        "b1_fail": find("UPDATE が lock_timeout"),
        "restart_start": find("points の PostgreSQL を再起動"),
        "restart_end": find("再起動が終わった"),
        "b2_start": find("別のアプリの UPDATE を再開"),
        "op_commit": find("orders ではコミット済み"),
        "b2_ok": find("待っていた UPDATE が通った"),
    }


def stuck_animation():
    e = read_events()
    T = 16.0
    STEP, SPEED = 0.5, 2.0
    W, H = 1000, 470
    x0, x1 = 230, 960

    def X(sec):
        return (x0 + (x1 - x0) * sec / T) * S

    lanes = ["コーディネータ", "注文 DB", "ポイント DB", "別アプリの UPDATE"]
    ys = [120, 190, 260, 330]
    frames = []
    n = int(T / STEP) + 1
    for k in range(n):
        now = min(k * STEP, T)
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((20 * S, 14 * S), "コーディネータが止まった後のポイント DB と、別アプリの UPDATE",
               font=font(20), fill=INK)
        d.text((20 * S, 46 * S), f"経過 {now:4.1f} 秒（PostgreSQL 17 で実測した時刻を 2 倍速で再生）",
               font=font(15), fill=SUB)
        # 時間の帯
        d.line([(X(0), 395 * S), (X(T), 395 * S)], fill=SUB, width=2 * S)
        for sec in range(0, 17, 2):
            d.line([(X(sec), 390 * S), (X(sec), 400 * S)], fill=SUB, width=2 * S)
            d.text((X(sec) - 6 * S, 404 * S), f"{sec}", font=font(13), fill=SUB)
        d.text((X(T) - 8 * S, 422 * S), "秒", font=font(13), fill=SUB)
        for name, y in zip(lanes, ys):
            d.text((20 * S, (y + 2) * S), name, font=font(16), fill=INK)

        def bar(a, b, y, fill, outline=None, label=None, color=INK):
            if now <= a:
                return
            r = min(now, b)
            d.rectangle([X(a), y * S, max(X(r), X(a) + 2 * S), (y + 30) * S], fill=fill, outline=outline,
                        width=2 * S)
            if label and r - a > 1.2:
                d.text((X(a) + 6 * S, (y + 4) * S), label, font=font(14), fill=color)

        # コーディネータ
        bar(0, e["coord_stop"], ys[0], GRAY_PALE, LINE)
        if now >= e["coord_stop"]:
            cx, cy = X(e["coord_stop"]) + 14 * S, (ys[0] + 15) * S
            d.line([(cx - 9 * S, cy - 9 * S), (cx + 9 * S, cy + 9 * S)], fill=RED, width=4 * S)
            d.line([(cx - 9 * S, cy + 9 * S), (cx + 9 * S, cy - 9 * S)], fill=RED, width=4 * S)
            d.text((cx + 18 * S, cy - 10 * S), "注文 DB にだけ COMMIT PREPARED を送って停止",
                   font=font(14), fill=RED)
        # 注文の DB
        bar(e["prep_orders"], e["commit_orders"], ys[1], RED_PALE, RED)
        bar(e["commit_orders"], T, ys[1], BLUE_PALE, BLUE, "コミット済み（注文 42 が見える）")
        # ポイントの DB
        bar(e["prep_points"], e["op_commit"], ys[2], RED_PALE, RED,
            "準備済み: 接続は無いが、行のロックを持ち続ける", RED)
        if now >= e["restart_start"]:
            rx = X(e["restart_start"])
            d.rectangle([rx, (ys[2] - 6) * S, X(min(now, e["restart_end"])) + 3 * S, (ys[2] + 36) * S],
                        fill=INK)
            d.text((rx - 40 * S, (ys[2] - 28) * S), "再起動しても残る", font=font(14), fill=INK)
        bar(e["op_commit"], T, ys[2], BLUE_PALE, BLUE)
        if now >= e["op_commit"]:
            d.text((X(e["op_commit"]) - 215 * S, (ys[2] + 40) * S), "運用者が COMMIT PREPARED",
                   font=font(14), fill=BLUE)
        # 別のアプリ
        bar(e["b1_start"], e["b1_fail"], ys[3], "#ffffff", RED, "ロックを待つ（pg_blocking_pids は {0}）", RED)
        if now >= e["b1_fail"]:
            d.text((X(e["b1_fail"]) - 120 * S, (ys[3] + 34) * S), "lock_timeout で失敗", font=font(14), fill=RED)
        bar(e["b2_start"], e["b2_ok"], ys[3], "#ffffff", RED, "再び待つ", RED)
        if now >= e["b2_ok"]:
            d.text((X(e["b2_ok"]) - 70 * S, (ys[3] + 34) * S), "通った", font=font(14), fill=BLUE)
        # 今の時刻の線
        d.line([(X(now), 100 * S), (X(now), 395 * S)], fill=INK, width=2 * S)
        frames.append(im.resize((W, H), Image.LANCZOS))
    dur = int(STEP / SPEED * 1000)
    durations = [dur] * (len(frames) - 1) + [3500]
    frames[0].save(OUT / "two-phase-commit_stuck.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=80, method=6)


def protocol_figure():
    W, H = 1000, 430
    im = Image.new("RGB", (W * S, H * S), "#ffffff")
    d = ImageDraw.Draw(im)
    lanes = {"coord": 90, "a": 230, "b": 330}
    x0, x1 = 200, 970
    d.text((20 * S, (lanes["coord"] - 12) * S), "コーディネータ", font=font(16), fill=INK)
    d.text((20 * S, (lanes["a"] - 12) * S), "参加者 A", font=font(16), fill=INK)
    d.text((20 * S, (lanes["b"] - 12) * S), "参加者 B", font=font(16), fill=INK)
    for y in lanes.values():
        d.line([(x0 * S, y * S), (x1 * S, y * S)], fill=LINE, width=2 * S)
    # フェーズの見出し
    d.rectangle([x0 * S, 14 * S, 520 * S, 44 * S], fill=GRAY_PALE)
    d.text((x0 * S + 10 * S, 18 * S), "準備フェーズ（prepare phase）", font=font(15), fill=INK)
    d.rectangle([540 * S, 14 * S, x1 * S, 44 * S], fill=GRAY_PALE)
    d.text((550 * S, 18 * S), "コミットフェーズ（commit phase）", font=font(15), fill=INK)

    def arrow(xa, ya, xb, yb, label, color=INK, lx=None, ly=None):
        d.line([(xa * S, ya * S), (xb * S, yb * S)], fill=color, width=2 * S)
        ang = math.atan2(yb - ya, xb - xa)
        for s in (0.45, -0.45):
            d.line([(xb * S, yb * S), ((xb - 12 * math.cos(ang + s)) * S, (yb - 12 * math.sin(ang + s)) * S)],
                   fill=color, width=2 * S)
        if label:
            d.text(((lx or (xa + xb) / 2 + 6) * S, (ly or (ya + yb) / 2 - 22) * S), label, font=font(13), fill=color)

    # 参加者の状態: 作業中 → 準備済み（自分で決められない） → コミット済み
    spans = {"a": (300, 650), "b": (330, 760)}
    for key, (p, c) in spans.items():
        y = lanes[key]
        d.rectangle([x0 * S, (y - 14) * S, p * S, (y + 14) * S], fill=GRAY_PALE, outline=LINE, width=2 * S)
        d.text(((x0 + 8) * S, (y - 10) * S), "作業中", font=font(13), fill=SUB)
        d.rectangle([p * S, (y - 14) * S, c * S, (y + 14) * S], fill=RED_PALE, outline=RED, width=2 * S)
        d.rectangle([c * S, (y - 14) * S, x1 * S, (y + 14) * S], fill=BLUE_PALE, outline=BLUE, width=2 * S)
        d.text(((max(c + 12, 790)) * S, (y - 10) * S), "コミット済み", font=font(13), fill=BLUE)
    d.text((420 * S, (lanes["a"] - 10) * S), "準備済み: ロックを持って待つ", font=font(13), fill=RED)
    d.text((440 * S, (lanes["b"] - 10) * S), "準備済み: 自分ではコミットも中止も選べない", font=font(13), fill=RED)
    # やり取り
    arrow(240, lanes["coord"], 300, lanes["a"] - 14, None)
    arrow(258, lanes["coord"], 330, lanes["b"] - 14, None)
    arrow(310, lanes["a"] - 14, 400, lanes["coord"] + 2, None)
    arrow(340, lanes["b"] - 14, 420, lanes["coord"] + 2, None)
    d.rectangle([440 * S, (lanes["coord"] - 16) * S, 590 * S, (lanes["coord"] + 16) * S], fill=INK)
    d.text((452 * S, (lanes["coord"] - 10) * S), "コミットと記録", font=font(14), fill="#ffffff")
    arrow(600, lanes["coord"], 650, lanes["a"] - 14, None)
    arrow(618, lanes["coord"], 760, lanes["b"] - 14, None)

    def tag(cx, cy, label):
        # 矢印の組の上に白地の名札を重ね、どの矢印の名前かを分かるようにする
        f = font(13)
        x0b, y0b, x1b, y1b = d.textbbox((0, 0), label, font=f)
        w, h = (x1b - x0b) / S, (y1b - y0b) / S
        d.rectangle([(cx - w / 2 - 5) * S, (cy - h / 2 - 4) * S, (cx + w / 2 + 5) * S, (cy + h / 2 + 4) * S],
                    fill="#ffffff", outline=LINE, width=S)
        d.text(((cx - w / 2) * S - x0b, (cy - h / 2) * S - y0b), label, font=f, fill=INK)

    tag(270, 130, "準備して")
    tag(356, 172, "はい（YES）")
    tag(655, 155, "コミットして")
    # 止まる所
    for x, label in ((340, "①"), (592, "②"), (690, "③")):
        d.text((x * S, (lanes["coord"] - 42) * S), label, font=font(18), fill=RED)
    d.text((20 * S, 382 * S),
           "コーディネータが止まる所　① 記録を書く前　② 記録の後、配る前　③ 配っている途中（本記事の実験はここ）",
           font=font(14), fill=SUB)
    im.resize((W, H), Image.LANCZOS).save(OUT / "two-phase-commit_protocol.webp", "WEBP", quality=90, method=6)


def vacuum_figure():
    text = (HERE / "lab" / "output_postgres.txt").read_text().split("== 3.")[1]
    rows = re.findall(r"tuples: (\d+) removed, (\d+) remain", text)
    labels = ["準備済みが無い", "準備済みが 1 つ残る", "ROLLBACK PREPARED の後"]
    removed = [int(r[0]) for r in rows]
    remain = [int(r[1]) for r in rows]
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10})
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    yy = range(len(labels))[::-1]
    ax.barh(list(yy), removed, color=BLUE, label="VACUUM が回収した行")
    ax.barh(list(yy), remain, left=removed, color=RED, label="消したのに回収できない行")
    for y, r, m in zip(yy, removed, remain):
        txt = f"回収 {r:,} 行" if r else f"回収 0 行、{m:,} 行が残る"
        ax.text(102000, y, txt, va="center", fontsize=9.5, color=INK)
    ax.set_yticks(list(yy), labels)
    ax.set_xlim(0, 150000)
    ax.set_xticks([0, 50000, 100000], ["0", "50,000", "100,000"])
    ax.set_xlabel("10 万行を消した直後の VACUUM（行）")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, 1.32), ncol=2, frameon=False, fontsize=9)
    fig.tight_layout()
    png = OUT / "_vacuum.png"
    fig.savefig(png, dpi=200, facecolor="#ffffff")
    plt.close(fig)
    Image.open(png).convert("RGB").save(OUT / "two-phase-commit_vacuum.webp", "WEBP", quality=90, method=6)
    png.unlink()


def indoubt_figure():
    """全員が準備済みの時、参加者からは区別できない 2 つの場合。"""
    W, H = 1000, 330
    im = Image.new("RGB", (W * S, H * S), "#ffffff")
    d = ImageDraw.Draw(im)
    panels = [
        (20, "コーディネータが記録を書く前に止まった", "ログ: 記録なし", "正しい決定: 中止"),
        (510, "コーディネータが記録を書いた直後に止まった", "ログ: コミット", "正しい決定: コミット"),
    ]
    for x, title, log, answer in panels:
        d.rounded_rectangle([x * S, 14 * S, (x + 470) * S, 316 * S], radius=12 * S, outline=LINE, width=2 * S)
        d.text(((x + 16) * S, 26 * S), title, font=font(16), fill=INK)
        # コーディネータ（止まっていて、外からは見えない）
        d.rectangle([(x + 16) * S, 66 * S, (x + 454) * S, 116 * S], fill=GRAY_PALE, outline=LINE, width=2 * S)
        d.text(((x + 28) * S, 74 * S), "コーディネータ（停止中）", font=font(14), fill=SUB)
        d.text(((x + 280) * S, 74 * S), log, font=font(14), fill=INK)
        # 参加者から見える所
        d.rectangle([(x + 16) * S, 140 * S, (x + 454) * S, 252 * S], outline=RED, width=2 * S)
        d.text(((x + 28) * S, 146 * S), "参加者から見えるもの", font=font(13), fill=RED)
        for k, name in enumerate(("参加者 A", "参加者 B")):
            bx = x + 34 + k * 212
            d.rectangle([bx * S, 176 * S, (bx + 192) * S, 236 * S], fill=RED_PALE, outline=RED, width=2 * S)
            d.text(((bx + 12) * S, 184 * S), f"{name}: 準備済み", font=font(14), fill=RED)
            d.text(((bx + 12) * S, 208 * S), "ロックを保持", font=font(13), fill=RED)
        d.text(((x + 16) * S, 270 * S), answer, font=font(16), fill=BLUE)
    im.resize((W, H), Image.LANCZOS).save(OUT / "two-phase-commit_indoubt.webp", "WEBP", quality=90, method=6)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    stuck_animation()
    protocol_figure()
    indoubt_figure()
    vacuum_figure()
