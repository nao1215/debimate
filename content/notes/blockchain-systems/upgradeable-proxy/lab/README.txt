Local upgradeable proxy experiment (ERC-1967 / ERC-7201)
Requirements: Python 3, git, Foundry anvil/cast 1.7.1, solc 0.8.28.
Put anvil, cast and solc on PATH (or set ANVIL, CAST, SOLC).
  anvil/cast: binaries of ghcr.io/foundry-rs/foundry:v1.7.1
  solc: solc-linux-amd64-v0.8.28+commit.7893614a from binaries.soliditylang.org
Run: bash run.sh

run.sh clones two OSS repositories at fixed commits into a temporary
directory (or $OZ_SRC if set). The sources are not copied into this repository.
  OpenZeppelin/openzeppelin-contracts v5.7.0 cab19933c33c2ad1d4c7a84864a3601dddfd16f3 (MIT)
  OpenZeppelin/openzeppelin-contracts-upgradeable v5.7.0 14f52c54d3a1eefbda3d4071efba24d3c1e07e8a (MIT)

Study.sol and Box.sol are educational contracts, not audited production code.
slots.py computes the ERC-1967 / ERC-7201 slots with a pure Python Keccak-256
(python3 slots.py prints them without any other tool).

run.py starts its own loopback-only Anvil (Prague, chain ID 31337) and stops
it on exit. Only Anvil's public test accounts are used; no real funds and no
external RPC. The "attacker" in step 6 is just Anvil test account 2.

It checks:
  1. a proxy that keeps the implementation in slot 0 is overwritten by the
     implementation's own variable in slot 0
  2. the ERC-1967 slots computed in Python match the proxy's storage,
     cast implementation and cast admin
  3. inserting a variable at the top of V2 shifts the meaning of every slot
  4. a constructor writes to the implementation, not to the proxy
  5. the ERC-7201 namespace slot computed in Python holds the values
  6. anyone can initialize an implementation without _disableInitializers(),
     upgradeToAndCall on the implementation itself is rejected (onlyProxy),
     and the locked implementation rejects initialize
output/ is overwritten on each run.
