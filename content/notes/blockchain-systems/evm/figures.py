"""Generate the figures of the EVM note.

Run: python3 figures.py  -> images/*.webp
Hand-drawn figures are built as SVG with the standard library, rendered with
headless Chrome at 2x and saved as WebP (Pillow). The charts use matplotlib
(PNG at 200 dpi -> WebP). Numbers come from lab/output/probe.json (written by
lab/run.sh), not from values typed into this file. The only typed values are
the Osaka gas constants of evm_gas_ladder.webp, copied from execution-specs
src/ethereum/forks/osaka/vm/gas.py (f9488c74).
The figures of the fork history (opcodes per fork, precompiles, EIP types)
live in ../evm-opcode-history/figures.py.
"""

from html import escape
import io
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab" / "output"
IMG = HERE / "images"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
GRAY_PALE = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"

PROBE = json.loads((LAB / "probe.json").read_text())


def to_webp(png, name):
    Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img"><title>{escape(title)}</title>',
            f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} .mono{{font-family:{MONO}}}</style>",
            '<defs>'
            f'<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            f'<marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
            '</defs>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls="", weight=None):
        c = f' class="{cls}"' if cls else ""
        wt = f' font-weight="{weight}"' if weight else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{wt}>{escape(str(s))}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, rx=8, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=2.5, arrow=True, dash=None, marker="a"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#{marker})"' if arrow else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}{m}/>')

    def path(self, d, color=SUB, sw=2.5, arrow=True, dash=None, fill="none"):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#a)"' if arrow else ""
        self.p.append(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}"{ds}{m}/>')

    def cross(self, x, y, r=12):
        self.p.append(f'<path d="M{x - r} {y - r} L{x + r} {y + r} M{x + r} {y - r} L{x - r} {y + r}" '
                      f'stroke="{RED}" stroke-width="5" stroke-linecap="round"/>')

    def save(self, name):
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            to_webp(png, name)


# 1. Cover: an EOA sends a transaction to a contract (code + storage); every node runs the same code.
def overview():
    s = Svg(960, 290, "EOA が署名したトランザクションがコントラクトに届き、コントラクトのコードが storage を書き換える。"
                      "全てのノードが同じコードを EVM で実行し、同じ新しい状態になる。命令にはガスの値段が付く")
    # EOA.
    s.rect(30, 50, 230, 190, "#ffffff", SUB, 2.5, rx=12)
    s.text(145, 100, "EOA", 30)
    s.text(145, 140, "秘密鍵", 24, cls="sub")
    s.text(145, 176, "残高", 24, cls="sub")
    s.text(145, 210, "nonce", 24, cls="sub")
    # Transaction.
    s.line(262, 120, 556, 120, SUB, 3.5)
    s.text(409, 104, "トランザクション", 26)
    s.text(409, 156, "宛先・額・入力", 24, cls="sub")
    s.text(409, 190, "ガスの上限", 24, cls="sub")
    # Contract account: code and storage.
    s.rect(560, 30, 370, 230, "#ffffff", BLUE, 3, rx=12)
    s.text(745, 70, "コントラクト", 28)
    s.rect(580, 92, 136, 144, BLUE_PALE, BLUE, 2.5, rx=8)
    s.text(648, 156, "コード", 26)
    s.text(648, 192, "不変", 24, cls="sub")
    s.rect(776, 92, 140, 144, OCHRE_PALE, OCHRE, 2.5, rx=8)
    s.text(846, 156, "storage", 26)
    s.text(846, 192, "キー → 値", 22, cls="sub")
    s.line(718, 164, 770, 164, BLUE, 3, marker="ab")
    s.text(746, 146, "読み書き", 18, cls="sub")
    s.save("evm_overview.webp")


# 1b. Every node runs the same transaction in its own EVM and reaches the same state.
def nodes():
    s = Svg(960, 300, "全てのノードが同じトランザクションを自分の EVM で実行し、同じ新しい状態になる。命令ごとにガスが掛かる")
    s.rect(30, 20, 900, 260, GRAY_PALE, SUB, 1.5, rx=12)
    s.text(54, 60, "全ノードが自分の EVM で同じトランザクションを実行", 24, "start", "sub")
    for i in range(3):
        y = 86 + i * 62
        s.rect(60, y, 150, 50, "#ffffff", SUB, 2, rx=6)
        s.text(135, y + 34, f"ノード {i + 1}", 24)
        s.rect(250, y, 170, 50, BLUE_PALE, BLUE, 2, rx=6)
        s.text(335, y + 34, "EVM", 24)
        s.line(210, y + 25, 246, y + 25, SUB, 2)
        s.line(420, y + 25, 586, 172, SUB, 2)
    s.rect(590, 112, 300, 120, "#ffffff", GREEN, 3, rx=10)
    s.text(740, 166, "同じ新しい状態", 28)
    s.text(740, 206, "1 つでも違えば合わない", 22, cls="sub")
    s.save("evm_nodes.webp")


