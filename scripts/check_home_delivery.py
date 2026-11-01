#!/usr/bin/env python3
"""Check homepage batches and report HTML size. Optionally compare an old build."""
import argparse
import gzip
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class Cards(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.sections = {}
        self.current = None
        self.links = []
        self.elements = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements += 1
        if tag == 'section' and attrs.get('aria-labelledby', '').startswith('home-'):
            self.current = {'links': [], 'next': '', 'total': 0}
            self.sections[attrs['aria-labelledby']] = self.current
        if tag == 'a' and 'entry-link' in attrs.get('class', '').split():
            # Ignore origin so local before/after builds can use separate ports.
            link = unquote(urlparse(attrs['href']).path)
            self.links.append(link)
            if self.current is not None:
                self.current['links'].append(link)
        if attrs.get('data-next') and self.current is not None:
            self.current['next'] = attrs['data-next']
            self.current['total'] = int(attrs['data-total'])

    def handle_endtag(self, tag):
        if tag == 'section':
            self.current = None


def check(root, baseline=None):
    raw = (root / 'index.html').read_bytes()
    home = Cards(raw.decode())
    old = Cards((baseline / 'index.html').read_text()) if baseline else None
    sizes = []
    summary = {}
    assert len(home.sections) == 3
    for name, section in home.sections.items():
        batch = 6 if name == 'home-posts-title' else 3
        assert len(section['links']) <= batch, f'{name}: too many inline cards'
        links = list(section['links'])
        next_url = section['next']
        seen = set()
        while next_url:
            assert next_url not in seen, f'{name}: batch cycle'
            seen.add(next_url)
            url = urlparse(next_url)
            assert not url.netloc and url.path.startswith('/assets/home/'), next_url
            path = root / unquote(url.path).lstrip('/')
            sizes.append(path.stat().st_size)
            payload = json.loads(path.read_text())
            cards = Cards(payload['html'])
            assert 0 < len(cards.links) <= batch, f'{name}: invalid batch size'
            links.extend(cards.links)
            next_url = payload['next']
        assert len(set(links)) == len(links), f'{name}: duplicate card'
        assert len(links) == (section['total'] or len(section['links'])), f'{name}: missing cards'
        for link in links:
            assert (root / link.lstrip('/') / 'index.html').is_file(), f'Missing page: {link}'
        if old:
            assert links == old.sections[name]['links'], f'{name}: changed order or missing cards'
        summary[name] = {'initial': len(section['links']), 'total': len(links), 'batches': len(seen)}
    result = {'html_bytes': len(raw), 'gzip_bytes': len(gzip.compress(raw, mtime=0)),
              'elements': home.elements, 'largest_batch_bytes': max(sizes, default=0), 'lists': summary}
    if baseline:
        before = (baseline / 'index.html').read_bytes()
        result['before'] = {'html_bytes': len(before), 'gzip_bytes': len(gzip.compress(before, mtime=0)), 'elements': old.elements}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path('public'))
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    check(args.root, args.baseline)
