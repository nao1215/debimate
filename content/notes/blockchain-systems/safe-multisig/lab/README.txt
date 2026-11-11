Safe multisig experiment (local only)

  bash run.sh          # needs Docker and git; Linux x86_64

run.sh fetches safe-smart-account v1.5.0 (commit dc437e8f..., LGPL-3.0-only)
and copies anvil / cast 1.7.1 and solc 0.7.6 out of their official images
(digests pinned in run.sh). The experiment runs in python:3.13-slim (digest
pinned) with --network none. Nothing connects to a public network.
The Safe contracts are compiled with solc 0.7.6 (the repository's default
compiler) and --optimize --optimize-runs 200 (chosen for this lab).

safe_multisig.py  anvil, Anvil's public test mnemonic only.
  2-of-3 Safe with owners EOA, EOA and StudySigner (ERC-1271, written for
  this lab, not audited). execTransaction with 1 signature, duplicated owner,
  descending / ascending owner order, replayed nonce-0 signatures, and an
  ERC-1271 contract signature before / after the contract approves the hash.

output/ holds the recorded run (moved from ../../multisig/lab/output/).
Addresses are fixed by Anvil's test mnemonic; the verdicts do not change.
