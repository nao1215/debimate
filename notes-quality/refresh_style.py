#!/usr/bin/env python3
"""本人の実文から、文体の基準を作り直す（2026-11-12）。

    python3 notes-quality/refresh_style.py           # 作り直して書き出す
    python3 notes-quality/refresh_style.py --check   # 書き出し済みのものが古ければ終了コード 1（CI 用）

本人の実文 = content/post/ja の技術記事（style/corpus_nontechnical.txt と style/corpus_llm_written.txt を除く）
            + content/weeknotes。表記の揺れは 2023 年以降だけで数える（2026-11-02 著者の指定）。

書き出すもの（どれも手で書き足さない）:
- style/variants.tsv: style/variant_groups.tsv の組ごとの、本人の使用数と割合。gate.py が使う
- style/vocabulary.md: build_vocab.py による、本人の実文とノートの言い回しの差
- style/corpus.sha256: 学習に使う本文のハッシュ。omokage のプロファイルを作り直すかの判定に使う

GitHub Actions（.github/workflows/style-refresh.yml）が週 1 回走らせ、変わっていれば main に commit する（2026-11-13 から。以前は pre-commit で毎回）。
"""
import csv, glob, hashlib, io, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STYLE = os.path.join(HERE, 'style')
SINCE = '2023'


def listfile(name):
    p = os.path.join(STYLE, name)
    return {l.strip() for l in open(p, encoding='utf-8') if l.strip() and not l.startswith('#')} if os.path.exists(p) else set()


def tech_posts():
    skip = listfile('corpus_nontechnical.txt') | listfile('corpus_llm_written.txt')
    out = []
    for d in sorted(glob.glob(os.path.join(ROOT, 'content/post/ja/*/'))):
        name = os.path.basename(d.rstrip('/'))
        if name not in skip and os.path.exists(os.path.join(d, 'index.md')):
            out.append(os.path.join(d, 'index.md'))
    return out


def weeknotes():
    return sorted(glob.glob(os.path.join(ROOT, 'content/weeknotes/*/*/index.md')))


def recent(paths):
    out = []
    for p in paths:
        head = open(p, encoding='utf-8').read(600)
        m = re.search(r'^date:\s*"?(\d{4})', head, re.M)
        y = m.group(1) if m else re.search(r'/(\d{4})[-/]', p).group(1) if re.search(r'/(\d{4})[-/]', p) else '0'
        if y >= SINCE:
            out.append(p)
    return out


def prose(md):
    md = re.sub(r'^---.*?\n---\n', '', md, flags=re.S)
    md = re.sub(r'```.*?```', '', md, flags=re.S)
    md = re.sub(r'`[^`]*`', '', md)
    md = re.sub(r'\]\([^)]*\)|https?://\S+', '', md)
    return md


def variants():
    texts = [prose(open(p, encoding='utf-8').read()) for p in recent(tech_posts()) + recent(weeknotes())]
    rows = [r for r in csv.reader(open(os.path.join(STYLE, 'variant_groups.tsv'), encoding='utf-8'), delimiter='\t')
            if r and not r[0].startswith('#')]
    counts = {}
    for g, mode, form, rx in rows:
        pat = re.compile(rx)
        counts[(g, form)] = (mode, rx, sum(len(pat.findall(t)) for t in texts))
    out = io.StringIO()
    out.write(f'# refresh_style.py が {len(texts)} 本（{SINCE} 年以降の技術記事と weeknotes）から数えた。手で書き足さない\n')
    w = csv.writer(out, delimiter='\t', lineterminator='\n')
    w.writerow(['組', 'mode', '形', '本人の使用数', '組の中の割合', '正規表現'])
    for g in dict.fromkeys(r[0] for r in rows):
        total = sum(c[2] for (gg, _), c in counts.items() if gg == g)
        for (gg, form), (mode, rx, n) in counts.items():
            if gg == g:
                w.writerow([g, mode, form, n, f'{n / total:.3f}' if total else '0', rx])
    return out.getvalue()


def corpus_hash():
    h = hashlib.sha256()
    for p in tech_posts():
        h.update(os.path.relpath(p, ROOT).encode())
        h.update(open(p, 'rb').read())
    return h.hexdigest() + '\n'


def vocabulary():
    r = subprocess.run([sys.executable, os.path.join(HERE, 'build_vocab.py'), '--stdout'], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr)
    return r.stdout


def main():
    check = '--check' in sys.argv
    outputs = {'variants.tsv': variants(), 'corpus.sha256': corpus_hash(), 'vocabulary.md': vocabulary()}
    stale = []
    for name, text in outputs.items():
        p = os.path.join(STYLE, name)
        old = open(p, encoding='utf-8').read() if os.path.exists(p) else None
        if old != text:
            stale.append(name)
            if not check:
                open(p, 'w', encoding='utf-8').write(text)
    if check:
        if stale:
            print('古い: ' + ', '.join(f'notes-quality/style/{n}' for n in stale) + '（python3 notes-quality/refresh_style.py で作り直す）')
            return 1
        print('OK: 文体の基準は本人の実文と一致')
        return 0
    print('作り直した: ' + (', '.join(stale) if stale else 'なし（変更なし）'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
