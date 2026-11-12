# Oracle experiments (local only)

Tested on Linux x86_64 with Foundry (anvil/cast) 1.7.1 and solc 0.8.28,
both installed through block (https://github.com/nao1215/block), and
Python 3 (standard library only).

Files:
- Oracle.sol      Token (tETH / tUSD), Pool (x*y=k, 0.3% fee, cumulative price
                  for TWAP), PushFeed (latestRoundData like Chainlink),
                  SpotSource / TwapSource / FeedSource, Lending (80% LTV),
                  FlashLender (0.09% fee) and Attacker.
- experiment.py   Compiles Oracle.sol, runs 2 experiments over JSON-RPC and
                  writes output/results.json.
- run.sh          Starts its own anvil on 127.0.0.1:18745, runs experiment.py
                  (stdout is saved to output/summary.txt), then stops anvil.

Reproduce:

    export PATH=<foundry dir>:<solc dir>:$PATH
    bash content/notes/blockchain-systems/oracle/lab/run.sh
    python3 content/notes/blockchain-systems/oracle/figures.py   # needs matplotlib and Pillow

Experiment 1 (attack): the same flash-loan attack (borrow 300,000 tUSD, buy
tETH, deposit 10 tETH, borrow the maximum, sell the rest back, repay) is run
against three Lending deployments that read spot / 30-minute TWAP / PushFeed.
evm_snapshot / evm_revert gives each run the same starting state. A failed
run reverts with Attacker.CannotRepay(held, owed, borrowed); the numbers are
read back with eth_call.

Experiment 2 (crash): 90 minutes of 12-second blocks set with evm_mine
<timestamp>. The "market" price is a scripted path (3,000 for 20 minutes,
linear drop to 2,100 over 10 minutes, then flat, with a +-0.2% sine wiggle).
It is not real market data. Each block an arbitrage account swaps the Pool to
the market price, and the updater writes PushFeed only when the market moved
0.5% or more from the stored value or 3,600 seconds have passed (the
conditions of Chainlink's ETH / USD feed on Ethereum, checked on 2026-11-13
at https://reference-data-directory.vercel.app/feeds-mainnet.json).
That updater writes in the same block it observed the market (no delay).
Two more PushFeeds run the same rule, but each write lands 1 block (12 s) or
5 blocks (60 s) after the observation; they are recorded as feed_lag12 and
feed_lag60 in results.json.

Safety: no public RPC, no fork URL, no real funds. Transactions are signed by
anvil's built-in development accounts through eth_sendTransaction. The
contracts are for this experiment only and are not audited.