# 1c. Gas limit, gas used and the fee.
def gas_fee():
    s = Svg(960, 330, "トランザクションのガスの上限のうち、実際に使った分だけに 1 ガスあたりの単価を掛けて手数料を払い、使わなかった分は払わない")
    s.text(40, 50, "ガスの上限（gas limit）= 送り主が用意した量", 24, "start")
    s.rect(40, 74, 880, 70, "#ffffff", SUB, 2, rx=6)
    s.rect(40, 74, 560, 70, BLUE_PALE, BLUE, 2.5, rx=6)
    s.text(320, 118, "使ったガス（gasUsed）", 26)
    s.text(760, 118, "使わなかった分", 24, cls="sub")
    s.line(320, 150, 320, 196)
    s.line(760, 150, 760, 196)
    s.rect(110, 200, 420, 96, OCHRE_PALE, OCHRE, 2.5, rx=8)
    s.text(320, 238, "手数料 = gasUsed × 単価", 26)
    s.text(320, 276, "ETH（wei）で払う", 22, cls="sub")
    s.rect(620, 200, 280, 96, "#ffffff", SUB, 2, rx=8, dash="7 5")
    s.text(760, 238, "払わない", 26)
    s.save("evm_gas_fee.webp")


# 1d. One specification, several implementations that must agree.
def clients():
    s = Svg(960, 330, "仕様は 1 つで、Go の geth、Rust の revm（Anvil が使う）など複数の実装が、同じブロックから同じ状態を計算する")
    s.rect(30, 110, 230, 90, BLUE_PALE, BLUE, 2.5, rx=8)
    s.text(145, 148, "仕様", 26)
    s.text(145, 182, "execution-specs", 22, cls="sub")
    impls = [("geth（Go）", 40), ("revm（Rust）", 120), ("他の実装", 200)]
    for name, y in impls:
        s.rect(360, y, 250, 64, "#ffffff", SUB, 2, rx=8)
        s.text(485, y + 41, name, 24)
        s.line(262, 155, 356, y + 32, SUB, 2)
        s.line(612, y + 32, 706, 155, SUB, 2)
    s.text(485, 310, "Anvil は revm を使う", 20, cls="sub")
    s.rect(710, 110, 220, 90, "#ffffff", GREEN, 3, rx=8)
    s.text(820, 148, "同じブロック", 24)
    s.text(820, 182, "→ 同じ状態", 24)
    s.save("evm_clients.webp")


# 2. A transaction contains a message call, which contains the opcode loop.
def pipeline():
    s = Svg(960, 470, "トランザクションの処理の中にメッセージ呼び出しがあり、その中で命令を 1 つずつ実行するループが回る。"
                      "CALL は同じループを持つ子のフレームを作る。前後にトランザクションの検査と精算がある")
    s.rect(20, 20, 920, 430, GRAY_PALE, SUB, 2, rx=12)
    s.text(44, 62, "トランザクションの処理（状態遷移）", 26, "start")
    # Before and after.
    s.rect(44, 100, 170, 310, "#ffffff", SUB, rx=10)
    s.text(129, 136, "検査", 22, cls="sub")
    for i, t in enumerate(["署名", "nonce", "intrinsic gas", "前払い"]):
        s.text(129, 180 + i * 58, t, 24)
    s.rect(746, 100, 170, 310, "#ffffff", SUB, rx=10)
    s.text(831, 136, "精算", 22, cls="sub")
    for i, t in enumerate(["払い戻し", "手数料", "レシート"]):
        s.text(831, 180 + i * 72, t, 24)
    s.line(214, 255, 252, 255)
    s.line(708, 255, 742, 255)
    # Message call with the interpreter loop.
    s.rect(256, 100, 450, 310, BLUE_PALE, BLUE, 2.5, rx=12)
    s.text(276, 140, "メッセージ呼び出し（フレーム）", 24, "start")
    s.rect(280, 168, 400, 120, "#ffffff", BLUE, 2, rx=10)
    for cx, t in ((335, "読む"), (480, "ガスを引く"), (625, "実行")):
        s.text(cx, 222, t, 24)
    s.line(382, 214, 408, 214)
    s.line(553, 214, 580, 214)
    s.path("M 625 236 C 625 276, 335 276, 335 240", SUB, 2)
    s.text(480, 318, "STOP・RETURN・REVERT・エラーまで", 24, cls="sub")
    s.rect(330, 340, 300, 54, "#ffffff", BLUE, 2, rx=8, dash="7 5")
    s.text(480, 376, "CALL → 子のフレーム", 24)
    s.save("evm_pipeline.webp")


