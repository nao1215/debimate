Bitcoin Block note: data and analysis (Python 3, standard library only)

  python3 fetch_mainnet.py     # 2,017 blocks (973,727-975,743) from mempool.space, about 135 requests (saved 2026-11-17: output/blocks.json)
  python3 fetch_coinbase.py    # coinbase transaction of block 973,962 (output/coinbase_973962.json)
  python3 fetch_duplicates.py  # coinbase txids of blocks 91,722 / 91,812 / 91,842 / 91,880 (output/duplicates.json)
  python3 analyze.py           # header hashes, time rules, version bits, BIP34 height, size and weight (output/analyze.txt)

Figures: python3 ../figures.py (matplotlib and Pillow).
