"""Chance that an online attacker guesses a 6-digit confirmation code for one
account, under different attempt limits (calculation, no randomness).

Assumptions:
- The code is uniform over 10^6 values and the attacker never repeats a guess
  for the same code, so k guesses on one code succeed with probability k/10^6.
- A code is valid for 10 minutes (the upper bound NIST SP 800-63B-4 sets for
  out-of-band authentication); after that the attacker asks for a new code.
- Without throttling the attacker sends 10 guesses per second.
- "lockout N": the authenticator is disabled after N consecutive failures
  (SP 800-63B-4 sec. 3.2.2 caps N at 100). No unlock within the horizon.
- "rate limit": at most 5 guesses per minute, never locked out.

Run: python3 lab/otp_guessing.py
"""

SPACE = 10**6
CODE_LIFETIME = 600  # seconds
SETTINGS = [
    ("no limit (10 guesses/s)", 10.0, None),
    ("rate limit 5 guesses/min", 5 / 60, None),
    ("lockout after 100 failures", 10.0, 100),
    ("lockout after 10 failures", 10.0, 10),
]
HOURS = [1 / 60, 1, 24, 24 * 30]


def success(rate, lockout, seconds):
    """Probability of at least one correct guess within `seconds`."""
    per_code = min(rate * CODE_LIFETIME, SPACE)  # guesses on one code
    total = rate * seconds
    if lockout is not None:
        total = min(total, lockout)
    full_codes, rest = divmod(total, per_code)
    fail = (1 - per_code / SPACE) ** full_codes * (1 - rest / SPACE)
    return 1 - fail


def main():
    print(f"code space={SPACE:,}  code lifetime={CODE_LIFETIME} s")
    header = "".join(f"{label:>12}" for label in ("1 min", "1 h", "1 day", "30 days"))
    print(f"{'setting':<28}{header}")
    for name, rate, lockout in SETTINGS:
        cells = "".join(f"{success(rate, lockout, h * 3600):12.4%}" for h in HOURS)
        print(f"{name:<28}{cells}")


if __name__ == "__main__":
    main()
