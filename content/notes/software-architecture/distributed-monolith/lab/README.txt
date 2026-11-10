Synchronous call chain experiment
Python 3 standard library only (checked with Python 3.14.4).
Run from the repository root:
  python3 content/notes/software-architecture/distributed-monolith/lab/chain.py
It starts three HTTP servers on 127.0.0.1 and takes about one minute.
No external network is used. Latencies change by a few ms on each run.
output.txt is actual output of chain.py.
The figure is drawn from output.txt (matplotlib needed):
  python3 content/notes/software-architecture/distributed-monolith/figures.py
