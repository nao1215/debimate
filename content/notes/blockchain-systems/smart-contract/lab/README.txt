# Smart Contract experiments (local only)

Tested on Linux x86_64 with Foundry (anvil/cast) 1.7.1 and solc 0.8.28,
both installed through block (https://github.com/nao1215/block).
The hardfork is not pinned: anvil 1.7.1 uses its default, which
anvil_nodeInfo reports as "Bpo1" (checked 2026-11-13).

Files:
- Contracts.sol   Lottery (winning number from block.prevrandao, block.timestamp
                  and the caller), Predictor (computes the same number inside the
                  same transaction) and Quiz (answer kept in a private variable).
- experiment.py   Starts 3 anvil nodes (A, B, C) with the same genesis, runs the
                  experiments over JSON-RPC and writes output/results.json.
- run.sh          Runs experiment.py and saves stdout to output/stdout.txt.

Experiments:
1. Lottery: 100 plays with a random guess (random.Random(1)) from an account,
   100 plays through Predictor. Losing plays revert ("miss").
2. Replay: every transaction of node A is sent to B and C as the same raw
   bytes. B uses the same block timestamps as A, C uses timestamp + 1 s.
   Node A's block timestamps are fixed to genesis + 12 s x block number, so
   the results are the same on every run (11 / 100 wins for the guesses,
   100 / 100 for Predictor, 16 differences on C).
   anvil 1.7.1 derives prevrandao from keccak256(parent hash || block number),
   so B (same timestamps and transactions) gets the same values as A, while on
   C the shifted timestamp changes the block hash and prevrandao also differs
   from A from the second block on. On mainnet prevrandao comes from the
   proposers' RANDAO reveals.
3. Quiz: read the private answer with eth_getStorageAt (slot 1) and from the
   deployment transaction input.
4. eth_call: call solve() as 0x...dEaD (a burn address whose key holder is
   not known), setAnswer() as the owner and as a stranger without any
   signature (asserts: no new block, solved stays 0), then send setAnswer()
   as a stranger in a real transaction (asserts: status 0, no logs, nonce +1,
   balance drops by gasUsed x effectiveGasPrice).

Reproduce:

    export PATH=<foundry dir>:<solc dir>:$PATH
    bash content/notes/blockchain-systems/smart-contract/lab/run.sh
    python3 content/notes/blockchain-systems/smart-contract/figures.py

Safety: no public RPC, no fork URL, no real funds. Transactions are signed by
anvil's built-in development accounts through eth_sendTransaction.
