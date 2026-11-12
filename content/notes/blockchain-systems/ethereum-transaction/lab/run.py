"""Ethereum のトランザクションを手元の Anvil で作り、書き換え・手数料・残高・失敗を記録する。

python3 run.py  -> output/results.json, output/log.txt

Foundry 1.7.1 の anvil と cast を PATH に置いて実行する。接続先は 127.0.0.1 だけで、
公開ネットワーク・実資産は使わない。秘密鍵は Anvil が全員に配る開発用の鍵（公開済みの値）。
"""

import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
PORT = 18651
RPC = f"http://127.0.0.1:{PORT}"
CHAIN = 31337
# Anvil の開発用アカウント 0 と 2 の秘密鍵（誰でも知っている値。実資産には使わない）
KEY0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
KEY2 = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
TO = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # アカウント 1
GWEI = 10**9
ETH = 10**18
log_lines = []


def cast(*args, check=True):
    offline = args[0] in ("mktx", "decode-transaction", "--version")
    cmd = ["cast", *args] if offline else ["cast", args[0], "--rpc-url", RPC, *args[1:]]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr)
    return p.returncode, (p.stdout + p.stderr).strip()


def rpc(method, *params):
    return json.loads(cast("rpc", method, *[json.dumps(x) if not isinstance(x, str) else x for x in params])[1])


def log(*xs):
    line = " ".join(str(x) for x in xs)
    print(line)
    log_lines.append(line)


def sign(key, nonce, value_wei, max_fee, prio, gas=21000, to=TO):
    """署名済みのトランザクション（type 2）のバイト列を作る。ノードには送らない。"""
    return cast("mktx", "--private-key", key, to, "--value", str(value_wei),
                "--nonce", str(nonce), "--gas-limit", str(gas),
                "--gas-price", str(max_fee), "--priority-gas-price", str(prio),
                "--chain", str(CHAIN))[1]


def decode(raw):
    """バイト列から欄を読み、署名から送り主（signer）を復元する。"""
    return json.loads(json.loads(cast("decode-transaction", raw)[1]))


def publish(raw):
    """署名済みのバイト列をノードへ送る。受け付けなければエラーの文を返す。"""
    code, out = cast("publish", raw, check=False)
    if code != 0:
        return None, out.splitlines()[-1]
    return json.loads(out) if out.startswith("{") else out.strip('"'), None


def receipt(h):
    r = rpc("eth_getTransactionReceipt", h)
    b = rpc("eth_getBlockByNumber", r["blockNumber"], False)
    return r, int(b["baseFeePerGas"], 16)


def set_base_fee(gwei):
    """次のブロックの base fee を固定する（Anvil の開発用の命令）。比べやすくするため。"""
    rpc("anvil_setNextBlockBaseFeePerGas", hex(gwei * GWEI))


def balance(addr):
    return int(cast("balance", addr)[1])


def tamper(raw, old_hex, new_hex):
    """署名はそのままに、バイト列の一部だけを同じ長さの値に置き換える。"""
    assert raw.count(old_hex) == 1
    return raw.replace(old_hex, new_hex)


