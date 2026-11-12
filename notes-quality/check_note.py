"""書き直したノートの機械の関門。著者の指摘のうち、数えられるものを全部確かめる。

使い方: python3 check_note.py <index.md のパス>
全部 OK なら終了コード 0。NG が 1 つでもあれば 1。書く担当は 0 になるまで直してから完了を報告する。
"""
import os
import re
import subprocess
import sys

p = sys.argv[1]
raw = open(p, encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
fm, body = (m.group(1), raw[m.end():]) if m else ("", raw)
nocode = re.sub(r"```.*?```", "", body, flags=re.S)
lines = nocode.split("\n")
ng, warn = [], []


def vis(s):
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    return s.strip()


def width(s):
    return sum(1 if ord(c) < 0x2E80 else 2 for c in s) / 2  # 全角換算の文字数


# 1. 文字だけの長い区間（debimate-visual-notes §3）
tr = subprocess.run(["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "textruns.py"), p],
                    capture_output=True, text=True).stdout
mm = re.search(r"700字以上の文字だけの区間 (\d+) 個 / 200字超の段落 (\d+) 個", tr)
if mm and int(mm.group(1)) > 0:
    ng.append(f"700 字以上の文字だけの区間が {mm.group(1)} 個（0 にする。図を入れるか段落を分けて <br>）\n" + tr)
if mm and int(mm.group(2)) > 8:
    warn.append(f"200 字超の段落が {mm.group(2)} 個（基準の Wallet は 5）")

# 2. 段落ごとの括弧（定義・理由・条件を括弧に入れない。1 段落に 2 つ以上は書き直しを疑う）
for para in re.split(r"\n\s*\n", nocode):
    t = para.strip()
    if not t or t.startswith(("{{", "|", "#", "<", "!", "-", "1.")):
        continue
    inner = re.findall(r"（([^（）]*)）", vis(t))
    # 略語・英語名・短い言い換えは数えない（スキルが初出で求める形）
    gloss = lambda x: len(x) <= 12 or re.match(r"^[A-Za-z0-9 ,.'’\-/:+_]+(、[^、]{1,20})?$", x) or x.startswith("「")  # noqa: E731
    real = [x for x in inner if not gloss(x)]
    if len(real) >= 2 or [x for x in real if len(x) >= 40]:
        ng.append(f"括弧が多い・長い段落: {vis(t)[:60]}… 括弧の中: {real}（定義・理由・条件・出典は本文の文にする）")
    elif real:
        warn.append(f"説明の括弧（読まなくても通じる補足か確かめる）: {real[0][:40]}")
    if re.search(r"（\[[^\]]+\]\([^)]+\)\s*の?ノート[^）]*）", t) or re.search(r"（[^（）]*\]\([^)]+\)[^（）]*のノート）", t):
        ng.append(f"文末の括弧でリンクを添えている（参照する理由が分かる文の中に置く）: {vis(t)[:60]}…")

# 3. 箇条書きの 1 項目が折り返さない（PC 幅で全角 44 字ほど）
for ln in lines:
    mm = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", ln)
    if mm and width(vis(mm.group(1))) > 48:
        ng.append(f"折り返す箇条書き（{width(vis(mm.group(1))):.0f} 字）: {vis(mm.group(1))[:50]}…")

# 4. 表のマスが 2 行を超えない
for ln in lines:
    if ln.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", ln):
        cells = [vis(c) for c in ln.strip().strip("|").split("|")]
        lim = {2: 34, 3: 24, 4: 17, 5: 13}.get(len(cells), 11) * 2
        for c in cells:
            if width(c) > lim:
                ng.append(f"表のマスが長い（{width(c):.0f} 字、{len(cells)} 列）: {c[:40]}…")

# 5. 太字・「正本」
if re.search(r"\*\*[^*\n]+\*\*", nocode):
    ng.append("太字がある（本文中の太字は使わない）")
if "正本" in nocode:
    ng.append("「正本」を使っている")

# 6. 型の節（利点・欠点・適さないケース・使いどころ）
for ln in lines:
    if re.match(r"^#{2,4} ", ln) and re.search(r"利点|欠点|メリット|デメリット|適さない|使いどころ|向かないケース|得られる性質|制約", ln):
        ng.append(f"型の節が残っている: {ln.strip()}（読者の次の判断で閉じる）")

# 7. 「本記事では」と問いの一覧、その前の <br>
k = nocode.find("\n本記事では")
if k < 0:
    ng.append("「本記事では」の段落が無い（読者の問いを箇条書きで並べる）")
else:
    before = nocode[:k].rstrip()
    if not before.endswith("<br>"):
        ng.append("「本記事では」の直前に空行で挟んだ <br> が無い")

# 8. details の前後の <br>、#### の前の <br>
for mm in re.finditer(r"<details>", nocode):
    if not nocode[:mm.start()].rstrip().endswith("<br>"):
        ng.append("<details> の前に <br> が無い")
for mm in re.finditer(r"</details>", nocode):
    if not nocode[mm.end():].lstrip().startswith("<br>"):
        ng.append("</details> の後に <br> が無い")
prev = ""
for ln in lines:
    if ln.startswith("#### ") and prev and not prev.startswith("### ") and prev != "<br>":
        ng.append(f"#### の前に <br> が無い: {ln.strip()}")
    if ln.strip():
        prev = ln.strip()

# 9. 図は WebP、図の中の文字は日本語
imgs = re.findall(r'src="([^"]+)"', body) + re.findall(r"!\[[^\]]*\]\(([^)\s]+)", nocode)
bad = [i for i in imgs if not i.startswith("http") and not i.endswith(".webp")]
if bad:
    ng.append(f"WebP でない図: {bad}")
if not imgs:
    ng.append("図が無い")
first_para = re.split(r"\n\s*\n", nocode.strip())
if imgs and nocode.find(imgs[0]) > nocode.find("本記事では") > 0:
    warn.append("最初の図が「本記事では」より後ろ（表紙は冒頭の結果か場面の図にする）")
gen = [os.path.join(os.path.dirname(p), "figures.py")]
slug = os.path.basename(os.path.dirname(p))
gen.append(os.path.join(os.path.dirname(p), "..", "..", "..", "scripts", "notes", f"{slug}_gen.py"))
for g in gen:
    if os.path.exists(g):
        src = open(g, encoding="utf-8").read()
        eng = [s for s in re.findall(r'(?:set_title|set_xlabel|set_ylabel|label=|text\([^)\n]*?)\(?\s*f?"([^"\n]{6,})"', src)
               if re.search(r"[A-Za-z]{4,} [A-Za-z]{3,}", s) and not re.search(r"[぀-ヿ一-鿿]", s)]
        if eng:
            ng.append(f"図の生成元に英語だけのラベル: {eng[:5]}（日本語にする。識別子・固有名・単位は原文のまま）")

# 10. 外部リンク（公式・原論文がある語は初出でリンク）と相互リンク
ext = len(re.findall(r"\]\(https?://", nocode))
internal = len(set(re.findall(r"\]\((/notes/[^)#]+|/ml/[^)#]+|\.\./[^)#]+)", nocode)))
if ext < 2:
    warn.append(f"外部リンクが {ext} 本（公式・原論文・実在の事例へ）")
if internal < 4:
    warn.append(f"他のノートへのリンクが {internal} 本（前提や詳しい説明がある所の初出に張る）")

print(("NG " if ng else "OK ") + p)
for x in ng:
    print("  NG:", x)
for x in warn:
    print("  注意:", x)
sys.exit(1 if ng else 0)
