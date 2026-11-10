Local ERC-721 experiment
Requirements: Python 3, Foundry anvil/cast 1.7.1, solc 0.8.28.
Set PATH or ANVIL, CAST, SOLC to executable paths.
Run: bash run.sh (from any directory)
StudyNFT.sol and Receivers.sol are educational implementations, not audited
production code. StudyNFT implements ERC-721 + ERC-721 Metadata + ERC-165;
mint and setBaseURI are the sample's own admin functions (not in ERC-721).
Counter has no NFT logic; StudyReceiver implements onERC721Received and a
keeper-only withdraw.
The script starts a fresh loopback-only Anvil (Cancun, chain ID 31337) with
four unlocked default test accounts, and a loopback HTTP server that serves
the metadata JSON from a temporary directory. Both stop on exit.
It checks mint/ownerOf/balanceOf, ERC-165 IDs, safeTransferFrom vs
transferFrom to a contract without onERC721Received, approve vs
setApprovalForAll (including a token minted after the approval), and
changing the metadata behind the same tokenURI and via setBaseURI.
The HTTP port is random; summary.txt prints it as WEB.
eip7702.sh (also run by run.sh) starts a separate Anvil with the Prague rules,
delegates the code of default test account #1 to Counter (EIP-7702) and shows
that safeTransferFrom to that EOA reverts. Output: output/eip7702.txt.
output/ is overwritten on each run. No real funds or external RPC is used.
