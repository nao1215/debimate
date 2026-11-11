Liquidations in a simulated over-collateralized lending market (no network access)
Python 3.10+ standard library only.
  cd content/notes/blockchain-systems/lending/lab
  python3 lending_sim.py > lending_sim_output.txt
The output is deterministic. The figures in ../images are drawn by
../figures.py as WebP (lending_rate.webp and lending_liquidation.webp need matplotlib,
the other figures need headless Chrome and Pillow):
  python3 ../figures.py
