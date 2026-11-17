UTXO experiments (Python 3.11+ standard library only, no network access, no real keys)

  cd content/notes/blockchain-systems/utxo/lab
  python3 utxo_lab.py

utxo_lab.py builds and signs SegWit v0 P2WPKH transactions (secp256k1 ECDSA with
RFC 6979 nonces, BIP 143 signature hash), checks the BIP 143 "Native P2WPKH" test
vector first, measures virtual sizes, and applies the transactions to a small
UTXO set that checks inputs and signatures. Keys are derived from fixed labels.
Tested with Python 3.14.4 on Linux x86_64 (about 30 seconds).
output/summary.txt and output/results.json are the recorded run.

  python3 fee_history.py

fee_history.py fetches https://mempool.space/api/v1/mining/blocks/fee-rates/3y once
(fetched on 2026-11-17) and writes output/fee_rates_3y.csv and
output/fee_history_summary.txt. Pass a saved copy of the response as the first
argument to avoid fetching again.

Policy numbers follow Bitcoin Core v30.0 (src/policy/policy.cpp GetDustThreshold,
src/wallet/spend.cpp GroupOutputs, src/wallet/rpc/spend.cpp sendall send_max).