# 3. Lifetimes of the data areas over one transaction.
def lifetimes():
    s = Svg(960, 520, "1 件のトランザクションの時間軸。stack と memory はフレームの間だけ、transient storage はトランザクションの終わりまで、"
                      "storage は次のトランザクションにも残る")
    x0, x1 = 300, 860
    s.text(40, 52, "時間 →", 24, "start", "sub")
    s.line(x0, 70, 930, 70, SUB, 2)
    s.line(x0, 60, x0, 480, SUB, 1.5, arrow=False, dash="5 5")
    s.line(x1, 60, x1, 480, SUB, 1.5, arrow=False, dash="5 5")
    s.text(x0, 46, "トランザクションの開始", 24, cls="sub")
    s.text(x1 + 40, 46, "トランザクションの終わり", 20, "end", "sub")
    rows = [
        ("フレーム A", x0, x1, GRAY_PALE, SUB),
        ("フレーム B（CALL）", 470, 680, GRAY_PALE, SUB),
        ("A の stack・memory", x0, x1, BLUE_PALE, BLUE),
        ("B の stack・memory", 470, 680, BLUE_PALE, BLUE),
        ("transient storage", 380, x1, OCHRE_PALE, OCHRE),
        ("storage", 240, 940, GREEN_PALE, GREEN),
    ]
    for i, (label, a, b, face, edge) in enumerate(rows):
        y = 100 + i * 64
        s.text(30, y + 33, label, 24, "start")
        s.rect(a, y + 6, b - a, 38, face, edge, 2, rx=6)
    s.text(392, 389, "TSTORE", 22, "start", "sub")
    s.cross(x1, 389, 11)
    s.text(924, 453, "次のトランザクション", 22, "end", "sub")
    s.save("evm_lifetimes.webp")


# 4. Bytes of code: the 0x5b inside PUSH1's immediate is data, not a jump destination.
def jumpdest():
    s = Svg(960, 400, "コード 60 5b 5b 00 の各バイト。PC 1 の 5b は PUSH1 の即値で、飛び先にできない。PC 2 の 5b は JUMPDEST で飛べる")
    bytes_ = [("60", "PUSH1"), ("5b", "即値"), ("5b", "JUMPDEST"), ("00", "STOP")]
    for i, (b, role) in enumerate(bytes_):
        x = 120 + i * 190
        face = OCHRE_PALE if role == "即値" else BLUE_PALE
        edge = OCHRE if role == "即値" else BLUE
        s.text(x + 80, 60, f"PC {i}", 24, cls="sub")
        s.rect(x, 80, 160, 90, face, edge, 2.5, rx=8)
        s.text(x + 80, 140, b, 34, cls="mono")
        s.text(x + 80, 214, role, 24)
    s.path("M 130 240 L 130 254 L 470 254 L 470 240", SUB, 2, arrow=False)
    s.text(300, 288, "1 つの命令: PUSH1 0x5b", 24, cls="sub")
    s.text(310, 352, "1 へ JUMP", 26)
    s.cross(420, 344)
    s.text(650, 352, "2 へ JUMP", 26)
    s.p.append(f'<path d="M 748 344 l 10 10 l 20 -22" fill="none" stroke="{GREEN}" stroke-width="5" stroke-linecap="round"/>')
    s.save("evm_jumpdest.webp")


# 5. CALL / DELEGATECALL / STATICCALL measured with lab/Context.sol.
def contexts():
    rows = {r["mode"]: r for r in PROBE["context"]}
    s = Svg(960, 650, "同じ Caller から同じ Target を 3 通りに呼んだ実測。CALL は Target の storage、DELEGATECALL は Caller の "
                      "storage に書き、STATICCALL は書き込みで失敗する")
    panels = [("CALL", "CALL record", "Target"), ("DELEGATECALL", "DELEGATECALL record", "Caller"),
              ("STATICCALL", "STATICCALL record", None)]
    for i, (title, key, owner) in enumerate(panels):
        x = 20 + i * 312
        r = rows[key]
        s.rect(x, 20, 296, 560, GRAY_PALE, SUB, 1.5, rx=12)
        s.text(x + 148, 62, title, 26, weight="normal")
        for j, (name, y) in enumerate((("Caller", 100), ("Target", 300))):
            s.rect(x + 24, y, 248, 160, "#ffffff", SUB, 2, rx=10)
            s.text(x + 44, y + 36, name, 24, "start")
            # code box
            runs = name == "Target"
            s.rect(x + 40, y + 52, 100, 92, BLUE_PALE if runs else "#ffffff", BLUE if runs else SUB, 2, rx=6)
            s.text(x + 90, y + 106, "コード", 24)
            # storage box
            written = owner == name
            refused = owner is None and name == "Target"
            f, e = (OCHRE_PALE, OCHRE) if written else (RED_PALE, RED) if refused else ("#ffffff", SUB)
            s.rect(x + 156, y + 52, 100, 92, f, e, 2.5 if refused else 2, rx=6)
            s.text(x + 206, y + 106, "slot 0", 24)
        s.line(x + 148, 260, x + 148, 296, SUB, 3)
        if owner is None:
            s.text(x + 148, 510, "SSTORE が失敗", 24)
            s.text(x + 148, 548, "ok = 0", 24, cls="sub")
        else:
            who = {"EOA": "EOA", "Caller": "Caller", "Target": "Target"}[r["sender"]]
            s.text(x + 148, 510, f"msg.sender = {who}", 24)
            s.text(x + 148, 548, f"msg.value = {r['value']} wei", 24, cls="sub")
    for x, f, e, t in ((40, BLUE_PALE, BLUE, "動いたコード"), (340, OCHRE_PALE, OCHRE, "書き込まれた slot"),
                       (680, RED_PALE, RED, "書き込めず失敗")):
        s.rect(x, 608, 34, 26, f, e, 2, rx=3)
        s.text(x + 44, 629, t, 22, "start")
    s.save("evm_call_context.webp")


