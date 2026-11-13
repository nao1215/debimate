#!/usr/bin/env python3
"""List the spends from Peter Todd's SHA-1 collision bounty address (mainnet, read only).

Reads the public Esplora API of blockstream.info twice (two pages of history).
Standard library only. Prints one line per transaction that spends the address.
"""
import datetime
import json
import urllib.request

ADDR = '37k7toV1Nv4DfmQbmZ8KuZDQCYK9x5KpzP'
API = 'https://blockstream.info/api/address/' + ADDR + '/txs'


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


txs = get(API)
txs += get(API + '/chain/' + txs[-1]['txid'])
print('block_time_utc       height  inputs  spent_sat  fee_sat  txid / to')
for t in sorted(txs, key=lambda t: t['status']['block_time']):
    ins = [i for i in t['vin'] if i['prevout'].get('scriptpubkey_address') == ADDR]
    if not ins:
        continue
    when = datetime.datetime.fromtimestamp(t['status']['block_time'], datetime.UTC).strftime('%Y-%m-%d %H:%M')
    spent = sum(i['prevout']['value'] for i in ins)
    to = t['vout'][0].get('scriptpubkey_address') or t['vout'][0]['scriptpubkey_type']
    print(f"{when}  {t['status']['block_height']:>7}  {len(ins):>6}  {spent:>9}  {t['fee']:>7}  {t['txid'][:16]}… -> {to}")
print('redeemScript:', ins[0]['inner_redeemscript_asm'])
sigs = [i['scriptsig'] for t in txs for i in t['vin'] if i['prevout'].get('scriptpubkey_address') == ADDR]
print(f'spent inputs: {len(sigs)}, distinct scriptSig: {len(set(sigs))}, scriptSig bytes: {len(sigs[0]) // 2}')
