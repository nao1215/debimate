Local Counter experiment
Requirements: Python 3, Foundry anvil/cast 1.7.1, solc 0.8.28.
Set PATH or ANVIL, CAST, SOLC to the executable paths.
Run: python3 run.py
The script starts its own loopback-only Anvil (Cancun, chain ID 31337), uses
unlocked development accounts, and terminates the node on exit.
No external RPC or real key is used. It overwrites output/ on each run.
The captured gas fees use gasPrice=2 gwei; values depend on compiler settings.
Receipts and versions are in output/. Assertions check persistent state,
logs, nonce and the exact sender balance change for successful/failed calls.
The ERC-20 sibling lab reuses this runner with LAB_MODE=token.