def exp_tamper(res):
    log("## 書き換え")
    raw = sign(KEY0, 0, 1 * ETH, 2 * GWEI, 1 * GWEI)
    d = decode(raw)
    log("raw", raw, "bytes", (len(raw) - 2) // 2)
    log("signer", d["signer"], "hash", d["hash"])
    cases = {
        "元のまま": raw,
        "value を 1 → 2 ETH": tamper(raw, "880de0b6b3a7640000", "881bc16d674ec80000"),
        "to の末尾 c8 → c9": tamper(raw, "dc79c8", "dc79c9"),
        "chainId を 31337 → 31338": tamper(raw, "827a6980", "827a6a80"),
    }
    rows = []
    for name, r in cases.items():
        dd = decode(r)
        rows.append({"case": name, "raw": r, "signer": dd["signer"], "hash": dd["hash"],
                     "signer_balance": balance(dd["signer"])})
    for row in rows:
        if row["case"] == "元のまま":
            continue
        _, err = publish(row["raw"])
        row["node"] = err or "受け付けた"
        log(row["case"], "signer", row["signer"], "balance", row["signer_balance"], "->", row["node"])
    # 書き換えで現れた送り主に残高を入れると、書き換えたバイト列がそのまま通る
    forged = rows[1]
    rpc("anvil_setBalance", forged["signer"], hex(10 * ETH))
    h, err = publish(forged["raw"])
    r, _ = receipt(forged["hash"])
    forged["after_funding"] = {"status": r["status"], "from": r["from"], "to": r["to"],
                               "value_wei": int(rpc("eth_getTransactionByHash", forged["hash"])["value"], 16)}
    log("資金を入れた後:", "status", r["status"], "from", r["from"], "hash", r["transactionHash"])
    h0, err0 = publish(raw)
    r0, _ = receipt(d["hash"])
    rows[0]["node"] = "受け付けた"
    rows[0]["receipt_hash"] = r0["transactionHash"]
    log("元のまま -> status", r0["status"], "receipt hash", r0["transactionHash"])
    res["tamper"] = {"raw": raw, "decoded": d, "rows": rows}


def exp_fee(res):
    log("## 手数料")
    rows = []
    nonce = int(cast("nonce", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")[1])
    for prio in [1, 50, 100]:
        raw = sign(KEY0, nonce, 0, 100 * GWEI, prio * GWEI)
        nonce += 1
        h = decode(raw)["hash"]
        set_base_fee(10)
        publish(raw)
        r, base = receipt(h)
        used, eff = int(r["gasUsed"], 16), int(r["effectiveGasPrice"], 16)
        row = {"max_fee_gwei": 100, "prio_gwei": prio, "base_gwei": base / GWEI,
               "eff_gwei": eff / GWEI, "gas_used": used, "fee_eth": used * eff / ETH,
               "burn_eth": used * base / ETH, "tip_eth": used * (eff - base) / ETH,
               "cap_eth": 21000 * 100 * GWEI / ETH}
        rows.append(row)
        log(row)
    raw = sign(KEY0, nonce, 0, 10 * GWEI, 20 * GWEI)
    _, err = publish(raw)
    log("priority fee 20 > maxFee 10 ->", err)
    res["fee"] = {"rows": rows, "prio_over_max": err}


def exp_reserve(res):
    log("## 残高")
    addr = decode(sign(KEY2, 0, 0, GWEI, GWEI))["signer"]
    bal = 1 * ETH + 1_000_000 * GWEI  # 1.001 ETH
    rpc("anvil_setBalance", addr, hex(bal))
    rows = []
    for gas, max_fee in [(21000, 100), (1_000_000, 40), (21000, 40)]:
        nonce = int(cast("nonce", addr)[1])
        raw = sign(KEY2, nonce, 1 * ETH, max_fee * GWEI, 1 * GWEI, gas=gas)
        need = 1 * ETH + gas * max_fee * GWEI
        h = decode(raw)["hash"]
        set_base_fee(10)
        _, err = publish(raw)
        row = {"gas_limit": gas, "max_fee_gwei": max_fee, "balance_eth": bal / ETH,
               "need_eth": need / ETH, "node": err or "受け付けた"}
        if not err:
            r, base = receipt(h)
            row["fee_eth"] = int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16) / ETH
            row["base_gwei"] = base / GWEI
        rows.append(row)
        log(row)
    res["reserve"] = rows


def exp_revert(res):
    log("## 失敗")
    # 呼ばれると必ず REVERT するだけのコントラクト: PUSH1 0 PUSH1 0 REVERT
    runtime = "60006000fd"
    initcode = "0x600580600b6000396000f3" + runtime
    out = cast("send", "--private-key", KEY0, "--json", "--create", initcode)[1]
    target = json.loads(out)["contractAddress"]
    sender = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    nonce = int(cast("nonce", sender)[1])
    before = balance(sender)
    raw = sign(KEY0, nonce, 0, 100 * GWEI, 1 * GWEI, gas=100_000, to=target)
    h = decode(raw)["hash"]
    set_base_fee(10)
    _, err = publish(raw)
    r, base = receipt(h)
    after = balance(sender)
    used, eff = int(r["gasUsed"], 16), int(r["effectiveGasPrice"], 16)
    row = {"status": r["status"], "gas_limit": 100_000, "gas_used": used,
           "eff_gwei": eff / GWEI, "fee_eth": used * eff / ETH,
           "balance_delta_eth": (before - after) / ETH, "nonce_after": int(cast("nonce", sender)[1]),
           "nonce_before": nonce, "block": int(r["blockNumber"], 16)}
    row["receipt"] = {k: v for k, v in r.items() if k != "logsBloom"}
    log(row)
    res["revert"] = row


def main():
    OUT.mkdir(exist_ok=True)
    anvil = subprocess.Popen(["anvil", "--port", str(PORT), "--silent"])
    try:
        for _ in range(100):
            if subprocess.run(["cast", "chain-id", "--rpc-url", RPC], capture_output=True).returncode == 0:
                break
            time.sleep(0.2)
        res = {"versions": {"cast": cast("--version", check=False)[1].splitlines()[0]}}
        exp_tamper(res)
        exp_fee(res)
        exp_reserve(res)
        exp_revert(res)
    finally:
        anvil.terminate()
    (OUT / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    (OUT / "log.txt").write_text("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    main()
