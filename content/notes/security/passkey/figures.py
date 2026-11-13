"""Passkey のノートの図を作る（matplotlib → PNG → WebP）。

数値と判定は lab/output.txt（lab/verify.py の出力）と lab/browser_output.txt（lab/run_browser.sh の出力）から読む。
実行: python3 figures.py
"""
import io
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

HERE = Path(__file__).resolve().parent
IMG = HERE / "images"
LAB = HERE / "lab"

font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["font.weight"] = "normal"

INK = "#28343b"
SUB = "#5d6b74"
LINE = "#9cabb5"
OK_FILL = "#eaf1f5"
NG_FILL = "#f6e3df"
NG_LINE = "#b5654f"
STOP_FILL = "#f4f4f2"
MONO = "DejaVu Sans Mono"


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(IMG / f"{name}.webp", "WEBP", quality=90, method=6)


def read_verify():
    rows, counters, kind = [], {}, None
    for line in (LAB / "output.txt").read_text(encoding="utf-8").splitlines():
        if " | " in line and not line.startswith("応答"):
            rows.append([c.strip() for c in line.split(" | ")])
        elif line and not line.startswith(" ") and " | " not in line:
            kind = line.strip()
            counters[kind] = []
        elif line.startswith("  ") and kind:
            m = re.match(r"\s+(\S+ \S+) signCount=(\d+) -> (.+)", line)
            counters[kind].append((m.group(1), int(m.group(2)), m.group(3)))
    return rows, counters


def cover_grid(rows):
    """冒頭の図: 1 欄ずつ変えた応答 7 通りを、2 つのサーバーがどう判定したか。"""
    labels = {
        "正規の応答": "正規の応答",
        "サブドメインのページ": "サブドメインのページで作った応答",
        "前回の challenge": "前回の challenge を使い回した応答",
        "似たドメインの rpId": "似たドメインの rpId で作った応答",
        "UV なし": "ユーザー確認（UV）をしていない応答",
        "署名後に 1 byte 変更": "署名した後に 1 byte 変えた応答",
        "別の鍵で署名": "登録していない鍵で署名した応答",
    }
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, len(rows) + 1.6)
    ax.axis("off")
    x_label, x1, x2, w = 0, 50, 76, 23
    top = len(rows) + 0.6
    ax.text(x1 + w / 2, top + 0.45, "全部チェックする\nサーバー", ha="center", va="center", fontsize=11, color=INK, linespacing=1.1)
    ax.text(x2 + w / 2, top + 0.45, "origin をチェックしない\nサーバー", ha="center", va="center", fontsize=11, color=INK, linespacing=1.1)
    for i, (case, full, loose) in enumerate(rows):
        y = top - 1 - i
        ax.text(x_label + 1, y + 0.42, labels.get(case, case), ha="left", va="center", fontsize=10.5, color=INK)
        for x, verdict in ((x1, full), (x2, loose)):
            accepted = verdict.startswith("通す")
            wrong = accepted and case != "正規の応答"
            fill = NG_FILL if wrong else (OK_FILL if accepted else STOP_FILL)
            edge = NG_LINE if wrong else LINE
            ax.add_patch(FancyBboxPatch((x, y + 0.08), w, 0.72, boxstyle="round,pad=0,rounding_size=0.12",
                                        facecolor=fill, edgecolor=edge, linewidth=1.4 if wrong else 0.8))
            text = "通す" if accepted else verdict
            ax.text(x + w / 2, y + 0.44, text, ha="center", va="center", fontsize=10,
                    color=NG_LINE if wrong else (INK if accepted else SUB))
    ax.text(0, -0.05, "応答は Python で書いた認証器が P-256 で署名したもの。サーバーは UV を必須（required）にした設定。判定は lab/verify.py の実測", fontsize=8.5, color=SUB)
    save(fig, "passkey_verify_grid")


