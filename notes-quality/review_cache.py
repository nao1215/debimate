#!/usr/bin/env python3
"""ノートの精読キャッシュ（debimate-note-review スキルが使う）。scan は記事を読んだことにしない。標準ライブラリだけ。

    python3 notes-quality/review_cache.py scan
    python3 notes-quality/review_cache.py inspect <index.md> [--extra <path>]
    python3 notes-quality/review_cache.py diff <index.md>
    python3 notes-quality/review_cache.py record <index.md> --expected <fingerprint> --level complete|partial --evidence <json>

記録は notes-quality/reviews/<区分>__<スラッグ>.json に記事ごとに置き、git で管理する（2026-11-12、
SQLite の .note-review/reviews.sqlite3 から移した。別の環境でも同じ記録を使うため）。
確認時点の本文は保存しない。代わりに git_head と、各テキストファイルの git の blob を残す。
blob が手元に無い環境では git_head との差分だけを見る。
描画に効く共通ファイル（shortcode・partial・CSS・JS・config）のハッシュは reviews/_shared/<指紋>.json に 1 回だけ置く。
"""
import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TEXT_EXT = {'.md', '.txt', '.py', '.sh', '.json', '.yaml', '.yml', '.toml', '.html', '.css', '.js', '.go', '.rs'}


def now():
    return datetime.now(timezone.utc).isoformat()


def git(repo, *args, data=None):
    p = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=data is None,
                       input=data)
    if p.returncode != 0:
        return None
    return p.stdout.strip() if data is None else p.stdout.decode().strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def key_of(article):
    parts = Path(article).parts
    return f'{parts[-3]}__{parts[-2]}'


def snapshot(repo, article, extra=()):
    page = (repo / article).resolve()
    page.relative_to(repo)
    if not page.is_file():
        raise ValueError('Article does not exist: ' + article)
    paths = {p for p in page.parent.rglob('*') if p.is_file() and not any(
        s in {'.git', '.venv', '__pycache__', 'node_modules', 'target'} for s in p.parts)}
    generator = repo / 'projects/ml/scripts/notes' / (page.parent.name + '_gen.py')
    if article.startswith('projects/ml/notes/') and generator.exists():
        paths.add(generator)
    for item in extra:
        p = (repo / item).resolve()
        p.relative_to(repo)
        paths.add(p)
    files, texts = {}, {}
    for p in sorted(paths):
        p = p.resolve()
        k = str(p.relative_to(repo))
        if not p.exists():
            files[k] = None
            continue
        b = p.read_bytes()
        files[k] = digest(b)
        if p.suffix.lower() in TEXT_EXT and len(b) <= 1_000_000:
            texts[k] = b
    shared = {}
    for base in ['layouts/shortcodes', 'layouts/partials', 'assets/css', 'assets/js', 'config']:
        for p in sorted((repo / base).rglob('*')):
            if p.is_file():
                shared[str(p.relative_to(repo))] = digest(p.read_bytes())
    manifest = {'files': files, 'shared': shared, 'extra': sorted(extra)}
    manifest['fingerprint'] = digest(json.dumps(manifest, sort_keys=True).encode())
    return manifest, texts


