"""Generate the figures of the EVM note.

Run: python3 figures.py  -> images/*.svg
Hand-drawn SVGs use the standard library only. The four charts use matplotlib.
Numbers come from lab/output/*.json (written by lab/run.sh, lab/count_opcodes.sh
and lab/eip_graph.py), not from values typed into this file. The only typed
values are the mainnet activation dates, copied from go-ethereum's
params/chainspecs/mainnet.json (ddaa6957) and https://ethereum.org/ethereum-forks/,
and the Osaka gas constants of evm_gas_ladder.svg, copied from execution-specs
src/ethereum/forks/osaka/vm/gas.py (f9488c74).
"""

from datetime import date
from html import escape
import json
from pathlib import Path

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
GETH = json.loads((LAB / "geth_tables.json").read_text())
GRAPH = json.loads((LAB / "eip_graph.json").read_text())

# Mainnet activation (UTC). Block-number forks: ethereum.org; timestamp forks: mainnet.json.
FORK_DATES = {
    "Frontier": date(2015, 7, 30), "Homestead": date(2016, 3, 14),
    "Tangerine Whistle": date(2016, 10, 18), "Spurious Dragon": date(2016, 11, 22),
    "Byzantium": date(2017, 10, 16), "Constantinople": date(2019, 2, 28),
    "Istanbul": date(2019, 12, 8), "Berlin": date(2021, 4, 15), "London": date(2021, 8, 5),
    "Merge": date(2022, 9, 15), "Shanghai": date(2023, 4, 12), "Cancun": date(2024, 3, 13),
    "Prague": date(2025, 5, 7), "Osaka": date(2025, 12, 3),
}


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
        (IMG / name).write_text("\n".join(self.p + ["</svg>"]) + "\n")


# 1. Cover: where the EVM sits. Consensus picks the block, the EVM computes the state.
def concept():
    s = Svg(960, 540, "合意層がブロックを選び、実行層の EVM が前の状態に取引を適用して次の状態とレシートを作る。"
                      "EVM の中では呼び出しごとにフレームが積み重なる")
    # Consensus layer band with a chain of blocks.
    s.rect(30, 24, 900, 96, OCHRE_PALE, OCHRE)
    s.text(56, 82, "consensus layer", 26, "start")
    for i in range(4):
        x = 330 + i * 110
        s.rect(x, 46, 74, 52, "#ffffff", OCHRE, rx=6)
        if i:
            s.line(x - 36, 72, x - 2, 72, OCHRE, 3, arrow=False)
    s.text(906, 82, "picks one", 24, "end", "sub")
    # Execution layer.
    s.rect(30, 160, 900, 356, BLUE_PALE, BLUE)
    s.text(56, 202, "execution layer", 26, "start")
    s.line(480, 120, 480, 160, SUB, 2.5, dash="6 5")
    s.text(494, 146, "valid?", 24, "start", "sub")
    # State before, EVM, state after.
    s.rect(60, 286, 170, 120, "#ffffff", SUB, rx=10)
    s.text(145, 340, "state", 28)
    s.text(145, 378, "before", 24, cls="sub")
    s.rect(730, 286, 170, 120, "#ffffff", SUB, rx=10)
    s.text(815, 340, "state", 28)
    s.text(815, 378, "after", 24, cls="sub")
    s.text(815, 450, "+ receipt", 24, cls="sub")
    # The EVM with nested call frames.
    s.rect(300, 226, 360, 268, "#ffffff", BLUE, 3, rx=12)
    s.text(480, 266, "EVM", 30, weight="normal")
    for i, label in enumerate(["frame 1", "frame 2", "frame 3"]):
        x, y = 336 + i * 34, 292 + i * 58
        s.rect(x, y, 290 - i * 68, 74, BLUE_PALE if i else "#ffffff", BLUE, 2, rx=8)
        s.text(x + 18, y + 46, label, 24, "start")
    s.line(230, 346, 296, 346, SUB, 3)
    s.text(263, 330, "tx", 24, cls="sub")
    s.line(660, 346, 726, 346, SUB, 3)
    s.save("evm_concept.svg")


