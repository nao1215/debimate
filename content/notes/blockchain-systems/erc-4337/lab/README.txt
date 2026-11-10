Local ERC-4337 experiment
EntryPoint version: v0.9.0 (eth-infinitism/account-abstraction tag v0.9.0, PackedUserOperation ABI)
Requirements: Python 3, git, Foundry anvil/cast 1.7.1, solc 0.8.28.
Put anvil, cast and solc on PATH (or set ANVIL, CAST, SOLC).
  anvil/cast: binaries of ghcr.io/foundry-rs/foundry:v1.7.1
  solc: solc-linux-amd64-v0.8.28+commit.7893614a from binaries.soliditylang.org
Run: bash run.sh

run.sh clones two OSS repositories at fixed commits into a temporary
directory (or $AA_SRC if set) and compiles them with the settings of the
account-abstraction hardhat config (via-ir, optimizer runs 1000000, cancun):
  eth-infinitism/account-abstraction v0.9.0 b36a1ed52ae00da6f8a4c8d50181e2877e4fa410
    EntryPoint.sol (GPL-3.0), SimpleAccountFactory.sol / SimpleAccount.sol (MIT),
    test/TestPaymasterAcceptAll.sol (GPL-3.0, a test paymaster that pays for anything)
  OpenZeppelin/openzeppelin-contracts v5.1.0 69c8def5f222ff96f2b5beff05dfba996368aa79 (MIT)
The sources are not copied into this repository.

run.py starts its own loopback-only Anvil (Prague, chain ID 31337) and
terminates it on exit. Keys come only from Anvil's public test mnemonic.
There is no bundler software and no UserOperation mempool: the script builds
UserOperations itself and a funded test EOA calls EntryPoint.handleOps
directly, standing in for a bundler.

It checks: the CREATE2 address before deployment (3 ways), rejection of a
UserOperation whose signature no longer matches (eth_call, nothing mined),
three successful UserOperations (create + self-paid, self-paid, paymaster)
with the balance changes of each party, and the gas of each call frame
(debug_traceTransaction callTracer) against a plain 21,000 gas transfer.
output/ is overwritten on each run.
