"""Silverback bot for the monitor experiment: every Token Transfer to bob -> HTTP POST to the sink.

Written the way the docs show it (no on_startup backfill: after a restart the bot starts at head).
Env: TOKEN, BOB, SINK_URL, SINK_RAISE (1 = raise_for_status on the POST, the default here).
"""
import json
import os
import time
from pathlib import Path

import requests
from ape import Contract

from silverback import SilverbackBot

bot = SilverbackBot()

token = Contract(os.environ["TOKEN"], abi=json.loads((Path(__file__).parent / "token_abi.json").read_text()))
BOB = os.environ["BOB"]
SINK_URL = os.environ["SINK_URL"]
RAISE = os.environ.get("SINK_RAISE", "1") == "1"


@bot.on_(token.Transfer, to=BOB)
def notify(log):
    body = {
        "amount": int(log.value),
        "block": log.block_number,
        "block_hash": log.block_hash.hex() if isinstance(log.block_hash, bytes) else str(log.block_hash),
        "tx": log.transaction_hash.hex() if isinstance(log.transaction_hash, bytes) else str(log.transaction_hash),
        "log_index": log.log_index,
        "removed": getattr(log, "removed", None),
        "handled_at": time.time(),
    }
    r = requests.post(SINK_URL, json=body, timeout=5)
    if RAISE:
        r.raise_for_status()
    return {"notified_amount": int(log.value)}
