Per-route versus total error-rate alert simulation
Python 3 standard library only. random.seed is fixed, so the output is deterministic.
  python3 route_alert.py
From the repository root, the figure is regenerated with matplotlib:
  python3 content/notes/software-architecture/strangler-fig/figures.py
This is a simulation, not a measurement. Assumptions (20 routes, Zipf traffic,
error rates, alert thresholds) are written at the top of route_alert.py.
output.txt is the actual output of route_alert.py.
