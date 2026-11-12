"""blob の手数料の式（EIP-4844 と EIP-7918）を Python で書き、mainnet のブロックヘッダーと照らす。

式は仕様の擬似コードをそのまま写した:
  https://eips.ethereum.org/EIPS/eip-4844#helpers
  https://eips.ethereum.org/EIPS/eip-7918#specification
"""
import datetime, json, os, statistics

GAS_PER_BLOB = 2**17          # 131,072
BLOB_BASE_COST = 2**13        # EIP-7918 の定数
MIN_BASE_FEE_PER_BLOB_GAS = 1

# (target, max, update fraction, EIP-7918 の有無)
CANCUN = (3, 6, 3338477, False)       # Dencun、2024-03-13
PRAGUE = (6, 9, 5007716, False)       # Pectra、2025-05-07（EIP-7691）
BPO2 = (14, 21, 11684671, True)       # Fusaka の BPO2、2026-01-07


def fake_exponential(factor, numerator, denominator):
    i, output, acc = 1, 0, factor * denominator
    while acc > 0:
        output += acc
        acc = (acc * numerator) // (denominator * i)
        i += 1
    return output // denominator


def blob_base_fee(excess, params):
    return fake_exponential(MIN_BASE_FEE_PER_BLOB_GAS, excess, params[2])


def next_excess(excess, used, base_fee, params):
    target, mx, _, reserve = params
    if excess + used < target * GAS_PER_BLOB:
        return 0
    if reserve and BLOB_BASE_COST * base_fee > GAS_PER_BLOB * blob_base_fee(excess, params):
        return excess + used * (mx - target) // mx      # 下限より安い間は、使った blob に応じて上がるだけで下がらない
    return excess + used - target * GAS_PER_BLOB


def verify(path, params):
    rows = json.load(open(path))
    ok = sum(next_excess(a["excessBlobGas"], a["blobGasUsed"], a["baseFeePerGas"], params) == b["excessBlobGas"]
             for a, b in zip(rows, rows[1:]) if b["number"] == a["number"] + 1)
    pairs = sum(1 for a, b in zip(rows, rows[1:]) if b["number"] == a["number"] + 1)
    return ok, pairs


def utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    spike_path = os.path.join(out, "mainnet_2024-03-27_every_block.json")
    now_path = os.path.join(out, "mainnet_2026-11_every_block.json")

    print("== 式とヘッダーの照合")
    for path, params, name in ((spike_path, CANCUN, "Cancun の式"), (now_path, BPO2, "BPO2 の式"),
                               (now_path, BPO2[:3] + (False,), "BPO2 から EIP-7918 を外した式")):
        ok, n = verify(path, params)
        print(f"{name}: 次のブロックの excessBlobGas が一致 {ok}/{n}")

    print("== 2024-03-27（Cancun、target 3・max 6）")
    rows = json.load(open(spike_path))
    last_floor = max((r for r in rows if r["excessBlobGas"] == 0), key=lambda r: r["number"])
    peak = max(rows, key=lambda r: r["excessBlobGas"])
    for label, r in (("最後に 1 wei だったブロック", last_floor), ("最も高いブロック", peak)):
        fee = blob_base_fee(r["excessBlobGas"], CANCUN)
        print(f"{label}: {r['number']} {utc(r['timestamp'])} blob の単価 {fee} wei, "
              f"base fee {r['baseFeePerGas']} wei")
    fee = blob_base_fee(peak["excessBlobGas"], CANCUN)
    blob_per_byte = fee * GAS_PER_BLOB / 126945         # 1 個の blob を満たした時の 1 バイトあたり
    calldata_per_byte = 16 * peak["baseFeePerGas"]      # Cancun の calldata（0 でないバイト 16 gas）
    print(f"最も高いブロックで、blob の 1 バイトの値段は calldata の {blob_per_byte / calldata_per_byte:.2f} 倍")
    full = [r for r in rows if last_floor["number"] < r["number"] <= peak["number"]]
    print(f"その間の {len(full)} ブロックのうち、上限の 6 個を入れたブロック {sum(r['blobGasUsed'] == 6 * GAS_PER_BLOB for r in full)}")

    print("== 2026-11-12（BPO2、target 14・max 21）")
    rows = json.load(open(now_path))
    blobs = [r["blobGasUsed"] // GAS_PER_BLOB for r in rows]
    fees = [blob_base_fee(r["excessBlobGas"], BPO2) for r in rows]
    reserve = [BLOB_BASE_COST * r["baseFeePerGas"] // GAS_PER_BLOB for r in rows]
    below = sum(BLOB_BASE_COST * r["baseFeePerGas"] > GAS_PER_BLOB * f for r, f in zip(rows, fees))
    print(f"{utc(rows[0]['timestamp'])} から {utc(rows[-1]['timestamp'])} の {len(rows)} ブロック")
    print(f"1 ブロックの blob の数: 平均 {statistics.mean(blobs):.1f}, 中央値 {statistics.median(blobs)}, "
          f"target の 14 を超えたブロック {sum(b > 14 for b in blobs)}")
    print(f"blob の単価の中央値 {statistics.median(fees):.0f} wei, 下限（base fee x 8192 / 131072）の中央値 "
          f"{statistics.median(reserve):.0f} wei, 単価が下限より安かったブロック {below}")
    print(f"base fee の中央値 {statistics.median(r['baseFeePerGas'] for r in rows):.0f} wei")
    ex = rows[0]["excessBlobGas"]
    for r in rows:
        ex = next_excess(ex, r["blobGasUsed"], r["baseFeePerGas"], BPO2[:3] + (False,))
    print(f"同じ使われ方を EIP-7918 なしの式に通すと、300 ブロック後の単価は {blob_base_fee(ex, BPO2)} wei")
    print(f"下限にある時、1 個の blob は calldata（0 でないバイト 40 gas）の {BLOB_BASE_COST / 40:.1f} バイト分")

    print("== batch の件数と 1 件あたりの手数料（L2 の 1 件 180 バイト、1 個の blob に 126,945 バイト、上の中央値）")
    base, fee = statistics.median(r["baseFeePerGas"] for r in rows), statistics.median(fees)
    for n in (100, 352, 705, 706, 1410, 4230):    # 1 つのトランザクションに blob は 6 個まで（EIP-7594）
        k = -(-n * 180 // 126945)
        print(f"{n:5d} 件 blob {k:2d} 個 1 件あたり {(21000 * base + k * GAS_PER_BLOB * fee) / n / 1e9:.1f} gwei")
