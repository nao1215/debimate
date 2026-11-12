# ERC-20 experiments (local only)

Tested on Linux x86_64 with Foundry (anvil/cast) 1.7.1 and solc 0.8.28,
both installed through block (https://github.com/nao1215/block).

Files:
- Tokens.sol      StandardToken / NoReturnToken (USDT-like) / FalseToken (ZRX-like)
                  / FeeToken (2% fee, STA-like) and Vault with 4 deposit styles.
- experiment.py   Compiles Tokens.sol, runs 4 experiments over JSON-RPC and writes
                  output/results.json.
- run.sh          Starts its own anvil on 127.0.0.1:18645 (--order fees), runs
                  experiment.py, then stops anvil.

Reproduce:

    export PATH=<foundry dir>:<solc dir>:$PATH
    bash content/notes/blockchain-systems/erc-20/lab/run.sh
    python3 content/notes/blockchain-systems/erc-20/figures.py

Safety: no public RPC, no fork URL, no real funds. Transactions are signed by
anvil's built-in development accounts through eth_sendTransaction.

Notes on the race experiment:
- Blocks are mined every 2 seconds (evm_setIntervalMining) instead of
  mainnet's 12 seconds. Ordering is anvil's fee ordering, not a real
  block builder. Times in results.json are wall-clock seconds measured
  from the owner's send; they vary slightly between runs.
- The ordering of transactions within a block and the final totals
  (150 / 150 / 100) were the same in every run we made.
