Local ERC-7562 experiment
EntryPoint version: v0.9.0 (eth-infinitism/account-abstraction tag v0.9.0), the same as the erc-4337 note.
ERC-7562 text checked: ethereum/ERCs cab9f75eaf10ffb30d4aa4b4f712e8324a24f4db (2026-10-23, status Review)
Requirements: Python 3, git, Foundry anvil/cast 1.7.1, solc 0.8.28.
Put anvil, cast and solc on PATH (or set ANVIL, CAST, SOLC).
  anvil/cast: binaries of ghcr.io/foundry-rs/foundry:v1.7.1
  solc: solc-linux-amd64-v0.8.28+commit.7893614a from binaries.soliditylang.org
Run: bash run.sh

run.sh clones two OSS repositories at fixed commits into a temporary
directory (or $AA_SRC if set) and compiles them, together with Lab.sol,
with the settings of the account-abstraction hardhat config:
  eth-infinitism/account-abstraction v0.9.0 b36a1ed52ae00da6f8a4c8d50181e2877e4fa410
    EntryPoint.sol (GPL-3.0), SimpleAccountFactory.sol / SimpleAccount.sol (MIT)
  OpenZeppelin/openzeppelin-contracts v5.1.0 69c8def5f222ff96f2b5beff05dfba996368aa79 (MIT)
The sources are not copied into this repository.

Lab.sol (MIT) holds learning contracts written for this note. They are not
audited and skip signature checks on purpose. Do not deploy them anywhere.

run.py starts its own loopback-only Anvil (Prague, chain ID 31337, +1 s per
block) and terminates it on exit. Keys come only from Anvil's public test
mnemonic. There is no bundler software: the script calls eth_call,
debug_traceCall (default struct log tracer with memory) and handleOps itself.

It checks:
  1. six accounts: eth_call of handleOps, and a small ERC-7562 checker over
     the validation trace (OP-011, OP-012, OP-080, STO-010, STO-021 only)
  2. a TIMESTAMP-dependent account that passes simulation and reverts in the
     block, and what the bundler pays
  3. ten accounts that read one shared switch; the switch owner front-runs
     the bundle in the same block
  4. two UserOperations of one sender that are valid alone but not together
output/ is overwritten on each run.