# 8. Calldata of set(42) and the dispatcher that reads it.
def dispatcher():
    d = next(x for x in PROBE["dispatcher"] if x["x"] == 42)
    sel, arg = d["calldata"][:8], d["calldata"][8:]
    head = {pc: op for pc, op, _ in PROBE["trace_head"]}
    jump_pc = [pc for pc, op, _ in PROBE["trace_head"]][-1]
    s = Svg(960, 560, f"set(42) の calldata は先頭 4 バイトの selector {sel} と 32 バイトの引数。"
                      "CALLDATALOAD と SHR で selector を取り出し、EQ と JUMPI で関数ごとの位置に分岐する。一致しなければ REVERT")
    # calldata strip
    s.text(30, 44, "calldata（36 バイト）", 24, "start", "sub")
    s.rect(30, 60, 220, 70, BLUE_PALE, BLUE, 2.5, rx=6)
    s.text(140, 106, sel, 28, cls="mono")
    s.rect(250, 60, 680, 70, OCHRE_PALE, OCHRE, 2.5, rx=6)
    s.text(590, 106, "00 … 00 2a  (42)", 28, cls="mono")
    s.text(140, 160, "4 バイト", 24, cls="sub")
    s.text(590, 160, "32 バイト", 24, cls="sub")
    getter = PROBE["getter_selector"]
    # Row 1: take the selector out of the first 32 bytes.
    x = 30
    for i, t in enumerate(["CALLDATALOAD 0", "SHR 224"]):
        s.rect(x, 200, 250, 64, "#ffffff", SUB, 2, rx=8)
        s.text(x + 125, 241, t, 24, cls="mono")
        s.line(x + 254, 232, x + 286, 232)
        x += 290
    s.rect(x, 200, 250, 64, BLUE_PALE, BLUE, 2.5, rx=8)
    s.text(x + 125, 241, sel, 26, cls="mono")
    # Row 2: compare with each function's selector.
    s.rect(30, 330, 250, 64, "#ffffff", SUB, 2, rx=8)
    s.text(155, 371, f"EQ {getter}", 24, cls="mono")
    s.text(155, 426, "value()", 24, cls="sub")
    s.line(284, 362, 316, 362)
    s.text(300, 394, "否", 14, cls="sub")
    s.rect(320, 330, 250, 64, "#ffffff", SUB, 2, rx=8)
    s.text(445, 371, f"EQ {sel}", 24, cls="mono")
    s.text(445, 426, "set(uint256)", 24, cls="sub")
    s.line(574, 362, 606, 362)
    s.text(590, 394, "一致", 14, cls="sub")
    s.rect(610, 330, 320, 64, BLUE_PALE, BLUE, 2.5, rx=8)
    s.text(770, 371, f"JUMPI → pc {jump_pc}", 24, cls="mono")
    s.path("M 735 268 L 735 300 L 155 300 L 155 326", SUB, 2.5)
    s.text(30, 470, "どれとも不一致 → REVERT", 24, "start")
    s.line(770, 398, 770, 446)
    s.rect(610, 450, 320, 90, "#ffffff", BLUE, 2, rx=8)
    s.text(770, 486, "SSTORE, LOG2, STOP", 24, cls="mono")
    s.text(770, 524, "set() の本体", 24, cls="sub")
    s.text(30, 514, "EVM は set という", 24, "start", "sub")
    s.text(30, 548, "名前を見ない", 24, "start", "sub")
    assert head.get(26) == "CALLDATALOAD"
    s.save("evm_dispatcher.webp")


