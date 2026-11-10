Multisig experiments (local only)

  bash run.sh          # needs Docker, git, curl, sha256sum; Linux x86_64

run.sh downloads three things on the host, then runs every experiment in a
container started with --network none. Nothing connects to a public network.

- Bitcoin Core 32.1 release binary from https://bitcoincore.org/bin/bitcoin-core-32.1/
  checked against the SHA256 in SHA256SUMS. The Bitcoin Core project does not
  publish an official Docker image; the bitcoin/bitcoin image on Docker Hub
  describes itself as unofficial, so it is not used.
- safe-global/safe-smart-account v1.5.0 (commit dc437e8f...), LGPL-3.0-only.
  Compiled with solc 0.7.6 (the repository's default compiler) and
  --optimize --optimize-runs 200 (chosen for this lab).
- anvil / cast 1.7.1 and solc 0.7.6 copied out of their official images
  (digests pinned in run.sh). Python runs in python:3.13-slim (digest pinned).

bitcoin_multisig.py  regtest. Three throwaway wallets a, b, c each give one key.
  1. wsh(multi(2,a,b,c)): PSBT signed by a only / by two of them; then the
     witness is rewritten (one sig, swapped order, dummy 0x01, no dummy) and
     each variant is put into a block with generateblock to get the
     consensus verdict.
  2. tr(musig(a,b,c)): MuSig2 (BIP-327) signing in two PSBT rounds inside
     Bitcoin Core, then the same spend shape from a single-key P2TR wallet.
safe_multisig.py  anvil, Anvil's public test mnemonic only.
  2-of-3 Safe with owners EOA, EOA and StudySigner (ERC-1271, written for
  this lab, not audited). execTransaction with 1 signature, duplicated owner,
  descending / ascending owner order, replayed nonce-0 signatures, and an
  ERC-1271 contract signature before / after the contract approves the hash.

output/ holds the recorded run. Keys and txids change on every run; the
verdicts do not. Witness sizes and weights matched in repeated runs; an
ECDSA signature is usually 71 bytes because Bitcoin Core grinds for low R,
but a shorter one (and a 1-unit smaller weight) is possible.
