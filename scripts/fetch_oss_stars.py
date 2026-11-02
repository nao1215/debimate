#!/usr/bin/env python3
"""Refresh the OSS catalog's star snapshot before Hugo builds (requires gh)."""
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

CATALOG = Path(__file__).resolve().parents[1] / 'data/oss_catalog.json'


def query_for(catalog):
    names = [project['name'] for project in catalog['projects']]
    if not names or len(set(names)) != len(names):
        raise ValueError('Catalog must contain unique repositories')
    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+', name) for name in names):
        raise ValueError('Invalid repository name')
    return 'query { ' + ' '.join(
        f'r{i}: repository(owner: "nao1215", name: "{name}") {{ stargazerCount }}'
        for i, name in enumerate(names)
    ) + ' }'


def updated_catalog(catalog, response, date):
    if response.get('errors') or not isinstance(response.get('data'), dict):
        raise ValueError('GitHub returned an incomplete response')
    result = copy.deepcopy(catalog)
    for i, project in enumerate(result['projects']):
        repo = response['data'].get(f'r{i}')
        stars = repo.get('stargazerCount') if isinstance(repo, dict) else None
        if type(stars) is not int or stars < 0:
            raise ValueError(f'Missing or invalid star count for {project["name"]}')
        project['stars'] = stars
    result['asOf'] = date
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--output', type=Path, help='Defaults to updating the catalog in place')
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())
    response = subprocess.run(
        ['gh', 'api', 'graphql', '--input', '-'],
        input=json.dumps({'query': query_for(catalog)}), text=True,
        capture_output=True, check=True,
    )
    result = updated_catalog(catalog, json.loads(response.stdout), datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat())
    output = args.output or args.catalog
    # Validate every repository before replacing the last complete snapshot.
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(output)
    print(f'Updated OSS star counts: {output}')


if __name__ == '__main__':
    main()
