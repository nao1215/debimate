EIP-1559 base fee experiment on a local Anvil chain
Requirements: Python 3 (standard library only), Foundry anvil 1.7.1.
Put anvil on PATH, or set ANVIL to the executable path.
From this directory: python3 run.py > output/output.txt

- Anvil listens on 127.0.0.1:8547 only, with --no-mining so that transactions stay in
  the txpool until evm_mine is called. --order fees puts higher-tip transactions first.
- The block gas limit is lowered to 1,050,000 (50 plain transfers of 21,000 gas), so the
  number of transfers decides how full a block is. The target is half of it (25 transfers).
- run.py prints, for every block, the base fee reported by Anvil and the value computed
  with the EIP-1559 formula from the parent block.
- Accounts are Anvil's default test accounts. Their keys are public and worthless.
  No public network, real funds or real private keys are used.
- The figures are drawn by ../figures.py from output/output.txt.
