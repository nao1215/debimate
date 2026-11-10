Local hard fork experiment
Requirements: Docker, bash. Images (tags pinned; digests are written to output/versions.txt):
  ghcr.io/foundry-rs/foundry:v1.7.1  (anvil 1.7.1)
  ethereum/solc:0.8.28
  python:3.13-slim
Run from this directory: bash run.sh   (about 10 seconds)

run.sh compiles Copy.sol / Sender.sol / Guard.sol with several --evm-version
values, starts one Anvil per hard fork (petersburg istanbul berlin london
shanghai cancun prague osaka) on a private Docker network named
note-ethereum-hard-forks-net, runs probe.py in a Python container on that
network, and removes every container and the network on exit.
No host port is published, no public network or RPC is contacted, and only
Anvil's default unlocked test accounts are used. No real funds or keys.

probe.py checks:
  1. which new opcodes (BASEFEE, PUSH0, TSTORE/TLOAD, MCOPY, CLZ) run on each fork
  2. gas of the first and second SLOAD of the same slot
  3. Solidity transfer() (2300 gas stipend) to a receiver that reads 3 slots,
     without and with an EIP-2930 access list
  4. whether SELFDESTRUCT in a later transaction deletes the code
  5. the same source compiled for paris / shanghai / cancun: PUSH0 and MCOPY
     counts and whether deployment succeeds on london / shanghai / cancun
The Solidity files and hand-assembled bytecode are educational and not audited.
output/ is deleted and rewritten on each run; anvil uses --timestamp 1700000000,
so output/summary.txt is identical across runs.
