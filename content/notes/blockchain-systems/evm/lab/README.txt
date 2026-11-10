Local EVM experiment for the EVM note
Requirements: Docker, bash, python3 (host, only to read the solc JSON).
Images (tags pinned; digests are written to output/versions.txt):
  ghcr.io/foundry-rs/foundry:v1.7.1  (anvil / cast 1.7.1)
  ethereum/solc:0.8.28
  python:3.13-slim
Run from the repository root: bash content/notes/blockchain-systems/evm/lab/run.sh  (about 5 seconds)

run.sh compiles Dispatcher.sol / Context.sol / Deep.sol (optimizer off,
evmVersion cancun, no metadata hash), starts one Anvil pinned to Osaka on a
private Docker network named note-evm-net (container note-evm-anvil), runs
probe.py in a Python container on that network, and removes the container
and the network on exit. No host port is published, no public network or RPC
is contacted, and only Anvil's default test accounts and the publicly known
test key of account 0 are used. No real funds or keys.

probe.py checks:
  1. memory expansion gas against 3a + floor(a*a/512)
  2. the 63/64 limit of the gas a CALL forwards (exact numbers)
  3. gasleft() at the entry of nested self-calls and the deepest call that succeeds
  4. msg.sender / address(this) / msg.value / storage owner for CALL,
     DELEGATECALL and STATICCALL
  5. the dispatcher of Dispatcher.sol: calldata, executed opcodes
     (debug_traceTransaction), intrinsic gas, EIP-7623 floor, SSTORE, LOG2, refund
  6. precompiles 0x02 (SHA-256), 0x01 (ecrecover) and 0x100 (P-256, Osaka)
The Solidity files, the hand-assembled bytecode and the small P-256 signer in
probe.py are educational and not audited. Anvil runs with a fixed timestamp,
so output/summary.txt is identical across runs.

Data for the figures that need pinned source checkouts (not run by run.sh):
  GETH_SRC=/path/to/go-ethereum bash count_opcodes.sh
    -> output/geth_tables.json (opcodes per instruction set, precompiles per fork)
       needs Go; go-ethereum must be at ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f.
       zz_count_opcodes_test.go is copied into core/vm, run, and removed.
  EIPS_SRC=/path/to/EIPs ERCS_SRC=/path/to/ERCs python3 eip_graph.py
    -> output/eip_graph.json (category, status and requires from the front matter)
       EIPs at 542e62eb129517130b7facc52bbb9a1f333c711e,
       ERCs at f94e400afdddaa2625c291f71646bde0ef44df9d.
Then python3 ../figures.py redraws images/.
