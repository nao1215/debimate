#!/usr/bin/env python3
"""regtest の Bitcoin Core と LND 3 台（alice・bob・carol）で、チャネルの残高と
送れる額・受け取れる額・閉じた後に使えるまでの時間・古い状態を出した時の結末を測る。

実資産・公開ネットワークは使わない。docker-compose.yml と同じディレクトリで

    python3 run.py

を実行すると、コンテナを作り直して全ての手順を流し、result.json と output.txt を書く。
終わるとコンテナを消す（--keep で残す）。
"""
import json
import pathlib
import secrets
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
LOG = []
RESULT = {}


def log(msg):
    print(msg, flush=True)
    LOG.append(msg)


def run(*args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{args}: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout


def btc(*args):
    return run("docker", "exec", "lnlab-bitcoind", "bitcoin-cli", "-regtest",
               "-rpcuser=lab", "-rpcpassword=lab", *args).strip()


def ln(node, *args, check=True):
    out = run("docker", "exec", f"lnlab-{node}", "lncli", "--network=regtest",
              *args, check=check)
    # payinvoice --json は最後に "[lncli] FAILED" などを付けるので JSON だけを取る
    text = out[: out.rfind("}") + 1] if "}" in out else out
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 支払いの途中経過が複数の JSON で出る時は最後のものを使う
        last = text[text.rfind("\n{") + 1:]
        return json.loads(last)


def height():
    return int(btc("getblockcount"))


def mine(n=1):
    btc("generatetoaddress", str(n), MINER)
    time.sleep(1.5)


def wait(cond, what, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if cond():
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"timeout: {what}")


def synced(node):
    info = ln(node, "getinfo")
    return info["synced_to_chain"] and info["block_height"] == height()


def wait_synced(*nodes):
    for n in nodes:
        wait(lambda: synced(n), f"{n} synced")


def pubkey(node):
    return ln(node, "getinfo")["identity_pubkey"]


def chan(node, peer):
    for c in ln(node, "listchannels")["channels"]:
        if c["remote_pubkey"] == PUB[peer]:
            return c
    return None


def onchain(node):
    return int(ln(node, "walletbalance")["confirmed_balance"])


def pay(payer, payee, amt):
    """payee の請求書（invoice）を payer が払う。"""
    req = ln(payee, "addinvoice", "--amt", str(amt))["payment_request"]
    t0 = time.time()
    r = ln(payer, "payinvoice", "--force", "--json", "--timeout", "30s", req,
           check=False)
    return {
        "amt": amt,
        "status": r["status"],
        "failure_reason": r.get("failure_reason"),
        "fee_sat": int(r.get("fee_sat", 0)),
        "attempts": len(r.get("htlcs", [])),
        "elapsed_ms": round((time.time() - t0) * 1000),
    }


def probe(payer, dest, amt):
    """払えない支払い（でたらめな payment_hash）を送り、相手に届くかだけを見る。

    受取人まで HTLC が届けば INCORRECT_PAYMENT_DETAILS で戻り、
    途中の残高が足りなければ別の理由で失敗する。どちらでも残高は動かない。
    """
    r = ln(payer, "sendpayment", "--dest", PUB[dest], "--amt", str(amt),
           "--payment_hash", secrets.token_hex(32), "--final_cltv_delta", "40",
           "--json", "--timeout", "30s", check=False)
    return r.get("failure_reason") == "FAILURE_REASON_INCORRECT_PAYMENT_DETAILS"


def max_reachable(payer, dest, lo, hi):
    """probe で届く最大の額（sat）を二分探索する。lo は届く、hi は届かない額。"""
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if probe(payer, dest, mid):
            lo = mid
        else:
            hi = mid
    return lo


def snapshot(node, peer):
    c = chan(node, peer)
    return {k: (int(c[k]) if str(c[k]).isdigit() else c[k]) for k in (
        "capacity", "local_balance", "remote_balance", "commit_fee",
        "local_chan_reserve_sat", "remote_chan_reserve_sat", "csv_delay",
        "commitment_type", "initiator")}


def stop(node):
    run("docker", "stop", f"lnlab-{node}")


def start(node):
    run("docker", "start", f"lnlab-{node}")
    wait(lambda: ln(node, "getinfo") is not None, f"{node} rpc")
    wait_synced(node)


def main():
    global MINER, PUB
    run("docker", "compose", "down", "-v", check=False)
    run("docker", "compose", "up", "-d")
    wait(lambda: btc("getblockchaininfo"), "bitcoind")
    btc("createwallet", "miner")
    MINER = btc("getnewaddress")
    for n in ("alice", "bob", "carol"):
        wait(lambda: ln(n, "getinfo"), f"{n} rpc")
    btc("generatetoaddress", "101", MINER)
    for n in ("alice", "bob", "carol"):
        addr = ln(n, "newaddress", "p2tr")["address"]
        btc("sendtoaddress", addr, "1")
    mine(6)
    wait_synced("alice", "bob", "carol")
    PUB = {n: pubkey(n) for n in ("alice", "bob", "carol")}

    # 1. alice が bob へ 1,000,000 sat のチャネルを開く
    log("== 1. alice opens 1,000,000 sat to bob")
    ln("alice", "connect", f"{PUB['bob']}@bob:9735")
    ln("alice", "openchannel", "--node_key", PUB["bob"], "--local_amt", "1000000")
    mine(6)
    wait(lambda: chan("alice", "bob") and chan("alice", "bob")["active"], "a-b active")
    a = snapshot("alice", "bob")
    log(json.dumps(a))
    RESULT["open"] = a

    # 受け取れるか: bob から alice へ 1 sat
    r = pay("bob", "alice", 1)
    log(f"bob -> alice 1 sat: {r['status']} {r['failure_reason']}")
    RESULT["receive_1sat"] = r

    # 送れる上限: 残高を動かさない probe で二分探索
    mx = max_reachable("alice", "bob", 1, a["local_balance"] + 1)
    log(f"alice max sendable to bob: {mx}")
    RESULT["alice_max_send"] = mx

    # 2. alice が bob へ 10,000 sat 払った後、bob は 5,000 sat を返せるか
    log("== 2. alice pays bob 10,000, then bob pays alice 5,000")
    RESULT["pay_10000"] = pay("alice", "bob", 10000)
    log(json.dumps(RESULT["pay_10000"]))
    b = snapshot("bob", "alice")
    log(json.dumps(b))
    RESULT["bob_after_10000"] = b
    r = pay("bob", "alice", 5000)
    log(f"bob -> alice 5,000: {r['status']} {r['failure_reason']}")
    RESULT["bob_back_5000"] = r
    RESULT["bob_max_send"] = max_reachable("bob", "alice", 0, b["local_balance"] + 1)
    log(f"bob max sendable to alice: {RESULT['bob_max_send']}")

    # 3. bob が carol へ 500,000 sat のチャネルを開き、alice が bob 経由で carol へ払う
    log("== 3. bob opens 500,000 sat to carol; alice pays carol via bob")
    ln("bob", "connect", f"{PUB['carol']}@carol:9735")
    ln("bob", "openchannel", "--node_key", PUB["carol"], "--local_amt", "500000")
    mine(6)
    wait(lambda: chan("bob", "carol") and chan("bob", "carol")["active"], "b-c active")

    def alice_sees_bc():
        edges = ln("alice", "describegraph")["edges"]
        return any({e["node1_pub"], e["node2_pub"]} == {PUB["bob"], PUB["carol"]}
                   and e.get("node1_policy") and e.get("node2_policy") for e in edges)
    wait(alice_sees_bc, "alice learns b-c", timeout=180)
    edges = ln("alice", "describegraph")["edges"]
    bc_pub = [e for e in edges
              if {e["node1_pub"], e["node2_pub"]} == {PUB["bob"], PUB["carol"]}][0]
    RESULT["bc_advertised_capacity"] = int(bc_pub["capacity"])
    pol = bc_pub["node1_policy"] if bc_pub["node1_pub"] == PUB["bob"] else bc_pub["node2_policy"]
    RESULT["bob_fee_policy"] = {"base_msat": int(pol["fee_base_msat"]),
                                "rate_ppm": int(pol["fee_rate_milli_msat"]),
                                "time_lock_delta": int(pol["time_lock_delta"])}
    RESULT["bc_open"] = snapshot("bob", "carol")
    RESULT["ac_max_before"] = max_reachable("alice", "carol", 1, 500001)
    log(f"alice -> carol reachable max (before): {RESULT['ac_max_before']}")

    pays = []
    for i in range(4):
        r = pay("alice", "carol", 150000)
        r["ab_bob_local"] = int(chan("bob", "alice")["local_balance"])
        r["bc_bob_local"] = int(chan("bob", "carol")["local_balance"])
        r["bc_carol_local"] = int(chan("carol", "bob")["local_balance"])
        pays.append(r)
        log(json.dumps(r))
    RESULT["ac_pays"] = pays
    RESULT["ac_max_after"] = max_reachable("alice", "carol", 0, 500001)
    log(f"alice -> carol reachable max (after): {RESULT['ac_max_after']}")
    RESULT["ab_after_route"] = snapshot("alice", "bob")
    RESULT["bc_after_route"] = snapshot("bob", "carol")

    # 4. 古い状態の提出: bob の channel.db を写し、bob が alice へ払った後に戻す
    log("== 4. bob keeps an old channel.db, pays alice, restores it and force-closes")
    db = "/root/.lnd/data/graph/regtest/channel.db"
    stop("bob")
    run("docker", "cp", f"lnlab-bob:{db}", str(HERE / "bob-old-channel.db"))
    start("bob")
    wait(lambda: chan("bob", "alice")["active"], "a-b active again")
    old_bob_local = int(chan("bob", "alice")["local_balance"])
    r = pay("bob", "alice", 200000)
    log(f"bob -> alice 200,000: {json.dumps(r)}")
    honest = snapshot("bob", "alice")
    RESULT["breach"] = {"old_bob_local": old_bob_local, "pay_back": r,
                        "honest_bob_local": honest["local_balance"],
                        "honest_alice_local": honest["remote_balance"],
                        "bob_csv_delay": honest["csv_delay"]}
    alice_onchain0 = onchain("alice")
    bob_onchain0 = onchain("bob")
    stop("alice")
    stop("bob")
    run("docker", "cp", str(HERE / "bob-old-channel.db"), f"lnlab-bob:{db}")
    (HERE / "bob-old-channel.db").unlink()
    start("bob")
    ab = [c for c in ln("bob", "listchannels")["channels"]
          if c["remote_pubkey"] == PUB["alice"]][0]
    RESULT["breach"]["restored_bob_local"] = int(ab["local_balance"])
    txid, idx = ab["channel_point"].split(":")
    ln("bob", "closechannel", "--force", "--funding_txid", txid, "--output_index", idx,
       "--block=false")
    time.sleep(2)
    h0 = height()
    mine(1)
    RESULT["breach"]["broadcast_height"] = h0 + 1
    log(f"old state confirmed at height {h0 + 1}; alice is offline")
    offline_blocks = 10
    mine(offline_blocks - 1)
    RESULT["breach"]["alice_back_height"] = height()
    start("alice")
    timeline = []
    for _ in range(12):
        timeline.append({"height": height(), "alice_onchain": onchain("alice"),
                         "bob_onchain": onchain("bob")})
        mine(1)
        wait_synced("alice", "bob")
    closed = ln("alice", "closedchannels")["channels"]
    ab_closed = [c for c in closed if c["remote_pubkey"] == PUB["bob"]][0]
    RESULT["breach"].update({
        "close_type": ab_closed["close_type"],
        "settled_balance_alice": int(ab_closed["settled_balance"]),
        "time_locked_balance_alice": int(ab_closed["time_locked_balance"]),
        "alice_onchain_before": alice_onchain0, "bob_onchain_before": bob_onchain0,
        "alice_onchain_after": onchain("alice"), "bob_onchain_after": onchain("bob"),
        "timeline": timeline,
    })
    log(json.dumps(RESULT["breach"]))

    # 5. 閉じ方の違い: bob が b-c を強制的に閉じ、carol が開いた c-a を協調して閉じる
    log("== 5. force close (bob, b-c) vs cooperative close (carol, c-a)")
    ln("carol", "connect", f"{PUB['alice']}@alice:9735")
    ln("carol", "openchannel", "--node_key", PUB["alice"], "--local_amt", "200000")
    mine(6)
    wait(lambda: chan("carol", "alice") and chan("carol", "alice")["active"], "c-a active")
    wait(lambda: chan("bob", "carol") and chan("bob", "carol")["active"], "b-c active")
    bc = chan("bob", "carol")
    bc_snap = snapshot("bob", "carol")
    ca = chan("carol", "alice")
    start_onchain = {n: onchain(n) for n in ("alice", "bob", "carol")}
    t, i = bc["channel_point"].split(":")
    ln("bob", "closechannel", "--force", "--funding_txid", t, "--output_index", i,
       "--block=false")
    t, i = ca["channel_point"].split(":")
    ln("carol", "closechannel", "--funding_txid", t, "--output_index", i,
       "--block=false")
    time.sleep(2)
    h_start = height()
    series = []
    pend = ln("bob", "pendingchannels")
    for step in range(170):
        mine(1)
        if step % 1 == 0:
            wait_synced("alice", "bob", "carol")
        row = {"height": height(), **{n: onchain(n) for n in ("alice", "bob", "carol")}}
        p = ln("bob", "pendingchannels")
        fc = p.get("pending_force_closing_channels", [])
        row["bob_blocks_til_maturity"] = int(fc[0]["blocks_til_maturity"]) if fc else None
        row["bob_limbo"] = int(fc[0]["limbo_balance"]) if fc else 0
        series.append(row)
        if step > 150 and not fc:
            break
    RESULT["close"] = {"start_height": h_start, "start_onchain": start_onchain,
                       "bc": bc_snap, "ca_capacity": int(ca["capacity"]),
                       "ca_carol_local": int(ca["local_balance"]),
                       "ca_alice_local": int(ca["remote_balance"]),
                       "bob_pending_at_start": pend, "series": series}
    log(json.dumps({k: v for k, v in RESULT["close"].items() if k != "series"},
                   ensure_ascii=False)[:2000])
    for row in series:
        if row["height"] - h_start in (1, 2, 3, 143, 144, 145, 146, 147) or row is series[-1]:
            log(json.dumps(row))

    RESULT["versions"] = {
        "lnd": ln("alice", "getinfo")["version"],
        "bitcoind": json.loads(btc("getnetworkinfo"))["subversion"],
    }
    (HERE / "result.json").write_text(json.dumps(RESULT, indent=2, ensure_ascii=False) + "\n")
    (HERE / "output.txt").write_text("\n".join(LOG) + "\n")
    if "--keep" not in sys.argv:
        run("docker", "compose", "down", "-v", check=False)


if __name__ == "__main__":
    main()
