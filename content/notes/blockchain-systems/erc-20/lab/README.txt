Local ERC-20 experiment
Requirements: Python 3, Foundry anvil/cast 1.7.1, solc 0.8.28.
Set PATH or ANVIL, CAST, SOLC to executable paths.
From this directory: bash run.sh
Requires sibling ../../smart-contract/lab/run.py (shared runner).
StudyToken.sol is an educational implementation, not audited production code.
100 tokens, decimals=0, fixed supply, no upgrade/admin mechanism.
The script starts a fresh loopback-only Anvil with three unlocked test accounts.
It checks direct transfer, approval, delegated transfer, excess allowance,
revocation, attempted spending after revocation, logs and constant total supply.
output/ is overwritten on each run. No real funds or external RPC is used.
