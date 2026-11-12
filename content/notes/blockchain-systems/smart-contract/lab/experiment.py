#!/usr/bin/env python3
"""Smart Contract のノートの実験。手元の anvil だけを使い、公開ネットワークには繋がない。

1. 抽選（Lottery）に、当てずっぽうの番号で 100 回、同じトランザクションの中で
   当たり番号を計算するコントラクト（Predictor）で 100 回参加する。
2. ノード A の全トランザクションを、生のバイト列のままノード B・C に送り直す。
   B は A と同じブロックの時刻で、C は時刻を 1 秒ずらして実行させる。
3. private の変数に置いたクイズの正解を、eth_getStorageAt と配置のトランザクションから読む。
4. eth_call で、書き込む関数・所有者だけの関数を署名なしで呼び、状態もブロック数も変わらないことを見る。
   最後に所有者でない人が setAnswer を送り、revert しても nonce が進み手数料を払うことを見る。

結果は output/results.json に書く。
"""
import json
import os
import random
import subprocess
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
GENESIS_TS = 1767225600  # 2026-01-01T00:00:00Z。3 台のノードで同じ初期状態にする
PORTS = {"A": 18745, "B": 18746, "C": 18747}
ROUNDS = 100


def rpc(node, method, *params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORTS[node]}", body, {"Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req))
    if "error" in res:
        raise RuntimeError(res["error"])
    return res["result"]


def calldata(sig, *args):
    return subprocess.check_output(["cast", "calldata", sig, *map(str, args)], text=True).strip()


def compile_all():
    out = subprocess.check_output(
        ["solc", "--combined-json", "abi,bin", "--optimize", os.path.join(HERE, "Contracts.sol")], text=True)
    return {k.split(":")[-1]: v for k, v in json.loads(out)["contracts"].items()}


def send(node, frm, to, data, gas=300_000):
    tx = {"from": frm, "data": data, "gas": hex(gas),
          "maxFeePerGas": hex(3 * 10**9), "maxPriorityFeePerGas": hex(10**9)}
    if to:
        tx["to"] = to
    # A のブロックの時刻を 12 秒ずつ進め、実行のたびに同じ結果にする（Ethereum のスロットも 12 秒）
    rpc(node, "evm_setNextBlockTimestamp", GENESIS_TS + 12 * (int(rpc(node, "eth_blockNumber"), 16) + 1))
    return receipt(node, rpc(node, "eth_sendTransaction", tx))


def receipt(node, h):
    for _ in range(500):
        r = rpc(node, "eth_getTransactionReceipt", h)
        if r:
            return r
        time.sleep(0.01)
    raise TimeoutError(h)


def call(node, frm, to, data):
    try:
        return {"ok": True, "result": rpc(node, "eth_call", {"from": frm, "to": to, "data": data}, "latest")}
    except RuntimeError as e:
        return {"ok": False, "error": e.args[0].get("message")}


def uint(node, to, sig, *args):
    return int(rpc(node, "eth_call", {"to": to, "data": calldata(sig, *args)}, "latest"), 16)


def start_nodes():
    procs = []
    for name, port in PORTS.items():
        procs.append(subprocess.Popen(
            ["anvil", "--port", str(port), "--timestamp", str(GENESIS_TS), "--silent"]))
    for name in PORTS:
        for _ in range(100):
            try:
                rpc(name, "eth_chainId")
                break
            except Exception:
                time.sleep(0.1)
    return procs


def exp_lottery(c, acct):
    deployer, attacker, player = acct[0], acct[1], acct[2]
    lot = send("A", deployer, None, "0x" + c["Lottery"]["bin"], 1_000_000)["contractAddress"]
    pred = send("A", attacker, None, "0x" + c["Predictor"]["bin"], 1_000_000)["contractAddress"]
    rng = random.Random(1)
    rows = []
    for i in range(ROUNDS):
        guess = rng.randrange(10)
        r1 = send("A", player, lot, calldata("play(uint256)", guess))
        r2 = send("A", attacker, pred, calldata("attack(address)", lot))
        for who, r, g in (("guess", r1, guess), ("predictor", r2, None)):
            rows.append({"round": i, "who": who, "guess": g, "status": int(r["status"], 16),
                         "gasUsed": int(r["gasUsed"], 16), "fee_wei": int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16),
                         "block": int(r["blockNumber"], 16), "hash": r["transactionHash"]})
    summary = {}
    for who in ("guess", "predictor"):
        rs = [r for r in rows if r["who"] == who]
        summary[who] = {"plays": len(rs), "wins": sum(r["status"] for r in rs),
                        "fee_eth": sum(r["fee_wei"] for r in rs) / 1e18,
                        "gas_win": sorted({r["gasUsed"] for r in rs if r["status"] == 1}),
                        "gas_miss": sorted({r["gasUsed"] for r in rs if r["status"] == 0})}
    summary["winsOf_player"] = uint("A", lot, "winsOf(address)(uint256)", player)
    summary["winsOf_predictor"] = uint("A", lot, "winsOf(address)(uint256)", pred)
    return {"lottery": lot, "predictor": pred, "player": player, "rows": rows, "summary": summary}


