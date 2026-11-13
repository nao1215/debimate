Proof of Work note: experiments (Python 3, standard library only)

  python3 genesis.py          # check the genesis block's proof of work (output/genesis.txt)
  python3 mine.py 3000        # mine 3,000 toy blocks, about 3 minutes (output/trials.csv, mine.txt)
  python3 wait.py             # wait from a random send (output/wait.txt, wait.json)
  python3 fork.py 60 600      # two miners, 60 s delay (output/fork_60s.txt, fork_60s.json)
  python3 fork.py 6 600       # two miners, 6 s delay (output/fork_6s.txt, fork_6s.json)
  python3 attack.py           # white paper section 11 (output/attack.txt)
  python3 double_spend.py 200 # attacker with 40% hides a chain, about 2 minutes (output/double_spend.txt, double_spend.json)
  python3 catch_up.py         # exact probabilities for the double_spend.py race (output/catch_up.txt)
  python3 fetch_mainnet.py    # mainnet data from mempool.space (saved 2026-11-13; output/tip.json, difficulty_adjustments.json, difficulty_adjustment.json)

Figures: python3 ../figures.py (matplotlib and Pillow).
