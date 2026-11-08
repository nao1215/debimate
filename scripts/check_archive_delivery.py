#!/usr/bin/env python3
"""Verify bounded archive pages, ordered complete traversal, and lazy game media."""
import argparse
import gzip
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.cards, self.weeks, self.entries = [], 0, []
        self.next, self.prev = None, None
        self.videos, self.demos, self.anchor_index = [], [], None
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'a':
            if 'listing-card-link' in classes:
                self.cards.append(urlparse(attrs['href']).path)
            if attrs.get('rel') in {'prev', 'next'}:
                setattr(self, attrs['rel'], attrs['href'])
        if attrs.get('data-anchor-index'):
            self.anchor_index = attrs['data-anchor-index']
        if 'weeknotes-index-week' in classes:
            self.weeks += 1
        if 'weeknotes-entry-title' in classes:
            self.entries.append(attrs['id'])
        if tag == 'video':
            self.videos.append(attrs)
        if tag == 'img' and '-demo' in attrs.get('src', ''):
            self.demos.append(attrs)


def traversal(root, path):
    seen = set()
    pages = []
    while path:
        path = urlparse(path).path
        assert path not in seen, f'Pagination cycle: {path}'
        seen.add(path)
        page = Page(root / path.strip('/') / 'index.html')
        if pages:
            assert urlparse(page.prev or '').path == pages[-1][0], f'Broken previous link: {path}'
        pages.append((path, page))
        path = page.next
    return pages


def check(root, baseline=None):
    report = {}
    years = sorted(p.parent.name for p in (root / 'weeknotes').glob('[0-9][0-9][0-9][0-9]/index.html'))
    for path in ['/post/', '/post/ja/', '/weeknotes/', *[f'/weeknotes/{y}/' for y in years]]:
        pages = traversal(root, path)
        cards, entries = [], []
        for _, page in pages:
            if path.startswith('/post/'):
                assert 0 < len(page.cards) <= 20
            elif path == '/weeknotes/':
                assert 0 < page.weeks <= 2
            else:
                assert len(page.entries) == 1
            cards.extend(page.cards)
            entries.extend(page.entries)
        assert len(cards) == len(set(cards)), f'Duplicate cards: {path}'
        assert len(entries) == len(set(entries)), f'Duplicate weeks: {path}'
        if entries:
            targets = {entry: url for url, page in pages for entry in page.entries}
            for _, page in pages:
                assert page.anchor_index
                index = json.loads((root / urlparse(page.anchor_index).path.lstrip('/')).read_text())
                for anchor, url in targets.items():
                    assert index.get(anchor) == url
        if baseline:
            old = Page(baseline / path.strip('/') / 'index.html')
            assert cards == old.cards, f'Missing or reordered cards: {path}'
            assert entries == old.entries, f'Missing or reordered weeks: {path}'
        data = (root / path.strip('/') / 'index.html').read_bytes()
        report[path] = {'pages': len(pages), 'html_bytes': len(data), 'gzip_bytes': len(gzip.compress(data, mtime=0))}
        if baseline:
            old_data = (baseline / path.strip('/') / 'index.html').read_bytes()
            report[path]['before_bytes'] = len(old_data)
            report[path]['before_gzip_bytes'] = len(gzip.compress(old_data, mtime=0))
    games = Page(root / 'games/index.html')
    assert not games.videos, 'Games must use animated images, not video players'
    assert len(games.demos) == 3
    for i, demo in enumerate(games.demos):
        assert demo['loading'] == ('eager' if i == 0 else 'lazy')
        assert demo.get('srcset') and demo.get('sizes')
        assert (root / unquote(demo['src']).lstrip('/')).is_file()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path('public'))
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    check(args.root, args.baseline)
