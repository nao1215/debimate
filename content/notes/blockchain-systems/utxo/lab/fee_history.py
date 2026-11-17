"""Median fee rate of Bitcoin blocks over 3 years, from the public mempool.space API.

    python3 fee_history.py                 # fetches https://mempool.space/api/v1/mining/blocks/fee-rates/3y once
    python3 fee_history.py saved.json      # or reads a saved copy of that response

Writes output/fee_rates_3y.csv (time, block height, median fee rate in sat/vB) and
prints, per year, how often the median was at or above the break-even rate of a
1,000 sat P2WPKH coin (1000 / 68 = 14.7 sat/vB). Fetched on 2026-11-17 for the note.
"""
import csv
import datetime as dt
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

URL = 'https://mempool.space/api/v1/mining/blocks/fee-rates/3y'
BREAK_EVEN = 1000 / 68

if len(sys.argv) > 1:
    rows = json.loads(Path(sys.argv[1]).read_text())
else:
    with urllib.request.urlopen(URL, timeout=30) as response:
        rows = json.load(response)

out = Path(__file__).resolve().parent / 'output'
out.mkdir(exist_ok=True)
by_year = defaultdict(list)
with (out / 'fee_rates_3y.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['utc', 'avg_height', 'median_sat_per_vb'])
    for r in rows:
        t = dt.datetime.fromtimestamp(r['timestamp'], dt.UTC)
        w.writerow([t.strftime('%Y-%m-%dT%H:%M'), r['avgHeight'], r['avgFee_50']])
        by_year[t.year].append(r['avgFee_50'])

lines = [f'source: {URL}', f'points: {len(rows)}']
for year, values in sorted(by_year.items()):
    above = sum(v >= BREAK_EVEN for v in values)
    lines.append(f'{year}: points={len(values)} median>={BREAK_EVEN:.1f}: {above} ({above / len(values):.0%}) max={max(values)}')
peak = max(rows, key=lambda r: r['avgFee_50'])
lines.append(f"peak median: {peak['avgFee_50']} sat/vB at {dt.datetime.fromtimestamp(peak['timestamp'], dt.UTC):%Y-%m-%d} (avg height {peak['avgHeight']})")
(out / 'fee_history_summary.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
