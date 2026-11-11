"""L1 cost per L2 transaction when a batch is posted in blobs (calculation only).

Constants from the specs:
  GAS_PER_BLOB = 2**17, 4096 field elements x 32 bytes = 131,072 bytes per blob
    (https://eips.ethereum.org/EIPS/eip-4844)
  blobs per block (target / max), by period:
    3 / 6   Cancun, 2024-03  (EIP-4844)
    6 / 9   Prague, 2025-05  (https://eips.ethereum.org/EIPS/eip-7691)
    10 / 15 BPO1, 2025-12-09  (dates: https://eips.ethereum.org/EIPS/eip-7607,
    14 / 21 BPO2, 2026-01-07   values: go-ethereum params/chainspecs/mainnet.json)
  21,000 intrinsic gas per L1 transaction
    (https://ethereum.org/en/developers/docs/gas/)
Assumptions (not measured):
  one compressed L2 transaction is 150 bytes;
  a batch is one blob transaction, and the gas of the rollup contract call on L1
  is ignored, so the execution gas is only the 21,000 fixed part;
  131,072 bytes per blob is an upper bound (real encodings fit a little less).
Execution gas and blob gas are priced by different base fees, so they are kept
apart and never added together.
Run: python3 batch_cost.py
"""

GAS_PER_BLOB = 2**17
BLOB_BYTES = 4096 * 32
TX_GAS = 21_000
TX_BYTES = 150
SLOT_SECONDS = 12
# (period, target, max) blobs per block
PARAMS = [("Cancun 2024-03", 3, 6), ("Prague 2025-05", 6, 9),
          ("BPO1 2025-12", 10, 15), ("BPO2 2026-01", 14, 21)]


def blobs_for(n):
    return -(-n * TX_BYTES // BLOB_BYTES)  # ceil


def per_tx(n):
    """(execution gas per tx, blob gas per tx) for a batch of n transactions."""
    return TX_GAS / n, GAS_PER_BLOB * blobs_for(n) / n


def main():
    print(f"{'txs':>6} {'blobs':>5} {'exec gas/tx':>12} {'blob gas/tx':>12}")
    for n in (1, 10, 100, 500, 873, 874, 1000, 2000, 5000):
        e, b = per_tx(n)
        print(f"{n:>6} {blobs_for(n):>5} {e:>12.1f} {b:>12.1f}")
    per_blob = BLOB_BYTES // TX_BYTES
    print(f"txs that fill one blob: {per_blob}")
    for period, target, most in PARAMS:
        print(f"{period}: target {target} blobs = {per_blob * target / SLOT_SECONDS:.0f} txs/s, "
              f"max {most} blobs = {per_blob * most / SLOT_SECONDS:.0f} txs/s "
              "for all rollups together")


if __name__ == "__main__":
    main()
