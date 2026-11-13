Bitcoin Script experiments (local only, except sha1_bounty.py which reads a public API)

  bash run.sh            # needs Docker, curl, sha256sum; Linux x86_64

run.sh downloads the Bitcoin Core 32.1 release binary on the host from
https://bitcoincore.org/bin/bitcoin-core-32.1/ and checks it against the
published SHA256. The experiment runs in python:3.13-slim (digest pinned)
with --network none. Set SCRIPT_LAB_WORK to choose where the binary is kept
(default: $TMPDIR/note-bitcoin-script-lab).

script_race.py  regtest. Three P2WSH/bare cases, see the docstring.
  output/race.json  the recorded run. Keys, txids and the times change on
  every run; the winner of each case and the reject reasons do not.

concat_bug.py   a toy model (standard library only) of how 0.3.x joined
  scriptSig and scriptPubKey. Not a Bitcoin implementation.
  python3 concat_bug.py > output/concat_bug.txt

sha1_bounty.py  reads the history of 37k7toV1Nv4DfmQbmZ8KuZDQCYK9x5KpzP
  (Peter Todd's SHA-1 collision bounty, mainnet) from blockstream.info,
  two requests. python3 -I sha1_bounty.py > output/sha1_bounty.txt

The figures are drawn by ../figures.py from output/race.json.
