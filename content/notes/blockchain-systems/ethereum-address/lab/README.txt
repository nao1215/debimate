Local Ethereum address experiment
Requirements: Python 3 (standard library only) and Docker.
Images (pinned by digest in run.py):
  ghcr.io/foundry-rs/foundry:v1.7.1  (anvil, cast)
  ethereum/solc:0.8.28
Run from this directory: python3 -I run.py

address.py computes EOA (secp256k1 + keccak256), CREATE (rlp(sender, nonce)),
CREATE2 (0xff ++ sender ++ salt ++ keccak256(initcode)) and EIP-55 addresses
with no third-party library. run.py starts throwaway Anvil containers named
note-ethereum-address-* with --network none (no published ports; RPC through
docker exec + cast), checks the computed addresses against the nodes, and
removes the containers on exit.

Steps:
  1. EOA: Anvil's default key gives the same address on chain IDs 31337/31338/31339;
     a tx signed for 31337 is rejected by 31338.
  2. CREATE: nonce 0 on chain A and C -> same address; on chain B a different
     contract (V2) takes that address at nonce 0, Factory moves to nonce 1.
  3. CREATE2: salt and the constructor argument change the address; the same
     factory address on another chain gives the same address; reuse fails.
  4. Metamorphic: CREATE2 a Deployer, CREATE V1 from it, SELFDESTRUCT both in
     later transactions, CREATE2 the Deployer again and CREATE V2.
     Compared with --hardfork shanghai, cancun and prague.

Address.sol is educational code and not audited. kill() has no access control.
Contracts are compiled with --evm-version shanghai so that the same bytecode
runs on every fork compared. The key is Anvil's public test key; never use it
with real funds. No public network is contacted. output/ is overwritten.
