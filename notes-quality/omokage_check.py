#!/usr/bin/env python3
"""ノートの地の文を、本人の技術記事で学習した omokage のプロファイルと比べる（2026-11-12）。

    python3 notes-quality/omokage_check.py <index.md>             # 一致度（%）を 1 行で出す
    python3 notes-quality/omokage_check.py --explain <index.md>   # 崩れた段落と、直しやすい差を出す

プロファイルは git に入れない。学習に使う本文（refresh_style.py と同じ技術記事の集合）のハッシュごとに
${XDG_CACHE_HOME:-~/.cache}/debimate-omokage/<ハッシュ>/ へ作り、本文が変われば作り直す（初回は 1 分ほど）。
omokage が無い環境では終了コード 2 で何も出さない（gate.py は判定を飛ばす）。
"""
import hashlib, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from refresh_style import tech_posts, ROOT  # noqa: E402

AUTHOR = 'nao-tech'


def main():
    explain = '--explain' in sys.argv
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(files) != 1:
        sys.exit(__doc__)
    if not shutil.which('omokage'):
        return 2
    posts = tech_posts()
    h = hashlib.sha256()
    for p in posts:
        h.update(os.path.relpath(p, ROOT).encode()); h.update(open(p, 'rb').read())
    cache = os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), 'debimate-omokage', h.hexdigest()[:16])
    cfg = os.path.join(cache, 'store', 'omokage.toml')
    if not os.path.exists(os.path.join(cache, 'store', 'profiles', f'{AUTHOR}.db')):
        stage = os.path.join(cache, 'corpus')
        shutil.rmtree(cache, ignore_errors=True)
        os.makedirs(stage)
        for i, p in enumerate(posts):
            shutil.copy(p, os.path.join(stage, f'{i:04d}.md'))
        os.makedirs(os.path.join(cache, 'store'))
        subprocess.run(['omokage', 'init', '--name', 'debimate'], cwd=os.path.join(cache, 'store'), check=True, capture_output=True)
        print(f'omokage のプロファイルを {len(posts)} 本で作り直しています（1 分ほど）', file=sys.stderr)
        subprocess.run(['omokage', 'train', '--config', cfg, '--author', AUTHOR, stage], check=True, capture_output=True)
        shutil.rmtree(stage)
    r = subprocess.run(['omokage', 'check', '--config', cfg, '--author', AUTHOR, '--explain' if explain else '--score-only', os.path.abspath(files[0])],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return 1
    print(r.stdout.strip())
    return 0


if __name__ == '__main__':
    sys.exit(main())