# 9. What LOG2 writes into the receipt.
def log_figure():
    d = next(x for x in PROBE["dispatcher"] if x["x"] == 42)
    s = Svg(960, 470, f"LOG2 が書く内容。topic0 はイベントの署名のハッシュ、topic1 は indexed の sender、data は値。"
                      f"bloom にはアドレスと topic だけが入る。この LOG2 は {d['log']} ガス")
    s.text(30, 50, f"set(42) の LOG2: {d['log']:,} ガス", 26, "start", weight="normal")
    s.text(30, 90, "= 375 + 2 × 375 + 8 × 32 バイト", 24, "start", "sub")
    parts = [("address", "Dispatcher", BLUE_PALE, BLUE), ("topic0", "keccak(\"Changed(...)\")", BLUE_PALE, BLUE),
             ("topic1", "sender（indexed）", BLUE_PALE, BLUE), ("data", "value = 42", OCHRE_PALE, OCHRE)]
    for i, (k, v, f, e) in enumerate(parts):
        y = 120 + i * 78
        s.rect(30, y, 560, 64, f, e, 2, rx=6)
        s.text(50, y + 42, k, 24, "start", weight="normal")
        s.text(190, y + 42, v, 24, "start")
    s.rect(700, 140, 230, 200, GRAY_PALE, SUB, 2, rx=8)
    s.text(815, 220, "bloom", 26)
    s.text(815, 258, "2048 ビット", 24, cls="sub")
    for i in range(3):
        y = 152 + i * 78
        s.line(594, y, 696, 200 + i * 30, SUB, 2)
    s.text(815, 400, "data は bloom に入らない", 24, cls="sub")
    s.save("evm_log.webp")


# 10. Where a transaction can fail: rejected by the checks, or included with status 0.
def failure_kinds():
    s = Svg(960, 400, "トランザクションの失敗は 2 種類ある。署名・nonce・前払いの検査で弾かれたトランザクションはブロックに入らない。"
                      "コードの実行中に失敗したトランザクションはブロックに入り、status 0 になり、nonce が進み、手数料を払う")
    s.text(12, 92, "トランザクション", 15, "start")
    s.line(76, 104, 136, 104)
    s.rect(140, 60, 250, 90, GRAY_PALE, SUB, 2)
    s.text(265, 98, "検査", 26)
    s.text(265, 132, "署名・nonce・前払い", 24, cls="sub")
    s.line(390, 104, 436, 104)
    s.rect(440, 60, 250, 90, BLUE_PALE, BLUE, 2.5)
    s.text(565, 98, "コードの実行", 26)
    s.text(565, 132, "EVM のフレーム", 24, cls="sub")
    s.line(690, 104, 756, 104)
    s.rect(760, 40, 180, 340, "#ffffff", SUB, 2, rx=10)
    s.text(850, 80, "ブロック", 26)
    s.text(850, 124, "status 1", 24)
    s.text(850, 156, "nonce + 1", 20, cls="sub")
    # Rejected by the outer checks.
    s.line(265, 150, 265, 212, SUB, 2.5, dash="6 5")
    s.cross(176, 246, 11)
    s.text(280, 254, "拒否", 26)
    s.text(265, 296, "ブロックに入らない", 24, cls="sub")
    s.text(265, 332, "nonce も残高も不変", 24, cls="sub")
    # Failed while running code.
    s.line(565, 150, 565, 216)
    s.rect(440, 220, 250, 90, OCHRE_PALE, OCHRE, 2.5)
    s.text(565, 258, "エラー / REVERT", 26)
    s.text(565, 292, "状態を取り消す", 24, cls="sub")
    s.line(690, 265, 756, 265)
    s.text(850, 262, "status 0", 24)
    s.text(850, 302, "nonce + 1", 24, cls="sub")
    s.text(850, 338, "手数料は払う", 24, cls="sub")
    s.save("evm_failure_kinds.webp")


# 11. PUSH1 2, PUSH1 3, ADD on the stack.
def stack():
    s = Svg(960, 400, "PUSH1 2 と PUSH1 3 で 2 と 3 が積まれ、ADD が 2 つを取り出して 5 を積む。1 要素は 256 ビットで、最大 1,024 要素")
    states = [("PUSH1 2", [2]), ("PUSH1 3", [2, 3]), ("ADD", [5])]
    base = 300
    for i, (op, items) in enumerate(states):
        cx = 170 + i * 310
        s.text(cx, 60, op, 28, cls="mono")
        for j, v in enumerate(items):
            top = j == len(items) - 1
            y = base - (j + 1) * 70
            s.rect(cx - 80, y, 160, 62, BLUE_PALE if top else "#ffffff", BLUE if top else SUB, 2.5 if top else 2, rx=6)
            s.text(cx, y + 42, v, 30, cls="mono")
        s.line(cx - 100, base + 6, cx + 100, base + 6, SUB, 2.5, arrow=False)
        if i < 2:
            s.line(cx + 104, 200, cx + 200, 200, SUB, 3)
    s.text(590, 186, "2 と 3 を取り出す", 20, "start", "sub")
    s.text(480, 360, "1 要素は 256 ビットの語、最大 1,024 要素", 24, cls="sub")
    s.save("evm_stack.webp")


