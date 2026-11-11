#!/usr/bin/env python3
"""Read the front matter (category, status, requires) of the EIPs and ERCs used in the note.

Usage: EIPS_SRC=/path/to/EIPs ERCS_SRC=/path/to/ERCs python3 eip_graph.py
Both checkouts must be at the commits below. Output: output/eip_graph.json
Only `requires` in the front matter becomes an edge. Links in the prose do not.
"""
import json
import os
from pathlib import Path
import re
import subprocess

COMMITS = {'EIPs': '542e62eb129517130b7facc52bbb9a1f333c711e',
           'ERCs': 'f94e400afdddaa2625c291f71646bde0ef44df9d'}
# Proposals that appear in the note, plus the direct requires of each.
SEEDS = [20, 165, 191, 712, 721, 1155, 1271, 2612, 4337, 7562, 155, 214, 7702]
OUT = Path(__file__).resolve().parent / 'output' / 'eip_graph.json'


def front_matter(path):
    text = path.read_text()
    block = re.match(r'\A---\s*\n(.*?)\n---', text, re.S)[1]
    fields = dict(re.findall(r'^([a-z-]+):\s*(.*)$', block, re.M))
    return fields, block.count('\n') + 2


def load(number):
    for repo, sub, prefix in (('ERCs', 'ERCS', 'erc'), ('EIPs', 'EIPS', 'eip')):
        root = Path(os.environ[repo.upper() + '_SRC'])
        path = root / sub / f'{prefix}-{number}.md'
        if not path.exists():
            continue
        fm, end = front_matter(path)
        if fm.get('status') == 'Moved':
            continue
        category = fm.get('category') or fm['type']
        requires = [int(x) for x in re.findall(r'\d+', fm.get('requires', ''))]
        return {
            'id': f"{'ERC' if category == 'ERC' else 'EIP'}-{number}",
            'title': fm['title'].strip('"'), 'category': category, 'status': fm['status'],
            'requires': requires,
            'url': f'https://github.com/ethereum/{repo}/blob/{COMMITS[repo]}/{sub}/{path.name}#L1-L{end}',
        }
    raise FileNotFoundError(number)


def main():
    for repo, commit in COMMITS.items():
        head = subprocess.check_output(['git', '-C', os.environ[repo.upper() + '_SRC'], 'rev-parse', 'HEAD'], text=True)
        assert head.strip() == commit, repo
    nodes = {}
    for n in SEEDS:
        nodes[n] = load(n)
    for n in list(nodes):
        for r in nodes[n]['requires']:
            nodes.setdefault(r, load(r))
    graph = {'commits': COMMITS, 'seeds': SEEDS,
             'nodes': [nodes[n] for n in sorted(nodes)],
             'edges': [{'from': nodes[n]['id'], 'to': nodes[r]['id']}
                       for n in SEEDS for r in nodes[n]['requires']]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n')
    print(f"{len(graph['nodes'])} nodes, {len(graph['edges'])} requires edges")


if __name__ == '__main__':
    main()