# 2. A transaction contains a message call, which contains the opcode loop.
def pipeline():
    s = Svg(960, 470, "取引の処理の中にメッセージ呼び出しがあり、その中で命令を 1 つずつ実行するループが回る。"
                      "CALL は同じループを持つ子のフレームを作る。前後に取引の検査と精算がある")
    s.rect(20, 20, 920, 430, GRAY_PALE, SUB, 2, rx=12)
    s.text(44, 62, "transaction (state transition)", 26, "start")
    # Before and after.
    s.rect(44, 100, 170, 310, "#ffffff", SUB, rx=10)
    for i, t in enumerate(["signature", "nonce", "intrinsic gas", "buy gas"]):
        s.text(129, 160 + i * 64, t, 24)
    s.rect(746, 100, 170, 310, "#ffffff", SUB, rx=10)
    for i, t in enumerate(["refund", "pay fee", "receipt"]):
        s.text(831, 180 + i * 72, t, 24)
    s.line(214, 255, 252, 255)
    s.line(708, 255, 742, 255)
    # Message call with the interpreter loop.
    s.rect(256, 100, 450, 310, BLUE_PALE, BLUE, 2.5, rx=12)
    s.text(276, 140, "message call (frame)", 24, "start")
    s.rect(280, 168, 400, 120, "#ffffff", BLUE, 2, rx=10)
    for cx, t in ((335, "read op"), (480, "charge gas"), (625, "execute")):
        s.text(cx, 222, t, 24)
    s.line(382, 214, 408, 214)
    s.line(553, 214, 580, 214)
    s.path("M 625 236 C 625 276, 335 276, 335 240", SUB, 2)
    s.text(480, 318, "until STOP / RETURN / REVERT / error", 24, cls="sub")
    s.rect(330, 340, 300, 54, "#ffffff", BLUE, 2, rx=8, dash="7 5")
    s.text(480, 376, "CALL → child frame", 24)
    s.save("evm_pipeline.svg")


# 3. Lifetimes of the data areas over one transaction.
def lifetimes():
    s = Svg(960, 520, "1 件の取引の時間軸。stack と memory はフレームの間だけ、transient storage は取引の終わりまで、"
                      "storage は次の取引にも残る")
    x0, x1 = 300, 860
    s.text(40, 52, "time →", 24, "start", "sub")
    s.line(x0, 70, 930, 70, SUB, 2)
    s.line(x0, 60, x0, 480, SUB, 1.5, arrow=False, dash="5 5")
    s.line(x1, 60, x1, 480, SUB, 1.5, arrow=False, dash="5 5")
    s.text(x0, 46, "tx start", 24, cls="sub")
    s.text(x1, 46, "tx end", 24, cls="sub")
    rows = [
        ("frame A", x0, x1, GRAY_PALE, SUB),
        ("frame B (CALL)", 470, 680, GRAY_PALE, SUB),
        ("stack, memory of A", x0, x1, BLUE_PALE, BLUE),
        ("stack, memory of B", 470, 680, BLUE_PALE, BLUE),
        ("transient storage", 380, x1, OCHRE_PALE, OCHRE),
        ("storage", 240, 940, GREEN_PALE, GREEN),
    ]
    for i, (label, a, b, face, edge) in enumerate(rows):
        y = 100 + i * 64
        s.text(30, y + 33, label, 24, "start")
        s.rect(a, y + 6, b - a, 38, face, edge, 2, rx=6)
    s.text(392, 397, "TSTORE", 24, "start", "sub")
    s.cross(x1, 389, 11)
    s.text(924, 461, "next tx", 24, "end", "sub")
    s.save("evm_lifetimes.svg")


# 4. Bytes of code: the 0x5b inside PUSH1's immediate is data, not a jump destination.
def jumpdest():
    s = Svg(960, 400, "コード 60 5b 5b 00 の各バイト。PC 1 の 5b は PUSH1 の即値で、飛び先にできない。PC 2 の 5b は JUMPDEST で飛べる")
    bytes_ = [("60", "PUSH1"), ("5b", "data"), ("5b", "JUMPDEST"), ("00", "STOP")]
    for i, (b, role) in enumerate(bytes_):
        x = 120 + i * 190
        face = OCHRE_PALE if role == "data" else BLUE_PALE
        edge = OCHRE if role == "data" else BLUE
        s.text(x + 80, 60, f"PC {i}", 24, cls="sub")
        s.rect(x, 80, 160, 90, face, edge, 2.5, rx=8)
        s.text(x + 80, 140, b, 34, cls="mono")
        s.text(x + 80, 214, role, 24)
    s.path("M 130 240 L 130 254 L 470 254 L 470 240", SUB, 2, arrow=False)
    s.text(300, 288, "one instruction: PUSH1 0x5b", 24, cls="sub")
    s.text(310, 352, "JUMP to 1", 26)
    s.cross(420, 344)
    s.text(650, 352, "JUMP to 2", 26)
    s.p.append(f'<path d="M 748 344 l 10 10 l 20 -22" fill="none" stroke="{GREEN}" stroke-width="5" stroke-linecap="round"/>')
    s.save("evm_jumpdest.svg")