class Store:
    def __init__(self, path):
        self.path = path
        (path / '_shared').mkdir(parents=True, exist_ok=True)

    def _write(self, p, obj):
        tmp = p.with_suffix(p.suffix + f'.tmp{os.getpid()}')
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        os.replace(tmp, p)

    def load(self, article):
        p = self.path / f'{key_of(article)}.json'
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

    def shared(self, fp):
        p = self.path / '_shared' / f'{fp}.json'
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

    def manifest(self, rec):
        m = rec['latest']['manifest']
        return {'files': m['files'], 'shared': self.shared(m['shared_fingerprint']), 'extra': m['extra'],
                'fingerprint': m['fingerprint']}

    def save(self, article, review, manifest, history_from=None):
        sfp = digest(json.dumps(manifest['shared'], sort_keys=True).encode())
        sp = self.path / '_shared' / f'{sfp}.json'
        if not sp.exists():
            self._write(sp, manifest['shared'])
        review = dict(review)
        review['manifest'] = {'files': manifest['files'], 'shared_fingerprint': sfp, 'extra': manifest['extra'],
                              'fingerprint': manifest['fingerprint']}
        old = history_from if history_from is not None else self.load(article)
        history = (old or {}).get('history', [])
        if old and 'latest' in old:
            lv = old['latest']
            history = history + [{'reviewed_at': lv['reviewed_at'], 'level': lv['level'], 'git_head': lv.get('git_head'),
                                  'judgment': lv['evidence'].get('judgment')}]
        self._write(self.path / f'{key_of(article)}.json', {'article': article, 'latest': review, 'history': history})

    def articles(self):
        out = set()
        for p in self.path.glob('*.json'):
            try:
                out.add(json.loads(p.read_text(encoding='utf-8'))['article'])
            except (ValueError, KeyError):
                pass
        return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    parser.add_argument('--repo', type=Path, default=here.parent)
    parser.add_argument('--store', type=Path, default=None, help='既定は <repo>/notes-quality/reviews')
    parser.add_argument('--db', type=Path, default=None, help='廃止（SQLite から JSON に移した）。指定しても使わない')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('scan')
    for name in ['inspect', 'diff', 'record']:
        p = sub.add_parser(name)
        p.add_argument('article')
        p.add_argument('--extra', action='append', default=[])
        if name == 'record':
            p.add_argument('--evidence', type=Path, required=True)
            p.add_argument('--expected', required=True, help='読む前に inspect で得た fingerprint')
            p.add_argument('--level', choices=['partial', 'complete'], required=True)
    args = parser.parse_args()
    if args.db:
        print('注意: --db は廃止。notes-quality/reviews の JSON を使う', file=sys.stderr)
    repo = args.repo.resolve()
    store = Store((args.store or repo / 'notes-quality/reviews').resolve())

    if args.command == 'scan':
        articles = sorted(str(p.relative_to(repo)) for base in ['content/notes', 'projects/ml/notes']
                          for p in (repo / base).rglob('index.md') if p.parent.name != 'quiz')
        result = []
        for article in articles:
            rec = store.load(article)
            extra = rec['latest']['manifest']['extra'] if rec else []
            manifest, _ = snapshot(repo, article, extra)
            status = 'unread'
            if rec:
                if manifest['fingerprint'] != rec['latest']['manifest']['fingerprint']:
                    status = 'changed'
                elif rec['latest']['level'] != 'complete':
                    status = 'incomplete'
                else:
                    status = 'unchanged'
            result.append({'article': article, 'status': status,
                           'reviewed_at': rec['latest']['reviewed_at'] if rec else None,
                           'fingerprint': manifest['fingerprint']})
        known = store.articles()
        counts = {s: sum(r['status'] == s for r in result) for s in ['unread', 'incomplete', 'changed', 'unchanged']}
        print(json.dumps({'scanned_at': now(), 'counts': counts,
                          'selection_ready': all(r['status'] == 'unchanged' for r in result) and bool(result),
                          'removed': sorted(a for a in known - set(articles) if Path(a).parent.name != 'quiz'),
                          'excluded': sorted(a for a in known if Path(a).parent.name == 'quiz'),
                          'articles': result}, ensure_ascii=False, indent=2))
        return

    article = str((repo / args.article).resolve().relative_to(repo))
    rec = store.load(article)
    extra = sorted(set(args.extra + (rec['latest']['manifest']['extra'] if rec else [])))
    manifest, texts = snapshot(repo, article, extra)
    if args.command == 'inspect':
        print(json.dumps({'manifest': manifest, 'last_review': rec}, ensure_ascii=False, indent=2))
    elif args.command == 'diff':
        if not rec:
            raise ValueError('No baseline: read the entire article')
        lv = rec['latest']
        old = store.manifest(rec)
        print('Baseline review:', lv['reviewed_at'], 'Git HEAD:', lv.get('git_head'))
        if lv.get('git_head'):
            paths = sorted(set(old['files']) | set(manifest['files']))
            print(git(repo, 'diff', '--no-ext-diff', lv['git_head'], '--', *paths) or '(No Git diff or baseline unavailable.)')
        print('\nDiff from the reviewed version of each file (git blob, includes uncommitted baseline when available):')
        blobs = lv.get('blobs', {})
        for k in sorted(set(old['files']) | set(manifest['files'])):
            if old['files'].get(k) == manifest['files'].get(k):
                continue
            print('CHANGED', k)
            b = blobs.get(k)
            before = git(repo, 'cat-file', '-p', b) if b else None
            if before is None and lv.get('git_head'):
                before = git(repo, 'show', f"{lv['git_head']}:{k}")
                if before is not None:
                    print('(baseline blob unavailable here; using the file at git_head)')
            now_text = texts.get(k, b'').decode('utf-8', 'replace') if k in texts else None
            if before is not None or now_text is not None:
                print(''.join(difflib.unified_diff((before or '').splitlines(True), (now_text or '').splitlines(True),
                                                   fromfile='reviewed/' + k, tofile='current/' + k)))
            else:
                print('Binary or large file: inspect rendered output/content directly.')
        for k in sorted(set(old['shared']) | set(manifest['shared'])):
            if old['shared'].get(k) != manifest['shared'].get(k):
                print('SHARED RENDERING CHANGE', k)
    else:
        if manifest['fingerprint'] != args.expected:
            raise ValueError('Files changed since inspect: review the new diff before recording')
        evidence = json.loads(args.evidence.read_text())
        if not evidence.get('judgment') or not evidence.get('reason'):
            raise ValueError('Evidence requires judgment and reason')
        if args.level == 'complete':
            for k in ['body', 'figures', 'code_results', 'sources', 'limitations']:
                if not isinstance(evidence.get(k), str) or not evidence[k].strip():
                    raise ValueError('Complete review requires explicit evidence: ' + k)
        blobs = {k: git(repo, 'hash-object', '-w', '--stdin', data=b) for k, b in texts.items()}
        store.save(article, {'reviewed_at': now(), 'git_head': git(repo, 'rev-parse', 'HEAD'),
                             'source_updated_at': git(repo, 'log', '-1', '--format=%cI', '--', article),
                             'level': args.level, 'blobs': blobs, 'evidence': evidence}, manifest)
        print(json.dumps({'article': article, 'level': args.level, 'reviewed_at': now()}))


if __name__ == '__main__':
    main()
