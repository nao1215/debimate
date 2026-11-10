Tor guard exposure simulation (not a measurement of the live Tor network)
Requirements: Python 3 (stdlib only).
From content/notes/security/tor: python3 lab/guard_exposure.py > lab/guard_exposure_output.txt
The seed is fixed, so the output is identical on every run.
Figure: uv run --with matplotlib python figures.py (writes images/tor_guard_exposure.svg).
Assumptions are in the docstring of guard_exposure.py: the attacker holds a
fraction c of guard and exit bandwidth, picks are independent, and a fixed
Guard is not rotated during the 1,000 circuits.
