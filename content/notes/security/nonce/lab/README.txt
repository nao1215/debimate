Counter nonce reuse after restarts (simulation) vs. random nonces (formula)
Requirements: Python 3 (stdlib only).
From content/notes/security/nonce: python3 lab/counter_restart.py > lab/counter_restart_output.txt
The crash gaps come from a fixed seed, so the output is identical on every run.
Figure: uv run --with matplotlib python figures.py (writes images/nonce_counter_restart.svg).
Assumptions are in the docstring of counter_restart.py: one sender and one key,
10,000,000 messages, crashes with exponential gaps of mean 10,000 messages,
a crash right after a send loses everything since the last write.
