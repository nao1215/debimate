#!/usr/bin/env python3
"""本人の実文とノートを突き合わせ、言い回しの差を洗い出す。

  python3 build_vocab.py            # 差分の一覧を表示
  python3 build_vocab.py --write    # references/vocabulary.md を再生成

規則を手で足すと、規則を守った別の文体が育つ（→ voice_markers.md）。ここは
手で書かずに、本人の実文（content/post/ja + content/weeknotes）とノートの
頻度差から機械的に出す。ノートを書き足す度に走らせ直せば、リストは古びない。

題材が違えば専門用語は当然ずれるので、ひらがなが半分以上を占める n-gram だけを
残す。「冪等」「outbox」「トランザクション」は落ち、「という形で」「する事に
なり」のような言い回しが残る。
"""
import re, glob, os, sys, collections

REPO = os.environ.get("DEBIMATE_REPO", os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
# 著者が「納得できるレベル」まで調整したノート（2026-11-02 ユーザー指定）
APPROVED = ['content/notes/blockchain-systems/wallet/index.md']
HIRA = re.compile(r'[ぁ-ん]')
JP   = re.compile(r'^[ぁ-んァ-ヶ一-龠ー、。]+$')

def strip(md):
    md = re.sub(r'^---.*?\n---\n', '', md, flags=re.S)
    md = re.sub(r'```.*?```', '', md, flags=re.S)
    md = re.sub(r'^\s*\|.*$', '', md, flags=re.M)
    md = re.sub(r'^#+ .*$', '', md, flags=re.M)
    md = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', md)
    md = re.sub(r'`[^`]*`', '', md)
    md = re.sub(r'<[^>]+>', '', md)
    return md

def load(pats):
    out = []
    for p in pats:
        for f in glob.glob(p if os.path.isabs(p) else os.path.join(REPO, p)):
            out.append(strip(open(f, encoding='utf-8', errors='replace').read()))
    return re.sub(r'\s+', '', '\n'.join(out))

def ngrams(t, lo=4, hi=7):
    c = collections.Counter()
    for n in range(lo, hi + 1):
        for i in range(len(t) - n + 1):
            g = t[i:i+n]
            if not JP.match(g):            continue
            if '。' in g[:-1] or '、' in g: continue
            if len(HIRA.findall(g)) * 2 < n: continue   # ひらがなが半分未満は専門語
            c[g] += 1
    return c

def rates(c, n):  return {k: v * 10000 / n for k, v in c.items()}

def dedupe(rows, keep=40):
    """長い方が同数で出ていれば短い方を落とす（部分文字列の重複を消す）"""
    rows = sorted(rows, key=lambda r: (-r[1], -len(r[0])))
    out = []
    for g, a, b, cnt in rows:
        if any(g in o[0] and abs(o[3] - cnt) <= 1 for o in out): continue
        out.append((g, a, b, cnt))
        if len(out) >= keep: break
    return out

def main():
    post  = load(['content/post/ja/*/index.md', 'content/weeknotes/*/*/index.md'])
    # 著者が文体まで調整したノート。ノート側の集計から外し、別の列で比べる
    notes = load([p for p in glob.glob(os.path.join(REPO, 'content/notes/*/*/index.md'))
                  if os.path.relpath(p, REPO) not in APPROVED])
    appr  = load(APPROVED)
    ra    = rates(ngrams(appr), max(len(appr), 1))
    cp, cn = ngrams(post), ngrams(notes)
    rp, rn = rates(cp, len(post)), rates(cn, len(notes))

    ng_only, author_only = [], []
    for g, r in rn.items():
        if cn[g] >= 8 and r >= 1.2 and rp.get(g, 0) * 6 < r:
            ng_only.append((g, r - rp.get(g, 0), rp.get(g, 0), cn[g]))
    for g, r in rp.items():
        if cp[g] >= 12 and r >= 1.2 and rn.get(g, 0) * 6 < r:
            author_only.append((g, r - rn.get(g, 0), rn.get(g, 0), cp[g]))

    # ジャンル差を落とす。本人の記事は体験の記録なので過去形と一人称が多い。
    # ノートはリファレンスなので、ここを寄せると別の壊れ方をする（→ writing_style.md §1）
    GENRE = re.compile(r'(まし|でし|私|思い|感じ|でしょ|ください)')
    genre = [r for r in author_only if GENRE.search(r[0])]
    author_only = [r for r in author_only if not GENRE.search(r[0])]

    ng_only, author_only = dedupe(ng_only), dedupe(author_only)
    body = []
    body.append(f"本人 {len(post):,} 字 / ノート {len(notes):,} 字を突き合わせた結果。数字は 1 万字あたり。"
                f"Wallet 列は著者が調整したノート（{len(appr):,} 字）での値で、件数が少ないので目安に留める。\n")
    body.append("## ノートだけで育った言い回し（使わない）\n")
    body.append("| 言い回し | ノート | 本人 | Wallet | ノートでの件数 |\n|---|---|---|---|---|")
    for g, d, a, c in ng_only:
        body.append(f"| {g} | {rn[g]:.1f} | {a:.1f} | {ra.get(g, 0):.1f} | {c} |")
    body.append("\n## 本人が使うのにノートから消えた言い回し（使う）\n")
    body.append("過去形・一人称・「〜でしょう」は、体験の記録という文種から来る差なので"
                "落としてある。ノートへ持ち込まない（→ `writing_style.md` §1）。\n")
    body.append("| 言い回し | 本人 | ノート | Wallet | 本人での件数 |\n|---|---|---|---|---|")
    for g, d, n_, c in author_only:
        body.append(f"| {g} | {rp[g]:.1f} | {n_:.1f} | {ra.get(g, 0):.1f} | {c} |")
    out = "\n".join(body)

    head = ("# 語彙の差分（自動生成）\n\n"
                "`notes-quality/refresh_style.py` が本人の実文から作り直す。手で書き足さない。\n"
                "ノートを書く度に本人との差は動くので、規則として固定せず、書いた後に\n"
                "この表を当てて言い換える使い方をする。\n\n"
                "専門用語は題材が違えば当然ずれるので、ひらがなが半分以上を占める\n"
                "言い回しだけを残してある。\n\n---\n\n")
    if '--stdout' in sys.argv:
        sys.stdout.write(head + out + "\n")
        return
    if '--write' in sys.argv:
        dst = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'style', 'vocabulary.md')
        open(dst, 'w', encoding='utf-8').write(head + out + "\n")
        print("wrote", dst)
    print(out)

main()
