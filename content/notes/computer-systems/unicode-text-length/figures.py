"""Generate the figures of the Unicode text length note.

Run: python3 figures.py  -> images/*.webp

Each figure is an HTML page built here, rendered by headless Chrome at 2x
(so that color emoji are drawn by the system emoji font) and saved as WebP
with Pillow. Only the WebP files are kept in images/. The limits figure is
drawn with matplotlib.

The numbers come from the programs in lab/ (count, limits, width-rs-*,
fullwidth) and from the sqly runs described in the note.

- units_figure(): one family emoji measured in UTF-8 bytes, UTF-16 code
  units, code points, grapheme clusters and terminal cells.
- limits_figure(): the same text against a limit counted in two units.
- delete_figure(): deleting one code point at a time versus one grapheme.
- width_figure(): where the terminal draws and where the program thinks it
  drew, for a tab and for half-width katakana with a sound mark.
- bom_figure(): how a BOM becomes part of the first column name.
- encoding_figure(): the three places a Shift_JIS round trip lost text.
- fold_figure(): folding a full-width @ and mapping positions back.
"""

from html import escape
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED, RED_PALE = "#7aa6c2", "#e15759", "#fbe3e3"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"
EMOJI = "'Noto Color Emoji'"

BASE_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #ffffff; color: {INK}; font-family: {FONT}; font-size: 20px; }}
.mono {{ font-family: {MONO}; }}
.emoji {{ font-family: {EMOJI}; }}
.sub {{ color: {SUB}; }}
.title {{ font-size: 24px; margin-bottom: 18px; }}
.cell {{ display: flex; align-items: center; justify-content: center; border: 2px solid {ACCENT};
        background: {PALE}; border-radius: 6px; height: 46px; }}