# 12. Which data areas belong to the frame and which to the account.
def data_areas():
    s = Svg(960, 500, "EVM のデータ領域。stack・memory・calldata・returndata はフレームに属し、"
                      "transient storage・storage・code はアカウントに属する。それぞれの寿命")
    groups = [
        (20, "フレームに属する", BLUE_PALE, BLUE, [
            ("stack", "フレームの終わりまで、256 ビット"), ("memory", "フレームの終わりまで、バイト列"),
            ("calldata", "フレームの終わりまで、読むだけ"), ("returndata", "次に子を呼ぶまで")]),
        (500, "アカウントに属する", OCHRE_PALE, OCHRE, [
            ("transient storage", "トランザクションの終わりまで"), ("storage", "書き換えるまで"),
            ("code", "デプロイ後は不変、読むだけ")]),
    ]
    for x, title, face, edge, items in groups:
        s.rect(x, 20, 440, 460, face, edge, 2, rx=12)
        s.text(x + 24, 62, title, 26, "start")
        for j, (name, life) in enumerate(items):
            y = 84 + j * 96
            s.rect(x + 20, y, 400, 84, "#ffffff", edge, 2, rx=8)
            s.text(x + 40, y + 36, name, 26, "start", "mono")
            s.text(x + 40, y + 70, life, 22, "start", "sub")
    s.save("evm_data_areas.webp")


# 13. The four ways a frame ends and what happens to the gas given to it.
def frame_exit():
    s = Svg(960, 560, "フレームの終わり方 4 通り。STOP・RETURN と REVERT は残りのガスを親に返し、例外は渡したガスを全て失い、"
                      "子を始められない時はガスが親に残る。状態の変更を残すのは STOP・RETURN だけ")
    s.text(30, 52, "終わり方", 24, "start", "sub")
    s.text(440, 52, "子に渡したガス", 24, cls="sub")
    s.text(700, 52, "状態", 24, cls="sub")
    s.text(880, 52, "親へ", 24, cls="sub")
    rows = [
        ("STOP / RETURN", "returned", "残す", "1 + データ"),
        ("REVERT", "returned", "取り消す", "0 + データ"),
        ("例外", "lost", "取り消す", "0"),
        ("始められない", "stays", "実行しない", "0"),
    ]
    for i, (name, gas, state, ret) in enumerate(rows):
        y = 80 + i * 104
        s.text(30, y + 42, name, 26, "start", "mono" if name.isupper() or "/" in name else "")
        if gas == "returned":
            s.rect(290, y + 8, 180, 52, GRAY_PALE, SUB, 2, rx=4)
            s.text(380, y + 42, "使った分", 24)
            s.rect(470, y + 8, 120, 52, BLUE_PALE, BLUE, 2, rx=4)
            s.text(530, y + 42, "返す", 24)
        elif gas == "lost":
            s.rect(290, y + 8, 300, 52, OCHRE_PALE, OCHRE, 2.5, rx=4)
            s.text(440, y + 42, "全て失う", 24)
        else:
            s.rect(290, y + 8, 300, 52, "#ffffff", SUB, 2, rx=4, dash="7 5")
            s.text(440, y + 42, "親に残る", 24, cls="sub")
        s.text(700, y + 42, state, 26)
        s.text(880, y + 42, ret, 26, cls="mono")
    s.text(30, 530, "「残す」の変更も、親が後で失敗すれば取り消される", 24, "start", "sub")
    s.save("evm_frame_exit.webp")


# 14. Gas of representative opcodes on a log scale.
#     Osaka values from execution-specs vm/gas.py (f9488c74), the same numbers as the table in the note.
OSAKA_GAS = [
    ("ADD, LT, AND", 3, "calc"), ("MUL, DIV", 5, "calc"), ("JUMPI", 10, "calc"),
    ("TLOAD, warm SLOAD", 100, "state"), ("LOG0", 375, "state"), ("cold SLOAD", 2100, "state"),
    ("cold の CALL 先", 2600, "state"), ("SSTORE 0 → 0 以外", 20000, "state"), ("CREATE", 32000, "state"),
]


