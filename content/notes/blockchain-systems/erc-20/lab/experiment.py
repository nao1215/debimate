#!/usr/bin/env python3
"""ERC-20 の実験 4 つをローカルの Anvil で走らせ、結果を output/ に JSON で残す。

1. 残高の置き場所: トークンを送っても ETH の残高は変わらず、コントラクトのストレージが変わる。
2. approve の付け替えの割り込み: 100 から 50 へ変える間に、spender が先に 100 を引き出す。
3. 他人の 0 トークンの transferFrom: 許可が無くても成功し、Transfer のイベントが残る。
4. 規格から外れたトークン 4 種と、預け入れの書き方 4 通りの組み合わせ。

前提: anvil・cast・solc が PATH にあること（run.sh が用意する）。公開のネットワークには繋がない。
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
RPC = "http://127.0.0.1:18645"
UNIT = 10**18  # decimals = 18。本文では 1 UNIT を「1 トークン」と書く
GWEI = 10**9


def rpc(method, *params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)}).encode()
    req = urllib.request.Request(RPC, body, {"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=10).read())
    if "error" in res:
        raise RuntimeError(f"{method}: {res['error']}")
    return res["result"]


def calldata(sig, *args):
    return subprocess.check_output(["cast", "calldata", sig, *map(str, args)], text=True).strip()


def send(frm, to, data, tip_gwei=1, gas=300_000):
    tx = {"from": frm, "data": data, "gas": hex(gas),
          "maxPriorityFeePerGas": hex(tip_gwei * GWEI), "maxFeePerGas": hex((tip_gwei + 5) * GWEI)}
    if to:
        tx["to"] = to
    return rpc("eth_sendTransaction", tx)


def receipt(h, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        r = rpc("eth_getTransactionReceipt", h)
        if r:
            return r
        time.sleep(0.02)
    raise TimeoutError(h)


def call_uint(to, sig, *args):
    return int(rpc("eth_call", {"to": to, "data": calldata(sig, *args)}, "latest"), 16)


def compile_all():
    out = subprocess.check_output(
        ["solc", "--combined-json", "abi,bin", "--optimize", os.path.join(HERE, "Tokens.sol")], text=True)
    return {k.split(":")[-1]: v for k, v in json.loads(out)["contracts"].items()}


def deploy(c, frm, name, ctor_sig=None, *args):
    data = "0x" + c[name]["bin"]
    if ctor_sig:
        data += calldata(ctor_sig, *args)[10:]  # 先頭 4 バイトのセレクタを除く
    r = receipt(send(frm, None, data, gas=3_000_000))
    assert r["status"] == "0x1", name
    return r["contractAddress"]


def exp_storage(c, acct):
    owner, receiver = acct[0], acct[2]
    tok = deploy(c, owner, "StandardToken", "f(string,string,uint256)", "Study Token", "STU", 1000 * UNIT)
    eth_before = int(rpc("eth_getBalance", receiver, "latest"), 16)
    slot = subprocess.check_output(["cast", "index", "address", receiver, "3"], text=True).strip()
    st_before = int(rpc("eth_getStorageAt", tok, slot, "latest"), 16)
    r = receipt(send(owner, tok, calldata("transfer(address,uint256)", receiver, 100 * UNIT)))
    eth_after = int(rpc("eth_getBalance", receiver, "latest"), 16)
    st_after = int(rpc("eth_getStorageAt", tok, slot, "latest"), 16)
    return {
        "token": tok, "receiver": receiver, "balanceOf_slot": slot,
        "receiver_eth_before_wei": eth_before, "receiver_eth_after_wei": eth_after,
        "storage_before": st_before, "storage_after": st_after,
        "balanceOf_after": call_uint(tok, "balanceOf(address)", receiver),
        "transfer_gasUsed": int(r["gasUsed"], 16), "transfer_to": r["to"],
        "transfer_logs": len(r["logs"]),
    }


def wait_new_block():
    b = int(rpc("eth_blockNumber"), 16)
    while int(rpc("eth_blockNumber"), 16) == b:
        time.sleep(0.01)
    return time.time()


def race(c, acct, change):
    """change は "approve"・"decrease"・"zero_then"（0 にしてから 50 にする）。owner が許可を 100 から 50 にしようとする所へ、spender が割り込む。"""
    owner, spender = acct[0], acct[1]
    tok = deploy(c, owner, "StandardToken", "f(string,string,uint256)", "Study Token", "STU", 1000 * UNIT)
    receipt(send(owner, tok, calldata("approve(address,uint256)", spender, 100 * UNIT)))

    rpc("evm_setAutomine", False)
    rpc("evm_setIntervalMining", 2)  # 2 秒ごとにブロックを作る（Ethereum の本番は 12 秒）
    events = []
    t0_box = {}
    done = threading.Event()

    def ev(kind, **kw):
        events.append({"t": round(time.time() - t0_box["t0"], 3), "kind": kind, **kw})

    def attacker():
        seen = set()
        while not done.is_set():
            pool = rpc("txpool_content")["pending"]
            for frm, txs in pool.items():
                for tx in txs.values():
                    if frm.lower() == owner.lower() and tx["hash"] not in seen:
                        seen.add(tx["hash"])
                        ev("attacker_saw", tx=tx["hash"], input=tx["input"][:10])
                        h = send(spender, tok, calldata("transferFrom(address,address,uint256)", owner, spender, 100 * UNIT), tip_gwei=20)
                        ev("attacker_sent", tx=h, amount=100, tip_gwei=20)
                        t0_box["front"] = h
                        return
            time.sleep(0.05)

    wait_new_block()
    time.sleep(0.4)
    t0_box["t0"] = time.time()
    th = threading.Thread(target=attacker)
    th.start()
    if change == "approve":
        h_owner = send(owner, tok, calldata("approve(address,uint256)", spender, 50 * UNIT), tip_gwei=1)
    elif change == "decrease":
        h_owner = send(owner, tok, calldata("decreaseAllowance(address,uint256)", spender, 50 * UNIT), tip_gwei=1)
    else:
        h_owner = send(owner, tok, calldata("approve(address,uint256)", spender, 0), tip_gwei=1)
    ev("owner_sent", tx=h_owner, change=change, tip_gwei=1)
    th.join(timeout=10)
    done.set()
    r_owner = receipt(h_owner)
    r_front = receipt(t0_box["front"])
    ev("block_mined", block=int(r_owner["blockNumber"], 16),
       order=[{"tx": "spender_transferFrom_100", "index": int(r_front["transactionIndex"], 16), "status": int(r_front["status"], 16)},
              {"tx": "owner_" + change, "index": int(r_owner["transactionIndex"], 16), "status": int(r_owner["status"], 16)}])
    allow = call_uint(tok, "allowance(address,address)", owner, spender)
    ev("allowance_after_block", allowance=allow // UNIT, spender_balance=call_uint(tok, "balanceOf(address)", spender) // UNIT)
    if change == "zero_then":
        # 0 になったのを見て、結果を見比べずに 50 を許可する
        h3 = send(owner, tok, calldata("approve(address,uint256)", spender, 50 * UNIT), tip_gwei=1)
        ev("owner_sent", tx=h3, change="approve_50_after_zero", tip_gwei=1)
        r3 = receipt(h3)
        ev("block_mined", block=int(r3["blockNumber"], 16),
           order=[{"tx": "owner_approve_50", "index": int(r3["transactionIndex"], 16), "status": int(r3["status"], 16)}])
        allow = call_uint(tok, "allowance(address,address)", owner, spender)
        ev("allowance_after_block", allowance=allow // UNIT, spender_balance=call_uint(tok, "balanceOf(address)", spender) // UNIT)
    second = None
    if allow > 0:
        h2 = send(spender, tok, calldata("transferFrom(address,address,uint256)", owner, spender, allow), tip_gwei=20)
        ev("attacker_sent", tx=h2, amount=allow // UNIT, tip_gwei=20)
        r2 = receipt(h2)
        second = int(r2["status"], 16)
        ev("block_mined", block=int(r2["blockNumber"], 16),
           order=[{"tx": f"spender_transferFrom_{allow // UNIT}", "index": int(r2["transactionIndex"], 16), "status": second}])
    rpc("evm_setAutomine", True)
    return {
        "change": change, "events": events,
        "front_block": int(r_front["blockNumber"], 16), "owner_block": int(r_owner["blockNumber"], 16),
        "spender_total": call_uint(tok, "balanceOf(address)", spender) // UNIT,
        "allowance_final": call_uint(tok, "allowance(address,address)", owner, spender) // UNIT,
    }


def exp_zero(c, acct):
    owner, stranger = acct[0], acct[3]
    lookalike = "0xf39F000000000000000000000000000000002266"
    tok = deploy(c, owner, "StandardToken", "f(string,string,uint256)", "Study Token", "STU", 1000 * UNIT)
    before = call_uint(tok, "allowance(address,address)", owner, stranger)
    r = receipt(send(stranger, tok, calldata("transferFrom(address,address,uint256)", owner, lookalike, 0)))
    log = r["logs"][0]
    return {
        "owner": owner, "stranger": stranger, "lookalike": lookalike, "allowance_before": before,
        "status": int(r["status"], 16), "log_topics": log["topics"], "log_data": log["data"],
        "owner_balance_after": call_uint(tok, "balanceOf(address)", owner) // UNIT,
    }


def exp_matrix(c, acct):
    owner, user, broke = acct[0], acct[4], acct[5]
    styles = ["depositRequire", "depositIgnore", "depositSafe", "depositMeasured"]
    tokens = [("StandardToken", "f(string,string,uint256)", ("Std", "STD", 1000 * UNIT)),
              ("NoReturnToken", "f(uint256)", (1000 * UNIT,)),
              ("FalseToken", "f(uint256)", (1000 * UNIT,)),
              ("FeeToken", "f(uint256)", (1000 * UNIT,))]
    rows = []
    for name, sig, args in tokens:
        for style in styles:
            tok = deploy(c, owner, name, sig, *args)
            vault = deploy(c, owner, "Vault")
            # FalseToken だけは残高 0 の利用者が預ける（失敗の扱いを見るため）
            depositor = broke if name == "FalseToken" else user
            if depositor == user:
                # FeeToken は渡す時にも 2% 減るので、多めに渡す
                receipt(send(owner, tok, calldata("transfer(address,uint256)", user, 200 * UNIT)))
            receipt(send(depositor, tok, calldata("approve(address,uint256)", vault, 100 * UNIT)))
            held = call_uint(tok, "balanceOf(address)", depositor) / UNIT
            r = receipt(send(depositor, vault, calldata(f"{style}(address,uint256)", tok, 100 * UNIT)))
            rows.append({
                "token": name, "style": style, "depositor_balance_before": held,
                "status": int(r["status"], 16),
                "credited": call_uint(vault, "credited(address,address)", tok, depositor) / UNIT,
                "vault_received": call_uint(tok, "balanceOf(address)", vault) / UNIT,
            })
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    c = compile_all()
    acct = rpc("eth_accounts")
    results = {
        "versions": {
            "anvil": subprocess.check_output(["anvil", "--version"], text=True).strip().splitlines()[0],
            "solc": subprocess.check_output(["solc", "--version"], text=True).strip().splitlines()[-1],
        },
        "storage": exp_storage(c, acct),
        "race_approve": race(c, acct, "approve"),
        "race_decrease": race(c, acct, "decrease"),
        "race_zero_then": race(c, acct, "zero_then"),
        "zero_transferFrom": exp_zero(c, acct),
        "matrix": exp_matrix(c, acct),
    }
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in results.items() if k != "matrix"}, indent=1, ensure_ascii=False)[:4000])
    for r in results["matrix"]:
        print(r["token"], r["style"], r["status"], r["credited"], r["vault_received"])


if __name__ == "__main__":
    sys.exit(main())
