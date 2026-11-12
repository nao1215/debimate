"""2021-09-27 に 7,676 ETH の手数料を払ったトランザクションを、公開の RPC から 1 回だけ読む。

python3 fetch_deversifi.py -> output/deversifi.json

読むだけで、何も送らない。標準ライブラリだけで動く。
"""

import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RPC = "https://eth.drpc.org"
TX = "0x2c9931793876db33b1a9aad123ad4921dfb9cd5e59dbb78ce78f277759587115"


def call(method, *params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)}).encode()
    req = urllib.request.Request(RPC, body, {"Content-Type": "application/json", "User-Agent": "note-lab"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["result"]


def main():
    tx = call("eth_getTransactionByHash", TX)
    rc = call("eth_getTransactionReceipt", TX)
    blk = call("eth_getBlockByNumber", tx["blockNumber"], False)
    g = lambda x: int(x, 16)
    gwei, eth = 10**9, 10**18
    used, eff, base = g(rc["gasUsed"]), g(rc["effectiveGasPrice"]), g(blk["baseFeePerGas"])
    summary = {
        "hash": TX, "block": g(tx["blockNumber"]), "type": g(tx["type"]), "value_wei": g(tx["value"]),
        "gas_limit": g(tx["gas"]), "gas_used": used, "status": rc["status"],
        "base_fee_gwei": base / gwei,
        "max_priority_fee_gwei": g(tx["maxPriorityFeePerGas"]) / gwei,
        "max_fee_gwei": g(tx["maxFeePerGas"]) / gwei,
        "effective_gas_price_gwei": eff / gwei,
        "fee_eth": used * eff / eth, "burn_eth": used * base / eth,
        "tip_eth": used * (eff - base) / eth, "cap_eth": g(tx["gas"]) * g(tx["maxFeePerGas"]) / eth,
    }
    out = HERE / "output"
    out.mkdir(exist_ok=True)
    (out / "deversifi.json").write_text(json.dumps(
        {"summary": summary, "tx": tx, "receipt": {k: v for k, v in rc.items() if k != "logsBloom"},
         "block_base_fee": blk["baseFeePerGas"], "block_miner": blk["miner"]},
        ensure_ascii=False, indent=2) + "\n")
    for k, v in summary.items():
        print(k, v)


if __name__ == "__main__":
    main()
