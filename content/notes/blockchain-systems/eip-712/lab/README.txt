Local EIP-712 / ERC-2612 / ERC-1271 experiment
Requirements: Python 3 (standard library only), git, Foundry anvil/cast 1.7.1, solc 0.8.28.
Put anvil, cast and solc on PATH (or set ANVIL, CAST, SOLC to executable paths).
From the repository root: bash content/notes/blockchain-systems/eip-712/lab/run.sh

run.sh clones OpenZeppelin Contracts v5.1.0 (MIT,
commit 69c8def5f222ff96f2b5beff05dfba996368aa79) into a temporary directory
(or reuses $OZ_SRC/oz) and checks the commit before compiling.

run.py starts two fresh Anvil nodes bound to 127.0.0.1 (chain IDs 31337 and
31338) and uses only Anvil's default test accounts. No public network, no
real funds or keys. Both nodes are stopped at the end.

Steps:
 1. hash the EIP-712 "Mail" example by hand (eip712.py, keccak.py) and compare
    with the values in EIP-712's Example.js; ecrecover the spec's signature.
 2. sign a Permit with eth_signTypedData_v4, compare with the token's
    DOMAIN_SEPARATOR() and ecrecover; submit the same signature to the same
    address on chain 31338 and to a second token with the same name.
 3. personal_sign over the same digest (EIP-191 prefix).
 4. the owner only signs; a third account calls permit and transferFrom.
 5. a minimal ERC-1271 account: ecrecover-only check vs SignatureChecker,
    isValidSignature, permit with the account as owner, and another account
    of the same owner.

StudyPermitToken.sol, StudyAccount.sol and SigCheck.sol are educational
contracts and have not been audited.
keccak.py is a small pure-Python Keccak-256 (hashlib.sha3_256 is NIST SHA3,
which uses different padding and gives different hashes).
output/ is overwritten on each run. Signatures are deterministic (RFC 6979),
so summary.txt is identical between runs.