def gas_ladder():
    import math
    s = Svg(960, 630, "Osaka の主な命令のガスを対数の目盛りで並べた図。ADD は 3、MUL は 5、JUMPI は 10 の計算の命令に対して、"
                      "storage やアカウントに触る命令は 100 から 32,000 で、ADD の約 30 倍から 1 万倍")
    x0, span, decades = 330, 560, 5
    xs = lambda v: x0 + span * math.log10(v) / decades
    top = 90
    for k in range(decades + 1):
        x = x0 + span * k / decades
        s.line(x, top - 10, x, top + len(OSAKA_GAS) * 50, GRAY_PALE, 2, arrow=False)
        s.text(x, top + len(OSAKA_GAS) * 50 + 34, f"{10 ** k:,}", 24, cls="sub")
    for i, (name, gas, kind) in enumerate(OSAKA_GAS):
        y = top + i * 50
        face, edge = (BLUE_PALE, BLUE) if kind == "calc" else (OCHRE_PALE, OCHRE)
        s.text(310, y + 32, name, 24, "end")
        s.rect(x0, y + 8, max(xs(gas) - x0, 6), 34, face, edge, 2, rx=3)
        s.text(xs(gas) + 10, y + 34, f"{gas:,}", 24, "start")
    s.rect(330, 26, 34, 26, BLUE_PALE, BLUE, 2, rx=3)
    s.text(374, 48, "計算", 24, "start")
    s.rect(560, 26, 34, 26, OCHRE_PALE, OCHRE, 2, rx=3)
    s.text(604, 48, "状態・ディスク・レシート", 24, "start")
    s.text(x0 + span / 2, 620, "ガス（対数目盛り）", 24, cls="sub")
    s.save("evm_gas_ladder.webp")


# 15. The 63/64 rule with the measured numbers of lab/probe.py.
def call_split():
    allr = next(r for r in PROBE["call_gas"] if r["request"] == "all")
    small = next(r for r in PROBE["call_gas"] if r["request"] == "10000")
    costs = 2600 + 3
    g = allr["before"] - costs
    keep = g - allr["entry"]
    assert allr["entry"] == allr["limit"] and keep == g // 64
    s = Svg(960, 360, f"CALL のコストを引いた残り {g:,} のうち、子が受け取ったのは 63/64 の {allr['entry']:,} で、"
                      f"親に {keep:,} が残った。10,000 だけを要求した時は 10,000 が渡った")
    s.text(40, 50, f"g = {allr['before']:,}（CALL の前）− {costs:,}（CALL の費用）= {g:,}", 24, "start", "sub")
    W = 880
    cw = W * allr["entry"] / g
    s.rect(40, 80, cw, 76, BLUE_PALE, BLUE, 2.5, rx=4)
    s.text(40 + cw / 2, 128, f"子が受け取る {allr['entry']:,}（63/64）", 26)
    s.rect(40 + cw, 80, W - cw, 76, OCHRE_PALE, OCHRE, 2.5, rx=2)
    s.line(920 - (W - cw) / 2, 160, 920 - (W - cw) / 2, 186, SUB, 2, arrow=False)
    s.text(920, 214, f"親に残る {keep:,}（1/64）", 24, "end")
    s.text(40, 290, f"10,000 を要求 → 子は {small['entry']:,} を受け取る", 26, "start")
    s.text(40, 326, f"（上限 {small['limit']:,} より小さい）", 24, "start", "sub")
    s.save("evm_call_split.webp")


# 16. Reentrancy: A's frame is paused while B calls A again.
def reentrancy():
    s = Svg(960, 430, "リエントランシーの時間軸。A が B を CALL すると A のフレームは途中で止まり、その間に B が A を呼び返す。"
                      "2 回目の A は、1 回目の A がまだ更新していない storage を読む")
    s.text(200, 44, "時間 →", 24, "start", "sub")
    rows = [("A（1 回目）", 80), ("B", 190), ("A（2 回目）", 300)]
    for name, y in rows:
        s.text(30, y + 40, name, 26, "start")
    # A, 1st call: runs, pauses during the CALL, then finishes.
    s.rect(180, 80, 250, 60, BLUE_PALE, BLUE, 2)
    s.text(305, 120, "残高 10 を読む", 24)
    s.rect(430, 80, 330, 60, OCHRE_PALE, OCHRE, 2)
    s.text(595, 120, "10 を送る CALL の途中", 24)
    s.rect(760, 80, 180, 60, BLUE_PALE, BLUE, 2)
    s.text(850, 118, "残高に 0 を書く", 20)
    # B, then A again.
    s.rect(450, 190, 290, 60, GRAY_PALE, SUB, 2)
    s.text(595, 230, "A を呼び返す", 24)
    s.rect(470, 300, 260, 60, BLUE_PALE, BLUE, 2)
    s.text(600, 340, "また 10 を読み、送る", 24)
    s.cross(756, 330, 11)
    s.line(440, 140, 456, 186)
    s.line(500, 250, 516, 296)
    s.line(700, 300, 716, 254)
    s.line(735, 190, 751, 144)
    s.text(30, 410, "×: 0 になる前の残高で 2 回目の送金が起きる（並列ではなく、フレームの入れ子）", 20, "start", "sub")
    s.save("evm_reentrancy.webp")


