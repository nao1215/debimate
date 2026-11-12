"""Generate the figures of the Ethereum hard fork note (standard library + Pillow).

Each figure is built as SVG text here, rendered with headless Chrome at 2x and
saved as WebP (Pillow). Only the WebP files are kept in images/.
opcodes_figure(), transfer_figure() and evmversion_figure() read
lab/output/summary.txt (written by lab/run.sh).

Run: python3 content/notes/blockchain-systems/ethereum-hard-forks/figures.py
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED, RED_PALE = "#e15759", "#fbe3e3"
GRAY_PALE = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
W, H = 960, 540


def render(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    (HERE / "images").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f"<style>html,body{{margin:0}} text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>",
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, rx=6, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=SUB, sw=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def raw(self, s):
        self.p.append(s)

    def save(self, name):
        render("\n".join(self.p + ["</svg>"]) + "\n", self.w, self.h, name)


def concept_figure():
    """The same bytecode costs and means different things on each side of a fork boundary."""
    left, seg = 200, 240
    forks = ["Istanbul", "Berlin", "Cancun"]
    # Row values per segment; True marks a value that changed at that fork.
    rows = [
        ("SLOAD", [("800", False), ("2100 / 100", True), ("2100 / 100", False)]),
        ("SELFDESTRUCT", [("コードを消す", False), ("コードを消す", False), ("コードを残す", True)]),
    ]
    s = Svg(W, H, "同じバイトコードのまま、フォークの境目で SLOAD のガスと SELFDESTRUCT の意味が変わる。"
                  "更新しなかったノードは古い規則で別の列を伸ばす")
    for i, name in enumerate(forks):
        s.text(left + seg * i + seg / 2, 52, name, 26)
    for i in range(1, len(forks)):
        x = left + seg * i
        s.line(x, 70, x, 515, SUB, 2, "8 6")

    s.text(16, 118, "ブロックの列", anchor="start", cls="sub")
    s.text(16, 339, "コード", anchor="start", cls="sub")
    for r, (label, _) in enumerate(rows):
        s.text(16, 421 + r * 70, label, anchor="start", cls="sub")

    xs = [left + 14 + 58 * k for k in range(12)]
    s.line(xs[0], 110, xs[-1] + 40, 110, BLUE, 3)
    for x in xs:
        s.rect(x, 90, 40, 40, BLUE_PALE, BLUE)

    # Nodes that kept the old rules at the Berlin boundary extend their own chain.
    bx = [left + seg + 30 + 58 * k for k in range(4)]
    split = xs[3] + 40
    s.raw(f'<path d="M{split} 110 L{bx[0]} 215 L{bx[-1] + 40} 215" fill="none" stroke="{OCHRE}" stroke-width="3"/>')
    for x in bx:
        s.rect(x, 195, 40, 40, OCHRE_PALE, OCHRE, 2, 6, "5 4")
    s.text(bx[-1] + 56, 210, "仮に更新しなかった", anchor="start", size=22, cls="sub")
    s.text(bx[-1] + 56, 240, "ノードの列", anchor="start", size=22, cls="sub")

    s.rect(left + 8, 310, seg * 3 - 16, 46, GRAY_PALE, SUB, 1.5)
    s.text(left + seg * 1.5, 341, "デプロイ済みの同じバイトコード")

    for r, (_, cells) in enumerate(rows):
        y = 390 + r * 70
        for i, (value, changed) in enumerate(cells):
            x = left + seg * i + 12
            if changed:
                s.rect(x, y, seg - 24, 50, BLUE_PALE, BLUE, 2.5)
            else:
                s.rect(x, y, seg - 24, 50, "#ffffff", SUB, 1.2)
            s.text(x + (seg - 24) / 2, y + 33, value)
    s.save("ethereum-hard-forks_concept.webp")


def rules_figure():
    """Soft fork narrows the valid set, hard fork adds blocks the old rules reject."""
    s = Svg(W, 500, "ソフトフォークは有効なブロックの範囲を狭め、古いノードも新しいブロックを受け入れる。"
                    "ハードフォークは古い規則では無効なブロックを有効にするので、古いノードは新しいブロックを拒む")
    for k, (title, hard) in enumerate([("ソフトフォーク", False), ("ハードフォーク", True)]):
        x0 = 30 + k * 470
        s.text(x0 + 210, 44, title, 28)
        # Old rules: gray box. New rules: blue box (inside, or sticking out).
        s.rect(x0, 70, 420, 220, GRAY_PALE, SUB, 1.5, 10)
        s.text(x0 + 16, 102, "古い規則で有効", 22, "start", "sub")
        if hard:
            s.rect(x0 + 150, 150, 300, 120, BLUE_PALE, BLUE, 2.5, 10)
            s.text(x0 + 165, 182, "新しい規則で有効", 22, "start")
            s.rect(x0 + 330, 200, 112, 56, OCHRE_PALE, OCHRE, 2, 6)
            s.text(x0 + 386, 236, "PUSH0", 22)
        else:
            s.rect(x0 + 110, 140, 250, 125, BLUE_PALE, BLUE, 2.5, 10)
            s.text(x0 + 235, 210, "新しい規則で有効", 22)
        # What the old node does with a new block.
        if hard:
            s.text(x0 + 210, 336, "古いノードは新しいブロックを拒む", 24)
            s.text(x0 + 210, 370, "（PUSH0 を含むブロックは範囲の外）", 22, cls="sub")
        else:
            s.text(x0 + 210, 336, "古いノードも新しいブロックを受け入れる", 24)
            s.text(x0 + 210, 370, "（狭めた範囲は古い範囲の中）", 22, cls="sub")
        # Chain below.
        y = 420
        for j in range(6):
            s.rect(x0 + 20 + j * 66, y, 44, 40, BLUE_PALE, BLUE)
        s.line(x0 + 20, y + 20, x0 + 20 + 5 * 66 + 44, y + 20, BLUE, 3)
        for j in range(6):
            s.rect(x0 + 20 + j * 66, y, 44, 40, BLUE_PALE, BLUE)
        if hard:
            s.raw(f'<path d="M{x0 + 20 + 2 * 66 + 44} {y + 20} L{x0 + 20 + 3 * 66} {y + 62} L{x0 + 20 + 5 * 66 + 44} {y + 62}" '
                  f'fill="none" stroke="{OCHRE}" stroke-width="3"/>')
            for j in range(3, 6):
                s.rect(x0 + 20 + j * 66, y + 46, 44, 32, OCHRE_PALE, OCHRE)
    s.save("ethereum-hard-forks_rules.webp")


def summary_tables():
    """Split lab/output/summary.txt into {section title: [rows as lists of cells]}."""
    tables, key = {}, None
    for line in (HERE / "lab" / "output" / "summary.txt").read_text().splitlines():
        if line.startswith("== "):
            key = line.strip("= ")
            tables[key] = []
        elif key and "|" in line:
            tables[key].append([c.strip() for c in line.split("|")])
    return tables


def opcodes_figure():
    """Which new opcodes run on each fork, and what SLOAD costs there."""
    t = summary_tables()
    probes = t["opcode probes (eth_call of init code)"]
    sload = {r[0]: r[1:] for r in t["SLOAD of the same slot twice in one call"][1:]}
    names = probes[0][1:]
    s = Svg(W, H, "フォークごとに、新しい命令が動くかと、同じスロットを 2 回読む SLOAD のガス")
    x0, cw, sw, top, rh = 150, 108, 104, 80, 50
    s.text(x0 + cw * len(names) / 2, top - 48, "新しい命令", 24, cls="sub")
    for j, name in enumerate(names):
        s.text(x0 + cw * j + cw / 2, top - 16, name, 22)
    sx = x0 + cw * len(names) + 16
    s.text(sx + sw, top - 48, "SLOAD のガス", 24, cls="sub")
    s.text(sx + sw / 2, top - 16, "1 回目", 22)
    s.text(sx + sw * 1.5, top - 16, "2 回目", 22)
    prev = None
    for i, row in enumerate(probes[1:]):
        fork, cells = row[0], row[1:]
        y = top + rh * i
        s.text(x0 - 16, y + 36, fork, 24, anchor="end")
        for j, cell in enumerate(cells):
            ok = cell.startswith("ok")
            fill, stroke = (BLUE_PALE, BLUE) if ok else (GRAY_PALE, "#ffffff")
            s.rect(x0 + cw * j + 4, y + 4, cw - 8, rh - 8, fill, stroke, 1.5, 5)
            s.text(x0 + cw * j + cw / 2, y + 33, "動く" if ok else "失敗", 24, cls="" if ok else "sub")
        gas = sload[fork]
        for k, g in enumerate(gas):
            changed = prev is not None and g != prev[k]
            s.rect(sx + sw * k + 4, y + 4, sw - 8, rh - 8, OCHRE_PALE if changed else "#ffffff",
                   OCHRE if changed else SUB, 2 if changed else 1, 5)
            s.text(sx + sw * k + sw / 2, y + 33, g, 24)
        prev = gas
    s.text(W / 2, top + rh * 8 + 42, "失敗 = NotActivated　黄土色の枠 = 前のフォークから変わった値", 24, cls="sub")
    s.save("ethereum-hard-forks_opcodes.webp")


def transfer_figure():
    """Gas that 3 SLOADs need in the receiver, against the 2300 gas that transfer() forwards."""
    t = summary_tables()
    sload = {r[0]: [int(v) for v in r[1:]] for r in t["SLOAD of the same slot twice in one call"][1:]}
    status = {r[0]: r[1:] for r in t["transfer(1 wei) to a receiver that reads 3 slots"][1:]}
    later = [f for f in sload if f not in ("petersburg", "istanbul")]
    assert len({tuple(sload[f]) for f in later}) == 1 and len({tuple(status[f]) for f in later}) == 1
    rows = [
        ("petersburg", 3 * sload["petersburg"][0], status["petersburg"][0]),
        ("istanbul", 3 * sload["istanbul"][0], status["istanbul"][0]),
        (f"{later[0]}–{later[-1]}", 3 * sload[later[0]][0], status[later[0]][0]),
        ("access list あり", 3 * sload[later[0]][1], status[later[0]][1]),
    ]
    s = Svg(W, H, "受け取る側の SLOAD 3 回に要るガスと、transfer が渡す 2300 ガス")
    x0, scale, top, rh = 230, 480 / 6300, 90, 92
    limit = x0 + 2300 * scale
    s.text(W / 2, 46, "受け取る側の SLOAD 3 回に要るガス", 24, cls="sub")
    for i, (label, gas, st) in enumerate(rows):
        y = top + rh * i
        over = gas > 2300
        s.text(x0 - 16, y + 44, label, 24, anchor="end")
        s.rect(x0, y + 14, f"{gas * scale:.1f}", 44, OCHRE_PALE if over else BLUE_PALE,
               OCHRE if over else BLUE, 2, 4)
        s.text(x0 + gas * scale + 12, y + 44, f"{gas:,}", 24, anchor="start")
        s.text(W - 20, y + 44, "成功" if st == "1" else "失敗", 24, anchor="end", cls="" if st == "1" else "sub")
    s.line(f"{limit:.1f}", top - 6, f"{limit:.1f}", top + rh * 4, INK, 2, "8 6")
    s.text(limit, top + rh * 4 + 34, "transfer が渡す 2300 ガス", 24)
    s.save("ethereum-hard-forks_transfer.webp")


def evmversion_figure():
    """The same source compiled for 3 evmVersion values, deployed to 3 forks."""
    t = summary_tables()
    rows = t["Copy.sol compiled with solc --evm-version"]
    header, body = rows[0], rows[1:]
    forks = [h.replace("deploy:", "").strip() for h in header[4:]]
    s = Svg(W, 470, "同じ Copy.sol を 3 つの evmVersion でコンパイルし、london・shanghai・cancun のノードにデプロイした結果")
    x0, cw, top, rh = 330, 200, 120, 92
    s.text(150, top - 52, "コンパイルの指定", 24, cls="sub")
    s.text(x0 + cw * 1.5, top - 52, "デプロイ先のノードのフォーク", 24, cls="sub")
    for j, f in enumerate(forks):
        s.text(x0 + cw * j + cw / 2, top - 14, f, 24)
    for i, r in enumerate(body):
        version, push0, mcopy, deploys = r[0], r[2], r[3], r[4:]
        y = top + rh * i
        s.text(30, y + 40, f"evmVersion={version}", 24, "start")
        s.text(30, y + 74, f"PUSH0 {push0} 個・MCOPY {mcopy} 個", 22, "start", "sub")
        for j, d in enumerate(deploys):
            ok = d == "1"
            s.rect(x0 + cw * j + 8, y + 10, cw - 16, rh - 20, BLUE_PALE if ok else OCHRE_PALE,
                   BLUE if ok else OCHRE, 2, 6)
            s.text(x0 + cw * j + cw / 2, y + 55, "成功" if ok else "失敗", 24)
    s.text(W / 2, top + rh * 3 + 50, "cancun 向けの MCOPY は実行用コードにだけ入る（関数の呼び出しは試していない）", 22, cls="sub")
    s.save("ethereum-hard-forks_evmversion.webp")


def month_x(date, start, x0, per_month):
    y, m, d = (int(v) for v in date.split("-"))
    return x0 + ((y - start[0]) * 12 + (m - start[1]) + (d - 1) / 31) * per_month


def solc_figure():
    """solc raises its default evmVersion right after each mainnet fork."""
    mainnet = [("Shanghai", "2023-04-12"), ("Cancun", "2024-03-13"), ("Prague", "2025-05-07"), ("Osaka", "2025-12-03")]
    solc = [("0.8.20", "shanghai", "2023-05-10"), ("0.8.25", "cancun", "2024-03-14"),
            ("0.8.30", "prague", "2025-05-07"), ("0.8.31", "osaka", "2025-12-03")]
    s = Svg(W, 420, "Ethereum mainnet でフォークが有効になった日と、solc が既定の evmVersion を上げた版の日")
    x0, per, start = 250, 660 / 36, (2023, 1)
    for year in (2023, 2024, 2025, 2026):
        x = month_x(f"{year}-01-01", start, x0, per)
        s.line(x, 60, x, 330, "#d0d0d0", 1.5)
        s.text(x, 46, str(year), 22, cls="sub")
    s.text(20, 140, "Ethereum mainnet", 24, "start")
    s.text(20, 250, "solc の既定の", 24, "start")
    s.text(20, 282, "evmVersion", 24, "start")
    s.line(x0, 130, x0 + 660, 130, BLUE, 2)
    s.line(x0, 255, x0 + 660, 255, SUB, 2)
    for name, date in mainnet:
        x = month_x(date, start, x0, per)
        s.raw(f'<circle cx="{x:.1f}" cy="130" r="9" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2.5"/>')
        s.text(x, 112, name, 22)
        s.text(x, 166, date[:7], 20, cls="sub")
    for ver, evm, date in solc:
        x = month_x(date, start, x0, per)
        s.raw(f'<circle cx="{x:.1f}" cy="255" r="9" fill="#ffffff" stroke="{SUB}" stroke-width="2.5"/>')
        s.text(x, 237, evm, 22)
        s.text(x, 291, ver, 20, cls="sub")
    s.rect(30, 350, W - 60, 52, OCHRE_PALE, OCHRE, 2, 6)
    s.text(W / 2, 384, "L2 などの別の EVM のチェーンは、どのフォークまで取り込むかを各自で決める", 22)
    s.save("ethereum-hard-forks_solc.webp")


def schedule_figure():
    """After Fusaka: BPO forks on mainnet, Glamsterdam on Sepolia, Hoodi paused, mainnet undecided."""
    s = Svg(W, 400, "Fusaka 以降の mainnet と、Glamsterdam のテストネットでの予定（2026 年 11 月 11 日時点）")
    x0, per, start = 200, 680 / 12, (2025, 12)
    for label, date in (("2025-12", "2025-12-01"), ("2026-04", "2026-04-01"), ("2026-08", "2026-08-01"),
                        ("2026-12", "2026-12-01")):
        x = month_x(date, start, x0, per)
        s.line(x, 50, x, 350, "#d0d0d0", 1.5)
        s.text(x, 40, label, 20, cls="sub")
    rows = [("mainnet", 120), ("Sepolia", 230), ("Hoodi", 310)]
    for name, y in rows:
        s.text(20, y + 8, name, 24, "start")
        s.line(x0, y, x0 + 680, y, SUB, 1.5)
    # mainnet: Fusaka, BPO1, BPO2 (blue = activated), Glamsterdam undecided (dashed).
    for label, date, dy in (("Fusaka", "2025-12-03", -22), ("BPO1", "2025-12-09", 44), ("BPO2", "2026-01-07", -22)):
        x = month_x(date, start, x0, per)
        s.raw(f'<circle cx="{x:.1f}" cy="120" r="9" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2.5"/>')
        s.text(x + (34 if label == "BPO2" else 0), 120 + dy, label, 20)
    today = month_x("2026-11-11", start, x0, per)
    s.line(today, 60, today, 340, INK, 2, "4 4")
    s.text(today, 356, "11-11", 20)
    s.text(today - 10, 98, "Glamsterdam の日付は未定", 20, "end", "sub")
    x = month_x("2026-10-06", start, x0, per)
    s.raw(f'<circle cx="{x:.1f}" cy="230" r="9" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2.5"/>')
    s.text(x - 14, 208, "Glamsterdam 10-06", 20, "end")
    x = month_x("2026-10-26", start, x0, per)
    s.raw(f'<circle cx="{x:.1f}" cy="310" r="9" fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="2.5" stroke-dasharray="4 3"/>')
    s.text(x - 14, 300, "10-26 の予定を保留", 20, "end")
    s.text(W / 2, 390, "青 = 有効になった　黄土色 = 予定を保留した　縦の点線 = 本記事の時点", 20, cls="sub")
    s.save("ethereum-hard-forks_schedule.webp")


def warm_figure():
    """Call another contract and read the same slot twice there: without and with an access list."""
    s = Svg(W, 420, "別のコントラクトを呼び、その中で同じストレージの値を 2 回読む時のガス。access list に書くと、"
                    "開始時に 4,300 ガスを先に払い、呼び出しの中の参照は全て 100 ガスになる")
    x0, scale = 250, 560 / 4800
    rows = [("access list なし", [("呼び出し先 cold 2,600", 2600, OCHRE_PALE, OCHRE),
                                 ("読む cold 2,100", 2100, OCHRE_PALE, OCHRE), ("", 100, BLUE_PALE, BLUE)],
             "2 回目の読み出しは warm で 100"),
            ("access list あり", [("開始時に先払い 4,300", 4300, GRAY_PALE, SUB), ("", 100, BLUE_PALE, BLUE),
                                 ("", 100, BLUE_PALE, BLUE), ("", 100, BLUE_PALE, BLUE)],
             "呼び出しと 2 回の読み出しは warm で 100 ずつ")]
    s.text(W / 2, 46, "別のコントラクトを呼び、その中で同じストレージの値を 2 回読む", 24, cls="sub")
    for i, (label, parts, note) in enumerate(rows):
        y = 100 + i * 130
        s.text(x0 - 16, y + 38, label, 24, "end")
        x = x0
        for name, gas, fill, stroke in parts:
            w = max(gas * scale, 22)
            s.rect(f"{x:.1f}", y + 8, f"{w:.1f}", 44, fill, stroke, 2, 4)
            if name:
                s.text(x + w / 2, y + 38, name, 20)
            x += w + 5
        s.text(x - 6, y + 86, note, 20, "end", "sub")
        total = sum(g for _, g, _, _ in parts)
        s.text(x + 10, y + 38, f"計 {total:,}", 22, "start")
    s.text(W / 2, 362, "先払い = アドレス 1 件の 2,400 ＋ キー 1 件の 1,900。トランザクションの開始時に払う", 20, cls="sub")
    s.text(W / 2, 396, "Berlin 以降。呼び出しの料金のうち、アドレスの参照以外の分は省いている", 20, cls="sub")
    s.save("ethereum-hard-forks_warm.webp")


def delegation_figure():
    """msg.sender == tx.origin no longer proves that no contract code ran in between."""
    s = Svg(W, 440, "以前は、間にコントラクトを挟むと msg.sender と tx.origin が食い違った。"
                    "EIP-7702 で委任した EOA は、自分のアドレスのままコードを実行し、両者が一致する")
    def node(x, y, w, label, sub, fill, stroke):
        s.rect(x, y, w, 70, fill, stroke, 2, 8)
        s.text(x + w / 2, y + 32, label, 22)
        s.text(x + w / 2, y + 58, sub, 18, cls="sub")
    def arrow(x1, x2, y):
        s.line(x1, y, x2 - 10, y, INK, 2)
        s.raw(f'<path d="M{x2} {y} L{x2 - 12} {y - 7} L{x2 - 12} {y + 7} Z" fill="{INK}"/>')
    # Before: EOA -> contract B -> A
    s.text(20, 44, "以前", 24, "start", "sub")
    node(20, 64, 190, "EOA", "署名して送る", BLUE_PALE, BLUE)
    node(290, 64, 240, "コントラクト B", "間に挟まったコード", GRAY_PALE, SUB)
    node(610, 64, 330, "コントラクト A の判定", "msg.sender = B ≠ tx.origin", "#ffffff", SUB)
    arrow(210, 290, 99); arrow(530, 610, 99)
    s.text(775, 164, "→ 拒否できた", 22)
    # After 7702: EOA runs delegated code as itself
    s.text(20, 234, "Prague 以降（EIP-7702 の委任）", 24, "start", "sub")
    node(20, 254, 510, "EOA ＋ 委任先のコード", "署名した EOA のアドレスのままコードが動く", OCHRE_PALE, OCHRE)
    node(610, 254, 330, "コントラクト A の判定", "msg.sender = EOA = tx.origin", "#ffffff", SUB)
    arrow(530, 610, 289)
    s.text(775, 354, "→ 通ってしまう", 22)
    s.text(W / 2, 414, "委任先のコードは 1 つのトランザクションの中で A を何度でも呼べ、「EOA から 1 回だけ」の前提が崩れる", 20, cls="sub")
    s.save("ethereum-hard-forks_delegation.webp")


if __name__ == "__main__":
    warm_figure()
    delegation_figure()
    solc_figure()
    schedule_figure()
    concept_figure()
    rules_figure()
    opcodes_figure()
    transfer_figure()
    evmversion_figure()
