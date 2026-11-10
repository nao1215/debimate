Liquidations in a simulated over-collateralized lending market (no network access)
Python 3.10+ standard library only.
  cd content/notes/blockchain-systems/lending/lab
  python3 lending_sim.py > lending_sim_output.txt
The output is deterministic. The figures in ../images are drawn by
../figures.py (lending_rate.svg and lending_liquidation.svg need matplotlib):
  python3 ../figures.py
