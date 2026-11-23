"""Print the per-variant table from output/results.json (used for output/summary.txt).
Usage: python3 make_summary.py [results.json]
"""
import json
import sys
from pathlib import Path


def ranges(xs):
    xs = sorted(xs)
    out, i = [], 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1:
            j += 1
        out.append(f'{xs[i]}' if i == j else f'{xs[i]}-{xs[j]}')
        i = j + 1
    return ','.join(out) or '-'


def main():
    p = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / 'output/results.json')
    R = json.loads(p.read_text())
    print('versions:', json.dumps(R.get('_versions'), ensure_ascii=False))
    for k, r in R.items():
        if k.startswith('_'):
            continue
        dup = [d for d in r['delivered'] if d['count'] > 1]
        print(f'\n[{k}] expected {len(r["expected"])} ({ranges(r["expected"])})')
        print(f'  delivered(200) {len(r["delivered"])}  missing {len(r["missing"])} ({ranges(r["missing"])})'
              f'  duplicated {len(dup)} ({", ".join(f"{d["amount"]}x{d["count"]}" for d in dup) or "-"})')
        if r.get('reorged_out_amounts'):
            print(f'  reorged-out amounts {r["reorged_out_amounts"]} delivered anyway {r["reorged_out_delivered"]}')
        print(f'  retractions {len(r["retractions"])}  alive_at_end {r["alive_at_end"]} exit {r.get("exit_code")}')
        failed = sum(1 for x in r.get('webhook_posts', []) if x['status'] != 200)
        if failed:
            print(f'  webhook POSTs answered 500: {failed}')
        late = [d for d in r['delivered'] for e in r['emitted'] if e['amount'] == d['amount'] and d['t'] - e['t'] > 5]
        if late:
            mx = max(d['t'] - e['t'] for d in r['delivered'] for e in r['emitted'] if e['amount'] == d['amount'])
            print(f'  delivered >5 s after emission: {len(late)} (max {mx:.1f} s)')
        for c in r.get('controls', []):
            print(f'  t={c["t"]:>7.1f} {c["what"][:160]}')
        for line in r.get('log_highlights', [])[:14]:
            print('   log|', line[:220])


main()
