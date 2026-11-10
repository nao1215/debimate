Repeated squaring timing on this machine (measurement, not a simulation)
Requirements: Python 3, uv (pulls sympy). Linux only (os.sched_setaffinity).
From content/notes/security/timelock-encryption:
  uv run --with sympy python lab/squaring_time.py > lab/squaring_time_output.txt
n is built from fixed-seed primes, so n and the match=True checks are the same
on every run. The timings are wall-clock measurements and change with CPU
boost and the load from other processes; each value is the fastest of 5 runs.
The saved output was taken on 2026-11-10 on an AMD Ryzen AI MAX+ 395
(16 cores / 32 threads) with a load average of about 20 from other jobs;
uptime lines at the top and bottom record the load.
Workers are pinned to logical CPUs 0-15 (distinct physical cores on this CPU).
Figure: uv run --with matplotlib --with numpy python figures.py
(reads lab/squaring_time_output.txt; it does not re-measure).
