#!/usr/bin/env python3
"""Local-only experiment for the mainnet-and-testnet note (Bitcoin part).

Runs the official Bitcoin Core 32.1 release binaries (bitcoincore.org, checked
against SHA256SUMS) inside one throwaway Docker container started with
--network none, so no node can reach a peer. For each of the five chains
(main, testnet3, testnet4, signet, regtest) it starts bitcoind on an empty
data directory and records:
  - the chain name and genesis block hash from getblockchaininfo
  - the P2P port the node binds (debug.log)
  - the first 4 bytes of blocks/blk00000.dat (the network magic)
  - the addresses derived from one public key (pkh / wpkh / tr descriptors)
Then, on regtest only, it mines 200 blocks and reads the block subsidy.

The public key is 1*G, the key of the private key 1. Everybody knows that
private key: it is for illustration only and must never hold coins.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

LAB = Path(__file__).resolve().parent
BIN = Path(os.environ.get('BITCOIN_BIN', LAB / 'bitcoin-32.1' / 'bin')).resolve()
IMAGE = 'python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90'
NAME = 'note-mainnet-and-testnet-btc'
PUBKEY = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'  # 1*G
CHAINS = {'main': '', 'test': 'testnet3', 'testnet4': 'testnet4', 'signet': 'signet', 'regtest': 'regtest'}
# Default signet challenge (1-of-2 multisig) from src/kernel/chainparams.cpp at v32.1.
SIGNET_CHALLENGE = bytes.fromhex(
    '512103ad5e0edad18cb1f0fc0d28a3d4f1f3e445640337489abb10404f2d1e086be430'
    '210359ef5021964fe22d6f8e05b2463c9540ce96883fe3b278760f048f5189f2e6c452ae')
OUT = LAB / 'output'


def sh(*args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()


def ex(*args, check=True):
    return sh('docker', 'exec', NAME, *args, check=check)


def cli(chain, *args):
    out = ex('/btc/bitcoin-cli', f'-chain={chain}', f'-datadir=/data/{chain}', *args)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def start(chain):
    ex('mkdir', '-p', f'/data/{chain}')
    ex('/btc/bitcoind', f'-chain={chain}', f'-datadir=/data/{chain}', '-daemonwait',
       '-listen=1', '-bind=127.0.0.1', '-connect=0', '-dnsseed=0', '-fixedseeds=0',
       '-blocksxor=0', '-printtoconsole=0')


def stop(chain):
    sub = CHAINS[chain]
    pid = f'/data/{chain}/{sub}/bitcoind.pid' if sub else f'/data/{chain}/bitcoind.pid'
    cli(chain, 'stop')
    while subprocess.run(['docker', 'exec', NAME, 'test', '-e', pid]).returncode == 0:
        time.sleep(0.1)


def descriptor(chain, desc):
    return cli(chain, 'getdescriptorinfo', desc)['descriptor']


def main():
    OUT.mkdir(exist_ok=True)
    lines = []

    def log(s=''):
        print(s)
        lines.append(s)

    sha256d = hashlib.sha256(hashlib.sha256(bytes([len(SIGNET_CHALLENGE)]) + SIGNET_CHALLENGE).digest()).digest()
    log(f'signet magic computed from the challenge: {sha256d[:4].hex()}')

    subprocess.run(['docker', 'rm', '-f', NAME], capture_output=True)
    sh('docker', 'run', '-d', '--name', NAME, '--network', 'none',
       '-v', f'{BIN}:/btc:ro', IMAGE, 'sleep', 'infinity')
    try:
        log(ex('/btc/bitcoind', '-version').splitlines()[0])
        log(f'{"chain":9} {"magic":8} {"port":>5}  {"pkh":34} {"wpkh":44} tr')
        for chain, sub in CHAINS.items():
            start(chain)
            info = cli(chain, 'getblockchaininfo')
            addrs = [cli(chain, 'deriveaddresses', descriptor(chain, f'{kind}({PUBKEY})'))[0]
                     for kind in ('pkh', 'wpkh', 'tr')]
            stop(chain)
            path = f'/data/{chain}/{sub}' if sub else f'/data/{chain}'
            magic = ex('sh', '-c', f'head -c 4 {path}/blocks/blk00000.dat | od -An -tx1 | tr -d " \\n"')
            port = ex('sh', '-c', f'grep -o "Bound to 127.0.0.1:[0-9]*" {path}/debug.log | head -1').rsplit(':', 1)[1]
            log(f'{info["chain"]:9} {magic:8} {port:>5}  {addrs[0]:34} {addrs[1]:44} {addrs[2][:12]}…')
            log(f'          genesis {info["bestblockhash"][:16]}… blocks={info["blocks"]}'
                + (f' warnings={info["warnings"]}' if info.get('warnings') else ''))

        log('== regtest: mine 200 blocks to the same key')
        start('regtest')
        desc = descriptor('regtest', f'wpkh({PUBKEY})')
        cli('regtest', 'generatetodescriptor', '200', desc)
        info = cli('regtest', 'getblockchaininfo')
        log(f'blocks={info["blocks"]} difficulty={info["difficulty"]:.3g}')
        for h in (1, 149, 150, 200):
            block = cli('regtest', 'getblock', cli('regtest', 'getblockhash', str(h)), '2')
            log(f'height {h:>3}: coinbase pays {block["tx"][0]["vout"][0]["value"]} BTC')
        stop('regtest')
    finally:
        subprocess.run(['docker', 'rm', '-f', NAME], capture_output=True)
    (OUT / 'btc_networks.txt').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