def exp_replay():
    """A の 1 番目以降のブロックを、生のトランザクションのまま B と C に送り直す。"""
    head = int(rpc("A", "eth_blockNumber"), 16)
    status = {"A": {}, "B": {}, "C": {}}
    same_hash = True
    for n in range(1, head + 1):
        blk = rpc("A", "eth_getBlockByNumber", hex(n), False)
        ts = int(blk["timestamp"], 16)
        for h in blk["transactions"]:
            status["A"][h] = int(receipt("A", h)["status"], 16)
            raw = rpc("A", "eth_getRawTransactionByHash", h)
            for node, shift in (("B", 0), ("C", 1)):
                rpc(node, "evm_setNextBlockTimestamp", ts + shift)
                h2 = rpc(node, "eth_sendRawTransaction", raw)
                same_hash &= h2 == h
                status[node][h] = int(receipt(node, h2)["status"], 16)
    return status, same_hash


def exp_quiz(c, acct):
    owner, stranger = acct[0], acct[3]
    word = "tsukimi"
    ctor = calldata("f(string)", word)[10:]
    r = send("A", owner, None, "0x" + c["Quiz"]["bin"] + ctor, 1_000_000)
    quiz = r["contractAddress"]
    tx = rpc("A", "eth_getTransactionByHash", r["transactionHash"])
    slot1 = rpc("A", "eth_getStorageAt", quiz, "0x1", "latest")
    b = bytes.fromhex(slot1[2:])
    length = b[-1] // 2  # 31 バイト以下の文字列は、末尾の 1 バイトに長さ × 2 が入る
    decoded = b[:length].decode()
    tail = tx["input"][-128:]
    # eth_call: 書き込む関数を、鍵の持ち主が知られていない焼却用のアドレスを名乗って呼ぶ
    nobody = "0x000000000000000000000000000000000000dEaD"
    block_before = int(rpc("A", "eth_blockNumber"), 16)
    c_solve = call("A", nobody, quiz, calldata("solve(string)", word))
    c_set_owner = call("A", owner, quiz, calldata("setAnswer(string)", "kaze"))
    c_set_stranger = call("A", stranger, quiz, calldata("setAnswer(string)", "kaze"))
    after = {"solved": uint("A", quiz, "solved()(uint256)"),
             "slot1": rpc("A", "eth_getStorageAt", quiz, "0x1", "latest"),
             "blocks_added": int(rpc("A", "eth_blockNumber"), 16) - block_before}
    assert after["blocks_added"] == 0 and after["solved"] == 0
    # 同じ setAnswer を、所有者でない人がトランザクションで送る
    nonce0 = int(rpc("A", "eth_getTransactionCount", stranger, "latest"), 16)
    bal0 = int(rpc("A", "eth_getBalance", stranger, "latest"), 16)
    r_bad = send("A", stranger, quiz, calldata("setAnswer(string)", "kaze"))
    nonce1 = int(rpc("A", "eth_getTransactionCount", stranger, "latest"), 16)
    bal1 = int(rpc("A", "eth_getBalance", stranger, "latest"), 16)
    fee = int(r_bad["gasUsed"], 16) * int(r_bad["effectiveGasPrice"], 16)
    # revert しても nonce は 1 進み、残高は手数料の分だけ減る
    assert int(r_bad["status"], 16) == 0 and nonce1 == nonce0 + 1 and bal0 - bal1 == fee
    assert len(r_bad["logs"]) == 0
    nobody_bal = rpc("A", "eth_getBalance", nobody, "latest")
    return {"quiz": quiz, "word": word, "slot1": slot1, "decoded": decoded, "deploy_input_tail": tail,
            "call_solve_as_dead": c_solve, "call_setAnswer_as_owner": c_set_owner,
            "call_setAnswer_as_stranger": c_set_stranger, "after_calls": after,
            "dead_balance": nobody_bal,
            "tx_setAnswer_as_stranger": {"status": int(r_bad["status"], 16), "gasUsed": int(r_bad["gasUsed"], 16),
                                         "logs": len(r_bad["logs"]), "nonce": [nonce0, nonce1],
                                         "fee_wei": fee, "balance_diff_wei": bal0 - bal1}}


def main():
    os.makedirs(OUT, exist_ok=True)
    c = compile_all()
    procs = start_nodes()
    try:
        acct = rpc("A", "eth_accounts")
        lot = exp_lottery(c, acct)
        status, same_hash = exp_replay()
        grid = {}
        for who in ("guess", "predictor"):
            rows = [r for r in lot["rows"] if r["who"] == who]
            grid[who] = {node: [status[node][r["hash"]] for r in rows] for node in ("A", "B", "C")}
        replay = {"txs": len(status["A"]), "same_hash": same_hash, "grid": grid,
                  "wins": {who: {n: sum(v) for n, v in g.items()} for who, g in grid.items()},
                  "diff_vs_A": {n: sum(1 for h in status["A"] if status["A"][h] != status[n][h]) for n in ("B", "C")}}
        quiz = exp_quiz(c, acct)
        versions = subprocess.check_output(["anvil", "--version"], text=True).splitlines()[0]
        solc = subprocess.check_output(["solc", "--version"], text=True).splitlines()[-1]
        res = {"versions": {"anvil": versions, "solc": solc}, "lottery": lot, "replay": replay, "quiz": quiz}
        json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
        print(json.dumps(lot["summary"], indent=1))
        print(json.dumps({k: v for k, v in replay.items() if k != "grid"}, indent=1))
        print(json.dumps(quiz, indent=1))
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