.cell.gray {{ border-color: #b5b5b5; background: {FILL}; }}
.cell.red {{ border-color: {RED}; background: {RED_PALE}; }}
.cell.ochre {{ border-color: {OCHRE}; background: {OCHRE_PALE}; }}
.cell.none {{ border: 2px dashed #c8c8c8; background: #ffffff; }}
"""


def render(body, w, h, name, css=""):
    """HTML body -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    page = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            f'<style>{BASE_CSS}{css}</style></head><body>{body}</body></html>')
    with tempfile.TemporaryDirectory() as tmp:
        src, png = Path(tmp) / "fig.html", Path(tmp) / "fig.png"
        src.write_text(page, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", src.as_uri()], check=True, capture_output=True)
        (HERE / "images").mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


# --- 1. units ---------------------------------------------------------------

FAMILY = [  # (code point, emoji or name, UTF-8 bytes, UTF-16 units)
    ("U+1F468", "👨", ["F0", "9F", "91", "A8"], ["D83D", "DC68"]),
    ("U+200D", "ZWJ", ["E2", "80", "8D"], ["200D"]),
    ("U+1F469", "👩", ["F0", "9F", "91", "A9"], ["D83D", "DC69"]),
    ("U+200D", "ZWJ", ["E2", "80", "8D"], ["200D"]),
    ("U+1F467", "👧", ["F0", "9F", "91", "A7"], ["D83D", "DC67"]),
]


def units_figure():
    unit = 38  # px per UTF-8 byte
    gap = 4

    def group_width(n_bytes):
        return n_bytes * unit + (n_bytes - 1) * gap

    def row(label, count, inner, note):
        return (f'<div class="row"><div class="label">{label}<br><span class="count">{count}</span></div>'
                f'<div class="groups">{inner}</div><div class="note">{note}</div></div>')

    def groups(make):
        return "".join(
            f'<div class="group" style="width:{group_width(len(b))}px">{make(cp, ch, b, u)}</div>'
            for cp, ch, b, u in FAMILY)

    def kind(ch):
        return "gray" if ch == "ZWJ" else ""

    utf8 = groups(lambda cp, ch, b, u: "".join(
        f'<div class="cell mono {kind(ch)}" style="flex:1;font-size:19px">{x}</div>' for x in b))
    utf16 = groups(lambda cp, ch, b, u: "".join(
        f'<div class="cell mono {kind(ch)}" style="flex:1;font-size:21px">{x}</div>' for x in u))
    cps = groups(lambda cp, ch, b, u: (
        f'<div class="cell {kind(ch)}" style="flex:1;flex-direction:column;height:64px">'
        f'<span class="{"sub" if ch == "ZWJ" else "emoji"}" style="font-size:{18 if ch == "ZWJ" else 24}px">{ch}</span>'
        f'<span class="mono" style="font-size:15px">{cp}</span></div>'))
    total = sum(group_width(len(b)) for _, _, b, _ in FAMILY) + gap * 2 * (len(FAMILY) - 1)
    grapheme = (f'<div class="cell ochre" style="width:{total}px;height:64px">'
                f'<span class="emoji" style="font-size:34px">👨‍👩‍👧</span></div>')
    cells = ('<div class="term"><div class="tcell"></div><div class="tcell"></div>'
             '<span class="emoji tchar">👨‍👩‍👧</span></div>')
    body = (
        '<div class="wrap">'
        '<div class="title" style="font-size:28px">同じ 1 つの絵文字（家族 👨‍👩‍👧）を、5 つの単位で数える</div>'
        + row("UTF-8 のバイト", "18", utf8, "Go の len、Rust の len()")
        + row("UTF-16 のコード単位", "8", utf16, "JavaScript の length")
        + row("コードポイント", "5", cps, "Python の len、<br>SQLite の length")
        + row("書記素クラスター", "1", grapheme, "Intl.Segmenter、uniseg")
        + row("表示幅", "2 セル", cells, "go-runewidth、<br>多くの端末")
        + '</div>')
    css = f"""
    .wrap {{ padding: 28px 32px; }}
    .row {{ display: flex; align-items: center; margin-bottom: 16px; }}
    .label {{ width: 230px; flex-shrink: 0; font-size: 23px; line-height: 1.3; }}
    .count {{ font-size: 30px; color: {INK}; }}
    .groups {{ display: flex; gap: {gap * 2}px; width: {total}px; }}
    .group {{ display: flex; gap: {gap}px; }}
    .note {{ margin-left: 20px; font-size: 21px; color: {SUB}; width: 240px; flex-shrink: 0; line-height: 1.3; }}
    .term {{ position: relative; display: flex; height: 64px; }}
    .tcell {{ width: 38px; height: 64px; border: 2px solid #b5b5b5; background: #ffffff; }}
    .tcell + .tcell {{ border-left: none; }}
    .tchar {{ position: absolute; left: 0; width: 76px; top: 0; height: 64px; display: flex;
             align-items: center; justify-content: center; font-size: 34px; }}
    """
    render(body, 1330, 540, "units.webp", css)


# --- 2. limits --------------------------------------------------------------

def limits_figure():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK-Regular" in f or "NotoSansCJKjp-Regular" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
    rows = [  # (group, unit, value, limit, over)
        ("Bluesky の投稿\n家族 4 人の絵文字を 121 個", "書記素クラスター", 121, 300, False),
        ("", "UTF-8 のバイト", 3025, 3000, True),
        ("Excel のセル\nU+1F600 の絵文字を 16,384 個", "コードポイント", 16384, 32767, False),
        ("", "UTF-16 のコード単位", 32768, 32767, True),
    ]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ys = [3.7, 3.0, 1.5, 0.8]
    for y, (_, unit, v, lim, over) in zip(ys, rows):
        ratio = v / lim * 100
        ax.barh(y, ratio, height=0.5, color=RED_PALE if over else PALE,
                edgecolor=RED if over else ACCENT, linewidth=1.6)
        ax.text(-3, y, unit, ha="right", va="center", fontsize=12, color=INK)
        label = f"{v:,} / {lim:,}　上限を超える" if over else f"{v:,} / {lim:,}"
        ax.text(ratio + 2, y, label, va="center", fontsize=11.5,
                color=RED if over else SUB)
    for y, label in ((4.35, rows[0][0]), (2.15, rows[2][0])):
        ax.text(-62, y, label.replace("\n", "：　"), ha="left", va="center", fontsize=12.5, color=INK)
    ax.axvline(100, color=INK, linewidth=1.4, linestyle=(0, (4, 3)), ymax=0.86)
    ax.text(100, 0.15, "上限", ha="center", va="center", fontsize=12, color=INK,
            bbox=dict(facecolor="#ffffff", edgecolor="none", pad=2))
    ax.set_xlim(0, 185)
    ax.set_ylim(0, 4.7)
    ax.set_yticks([])
    ax.set_xticks([0, 50, 100])
    ax.set_xticklabels(["0%", "50%", "100%"], fontsize=11, color=SUB)
    ax.set_xlabel("上限に対する割合", fontsize=11.5, color=SUB, x=0.27)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#b5b5b5")
    ax.spines["bottom"].set_bounds(0, 100)
    fig.subplots_adjust(left=0.27, right=0.99, top=0.97, bottom=0.14)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(buf).convert("RGB").save(HERE / "images" / "limits.webp", "WEBP", quality=90, method=6)


# --- 1b. clusters -----------------------------------------------------------

def clusters_figure():
    zwj, mod, acute = chr(0x200D), chr(0x1F3FD), chr(0x0301)
    man, woman, girl, thumb = chr(0x1F468), chr(0x1F469), chr(0x1F467), chr(0x1F44D)
    ri_j, ri_p = chr(0x1F1EF), chr(0x1F1F5)
    rows = [  # (whole, [(shown, code point, kind)], how)
        (man + zwj + woman + zwj + girl,
         [(man, "U+1F468", ""), ("ZWJ", "U+200D", "gray"), (woman, "U+1F469", ""),
          ("ZWJ", "U+200D", "gray"), (girl, "U+1F467", "")],
         "ZWJ でつなぐ"),
        (thumb + mod, [(thumb, "U+1F44D", ""), (mod, "U+1F3FD", "ochre")], "肌の色を変える修飾子を続ける"),
        (ri_j + ri_p, [(ri_j, "U+1F1EF", ""), (ri_p, "U+1F1F5", "")], "Regional Indicator を 2 つ並べる"),
        ("e" + acute, [("e", "U+0065", ""), ("◌" + acute, "U+0301", "ochre")], "結合文字を続ける"),
    ]

    def parts(items):
        out = []
        for i, (shown, cp, kind) in enumerate(items):
            if i:
                out.append('<div class="plus">+</div>')
            cls = "sub" if shown == "ZWJ" else "emoji"
            out.append(f'<div class="cell {kind} part"><span class="{cls}">{escape(shown)}</span>'
                       f'<span class="mono cp">{cp}</span></div>')
        return "".join(out)

    body = (
        '<div class="wrap"><div class="title">1 つの書記素クラスターに、複数のコードポイントがまとまる 4 つの形</div>'
        + "".join(
            f'<div class="row"><div class="cell ochre whole"><span class="emoji">{escape(w)}</span></div>'
            f'<div class="eq">=</div>{parts(items)}<div class="how">{how}</div></div>'
            for w, items, how in rows)
        + '</div>')
    css = f"""
    .wrap {{ padding: 26px 32px; }}
    .row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }}
    .whole {{ width: 78px; height: 64px; font-size: 34px; flex-shrink: 0; }}
    .eq, .plus {{ font-size: 22px; color: {SUB}; width: 20px; text-align: center; }}
    .part {{ flex-direction: column; width: 104px; height: 64px; font-size: 24px; }}
    .part .sub {{ font-size: 18px; }}
    .cp {{ font-size: 14px; color: {INK}; }}
    .how {{ margin-left: 14px; font-size: 18px; color: {SUB}; }}
    """
    render(body, 1060, 410, "clusters.webp", css)


# --- 3. delete --------------------------------------------------------------

def delete_figure():
    zwj = "\u200d"
    m, w, g, b = "\U0001F468", "\U0001F469", "\U0001F467", ""
    family = m + zwj + w + zwj + g
    by_cp = [family, m + zwj + w + zwj, m + zwj + w, m + zwj, m, b]
    by_g = [family, b]
    thumb = ["\U0001F44D\U0001F3FD", "\U0001F44D", b]
    flag = ["\U0001F1EF\U0001F1F5", "\U0001F1EF", b]

    def strip(states, notes):
        out = []
        for i, s in enumerate(states):
            if i:
                out.append('<div class="arrow">⌫</div>')
            broken = 0 < i < len(states) - 1
            cls = "red" if broken else ("none" if s == "" else "")
            shown = escape(s) if s else '<span class="sub" style="font-size:16px">空</span>'
            note = notes[i - 1] if i else "元の文字"
            out.append(f'<div class="frame"><div class="cell {cls} box"><span class="emoji">{shown}</span></div>'
                       f'<div class="fnote">{note}</div></div>')
        return "".join(out)

    def row(label, states, notes):
        return f'<div class="row"><div class="label">{label}</div>{strip(states, notes)}</div>'

    body = (
        '<div class="wrap">'
        '<div class="title">Backspace を押すたびに何が消えるか</div>'
        '<div class="head">コードポイントごとに消す（修正前の bsky の入力欄）</div>'
        + row("家族", by_cp, ["女の子が消える", "ZWJ が消える<br>（見た目は同じ）", "女性が消える", "ZWJ が消える<br>（見た目は同じ）", "男性が消える"])
        + row("肌の色付き", thumb, ["修飾子が消える", "親指が消える"])
        + row("国旗", flag, ["P が消える", "J が消える"])
        + '<div class="head" style="margin-top:22px">書記素クラスターごとに消す（修正後）</div>'
        + row("家族", by_g, ["まとめて消える"])
        + '<div class="legend"><span class="cell red mini"></span> 本来は無かった途中の形</div>'
        '</div>')
    css = f"""
    .wrap {{ padding: 26px 32px; }}
    .head {{ font-size: 19px; color: {SUB}; margin: 4px 0 10px; }}
    .row {{ display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; }}
    .label {{ width: 140px; flex-shrink: 0; font-size: 18px; padding-top: 18px; }}
    .frame {{ display: flex; flex-direction: column; align-items: center; width: 112px; }}
    .fnote {{ font-size: 14px; color: {SUB}; text-align: center; line-height: 1.3; margin-top: 4px; height: 38px; }}
    .box {{ width: 112px; height: 62px; font-size: 32px; }}
    .arrow {{ font-size: 22px; color: {SUB}; width: 28px; text-align: center; padding-top: 16px; }}
    .legend {{ margin-top: 14px; font-size: 16px; color: {SUB}; display: flex; align-items: center; gap: 8px; }}
    .mini {{ display: inline-block; width: 26px; height: 18px; }}
    """
    render(body, 1200, 680, "delete.webp", css)


# --- 4. width ---------------------------------------------------------------

def width_figure():
    def grid(chars, cursor, n=11, tone=""):
        cells = []
        for i in range(n):
            ch = chars.get(i, "")
            cur = ' cur' if i == cursor else ''
            cells.append(f'<div class="tc{cur} {tone}">{ch}</div>')
        return '<div class="grid">' + "".join(cells) + '</div>'

    def row(label, g):
        return f'<div class="row"><div class="label">{label}</div>{g}</div>'

    body = (
        '<div class="wrap">'
        '<div class="title">端末が描いた位置と、プログラムが数えた位置</div>'
        '<div class="head">a、タブ、b と入力した後のカーソル（prompt の修正前）</div>'
        + row("端末が描く", grid({0: "a", 8: "b"}, 9))
        + row("runewidth で数える<br><span class='sub'>タブ = 0 セル</span>", grid({0: "a", 1: "b"}, 2, tone="ghost"))
        + '<div class="head" style="margin-top:20px">ｶﾞ の後に x を描く（bsky と unicode-width 0.2.3）</div>'
        + row("端末が描く", grid({0: "ｶ", 1: "ﾞ", 2: "x"}, -1))
        + row("ratatui の計算<br><span class='sub'>ﾞ = 1 + 1 セル</span>", grid({0: "ｶ", 1: "ﾞ", 3: "x"}, -1, tone="ghost"))
        + '<div class="legend"><span class="tc cur mini"></span> カーソルを描いた位置　'
        '<span class="tc ghost mini"></span> プログラムが思っている画面</div>'
        '</div>')
    css = f"""
    .wrap {{ padding: 26px 32px; }}
    .head {{ font-size: 19px; color: {SUB}; margin: 4px 0 10px; }}
    .row {{ display: flex; align-items: center; margin-bottom: 10px; }}
    .label {{ width: 230px; font-size: 18px; line-height: 1.3; }}
    .label .sub {{ font-size: 15px; }}
    .grid {{ display: flex; }}
    .tc {{ width: 44px; height: 54px; border: 1.5px solid #b5b5b5; margin-left: -1.5px; display: flex;
          align-items: center; justify-content: center; font-family: {MONO}, {FONT}; font-size: 26px;
          background: #ffffff; }}
    .tc.ghost {{ background: {FILL}; border-style: dashed; }}
    .tc.cur {{ background: {RED_PALE}; border: 2.5px solid {RED}; }}
    .legend {{ margin-top: 16px; font-size: 16px; color: {SUB}; display: flex; align-items: center; gap: 8px; }}
    .mini {{ display: inline-block; width: 26px; height: 18px; margin-left: 0; }}
    """
    render(body, 900, 470, "width.webp", css)


# --- 5. bom -----------------------------------------------------------------

def bom_figure():
    data = [("EF", "bom"), ("BB", "bom"), ("BF", "bom"), ("69", "i"), ("64", "d"), ("2C", ","),
            ("6E", "n"), ("61", "a"), ("6D", "m"), ("65", "e"), ("0A", "改行")]

    def byte_cells():
        out = []
        for hx, ch in data:
            cls = "ochre" if ch == "bom" else ("gray" if ch in (",", "改行") else "")
            out.append(f'<div class="cell mono {cls} b">{hx}</div>')
        return "".join(out)

    def char_cells():
        out = ['<div class="cell ochre c" style="width:158px">U+FEFF（BOM）</div>']
        for _, ch in data[3:]:
            cls = "gray" if ch in (",", "改行") else ""
            out.append(f'<div class="cell {cls} c" style="width:50px">{ch}</div>')
        return "".join(out)

    body = (
        '<div class="wrap">'
        '<div class="title">BOM 付きの CSV の 1 行目が、列名になるまで</div>'
        '<div class="row"><div class="label">ファイルのバイト</div>' + byte_cells() + '</div>'
        '<div class="row"><div class="label">UTF-8 でデコードした文字</div>' + char_cells() + '</div>'
        '<div class="row"><div class="label">CSV の列名</div>'
        '<div class="cell red c" style="width:270px">1 列目: U+FEFF + id</div>'
        '<div class="cell gray c" style="width:50px">,</div>'
        '<div class="cell c" style="width:216px">2 列目: name</div></div>'
        '<div class="row"><div class="label">画面と SQL</div>'
        '<div class="note">表には <span class="mono">id</span> と表示される（U+FEFF は幅 0 で見えない）が、'
        '<br>SQL の <span class="mono">id</span>（69 64）とは一致せず no such column になる</div></div>'
        '</div>')
    css = f"""
    .wrap {{ padding: 26px 32px; }}
    .row {{ display: flex; align-items: center; gap: 4px; margin-bottom: 14px; }}
    .label {{ width: 240px; font-size: 18px; }}
    .b {{ width: 50px; font-size: 18px; }}
    .c {{ font-size: 17px; }}
    .note {{ font-size: 17px; line-height: 1.5; }}
    """
    render(body, 900, 340, "bom.webp", css)


# --- 6. encoding ------------------------------------------------------------

def encoding_figure():
    def node(text, sub="", cls=""):
        s = f'<div class="sub small">{sub}</div>' if sub else ""
        return f'<div class="cell {cls} node"><div>{text}</div>{s}</div>'

    def hole(n, title, what, fix):
        return (f'<div class="hole"><div class="num">{n}</div><div><div>{title}</div>'
                f'<div class="small red-t">{what}</div><div class="small sub">今: {fix}</div></div></div>')

    body = (
        '<div class="wrap">'
        '<div class="title">Shift_JIS の CSV を取り込んで書き戻すまでに、文字が化けた 3 か所</div>'
        '<div class="flow">'
        + node("CSV ファイル", "Shift_JIS のバイト", "gray")
        + '<div class="arr">→<div class="tag">①②</div></div>'
        + node("SQLite の表", "TEXT は UTF-8")
        + '<div class="arr">→<div class="tag">③</div></div>'
        + node("同じ CSV ファイル", ".save で書き戻す", "gray")
        + '</div>'
        '<div class="holes">'
        + hole("①", "UTF-8 として取り込む", "東京 が 4 つの化けた文字になる", "止めて --encoding を案内する")
        + hole("②", "--encoding shift-jis で取り込む", "デコードできないバイトが U+FFFD になる", "置き換えが起きたら止める")
        + hole("③", ".save で書き戻す", "UTF-8 で書かれ、次に化ける", "取り込んだ文字コードで書く")
        + '</div></div>')
    css = f"""
    .wrap {{ padding: 26px 32px; }}
    .title {{ font-size: 30px; }}
    .flow {{ display: flex; align-items: center; gap: 10px; margin-bottom: 26px; }}
    .node {{ flex-direction: column; width: 330px; height: 100px; font-size: 27px; }}
    .small {{ font-size: 21px; margin-top: 2px; }}
    .arr {{ font-size: 40px; color: {SUB}; width: 90px; text-align: center; position: relative; }}
    .tag {{ font-size: 24px; color: {RED}; position: absolute; top: -28px; width: 90px; }}
    .holes {{ display: flex; gap: 14px; }}
    .hole {{ display: flex; gap: 10px; width: 390px; border: 2px solid {RED}; background: {RED_PALE};
            border-radius: 6px; padding: 14px 14px; font-size: 24px; line-height: 1.45; }}
    .num {{ font-size: 26px; color: {RED}; }}
    .red-t {{ color: #b8383a; }}
    """
    render(body, 1270, 420, "encoding.webp", css)


# --- 7. fold ----------------------------------------------------------------

def fold_figure():
    # 「連絡先 」は 10 バイトで、どちらの列でも同じなので省き、a から描く。
    orig = [(10, "a", "61"), (11, "l", "6C"), (12, "i", "69"), (13, "c", "63"), (14, "e", "65"),
            (15, "＠", "EF"), (16, "", "BC"), (17, "", "A0"), (18, "e", "65"), (19, "x", "78")]
    folded = [(10, "a", 10), (11, "l", 11), (12, "i", 12), (13, "c", 13), (14, "e", 14),
              (15, "@", 15), (16, "e", 18), (17, "x", 19)]
    step = 66

    def ocells():
        out = []
        for off, ch, hx in orig:
            cls = "ochre" if hx in ("EF", "BC", "A0") else ""
            out.append(f'<div class="col" style="left:{(off - 10) * step}px">'
                       f'<div class="off">{off}</div><div class="cell mono {cls} b">{hx}</div>'
                       f'<div class="ch">{ch}</div></div>')
        return "".join(out)

    def fcells():
        out = []
        for off, ch, src in folded:
            cls = "ochre" if ch == "@" else ""
            out.append(f'<div class="col" style="left:{(off - 10) * step}px">'
                       f'<div class="ch">{ch}</div><div class="cell mono {cls} b">{ord(ch):02X}</div>'
                       f'<div class="off">{off}</div><div class="pos">→ {src}</div></div>')
        return "".join(out)

    lines = []
    for off, _, src in folded:
        x1 = (src - 10) * step + 28  # 上の段（元の位置）
        x2 = (off - 10) * step + 28  # 下の段（畳んだ位置）
        color = RED if off != src else "#b5b5b5"
        lines.append(f'<line x1="{x1}" y1="0" x2="{x2}" y2="70" stroke="{color}" stroke-width="2.5"/>')
    svg = f'<svg width="700" height="70" style="display:block">{"".join(lines)}</svg>'
    body = (
        '<div class="wrap">'
        '<div class="title">全角の ＠ を半角に畳み、見つけた位置を元のバイト位置へ戻す</div>'
        '<div class="row"><div class="label">元の文字列<br><span class="sub">先頭の「連絡先 」の<br>10 バイトは省略</span></div>'
        f'<div class="track">{ocells()}</div></div>'
        f'<div class="row" style="height:70px"><div class="label"></div><div>{svg}</div></div>'
        '<div class="row"><div class="label">畳んだ文字列<br><span class="sub">ここで @ を探す</span></div>'
        f'<div class="track">{fcells()}</div></div>'
        '<div class="note">下の段の「→ 数字」が位置の対応表です。全角の ＠ は 3 バイトなので、'
        '＠ より後ろは 2 バイトずれます。<br>畳んだ文字列で見つけた範囲（終わりを含まない 10〜27）は、対応表で元の 10〜29 に戻してから伏せます。27 と 29 は図より右の位置です。</div>'
        '</div>')
    css = f"""
    .wrap {{ padding: 26px 32px; }}
    .row {{ display: flex; align-items: center; }}
    .label {{ width: 210px; font-size: 18px; line-height: 1.4; }}
    .label .sub {{ font-size: 15px; }}
    .track {{ position: relative; width: 700px; height: 112px; }}
    .col {{ position: absolute; top: 0; width: 56px; text-align: center; }}
    .b {{ width: 56px; font-size: 18px; }}
    .off {{ font-family: {MONO}; font-size: 15px; color: {SUB}; height: 22px; }}
    .ch {{ font-size: 20px; height: 30px; line-height: 30px; }}
    .pos {{ font-family: {MONO}; font-size: 15px; color: {RED}; }}
    .note {{ margin-top: 18px; font-size: 16px; color: {SUB}; line-height: 1.6; }}
    """
    render(body, 960, 470, "fold.webp", css)


if __name__ == "__main__":
    units_figure()
    clusters_figure()
    limits_figure()
    delete_figure()
    width_figure()
    bom_figure()
    encoding_figure()
    fold_figure()
