Blockchain indexer experiments on a local Anvil chain

Requirements: Python 3 (standard library only), Foundry anvil 1.7.1, solc 0.8.28.
Put anvil and solc on PATH, or set ANVIL and SOLC to executable paths.
From this directory: python3 run.py | tee output/output.txt

- Token.sol is a minimal ERC-20-like contract for the experiment, not audited code.
- keccak.py is a small pure-Python Keccak-256 (copied from ../../eip-712/lab/).
- Anvil listens on 127.0.0.1:18771 only, with --no-mining; blocks are made with evm_mine.
- Accounts are Anvil's default test accounts. Their keys are public and worthless.
  No public network, real funds or real private keys are used.
- The reorg is made with anvil_reorg(depth=2, ...), which replaces the last two
  blocks with new blocks holding the given transaction. Transactions of the
  dropped blocks are not put back into the pool by Anvil.

Output:
- output/output.txt: the chain, the balances (node / naive / hash-checking) at each step.
- output/results.json: the same data, used by ../figures.py.
- With the fixed --timestamp, two runs gave identical output (same block hashes).

## ponder/: Ponder against reorgs inside and outside its reorg window

Requirements: Node.js 22, npm, plus anvil and solc as above.
Copy lab/ponder outside the Hugo content directory first (node_modules under content/ breaks
`hugo server`), then from the copy: npm ci && LAB=/path/to/lab python3 drive.py
(writes output/results.json, drive.txt, ponder.log; LAB is the directory holding Token.sol and keccak.py)

- Ponder 0.18.9 with PGlite (no external database). The reorg window is the default 180 seconds.
- Block timestamps advance 12 s per block (anvil_setBlockTimestampInterval).
- Blocks 1-50: deploy the token, then alice->bob 1 token per block.
- inside: anvil_reorg depth 3 (36 s, inside the window), no new block for 6 s, then one block.
- outside: anvil_reorg depth 30 (360 s, outside the window), then one block, then 60 s of watching
  (one new block every 5 s; records /ready, /status and the node head).
- The script compares Ponder's GraphQL balances with balanceOf on the node and records /ready and /health.
- pollingInterval is 200 ms (default 1000 ms) to keep the run short.
- Tested on Linux x86_64 with Node.js v22.22.1, anvil 1.7.1, solc 0.8.28.
