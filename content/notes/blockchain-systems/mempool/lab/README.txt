Bitcoin Core mempool policy experiment
Tested with Bitcoin Core 30.4 and Python 3.14, Linux x86_64.
Install Bitcoin Core from https://bitcoincore.org/bin/bitcoin-core-30.4/
Put bitcoind on PATH or set BITCOIND to its full path, then:
  python3 compare_policy.py

The script uses fresh temporary regtest data directories, loopback-only RPC,
listen=0/connect=0/dnsseed=0/discover=0/natpmp=0. It never connects to public peers.
It generates 101 blocks to mature a coinbase, sends every raw block to node B,
and signs one transaction on node A using an ephemeral descriptor wallet.
A: minrelaytxfee=0.00001 BTC/kvB (1 sat/vB).
B: minrelaytxfee=0.00010 BTC/kvB (10 sat/vB).
fundrawtransaction fee_rate=2 sat/vB, blockmintxfee=0.00001 BTC/kvB.
It checks preflight rejection on B, no mempool mutation from preflight, inclusion
on A, and acceptance of the resulting block on B including the target txid.
No private keys or RPC cookies are printed or copied to output/.
Node processes stop and temporary wallets/data are removed on normal exit/errors.
output/ contains actual RPC results and assertions from the recorded run.
