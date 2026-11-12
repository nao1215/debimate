#!/usr/bin/env python3
"""相互リンクの抜けを見つける（2026-11-12 著者の指定）。

    python3 notes-quality/crosslinks.py                 # 全ノートの抜けの候補
    python3 notes-quality/crosslinks.py <index.md>      # 1 本の抜けの候補（gate.py が使う）

各ノートの題の頭（「 - 」の前。「・」で区切った語ごと）を、そのノートの題材の語とする。別のノートの本文
（コード・引用・front matter を除く）にその語が出るのに、そのノートへのリンクが 1 本も無ければ候補にする。
語は大文字と小文字を区別しない。短すぎる語と、どこにでも出る語は style/crosslink_stop.txt で外す。
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MIN_LEN = 3


def notes():
    out = {}
    for base, url in (('content/notes', '/notes/'), ('projects/ml/notes', '/ml/')):
        for p in sorted(glob.glob(os.path.join(ROOT, base, '*', '*', 'index.md'))):
            sec, slug = p.split('/')[-3], p.split('/')[-2]
            if slug == 'quiz':
                continue
            text = open(p, encoding='utf-8').read()
            m = re.search(r'^title:\s*"?(.*?)"?\s*$', text, re.M)
            title = m.group(1) if m else slug
            out[os.path.relpath(p, ROOT)] = {'url': f'{url}{sec}/{slug}/', 'slug': slug, 'title': title, 'text': text}
    return out


def stopwords():
    p = os.path.join(HERE, 'style', 'crosslink_stop.txt')
    return {l.strip().lower() for l in open(p, encoding='utf-8') if l.strip() and not l.startswith('#')} if os.path.exists(p) else set()


def terms(title, stop):
    head = title.split(' - ', 1)[0]
    head = re.sub(r'（[^）]*）|\([^)]*\)', '', head)
    out = []
    for t in re.split(r'[・、/]| と ', head):
        t = t.strip()
        if len(t) >= MIN_LEN and t.lower() not in stop:
            out.append(t)
    return out


def prose(text):
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S)
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'\{\{<[^>]*>\}\}', '', text)
    return '\n'.join(l for l in text.splitlines() if not l.lstrip().startswith(('>', '#')))


def links_to(text, target):
    slug = re.escape(target['slug'])
    return re.search(r'\]\([^)]*(?:^|/|\.\./)' + slug + r'/?(?:#[^)]*)?\)', text) is not None


def candidates(rel, all_notes, stop):
    me = all_notes[rel]
    body = prose(me['text'])
    found = []
    for orel, o in all_notes.items():
        if orel == rel or o['slug'] == me['slug']:
            continue
        if links_to(me['text'], o):
            continue
        for t in terms(o['title'], stop):
            rx = re.compile(r'(?<![A-Za-z0-9_-])' + re.escape(t) + r'(?![A-Za-z0-9_-])', re.I)
            hits = [i + 1 for i, l in enumerate(body.splitlines()) if rx.search(re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', l))]
            if hits:
                found.append((t, o['url'], len(hits)))
                break
    return found


def main():
    all_notes, stop = notes(), stopwords()
    targets = [os.path.relpath(os.path.abspath(a), ROOT) for a in sys.argv[1:]] or list(all_notes)
    total = 0
    for rel in targets:
        if rel not in all_notes:
            continue
        c = candidates(rel, all_notes, stop)
        total += len(c)
        if c and (len(targets) == 1 or '--all' not in sys.argv):
            print(rel + ': ' + '、'.join(f'「{t}」{n} 回 → {u}' for t, u, n in c))
    if len(targets) > 1:
        print(f'候補 {total} 件 / {len(targets)} 本')
    return 0


if __name__ == '__main__':
    sys.exit(main())
