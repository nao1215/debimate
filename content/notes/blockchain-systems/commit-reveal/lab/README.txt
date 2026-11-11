Commit-reveal experiment on a local Anvil chain
Requirements: Python 3 (standard library only), Foundry anvil 1.7.1, solc 0.8.28.
Put anvil and solc on PATH, or set ANVIL and SOLC to executable paths.
From this directory: python3 run.py | tee output/output.txt

- Auction.sol is an educational implementation, not audited production code.
- keccak.py is a small pure-Python Keccak-256 (copied from ../../eip-712/lab/).
- Anvil listens on 127.0.0.1 only, with --no-mining so that transactions stay in
  the txpool until evm_mine is called. --order fees puts higher-fee transactions first.
- Accounts are Anvil's default test accounts. Their keys are public and worthless.
  No public network, real funds or real private keys are used.
- Salts are random on each run, so hashes in output/ change between runs.
