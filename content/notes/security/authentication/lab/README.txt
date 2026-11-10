6-digit confirmation code guessing (calculation, no randomness)
Requirements: Python 3 (stdlib only).
From content/notes/security/authentication: python3 lab/otp_guessing.py > lab/otp_guessing_output.txt
The output is identical on every run.
Figure: uv run --with matplotlib python figures.py (writes images/authentication_otp_guessing.svg).
Assumptions are in the docstring of otp_guessing.py: 10^6 equally likely codes,
no repeated guesses on one code, 10-minute code lifetime, 10 guesses/s when
unthrottled, and no unlock after a lockout within the horizon.
