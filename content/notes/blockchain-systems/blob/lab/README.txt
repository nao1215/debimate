Blob note experiments (2026-11-12)

1. basics.sh  (Foundry anvil/cast 1.7.1, jq, xxd, python3; loopback only)
   Starts its own anvil (--hardfork osaka) on 127.0.0.1:18611, deploys a tiny
   contract that stores BLOBHASH(0), BLOBHASH(1) and CALLDATASIZE, sends a
   5-byte blob to it, measures calldata gasUsed for 5..100000 bytes, and checks
   whether anvil advances excessBlobGas (it stays 0 in anvil 1.7.1).
   Uses anvil's built-in dev accounts via --unlocked. No public network, no real funds.
     ./basics.sh
   Output: output/basics.txt, calldata_gas.txt, anvil_excess.txt,
           blob_receipt.json, blob_tx.json (blobs and cell proofs trimmed)

2. fetch_headers.py  (network: one public RPC, run once on 2026-11-12)
   Saves number/timestamp/excessBlobGas/blobGasUsed/baseFeePerGas of
   mainnet blocks 19,526,600-19,527,399 (2024-03-27) and
   26,399,000-26,399,299 (2026-11-12) to output/mainnet_*.json.

3. blobfee.py  (Python 3.11+ standard library)
   The blob base fee formulas of EIP-4844 and EIP-7918, checked against the
   saved headers, and the numbers used in the note.
     python3 blobfee.py > output/blobfee_summary.txt

4. Beacon API check (curl, one public beacon node, 2026-11-12)
   Asked publicnode for the blobs of a slot 45 days back.
   Output: output/beacon_old_blobs.txt

Figures: python3 ../figures.py (matplotlib, Pillow, Noto Sans CJK) -> ../images/*.webp
