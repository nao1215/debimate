Python 3.10+ standard library only. No external service is contacted.

price_feed.py: checks of a mock feed value.
  python3 price_feed.py > output.txt

deviation_heartbeat.py: stored price vs a simulated market price under a
deviation threshold and a heartbeat (seeded random walk, not real data).
  python3 deviation_heartbeat.py > deviation_heartbeat_output.txt
The figure images/oracle_deviation_heartbeat.svg is drawn by ../figures.py
(needs matplotlib): python3 ../figures.py
