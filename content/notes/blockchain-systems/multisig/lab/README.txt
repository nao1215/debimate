Bitcoin multisig experiments (local only)

  bash run.sh          # needs Docker, curl, sha256sum; Linux x86_64

run.sh downloads the Bitcoin Core 32.1 release binary on the host from
https://bitcoincore.org/bin/bitcoin-core-32.1/ and checks it against the
SHA256 in SHA256SUMS. The Bitcoin Core project does not publish an official
Docker image; the bitcoin/bitcoin image on Docker Hub describes itself as
unofficial, so it is not used. The experiment then runs in python:3.13-slim
(digest pinned) with --network none. Nothing connects to a public network.

bitcoin_multisig.py  regtest. Three throwaway wallets a, b, c each give one key.
  1. wsh(multi(2,a,b,c)): PSBT signed by a only / by two of them; then the
     witness is rewritten (one sig, swapped order, dummy 0x01, no dummy) and
     each variant is put into a block with generateblock to get the
     consensus verdict.
  2. tr(musig(a,b,c)): MuSig2 (BIP-327) signing in two PSBT rounds inside
     Bitcoin Core, then the same spend shape from a single-key P2TR wallet.

output/ holds the recorded run. Keys and txids change on every run; the
verdicts do not. Witness sizes and weights matched in repeated runs; an
ECDSA signature is usually 71 bytes because Bitcoin Core grinds for low R,
but a shorter one (and a 1-unit smaller weight) is possible.

The Safe (Ethereum) experiment that used to live here moved to
../../safe-multisig/lab/.
