#!/usr/bin/env python3
"""Refresh the GitHub Sponsors lists shown on /oss/ before Hugo builds (requires gh).

Two lists: who sponsors nao1215 (sponsors) and whom nao1215 sponsors (sponsoring).
The API returns current sponsorships only, so one that ends is removed on the
next build. An account is kept only when the logged-out GitHub page also shows
it, so a private sponsorship never appears even if the token can see it.
When any source fails, the last snapshot stays as it is.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from zoneinfo import ZoneInfo

SNAPSHOT = Path(__file__).resolve().parents[1] / 'data/sponsors.json'
MAINTAINER = 'nao1215'
PUBLIC_PAGES = {
    'sponsors': f'https://github.com/sponsors/{MAINTAINER}',
    'sponsoring': f'https://github.com/{MAINTAINER}?tab=sponsoring',
}
ACCOUNT = '__typename ... on User { login name url avatarUrl(size: 96) } ... on Organization { login name url avatarUrl(size: 96) }'
QUERY = 'query { user(login: "%s") { sponsors(first: 100) { nodes { %s } } sponsoring(first: 100) { nodes { %s } } } }' % (
    MAINTAINER, ACCOUNT, ACCOUNT)
LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})')


def current_accounts(response, field):
    if response.get('errors') or not isinstance(response.get('data'), dict):
        raise ValueError('GitHub returned an incomplete response')
    user = response['data'].get('user')
    nodes = ((user or {}).get(field) or {}).get('nodes')
    if not isinstance(nodes, list):
        raise ValueError(f'Missing {field} list')
    accounts = []
    for node in nodes:
        login = node.get('login') if isinstance(node, dict) else None
        if not isinstance(login, str) or not LOGIN.fullmatch(login):
            raise ValueError(f'Invalid login: {login!r}')
        url, avatar = node.get('url'), node.get('avatarUrl')
        if url != f'https://github.com/{login}' or not str(avatar).startswith('https://avatars.githubusercontent.com/'):
            raise ValueError(f'Unexpected URL for {login}')
        accounts.append({'login': login, 'name': node.get('name') or login, 'url': url, 'avatar': avatar})
    return accounts


def public_logins(html):
    # Both pages link each account's avatar with the hovercard of their profile.
    if 'hovercard' not in html:
        raise ValueError('The public GitHub page did not look as expected')
    return set(re.findall(r'data-hovercard-url="/(?:users|orgs)/([A-Za-z0-9-]+)/hovercard"', html))


def snapshot(accounts, visible, date):
    result = {'asOf': date}
    for field in PUBLIC_PAGES:
        result[field] = [a for a in accounts[field] if a['login'] in visible[field]]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    try:
        response = subprocess.run(
            ['gh', 'api', 'graphql', '--input', '-'],
            input=json.dumps({'query': QUERY}), text=True, capture_output=True, check=True,
        )
        data = json.loads(response.stdout)
        accounts = {field: current_accounts(data, field) for field in PUBLIC_PAGES}
        visible = {}
        for field, url in PUBLIC_PAGES.items():
            request = urllib.request.Request(url, headers={'User-Agent': 'debimate-site-build'})
            with urllib.request.urlopen(request, timeout=30) as page:
                visible[field] = public_logins(page.read().decode('utf-8', 'replace'))
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f'::warning::Kept the last sponsors snapshot: {error}', file=sys.stderr)
        return
    result = snapshot(accounts, visible, datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat())
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(args.output)
    for field in PUBLIC_PAGES:
        print(f'Updated {field}: {[a["login"] for a in result[field]]}')


if __name__ == '__main__':
    main()
