Reentrancy experiment on a local Anvil chain
Requirements: Python 3 (standard library only), Foundry anvil 1.7.1, solc 0.8.28.
Put anvil and solc on PATH, or set ANVIL and SOLC to executable paths.
From this directory: python3 run.py > output/output.txt

- Bank.sol is an educational implementation, not audited production code.
- oz/ holds four files copied unchanged from OpenZeppelin Contracts v5.7.0
  (commit cab19933c33c2ad1d4c7a84864a3601dddfd16f3) under the MIT License (oz/LICENSE).
- keccak.py is a small pure-Python Keccak-256 (copied from ../../eip-712/lab/).
- Anvil listens on 127.0.0.1:8546 only, with the EVM rules fixed to Cancun.
- Accounts are Anvil's default test accounts. Their keys are public and worthless.
  No public network, real funds or real private keys are used.
- output/results.json holds the bank balances used by ../figures.py.
