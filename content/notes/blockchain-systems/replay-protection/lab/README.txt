Replay protection experiment on two local Anvil chains
Requirements: Python 3 (standard library only), Foundry anvil 1.7.1 (cast 1.7.1 for one cross-check), solc 0.8.28.
Put anvil, cast and solc on PATH, or set ANVIL, CAST and SOLC to executable paths.
From this directory: python3 run.py | tee output/output.txt

- Chain A listens on 127.0.0.1:8548 with chain ID 31337. After the setup, chain B is started on
  127.0.0.1:8549 with chain ID 31338 as a fork of chain A (anvil --fork-url), so both chains share
  balances, nonces and contracts up to the fork block.
- secp256k1.py is a small pure-Python ECDSA (RFC 6979 nonces, low-s, public key recovery).
  It is not constant-time: a teaching aid only. run.py checks it against `cast wallet sign`
  and against the example transaction in EIP-155.
- keccak.py is a small pure-Python Keccak-256 (copied from ../../eip-712/lab/).
- Voucher.sol is an educational implementation, not audited production code.
- Keys: Anvil's default test key 0 (public and worthless) and a key derived from a fixed string.
  No public network, real funds or real private keys are used.