def signed_bytes():
    """署名の対象: authenticatorData（37 byte）と clientDataJSON の SHA-256（32 byte）をつないだ 69 byte。"""
    fig, ax = plt.subplots(figsize=(8.6, 3.7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis("off")
    # authenticatorData: 32 + 1 + 4 byte。clientDataJSON のハッシュ: 32 byte。横幅を byte 数に比例させる。
    scale = 92 / 69
    x0 = 4
    parts = [
        (32, "rpIdHash\n32 byte", "認証器が書く", OK_FILL),
        (1, "", "", OK_FILL),
        (4, "", "", OK_FILL),
        (32, "SHA-256(clientDataJSON)\n32 byte", "ブラウザが書く", "#edf3ef"),
    ]
    x = x0
    spans = []
    for n, label, _, fill in parts:
        wdt = n * scale
        ax.add_patch(Rectangle((x, 20), wdt, 7, facecolor=fill, edgecolor=LINE, linewidth=0.9))
        if label:
            ax.text(x + wdt / 2, 23.5, label, ha="center", va="center", fontsize=9.5, color=INK, linespacing=1.15)
        spans.append((x, wdt))
        x += wdt
    # flags と signCount は箱が狭いので上に引き出す
    fx, fw = spans[1]
    cx, cw = spans[2]
    ax.annotate("flags 1 byte\nUP・UV など", xy=(fx + fw / 2, 27), xytext=(fx - 3, 33.5), fontsize=9, color=INK,
                ha="center", arrowprops=dict(arrowstyle="-", color=LINE, lw=0.8))
    ax.annotate("signCount\n4 byte", xy=(cx + cw / 2, 27), xytext=(cx + 9, 33.5), fontsize=9, color=INK,
                ha="center", arrowprops=dict(arrowstyle="-", color=LINE, lw=0.8))
    # 下の注記: 2 つの塊が誰の書いたものか
    ax.plot([x0, x0 + 37 * scale], [18.5, 18.5], color=LINE, lw=0.9)
    ax.text(x0 + 37 * scale / 2, 16.2, "authenticatorData（認証器が書く）", ha="center", va="top", fontsize=9.5, color=INK)
    hx = x0 + 37 * scale
    ax.plot([hx, hx + 32 * scale], [18.5, 18.5], color=LINE, lw=0.9)
    ax.text(hx + 32 * scale / 2, 16.2, "ブラウザが作る JSON のハッシュ値", ha="center", va="top", fontsize=9.5, color=INK)
    ax.text(hx + 32 * scale / 2, 11.6, '{"type":"webauthn.get",\n "challenge":"…", "origin":"https://…"}',
            ha="center", va="top", fontsize=8.5, color=SUB, family=MONO, linespacing=1.2)
    ax.text(x0, 3.2, "この 69 byte に端末の秘密鍵で署名し、サーバーは登録時に受け取った公開鍵で検証する（暗号化・復号ではない）",
            fontsize=9, color=SUB)
    save(fig, "passkey_signed_bytes")


def rpid_scope():
    """Chrome の仮想 authenticator で、どのページが rpId=app.localhost の鍵を使えたか。"""
    results = {}
    for line in (LAB / "browser_output.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"ページ (\S+) / rpId (\S+) -> (成功|失敗) ?(\S*)", line)
        if m:
            results[(m.group(1), m.group(2))] = (m.group(3), m.group(4))
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 44)
    ax.axis("off")

    def node(x, y, w, text, fill, edge=LINE, color=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, 6, boxstyle="round,pad=0,rounding_size=0.8",
                                    facecolor=fill, edgecolor=edge, linewidth=1.0))
        ax.text(x + w / 2, y + 3, text, ha="center", va="center", fontsize=10, color=color, family=MONO)

    node(38, 36, 24, "localhost", STOP_FILL)
    node(2, 22, 28, "app.localhost", OK_FILL)
    node(62, 22, 36, "app-localhost.localhost", STOP_FILL)
    node(2, 6, 28, "uploads.app.localhost", NG_FILL, edge=NG_LINE)
    for x1, y1, x2, y2 in ((50, 36, 16, 28), (50, 36, 80, 28), (16, 22, 16, 12)):
        ax.plot([x1, x2], [y1, y2], color=LINE, lw=0.9)
    ok_app = results.get(("app.localhost", "app.localhost"), ("?", ""))[0]
    ok_sub = results.get(("uploads.app.localhost", "app.localhost"), ("?", ""))[0]
    ng_look = results.get(("app-localhost.localhost", "app.localhost"), ("?", ""))
    ng_own = results.get(("app-localhost.localhost", "app-localhost.localhost"), ("?", ""))
    ax.text(32, 25, f"鍵を登録した rpId\nここで使うと{ok_app}", fontsize=9.5, color=INK, va="center")
    ax.text(32, 9, f"同じ rpId で{ok_sub}。\n正しい署名が返り、origin には\nuploads.app.localhost が入る", fontsize=9.5,
            color=NG_LINE, va="center")
    ax.text(62, 16.5, f"rpId=app.localhost → {ng_look[0]}\n（{ng_look[1]}）\n自分の rpId → {ng_own[0]}（{ng_own[1]}）",
            fontsize=9.5, color=SUB, va="top", linespacing=1.3)
    ax.text(0, 0.5, "Chrome の仮想認証器（CDP の WebAuthn）で実測。localhost の下の名前は全て 127.0.0.1 の同じサーバー",
            fontsize=8.5, color=SUB)
    save(fig, "passkey_rpid_scope")


def counter_steps(counters):
    """署名カウンタ: 同じ秘密鍵を持つ 2 台目の端末に、サーバーが気付けるか。"""
    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(-2, 30)
    ax.axis("off")
    for r, (kind, log) in enumerate(counters.items()):
        y = 19 - r * 12
        ax.text(0, y + 3, kind, fontsize=10, color=INK, va="center")
        for i, (who, count, verdict) in enumerate(log):
            x = 30 + i * 23
            flagged = "複製" in verdict
            ax.add_patch(FancyBboxPatch((x, y - 1), 20, 8, boxstyle="round,pad=0,rounding_size=0.8",
                                        facecolor=NG_FILL if flagged else OK_FILL,
                                        edgecolor=NG_LINE if flagged else LINE, linewidth=1.0))
            ax.text(x + 10, y + 4.9, f"{i + 1} 回目　{who}", ha="center", va="center", fontsize=9, color=INK)
            ax.text(x + 10, y + 2.6, f"signCount={count}", ha="center", va="center",
                    fontsize=8.5, color=NG_LINE if flagged else SUB)
            ax.text(x + 10, y + 0.5, {True: "通す・複製の疑い", False: "通す"}[flagged], ha="center", va="center",
                    fontsize=8.5, color=NG_LINE if flagged else SUB)
            if i:
                ax.annotate("", xy=(x, y + 3), xytext=(x - 3, y + 3), arrowprops=dict(arrowstyle="->", color=LINE, lw=0.8))
    ax.text(0, -1.8, "端末 B は端末 A と同じ秘密鍵を持つ。lab/verify.py の counters() の実測", fontsize=8.5, color=SUB)
    save(fig, "passkey_counter")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    rows, counters = read_verify()
    cover_grid(rows)
    signed_bytes()
    rpid_scope()
    counter_steps(counters)