# 5. CALL / DELEGATECALL / STATICCALL measured with lab/Context.sol.
def contexts():
    rows = {r["mode"]: r for r in PROBE["context"]}
    s = Svg(960, 600, "同じ Caller から同じ Target を 3 通りに呼んだ実測。CALL は Target の storage、DELEGATECALL は Caller の "
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
            s.text(x + 90, y + 106, "code", 24)
            # storage box
            written = owner == name
            refused = owner is None and name == "Target"
            f, e = (OCHRE_PALE, OCHRE) if written else (RED_PALE, RED) if refused else ("#ffffff", SUB)
            s.rect(x + 156, y + 52, 100, 92, f, e, 2.5 if refused else 2, rx=6)
            s.text(x + 206, y + 106, "slot 0", 24)
        s.line(x + 148, 260, x + 148, 296, SUB, 3)
        if owner is None:
            s.text(x + 148, 510, "SSTORE fails", 24)
            s.text(x + 148, 548, "ok = 0", 24, cls="sub")
        else:
            who = {"EOA": "EOA", "Caller": "Caller", "Target": "Target"}[r["sender"]]
            s.text(x + 148, 510, f"msg.sender = {who}", 24)
            s.text(x + 148, 548, f"msg.value = {r['value']} wei", 24, cls="sub")
    s.save("evm_call_context.svg")


# 6. Precompiled contracts by the fork that added them (go-ethereum contracts.go).
def precompiles():
    pre = GETH["precompiles"]
    names = {
        "ecrecover": "ecrecover", "sha256hash": "sha256", "ripemd160hash": "ripemd160", "dataCopy": "identity",
        "bigModExp": "modexp", "bn256AddByzantium": "bn254 add", "bn256AddIstanbul": "bn254 add",
        "bn256ScalarMulByzantium": "bn254 mul", "bn256ScalarMulIstanbul": "bn254 mul",
        "bn256PairingByzantium": "bn254 pair", "bn256PairingIstanbul": "bn254 pair", "blake2F": "blake2f",
        "kzgPointEvaluation": "KZG point", "bls12381G1Add": "G1 add", "bls12381G1MultiExp": "G1 MSM",
        "bls12381G2Add": "G2 add", "bls12381G2MultiExp": "G2 MSM", "bls12381Pairing": "pairing",
        "bls12381MapG1": "map G1", "bls12381MapG2": "map G2", "p256Verify": "p256verify",
    }
    seen, columns = set(), []
    for fork in pre:
        new = sorted((a for a in fork["contracts"] if a not in seen), key=lambda a: int(a, 16))
        if new:
            columns.append((fork["fork"], [(a, names[fork["contracts"][a]]) for a in new]))
            seen.update(new)
    label = {"Homestead": "Frontier", "Prague": "Prague"}
    s = Svg(960, 620, "プリコンパイル 18 個を導入したフォークごとに並べた図。Frontier の 4 個、Byzantium の 4 個、Istanbul の 1 個、"
                      "Cancun の 1 個、Prague の BLS12-381 の 7 個、Osaka の P-256 検証")
    cw = 156
    for i, (fork, items) in enumerate(columns):
        x = 12 + i * cw
        s.text(x + cw / 2 - 4, 44, label.get(fork, fork), 24, weight="normal")
        newest = i == len(columns) - 1
        for j, (addr, name) in enumerate(items):
            y = 66 + j * 76
            s.rect(x, y, cw - 10, 68, BLUE_PALE if newest else "#ffffff", BLUE if newest else SUB, 2, rx=6)
            a = "0x" + addr[2:].rjust(2, "0")
            s.text(x + (cw - 10) / 2, y + 28, a, 24, cls="mono")
            s.text(x + (cw - 10) / 2, y + 58, name, 24)
    s.text(4 * cw + 12 + cw / 2 - 4, 610, "BLS12-381", 24, cls="sub")
    s.save("evm_precompiles.svg")


# 7. EIP / ERC requires graph from lab/output/eip_graph.json.
def eip_graph():
    nodes = {n["id"]: n for n in GRAPH["nodes"]}
    short = {
        "ERC-721": "NFT", "ERC-1155": "multi token", "ERC-2612": "permit", "ERC-1271": "contract sig",
        "ERC-4337": "AA bundler", "ERC-7562": "AA rules", "ERC-165": "interface ID", "ERC-20": "token",
        "ERC-191": "signed data", "EIP-712": "typed data", "EIP-214": "STATICCALL",
        "EIP-155": "chain ID", "EIP-7702": "set code",
    }
    pos = {
        "ERC-721": (120, 100), "ERC-1155": (120, 196), "ERC-2612": (120, 300), "ERC-1271": (120, 400),
        "ERC-4337": (120, 500), "ERC-7562": (120, 640),
        "ERC-165": (380, 148), "ERC-20": (380, 252), "ERC-191": (380, 352), "EIP-712": (380, 452),
        "EIP-214": (790, 148), "EIP-155": (790, 452), "EIP-7702": (790, 560),
    }
    cluster = [e["to"] for e in GRAPH["edges"] if e["from"] == "EIP-7702"]
    face = {"ERC": (OCHRE_PALE, OCHRE), "Interface": (GREEN_PALE, GREEN), "Core": (BLUE_PALE, BLUE)}
    BW, BH = 200, 76
    s = Svg(960, 850, "EIP と ERC の requires の関係。左は ERC と Interface でフォークが要らない側、右は Core でフォークが要る側。"
                      "ERC-165 は EIP-214、EIP-712 は EIP-155、ERC-4337 は EIP-7702 を requires に挙げ、境界をまたぐ。"
                      "ERC-7562 と ERC-4337 は requires ではなく本文の参照")
    s.rect(560, 60, 390, 770, BLUE_PALE, BLUE, 1.5, rx=12)
    s.text(755, 40, "Core: needs a hard fork", 24)
    s.text(270, 40, "ERC / Interface: no fork", 24)
    s.line(540, 60, 540, 830, SUB, 2, arrow=False, dash="8 6")

    def box(nid):
        x, y = pos[nid]
        n = nodes[nid]
        f, e = face[n["category"]]
        dash = None if n["status"] == "Final" else "8 5"
        s.rect(x - BW / 2, y - BH / 2, BW, BH, f, e, 2.5, rx=8, dash=dash)
        s.text(x, y - 6, nid, 26, weight="normal")
        s.text(x, y + 26, short[nid], 24, cls="sub")

    def edge(a, b, dash=None, color=SUB):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        if x1 == x2:  # vertical
            sy = 1 if y2 > y1 else -1
            s.line(x1, y1 + sy * BH / 2, x2, y2 - sy * (BH / 2 + 4), color, 2.5, dash=dash)
            return
        sx = 1 if x2 > x1 else -1
        s.line(x1 + sx * BW / 2, y1, x2 - sx * (BW / 2 + 4), y2, color, 2.5, dash=dash)

    for e in GRAPH["edges"]:
        if e["from"] == "EIP-7702" or e["from"] not in pos or e["to"] not in pos:
            continue
        if (e["from"], e["to"]) == ("EIP-712", "ERC-191"):
            edge("EIP-712", "ERC-191")
            continue
        edge(e["from"], e["to"])
    # Relations that are not in `requires`.
    edge("ERC-7562", "ERC-4337", dash="7 6")
    edge("ERC-1271", "EIP-712", dash="7 6")
    for nid in pos:
        box(nid)
    # EIP-7702 requires nine Core EIPs.
    s.rect(620, 640, 340 - 20, 170, "#ffffff", BLUE, 2, rx=8)
    nums = [c.split("-")[1] for c in cluster]
    s.text(780, 674, f"{len(nums)} Core EIPs", 24, weight="normal")
    for r in range(0, len(nums), 3):
        s.text(780, 712 + r // 3 * 34, ", ".join(nums[r:r + 3]), 24, cls="mono")
    s.line(790, 560 + BH / 2, 790, 636, SUB, 2.5)
    # Legend.
    s.line(250, 730, 300, 730, SUB, 2.5)
    s.text(312, 738, "requires", 24, "start")
    s.line(250, 770, 300, 770, SUB, 2.5, dash="7 6")
    s.text(312, 778, "text only", 24, "start")
    s.rect(250, 796, 50, 34, OCHRE_PALE, OCHRE, 2, rx=6, dash="8 5")
    s.text(312, 822, "status Review", 24, "start")
    # Category colors.
    for i, (cat, (f, e)) in enumerate((("ERC", face["ERC"]), ("Interface", face["Interface"]), ("Core", face["Core"]))):
        y = 710 + i * 42
        s.rect(20, y, 50, 30, f, e, 2, rx=6)
        s.text(82, y + 25, cat, 24, "start")
    s.save("evm_eip_graph.svg")


# 8. Calldata of set(42) and the dispatcher that reads it.
def dispatcher():
    d = next(x for x in PROBE["dispatcher"] if x["x"] == 42)
    sel, arg = d["calldata"][:8], d["calldata"][8:]
    head = {pc: op for pc, op, _ in PROBE["trace_head"]}
    jump_pc = [pc for pc, op, _ in PROBE["trace_head"]][-1]
    s = Svg(960, 560, f"set(42) の calldata は先頭 4 バイトの selector {sel} と 32 バイトの引数。"
                      "CALLDATALOAD と SHR で selector を取り出し、EQ と JUMPI で関数ごとの位置に分岐する。一致しなければ REVERT")
    # calldata strip
    s.text(30, 44, "calldata (36 bytes)", 24, "start", "sub")
    s.rect(30, 60, 220, 70, BLUE_PALE, BLUE, 2.5, rx=6)
    s.text(140, 106, sel, 28, cls="mono")
    s.rect(250, 60, 680, 70, OCHRE_PALE, OCHRE, 2.5, rx=6)
    s.text(590, 106, "00 … 00 2a  (42)", 28, cls="mono")
    s.text(140, 160, "4 bytes", 24, cls="sub")
    s.text(590, 160, "32 bytes", 24, cls="sub")
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
    s.text(300, 350, "no", 22, cls="sub")
    s.rect(320, 330, 250, 64, "#ffffff", SUB, 2, rx=8)
    s.text(445, 371, f"EQ {sel}", 24, cls="mono")
    s.text(445, 426, "set(uint256)", 24, cls="sub")
    s.line(574, 362, 606, 362)
    s.text(590, 350, "yes", 22, cls="sub")
    s.rect(610, 330, 320, 64, BLUE_PALE, BLUE, 2.5, rx=8)
    s.text(770, 371, f"JUMPI → pc {jump_pc}", 24, cls="mono")
    s.line(155, 268, 155, 326)
    s.text(30, 470, "neither → REVERT", 24, "start")
    s.line(770, 398, 770, 446)
    s.rect(610, 450, 320, 90, "#ffffff", BLUE, 2, rx=8)
    s.text(770, 486, "SSTORE, LOG2, STOP", 24, cls="mono")
    s.text(770, 524, "body of set()", 24, cls="sub")
    s.text(30, 514, "The EVM never sees", 24, "start", "sub")
    s.text(30, 548, "the name \"set\".", 24, "start", "sub")
    assert head.get(26) == "CALLDATALOAD"
    s.save("evm_dispatcher.svg")


# 9. What LOG2 writes into the receipt.
def log_figure():
    d = next(x for x in PROBE["dispatcher"] if x["x"] == 42)
    s = Svg(960, 470, f"LOG2 が書く内容。topic0 はイベントの署名のハッシュ、topic1 は indexed の sender、data は値。"
                      f"bloom にはアドレスと topic だけが入る。この LOG2 は {d['log']} ガス")
    s.text(30, 50, f"LOG2 in set(42): {d['log']} gas", 26, "start", weight="normal")
    s.text(30, 90, "= 375 + 2 × 375 + 8 × 32 bytes", 24, "start", "sub")
    parts = [("address", "Dispatcher", BLUE_PALE, BLUE), ("topic0", "keccak(\"Changed(...)\")", BLUE_PALE, BLUE),
             ("topic1", "sender (indexed)", BLUE_PALE, BLUE), ("data", "value = 42", OCHRE_PALE, OCHRE)]
    for i, (k, v, f, e) in enumerate(parts):
        y = 120 + i * 78
        s.rect(30, y, 560, 64, f, e, 2, rx=6)
        s.text(50, y + 42, k, 24, "start", weight="normal")
        s.text(190, y + 42, v, 24, "start")
    s.rect(700, 140, 230, 200, GRAY_PALE, SUB, 2, rx=8)
    s.text(815, 220, "bloom", 26)
    s.text(815, 258, "2048 bits", 24, cls="sub")
    for i in range(3):
        y = 152 + i * 78
        s.line(594, y, 696, 200 + i * 30, SUB, 2)
    s.text(815, 400, "data is not in the bloom", 24, cls="sub")
    s.save("evm_log.svg")


# 10. Where a transaction can fail: rejected by the checks, or included with status 0.
def failure_kinds():
    s = Svg(960, 400, "取引の失敗は 2 種類ある。署名・nonce・前払いの検査で弾かれた取引はブロックに入らない。"
                      "コードの実行中に失敗した取引はブロックに入り、status 0 になり、nonce が進み、手数料を払う")
    s.text(40, 112, "tx", 26, "start")
    s.line(76, 104, 136, 104)
    s.rect(140, 60, 250, 90, GRAY_PALE, SUB, 2)
    s.text(265, 98, "checks", 26)
    s.text(265, 132, "sig, nonce, prepay", 24, cls="sub")
    s.line(390, 104, 436, 104)
    s.rect(440, 60, 250, 90, BLUE_PALE, BLUE, 2.5)
    s.text(565, 98, "code runs", 26)
    s.text(565, 132, "EVM frames", 24, cls="sub")
    s.line(690, 104, 756, 104)
    s.rect(760, 40, 180, 340, "#ffffff", SUB, 2, rx=10)
    s.text(850, 80, "block", 26)
    s.text(850, 124, "status 1", 24)
    # Rejected by the outer checks.
    s.line(265, 150, 265, 212, SUB, 2.5, dash="6 5")
    s.cross(176, 246, 11)
    s.text(280, 254, "rejected", 26)
    s.text(265, 296, "not in a block", 24, cls="sub")
    s.text(265, 332, "nonce, fee unchanged", 24, cls="sub")
    # Failed while running code.
    s.line(565, 150, 565, 216)
    s.rect(440, 220, 250, 90, OCHRE_PALE, OCHRE, 2.5)
    s.text(565, 258, "error / REVERT", 26)
    s.text(565, 292, "state undone", 24, cls="sub")
    s.line(690, 265, 756, 265)
    s.text(850, 262, "status 0", 24)
    s.text(850, 302, "nonce + 1", 24, cls="sub")
    s.text(850, 338, "fee paid", 24, cls="sub")
    s.save("evm_failure_kinds.svg")


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
    s.text(632, 180, "pops 2, 3", 24, cls="sub")
    s.text(480, 360, "1 slot = one 256-bit word, up to 1,024 slots", 24, cls="sub")
    s.save("evm_stack.svg")


# 12. Which data areas belong to the frame and which to the account.
def data_areas():
    s = Svg(960, 500, "EVM のデータ領域。stack・memory・calldata・returndata はフレームに属し、"
                      "transient storage・storage・code はアカウントに属する。それぞれの寿命")
    groups = [
        (20, "belongs to the frame", BLUE_PALE, BLUE, [
            ("stack", "to frame end, 256-bit words"), ("memory", "to frame end, bytes"),
            ("calldata", "to frame end, read only"), ("returndata", "until the next child call")]),
        (500, "belongs to the account", OCHRE_PALE, OCHRE, [
            ("transient storage", "until the tx ends"), ("storage", "until overwritten"),
            ("code", "fixed after deploy, read only")]),
    ]
    for x, title, face, edge, items in groups:
        s.rect(x, 20, 440, 460, face, edge, 2, rx=12)
        s.text(x + 24, 62, title, 26, "start")
        for j, (name, life) in enumerate(items):
            y = 84 + j * 96
            s.rect(x + 20, y, 400, 84, "#ffffff", edge, 2, rx=8)
            s.text(x + 40, y + 36, name, 26, "start", "mono")
            s.text(x + 40, y + 70, life, 24, "start", "sub")
    s.save("evm_data_areas.svg")


# 13. The four ways a frame ends and what happens to the gas given to it.
def frame_exit():
    s = Svg(960, 560, "フレームの終わり方 4 通り。STOP・RETURN と REVERT は残りのガスを親に返し、例外は渡したガスを全て失い、"
                      "子を始められない時はガスが親に残る。状態の変更を残すのは STOP・RETURN だけ")
    s.text(30, 52, "frame ends with", 24, "start", "sub")
    s.text(440, 52, "gas given to the child", 24, cls="sub")
    s.text(700, 52, "state", 24, cls="sub")
    s.text(880, 52, "returns", 24, cls="sub")
    rows = [
        ("STOP / RETURN", "returned", "kept", "1 + data"),
        ("REVERT", "returned", "undone", "0 + data"),
        ("exception", "lost", "undone", "0"),
        ("cannot start", "stays", "not run", "0"),
    ]
    for i, (name, gas, state, ret) in enumerate(rows):
        y = 80 + i * 104
        s.text(30, y + 42, name, 26, "start", "mono" if name.isupper() or "/" in name else "")
        if gas == "returned":
            s.rect(290, y + 8, 180, 52, GRAY_PALE, SUB, 2, rx=4)
            s.text(380, y + 42, "used", 24)
            s.rect(470, y + 8, 120, 52, BLUE_PALE, BLUE, 2, rx=4)
            s.text(530, y + 42, "back", 24)
        elif gas == "lost":
            s.rect(290, y + 8, 300, 52, OCHRE_PALE, OCHRE, 2.5, rx=4)
            s.text(440, y + 42, "all consumed", 24)
        else:
            s.rect(290, y + 8, 300, 52, "#ffffff", SUB, 2, rx=4, dash="7 5")
            s.text(440, y + 42, "kept by the parent", 24, cls="sub")
        s.text(700, y + 42, state, 26)
        s.text(880, y + 42, ret, 26, cls="mono")
    s.text(30, 530, "\"kept\" changes are still undone if the parent fails later", 24, "start", "sub")
    s.save("evm_frame_exit.svg")


# 14. Gas of representative opcodes on a log scale.
#     Osaka values from execution-specs vm/gas.py (f9488c74), the same numbers as the table in the note.
OSAKA_GAS = [
    ("ADD, LT, AND", 3, "calc"), ("MUL, DIV", 5, "calc"), ("JUMPI", 10, "calc"),
    ("TLOAD, warm SLOAD", 100, "state"), ("LOG0", 375, "state"), ("cold SLOAD", 2100, "state"),
    ("cold CALL target", 2600, "state"), ("SSTORE 0 → non-zero", 20000, "state"), ("CREATE", 32000, "state"),
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
    s.text(374, 48, "computation", 24, "start")
    s.rect(560, 26, 34, 26, OCHRE_PALE, OCHRE, 2, rx=3)
    s.text(604, 48, "state, disk, receipt", 24, "start")
    s.text(x0 + span / 2, 620, "gas (log scale)", 24, cls="sub")
    s.save("evm_gas_ladder.svg")


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
    s.text(40, 50, f"g = {allr['before']:,} (before CALL) − {costs:,} (CALL costs) = {g:,}", 24, "start", "sub")
    W = 880
    cw = W * allr["entry"] / g
    s.rect(40, 80, cw, 76, BLUE_PALE, BLUE, 2.5, rx=4)
    s.text(40 + cw / 2, 128, f"child gets {allr['entry']:,} (63/64)", 26)
    s.rect(40 + cw, 80, W - cw, 76, OCHRE_PALE, OCHRE, 2.5, rx=2)
    s.line(920 - (W - cw) / 2, 160, 920 - (W - cw) / 2, 186, SUB, 2, arrow=False)
    s.text(920, 214, f"parent keeps {keep:,} (1/64)", 24, "end")
    s.text(40, 290, f"request 10,000 → child gets {small['entry']:,}", 26, "start")
    s.text(40, 326, f"(below the limit {small['limit']:,})", 24, "start", "sub")
    s.save("evm_call_split.svg")


# 16. Reentrancy: A's frame is paused while B calls A again.
def reentrancy():
    s = Svg(960, 430, "再入の時間軸。A が B を CALL すると A のフレームは途中で止まり、その間に B が A を呼び返す。"
                      "2 回目の A は、1 回目の A がまだ更新していない storage を読む")
    s.text(200, 44, "time →", 24, "start", "sub")
    rows = [("A (1st)", 80), ("B", 190), ("A (2nd)", 300)]
    for name, y in rows:
        s.text(30, y + 40, name, 26, "start")
    # A, 1st call: runs, pauses during the CALL, then finishes.
    s.rect(180, 80, 250, 60, BLUE_PALE, BLUE, 2)
    s.text(305, 120, "reads value 10", 24)
    s.rect(430, 80, 330, 60, OCHRE_PALE, OCHRE, 2)
    s.text(595, 120, "paused in CALL", 24)
    s.rect(760, 80, 180, 60, BLUE_PALE, BLUE, 2)
    s.text(850, 120, "writes 0", 24)
    # B, then A again.
    s.rect(450, 190, 290, 60, GRAY_PALE, SUB, 2)
    s.text(595, 230, "calls A back", 24)
    s.rect(490, 300, 220, 60, BLUE_PALE, BLUE, 2)
    s.text(600, 340, "reads 10 again", 24)
    s.cross(740, 330, 11)
    s.line(440, 140, 456, 186)
    s.line(500, 250, 516, 296)
    s.line(700, 300, 716, 254)
    s.line(735, 190, 751, 144)
    s.text(30, 410, "one thread: nested frames, not parallel ones", 24, "start", "sub")
    s.save("evm_reentrancy.svg")


# 17. EIP-1 types and categories; only Core needs a hard fork.
def eip_types():
    s = Svg(960, 560, "EIP-1 の種類と分類。Standards Track の中に Core・Networking・Interface・ERC があり、"
                      "他に Meta と Informational がある。原則としてハードフォークが要るのは Core だけ")
    s.rect(380, 20, 200, 64, "#ffffff", SUB, 2.5)
    s.text(480, 62, "EIP", 28)
    s.line(480, 84, 480, 112, SUB, 2.5, arrow=False)
    s.line(360, 112, 945, 112, SUB, 2.5, arrow=False)
    s.line(360, 112, 360, 136)
    s.line(830, 112, 830, 136)
    s.line(945, 112, 945, 415, SUB, 2.5, arrow=False)
    s.line(945, 415, 934, 415)
    s.rect(20, 140, 680, 400, GRAY_PALE, SUB, 2, rx=12)
    s.text(40, 178, "Standards Track", 26, "start")
    cats = [
        (36, 200, "Core", ["opcodes, gas, tx types", "hard fork (as a rule)"], True),
        (368, 200, "Networking", ["devp2p", "no hard fork"], False),
        (36, 370, "Interface", ["ABI, method names", "no hard fork"], False),
        (368, 370, "ERC", ["tokens, wallets, signing", "no hard fork"], False),
    ]
    for x, y, name, lines, core in cats:
        s.rect(x, y, 316, 150, BLUE_PALE if core else "#ffffff", BLUE if core else SUB, 2.5 if core else 2, rx=8)
        s.text(x + 20, y + 42, name, 26, "start")
        s.text(x + 20, y + 84, lines[0], 24, "start", "sub")
        s.text(x + 20, y + 122, lines[1], 24, "start", "" if core else "sub")
    for y, h, name, sub in ((140, 180, "Meta", ["process,", "fork lists", "no hard fork"]),
                            (340, 150, "Informational", ["guidelines", "no hard fork"])):
        s.rect(720, y, 210, h, "#ffffff", SUB, 2, rx=8)
        s.text(740, y + 42, name, 26, "start")
        for k, t in enumerate(sub):
            s.text(740, y + 84 + k * 34, t, 24, "start", "sub")
    s.save("evm_eip_types.svg")


def charts():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    plt.rcParams.update({
        "font.size": 16, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "evm",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "font.family": "DejaVu Sans",
    })
    comma = matplotlib.ticker.StrMethodFormatter("{x:,.0f}")

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(IMG / name, metadata={"Date": None}, bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)

    # Memory expansion: formula curve and measured points.
    fig, ax = plt.subplots(figsize=(8, 4.6))
    xs = list(range(32, 131072 + 1, 512))
    a = [(x + 31) // 32 for x in xs]
    ax.plot(xs, [3 * w for w in a], color=BLUE, lw=2, ls="--", label="linear part 3a")
    ax.plot(xs, [3 * w + w * w // 512 for w in a], color=OCHRE, lw=2.5, label="total 3a + a²/512")
    m = PROBE["memory"]
    ax.scatter([p["size"] for p in m], [p["measured"] for p in m], s=70, color=INK, zorder=3, label="measured (Anvil, Osaka)")
    for p in m[2:]:
        ax.annotate(f"{p['size']:,} B → {p['measured']:,}", (p["size"], p["measured"]), textcoords="offset points",
                    xytext=(-12, 10), ha="right", fontsize=15)
    ax.set_xlabel("memory size in bytes (a = size / 32 words)")
    ax.set_ylabel("gas to expand from 0")
    ax.xaxis.set_major_formatter(comma)
    ax.yaxis.set_major_formatter(comma)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=15)
    save(fig, "evm_memory_gas.svg")

    # Opcodes per fork on a date axis, and how many existing opcodes changed.
    rows = [r for r in GETH["instruction_sets"] if r["fork"] in FORK_DATES]
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(8.4, 6.4), sharex=True, gridspec_kw={"height_ratios": [3, 1.4]})
    ds = [FORK_DATES[r["fork"]] for r in rows]
    ax.step(ds + [date(2026, 11, 10)], [r["defined"] for r in rows] + [rows[-1]["defined"]], where="post", color=BLUE, lw=2.5)
    notes = {"Homestead": "DELEGATECALL", "Byzantium": "REVERT, STATICCALL", "Constantinople": "CREATE2, SHL",
             "Istanbul": "CHAINID", "London": "BASEFEE", "Shanghai": "PUSH0", "Cancun": "TLOAD, MCOPY", "Osaka": "CLZ"}
    for r, d in zip(rows, ds):
        if r["added"]:
            ax.plot(d, r["defined"], "o", color=BLUE, ms=6)
        if r["fork"] in notes:
            # Label offsets in points: below-right for early forks, above-left for later ones.
            dx, dy = {"London": (-8, 8), "Shanghai": (-8, 30), "Cancun": (-8, 8), "Osaka": (-8, 30)}.get(r["fork"], (6, -18))
            ax.annotate(f"{r['fork']}: {notes[r['fork']]}", (d, r["defined"]), textcoords="offset points",
                        xytext=(dx, dy), ha="right" if dx < 0 else "left", fontsize=14)
    ams = next(r for r in GETH["instruction_sets"] if r["fork"] == "Amsterdam")
    ax.text(date(2015, 9, 1), 155, f"Amsterdam in geth: {ams['defined']} (date TBD)", fontsize=14, color=SUB)
    ax.set_ylabel("opcodes")
    ax.set_ylim(125, 158)
    ax.spines[["top", "right"]].set_visible(False)
    bx.bar(ds, [len(r["changed"]) for r in rows], width=90, color=OCHRE)
    for r, d in zip(rows, ds):
        if len(r["changed"]) >= 4:
            bx.annotate(r["fork"], (d, len(r["changed"])), textcoords="offset points", xytext=(6, -4),
                        fontsize=14, va="top")
    bx.set_ylabel("changed")
    bx.set_ylim(0, 13)
    bx.spines[["top", "right"]].set_visible(False)
    bx.xaxis.set_major_locator(mdates.YearLocator(2))
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    save(fig, "evm_opcodes_by_fork.svg")

    # 63/64: gas at the entry of each depth, against g0 * (63/64)^d.
    g = PROBE["depth"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ds = list(range(len(g)))
    ax.plot(ds, [g[0] * (63 / 64) ** d for d in ds], color=OCHRE, lw=2.5, label="g₀ × (63/64)^depth")
    ax.scatter(ds, g, s=24, color=BLUE, zorder=3, label="measured gasleft()")
    ax.set_xlabel("call depth")
    ax.set_ylabel("gas at the entry")
    ax.yaxis.set_major_formatter(comma)
    ax.set_ylim(0, 10_500_000)
    ax.text(1, 900_000, f"down({PROBE['max_depth']}) is the deepest that succeeds (gasleft {PROBE['max_depth_gas']:,});"
            "\nthe depth limit 1024 is never reached", fontsize=15, color=SUB)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right", fontsize=15)
    save(fig, "evm_depth_gas.svg")

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
            ax.text(d["gas_used"] + d["refund"] + 500, y - 0.4, f"refund {d['refund']:,}", va="center", fontsize=14)
        ax.plot([d["floor"]] * 2, [y - 0.36, y + 0.36], color=RED, lw=2)
        label = f"gasUsed {d['gas_used']:,}" + (f" (= {left:,} − {d['refund']:,})" if d["refund"] else "")
        ax.text(left + 600, y, label, va="center", fontsize=15)
    ax.set_yticks(range(3), [f"set({d['x']})" for d in reversed(PROBE["dispatcher"])])
    ax.set_xlim(0, 58_000)
    ax.xaxis.set_major_formatter(comma)
    ax.set_xlabel("gas")
    ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=f, edgecolor=e) for f, e in
               ((GRAY_PALE, SUB), (BLUE_PALE, BLUE), (OCHRE_PALE, OCHRE), ("#ffffff", SUB), (GREEN_PALE, GREEN))]
    handles.append(matplotlib.lines.Line2D([0], [0], color=RED, lw=2))
    ax.legend(handles, ["intrinsic", "SSTORE", "LOG2", "other opcodes", "refund", "EIP-7623 floor"],
              frameon=False, fontsize=14, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    save(fig, "evm_tx_gas.svg")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    concept()
    pipeline()
    lifetimes()
    jumpdest()
    contexts()
    precompiles()
    eip_graph()
    dispatcher()
    log_figure()
    failure_kinds()
    stack()
    data_areas()
    frame_exit()
    gas_ladder()
    call_split()
    reentrancy()
    eip_types()
    charts()
