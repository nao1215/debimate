"""mainnet のブロックヘッダーから、blob の手数料に関わる値だけを取り出して保存する。

2026-11-12 に、公開の RPC（https://ethereum-rpc.publicnode.com）へ 1 回ずつ
JSON-RPC のバッチ（1 回に 100 件の eth_getBlockByNumber）で問い合わせた。
  - 2024-03-27: ブロック 19,526,600〜19,527,399（800 個、blobscriptions で値上がりした時間帯）
  - 2026-11-12: ブロック 26,399,000〜26,399,299（300 個、BPO2 の設定）
取り出す値: number, timestamp, excessBlobGas, blobGasUsed, baseFeePerGas
"""
import json, os, subprocess

URL = "https://ethereum-rpc.publicnode.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
RANGES = {
    "mainnet_2024-03-27_every_block.json": range(19526600, 19527400),
    "mainnet_2026-11_every_block.json": range(26399000, 26399300),
}

for name, nums in RANGES.items():
    nums, res = list(nums), []
    for k in range(0, len(nums), 100):
        reqs = [{"jsonrpc": "2.0", "id": n, "method": "eth_getBlockByNumber", "params": [hex(n), False]}
                for n in nums[k:k + 100]]
        out = subprocess.run(["curl", "-s", "-m", "90", "-X", "POST", "-H", "content-type: application/json",
                              "--data", json.dumps(reqs), URL], capture_output=True, text=True, check=True).stdout
        res += json.loads(out)
    rows = [{k: int(r["result"][k], 16) for k in ("number", "timestamp", "excessBlobGas", "blobGasUsed", "baseFeePerGas")}
            for r in sorted(res, key=lambda r: r["id"])]
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(rows, f, indent=0)