def charts():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 16, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "font.family": ["Noto Sans CJK JP", "DejaVu Sans"],
    })
    comma = matplotlib.ticker.StrMethodFormatter("{x:,.0f}")

    def save(fig, name):
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)
        to_webp(buf, name)

    # Memory expansion: formula curve and measured points.
    fig, ax = plt.subplots(figsize=(8, 4.6))
    xs = list(range(32, 131072 + 1, 512))
    a = [(x + 31) // 32 for x in xs]
    ax.plot(xs, [3 * w for w in a], color=BLUE, lw=2, ls="--", label="直線の項 3a")
    ax.plot(xs, [3 * w + w * w // 512 for w in a], color=OCHRE, lw=2.5, label="合計 3a + a²/512")
    m = PROBE["memory"]
    ax.scatter([p["size"] for p in m], [p["measured"] for p in m], s=70, color=INK, zorder=3, label="実測（Anvil、Osaka）")
    for p in m[2:]:
        ax.annotate(f"{p['size']:,} バイト → {p['measured']:,}", (p["size"], p["measured"]), textcoords="offset points",
                    xytext=(-12, 10) if p["size"] > 100_000 else (12, -18), ha="right" if p["size"] > 100_000 else "left",
                    fontsize=15)
    ax.set_xlabel("memory の大きさ（バイト。a はその語数）")
    ax.set_ylabel("0 から広げるガス")
    ax.xaxis.set_major_formatter(comma)
    ax.yaxis.set_major_formatter(comma)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=15)
    save(fig, "evm_memory_gas.webp")

    # 63/64: gas at the entry of each depth, against g0 * (63/64)^d.
    g = PROBE["depth"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ds = list(range(len(g)))
    ax.plot(ds, [g[0] * (63 / 64) ** d for d in ds], color=OCHRE, lw=2.5, label="g₀ × (63/64)^深さ")
    ax.scatter(ds, g, s=24, color=BLUE, zorder=3, label="実測の gasleft()")
    ax.set_xlabel("呼び出しの深さ")
    ax.set_ylabel("入口のガス")
    ax.yaxis.set_major_formatter(comma)
    ax.set_ylim(0, 10_500_000)
    ax.text(1, 900_000, f"成功する最も深い呼び出しは down({PROBE['max_depth']})（残り {PROBE['max_depth_gas']:,}）"
            "\n深さの上限 1,024 には届かない", fontsize=15, color=SUB)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right", fontsize=15)
    save(fig, "evm_depth_gas.webp")

    # Gas of the three Dispatcher.set() transactions.
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    for y, d in enumerate(reversed(PROBE["dispatcher"])):
        parts = [(d["intrinsic"], GRAY_PALE, SUB), (d["sstore"], BLUE_PALE, BLUE), (d["log"], OCHRE_PALE, OCHRE),
                 (d["execution"] - d["sstore"] - d["log"], "#ffffff", SUB)]
        left = 0
        for w, f, e in parts:
            ax.barh(y, w, left=left, color=f, edgecolor=e, height=0.56)
            left += w
        if d["refund"]:  # returned after execution: drawn under the bar, ending at gasUsed
            ax.barh(y - 0.4, d["refund"], left=d["gas_used"], color=GREEN_PALE, edgecolor=GREEN, height=0.18)
            ax.text(d["gas_used"] + d["refund"] + 500, y - 0.4, f"払い戻し {d['refund']:,}", va="center", fontsize=14)
        ax.plot([d["floor"]] * 2, [y - 0.36, y + 0.36], color=RED, lw=2)
        label = f"gasUsed {d['gas_used']:,}" + (f" (= {left:,} − {d['refund']:,})" if d["refund"] else "")
        ax.text(left + 600, y, label, va="center", fontsize=15)
    ax.set_yticks(range(3), [f"set({d['x']})" for d in reversed(PROBE["dispatcher"])])
    ax.set_xlim(0, 58_000)
    ax.xaxis.set_major_formatter(comma)
    ax.set_xlabel("ガス")
    ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=f, edgecolor=e) for f, e in
               ((GRAY_PALE, SUB), (BLUE_PALE, BLUE), (OCHRE_PALE, OCHRE), ("#ffffff", SUB), (GREEN_PALE, GREEN))]
    handles.append(matplotlib.lines.Line2D([0], [0], color=RED, lw=2))
    ax.legend(handles, ["intrinsic gas", "SSTORE", "LOG2", "その他の命令", "払い戻し", "EIP-7623 の下限"],
              frameon=False, fontsize=14, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    save(fig, "evm_tx_gas.webp")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    overview()
    nodes()
    gas_fee()
    clients()
    pipeline()
    lifetimes()
    jumpdest()
    contexts()
    dispatcher()
    log_figure()
    failure_kinds()
    stack()
    data_areas()
    frame_exit()
    gas_ladder()
    call_split()
    reentrancy()
    charts()
