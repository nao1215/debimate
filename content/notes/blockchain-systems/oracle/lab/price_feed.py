"""Run with Python 3.10+: python3 price_feed.py (no external dependencies)."""
from dataclasses import dataclass, replace
from decimal import Decimal


@dataclass(frozen=True)
class FeedValue:
    pair: str
    answer: int
    decimals: int
    updated_at: int


NOW = 1_800_000_000
MAX_AGE = 300
MIN_PRICE = Decimal("1")
MAX_PRICE = Decimal("5000")


def read_price(feed: FeedValue, now: int) -> Decimal:
    if feed.pair != "DEMO/USD":
        raise ValueError("wrong pair")
    if not 0 <= feed.decimals <= 18:
        raise ValueError("unsupported decimals")
    if feed.answer <= 0:
        raise ValueError("non-positive price")
    if feed.updated_at <= 0 or feed.updated_at > now:
        raise ValueError("invalid timestamp")
    if now - feed.updated_at > MAX_AGE:
        raise ValueError("stale price")
    price = Decimal(feed.answer) / (Decimal(10) ** feed.decimals)
    if not MIN_PRICE <= price <= MAX_PRICE:
        raise ValueError("price outside application bounds")
    return price


base = FeedValue("DEMO/USD", 2000 * 10**8, 8, NOW - 30)
cases = [
    ("fresh", base, "ACCEPT 2000.00 USD"),
    ("age 300s", replace(base, updated_at=NOW - 300), "ACCEPT 2000.00 USD"),
    ("age 301s", replace(base, updated_at=NOW - 301), "REJECT stale price"),
    ("no update", replace(base, updated_at=0), "REJECT invalid timestamp"),
    ("future", replace(base, updated_at=NOW + 1), "REJECT invalid timestamp"),
    ("zero", replace(base, answer=0), "REJECT non-positive price"),
    ("negative", replace(base, answer=-1), "REJECT non-positive price"),
    ("6 decimals", replace(base, answer=2000 * 10**6, decimals=6),
     "ACCEPT 2000.00 USD"),
    ("bad decimals", replace(base, decimals=19), "REJECT unsupported decimals"),
    ("wrong pair", replace(base, pair="DEMO/ETH"), "REJECT wrong pair"),
    ("huge price", replace(base, answer=100_000 * 10**8),
     "REJECT price outside application bounds"),
    ("plausible wrong", replace(base, answer=1800 * 10**8), "ACCEPT 1800.00 USD"),
]

for name, value, expected in cases:
    try:
        result = f"ACCEPT {read_price(value, NOW):.2f} USD"
    except ValueError as error:
        result = f"REJECT {error}"
    assert result == expected, (name, result, expected)
    print(f"{name}: {result}")

print(f"Assertions: PASS ({len(cases)} cases)")
