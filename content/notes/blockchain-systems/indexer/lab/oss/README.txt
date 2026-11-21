Reorg experiments against 11 indexer projects (run on 2026-11-21)

Each directory holds the driver (drive.py), the project or config the indexer ran with,
and the recorded output (results.json is every sample where kept, drive.txt is the summary).
Logs, binaries, node_modules and build outputs are not kept here.
package-lock.json is not kept for graph-node and sqd (old transitive dependencies raise security alerts);
direct dependencies are pinned to the tested versions in package.json, so `npm install` resolves newer transitive versions.
Do not run npm install inside content/: node_modules under content/ breaks `hugo server`.
Copy a directory elsewhere first, and pass LAB=/path/to/lab (the directory with Token.sol and keccak.py).

Safety: everything listens on 127.0.0.1 only. EVM runs use Anvil's default test accounts,
Bitcoin runs use bitcoind in regtest. No public network, real funds or real private keys.
Docker containers are named indexer-note-<name>-... and are removed at the end.

Common procedure
1. Start a local chain: Anvil 1.7.1 (EVM) or Bitcoin Core 32.1 in regtest (Bitcoin).
2. EVM: deploy ../Token.sol and send alice->bob 1 token per block. Bitcoin: pay alice in a few blocks.
3. Wait until the indexer's table equals the node (balanceOf / scantxoutset).
4. Inside the window: replace the last 3 blocks (alice->carol 7), then mine one block.
5. Beyond the default depth: replace more blocks than the default (alice->dave 50),
   then watch for 60 s while mining a block every 5 s: table vs node, health endpoints, indexed height.
   EVM reorgs use anvil_reorg(depth, [[tx, 0]]); Bitcoin reorgs use invalidateblock and mine a longer branch.

Versions and results (default settings unless noted)
| dir          | project                          | version                     | default depth                 | beyond the depth |
| graph-node   | Graph Node                       | v0.45.0                     | none (kept history - 250 with prune; ~250 with prune: auto) | full history: 300 rewound in ~4.6 s; prune 260: stops after rewinding 21 blocks, health stays healthy |
| rindexer     | rindexer                         | 1.0.0                       | 2 x per-chain safe distance   | rewinds only the window and goes on out of sync, /health healthy |
| envio        | Envio HyperIndex                 | 3.17.1 (RPC source)         | 199 (max_reorg_depth at run)  | rewinds to head-200 and goes on out of sync, /healthz 200 |
| sqd          | SQD @subsquid/evm-processor      | 1.30.3                      | set by setFinalityConfirmation | stops with stale table, sync_ratio 1.0; restart is FATAL |
| substreams   | Substreams + firehose-ethereum   | v1.27.0 + v2.25.0           | RPC poller LIB = block - 200  | poller panics, /healthz stops answering, stack exits with code 0 after ~75 s; table stays stale in PostgreSQL |
| shovel       | Shovel                           | v1.6 and main aea8d42       | 10 (v1.6), 1000 (main)        | stays alive and stops; logs-only config never detects reorgs |
| blockscout   | Blockscout                       | v12.0.4 (built from source) | none                          | 100 and 300 rewound in ~3 s |
| blockbook    | Trezor Blockbook                 | v0.6.0                      | 300 (block_addresses_to_keep) | 301: stops with stale data, inSync true while blocks arrive; restart exits 255 |
| bitcoin      | electrs                          | v0.12.1                     | none                          | 120 rewound in 0.1 s |
| bitcoin      | Blockstream electrs              | new-index 6cad780           | none                          | 120 rewound in ~1 s; --address-search keeps reorged-out entries |
| bitcoin      | Fulcrum                          | v2.1.4                      | 100 (max_reorg)               | FATAL exit, same FATAL on restart with the same datadir; max_reorg 200 handles 120 |

Variants
- graph-node/output-prune260: indexerHints.prune 260 (subgraph-prune.yaml).
- rindexer/output/run_nofill: reorg right after reaching live (window almost empty).
- shovel/output/*: v1.6-* used the v1.6 tag, head-* used main; *-logs-only selects only log columns,
  *-block-time adds the block_time header column, v1.6-depth10/11 test the limit, head-prune tests a reorg after pruning.
- blockbook/output-pause-<D>: Blockbook paused (SIGSTOP) while the branch of depth D is built; only drive.txt kept.
  Without the pause (output/), Blockbook can see the half-built branch; the 300/301 boundary comes from the paused runs.
- bitcoin/output-maxreorg200: Fulcrum with max_reorg = 200 (only drive.txt kept).
