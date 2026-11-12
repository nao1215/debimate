#!/usr/bin/env python3
"""Oracle の実験 2 つをローカルの Anvil で走らせ、結果を output/results.json に残す。

1. 同じトランザクションの中の価格操作: フラッシュローンで借りた 300,000 tUSD で Pool の価格をつり上げ、
   その間に Lending から借りる。Lending が読む価格を Pool の今の価格（spot）・30 分の TWAP・
   外から書き込む価格（feed）の 3 通りに変えて、同じ攻撃を当てる。
2. 急落の追いかけ方: 市場の価格が 10 分で 3,000 から 2,100 に下がる 90 分を 12 秒ごとのブロックで流し、
   各ブロックで spot・TWAP・feed が返す値と、feed の最後の更新からの経過秒を記録する。
   Pool は裁定取引の役（アカウント 1）が毎ブロック市場の価格に合わせる。
   feed は更新役（アカウント 0）が、0.5% 以上ずれたか 3,600 秒たった時だけ書き込む（Chainlink の
   ETH / USD と同じ条件）。この feed は市場を見たのと同じブロックに入る（遅れ 0）。比べ役として、
   書き込みが 1 ブロック（12 秒）・5 ブロック（60 秒）遅れて入る feed も同じ条件で動かす。市場の価格の動きは本記事で決めた筋書きで、実在の相場ではない。

前提: anvil・cast・solc が PATH にあること（run.sh が用意する）。公開のネットワークには繋がない。
"""
import json
import math
import os
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
RPC = "http://127.0.0.1:18745"
E18 = 10**18


def rpc(method, *params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)}).encode()
    req = urllib.request.Request(RPC, body, {"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in res:
        raise RuntimeError(f"{method}: {res['error']}")
    return res["result"]


def calldata(sig, *args):
    return subprocess.check_output(["cast", "calldata", sig, *map(str, args)], text=True).strip()


def send(frm, to, data, gas=3_000_000):
    tx = {"from": frm, "data": data, "gas": hex(gas)}
    if to:
        tx["to"] = to
    return rpc("eth_sendTransaction", tx)


def receipt(h):
    r = rpc("eth_getTransactionReceipt", h)
    if r is None:
        rpc("evm_mine")
        r = rpc("eth_getTransactionReceipt", h)
    return r


def tx(frm, to, sig, *args):
    r = receipt(send(frm, to, calldata(sig, *args)))
    assert r["status"] == "0x1", (sig, r)
    return r


def call(to, sig, *args, block="latest"):
    return rpc("eth_call", {"to": to, "data": calldata(sig, *args)}, block)


def call_uint(to, sig, *args):
    return int(call(to, sig, *args), 16)


def try_price(src):
    try:
        return call_uint(src, "price()") / E18
    except RuntimeError as e:
        return "revert: " + ("stale price" if "stale" in str(e) else str(e)[:60])


def compile_all():
    out = subprocess.check_output(
        ["solc", "--combined-json", "abi,bin", "--optimize", os.path.join(HERE, "Oracle.sol")], text=True)
    return {k.split(":")[-1]: v for k, v in json.loads(out)["contracts"].items()}


def deploy(c, frm, name, ctor_sig=None, *args):
    data = "0x" + c[name]["bin"]
    if ctor_sig:
        data += calldata(ctor_sig, *args)[10:]
    r = receipt(send(frm, None, data, gas=6_000_000))
    assert r["status"] == "0x1", name
    return r["contractAddress"]


def setup(c, acct, eth_pool=100, usd_pool=300_000):
    """tETH・tUSD・Pool（100 tETH と 300,000 tUSD、1 tETH = 3,000 tUSD）・PushFeed を作り、1 時間進める。"""
    a0 = acct[0]
    eth = deploy(c, a0, "Token", "f(string)", "tETH")
    usd = deploy(c, a0, "Token", "f(string)", "tUSD")
    pool = deploy(c, a0, "Pool", "f(address,address)", eth, usd)
    for t, v in ((eth, eth_pool), (usd, usd_pool)):
        tx(a0, t, "mint(address,uint256)", a0, v * E18)
        tx(a0, t, "approve(address,uint256)", pool, 2**256 - 1)
    tx(a0, pool, "addLiquidity(uint256,uint256)", eth_pool * E18, usd_pool * E18)
    feed = deploy(c, a0, "PushFeed")
    tx(a0, feed, "update(int256)", 3000 * 10**8)
    rpc("evm_increaseTime", 3600)
    rpc("evm_mine")
    tx(a0, pool, "sync()")
    tx(a0, feed, "update(int256)", 3000 * 10**8)
    spot = deploy(c, a0, "SpotSource", "f(address)", pool)
    twap = deploy(c, a0, "TwapSource", "f(address,uint256)", pool, 1800)
    fsrc = deploy(c, a0, "FeedSource", "f(address,uint256)", feed, 3600)
    return {"eth": eth, "usd": usd, "pool": pool, "feed": feed, "spot": spot, "twap": twap, "feedsrc": fsrc}


STEP_TOPIC = None


def exp_attack(c, acct):
    global STEP_TOPIC
    STEP_TOPIC = subprocess.check_output(
        ["cast", "keccak", "Step(uint8,uint256,uint256,uint256,uint256,uint256)"], text=True).strip()
    env = setup(c, acct)
    a0, attacker_eoa = acct[0], acct[9]
    snap = rpc("evm_snapshot")
    results = {}
    for name in ("spot", "twap", "feedsrc"):
        rpc("evm_revert", snap)
        snap = rpc("evm_snapshot")
        lending = deploy(c, a0, "Lending", "f(address,address,address)", env["eth"], env["usd"], env[name])
        tx(a0, env["usd"], "mint(address,uint256)", lending, 1_000_000 * E18)
        flash = deploy(c, a0, "FlashLender", "f(address)", env["usd"])
        tx(a0, env["usd"], "mint(address,uint256)", flash, 10_000_000 * E18)
        atk = deploy(c, attacker_eoa, "Attacker", "f(address,address,address,address[3],uint256)",
                     env["pool"], lending, flash, f"[{env['spot']},{env['twap']},{env['feedsrc']}]", 10 * E18)
        before = call_uint(env["usd"], "balanceOf(address)", attacker_eoa)
        r = receipt(send(attacker_eoa, atk, calldata("attack(uint256)", 300_000 * E18), gas=5_000_000))
        logs = r["logs"]
        steps = []
        for log in logs:
            if log["topics"][0] == STEP_TOPIC:
                d = log["data"][2:]
                v = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
                steps.append({"step": v[0], "spot": v[1] / E18, "twap": v[2] / E18, "feed": v[3] / E18,
                              "usd_held": v[4] / E18, "eth_held": v[5] / E18})
        res = {"status": int(r["status"], 16), "gasUsed": int(r["gasUsed"], 16), "steps": steps,
               "attacker_profit_usd": (call_uint(env["usd"], "balanceOf(address)", attacker_eoa) - before) / E18,
               "lending_debt_usd": call_uint(lending, "debt(address)", atk) / E18,
               "lending_collateral_eth": call_uint(lending, "collateral(address)", atk) / E18,
               "pool_spot_after": call_uint(env["pool"], "spot()") / E18}
        if res["status"] == 0:
            # 失敗した時は、どこで止まったかを eth_call で取り出す
            # 同じトランザクションを eth_call で実行し直し、CannotRepay(held, owed, borrowed) を読む
            try:
                rpc("eth_call", {"from": attacker_eoa, "to": atk, "data": calldata("attack(uint256)", 300_000 * E18)}, "latest")
            except RuntimeError as e:
                data = e.args[0].split("'data': '")[1].split("'")[0][10:]
                held, owed, borrowed = (int(data[i:i + 64], 16) / E18 for i in (0, 64, 128))
                res["revert"] = {"error": "CannotRepay", "held": held, "owed": owed, "borrowed": borrowed,
                                 "shortfall": owed - held}
        if name == "spot":
            res["collateral_value_at_pool_after"] = res["lending_collateral_eth"] * res["pool_spot_after"]
        results[name] = res
    return results


def market_price(t):
    """筋書きの市場の価格（秒 → tUSD）。0〜20 分は 3,000、20〜30 分で 2,100 へ直線で下がり、その後は 2,100。
    上下に ±0.2% の小さな揺れを足す（feed が 0.5% の条件で更新しない程度）。"""
    m = t / 60
    if m < 20:
        base = 3000
    elif m < 30:
        base = 3000 - 900 * (m - 20) / 10
    else:
        base = 2100
    return base * (1 + 0.002 * math.sin(t / 97.0))


def arb_swap(pool_r_eth, pool_r_usd, target):
    """Pool の価格を target に近付ける交換（入れる側と量）。手数料 0.3% を見込んだ近似。"""
    k = pool_r_eth * pool_r_usd
    new_eth = math.isqrt(int(k * E18 // int(target * E18)))
    if new_eth > pool_r_eth:   # tETH を入れる（売る）と価格が下がる
        return "eth", int((new_eth - pool_r_eth) * 1000 // 997)
    new_usd = k // new_eth
    return "usd", int((new_usd - pool_r_usd) * 1000 // 997)


LAGS = (1, 5)   # 書き込みが届くまでのブロック数（12 秒・60 秒）


def exp_crash(c, acct):
    env = setup(c, acct)
    a0, arb = acct[0], acct[1]
    for t in (env["eth"], env["usd"]):
        tx(a0, t, "mint(address,uint256)", arb, 10**9 * E18)
        tx(arb, t, "approve(address,uint256)", env["pool"], 2**256 - 1)
    # 書き込みが遅れて届く場合の比べ役。更新役が市場を見てから、書き込みが LAGS ブロック後に入る。
    lag_feeds = {}
    for lag in LAGS:
        f = deploy(c, a0, "PushFeed")
        tx(a0, f, "update(int256)", 3000 * 10**8)
        lag_feeds[lag] = {"addr": f, "ans": 3000.0, "at": None, "pending": None}
    rpc("evm_setAutomine", False)
    t0 = int(rpc("eth_getBlockByNumber", "latest", False)["timestamp"], 16) + 12
    feed_ans, feed_at = 3000.0, t0 - 12
    for lf in lag_feeds.values():
        lf["at"] = t0 - 12
    rows = []
    for i in range(0, 90 * 5 + 1):           # 12 秒ごとに 90 分
        ts = t0 + 12 * i
        el = ts - t0
        mp = market_price(el)
        r_eth = call_uint(env["pool"], "rEth()")
        r_usd = call_uint(env["pool"], "rUsd()")
        side, amt = arb_swap(r_eth, r_usd, mp)
        if amt > 0:
            send(arb, env["pool"], calldata("swap(address,uint256)", env[side], amt), gas=400_000)
        updated = False
        if abs(mp - feed_ans) / feed_ans >= 0.005 or ts - feed_at >= 3600:
            send(a0, env["feed"], calldata("update(int256)", int(mp * 10**8)), gas=200_000)
            feed_ans, feed_at, updated = mp, ts, True
        for lag, lf in lag_feeds.items():
            # 判定は、チェーンに載っている値と、今見た市場の価格で行う（届くまで次の判定はしない）
            if lf["pending"] and i >= lf["pending"][0]:
                send(a0, lf["addr"], calldata("update(int256)", int(lf["pending"][1] * 10**8)), gas=200_000)
                lf["pending"] = None
            if lf["pending"] is None and (abs(mp - lf["ans"]) / lf["ans"] >= 0.005 or ts - lf["at"] >= 3600):
                lf["pending"] = (i + lag, mp)
                lf["ans"], lf["at"] = mp, ts + 12 * lag
        rpc("evm_mine", ts)
        rd = call(env["feed"], "latestRoundData()")[2:]
        updated_at = int(rd[64 * 3:64 * 4], 16)
        row = {"t": el, "market": mp, "spot": call_uint(env["spot"], "price()") / E18,
               "twap": call_uint(env["twap"], "price()") / E18,
               "feed": int(rd[64:128], 16) / 10**8, "feed_age": ts - updated_at, "feed_updated": updated}
        for lag, lf in lag_feeds.items():
            row[f"feed_lag{lag * 12}"] = int(call(lf["addr"], "latestRoundData()")[2:][64:128], 16) / 10**8
        rows.append(row)
    rpc("evm_setAutomine", True)
    return rows


def summarize_crash(rows, collateral=10, debt=22_000, threshold=0.8):
    """担保 10 tETH・借入 22,000 tUSD の借り手を、どの価格で見た時に清算できるようになるか。"""
    def first(key):
        for r in rows:
            if collateral * r[key] * threshold < debt:
                return {"t": r["t"], "price_seen": r[key], "market": r["market"],
                        "collateral_value_at_market": collateral * r["market"]}
        return None
    ages = [r["feed_age"] for r in rows]
    calm = [r for r in rows if r["t"] >= 30 * 60]
    return {
        "borrower": {"collateral_eth": collateral, "debt_usd": debt, "liquidation_threshold": threshold},
        "liquidatable_from": {k: first(k) for k in ("market", "spot", "feed", "twap")
                              + tuple(f"feed_lag{lag * 12}" for lag in LAGS)},
        "feed_updates": sum(r["feed_updated"] for r in rows),
        "feed_updates_during_crash": sum(r["feed_updated"] for r in rows if 20 * 60 <= r["t"] <= 30 * 60),
        # 遅れて届くフィードは、チェーン上の値が変わったブロックの数を数える
        **{f"feed_lag{lag * 12}_updates_during_crash":
           sum(1 for p, r in zip(rows, rows[1:])
               if r[f"feed_lag{lag * 12}"] != p[f"feed_lag{lag * 12}"] and 20 * 60 <= r["t"] <= 30 * 60)
           for lag in LAGS},
        "feed_age_max": max(ages),
        "share_age_over_900_calm": sum(r["feed_age"] > 900 for r in calm) / len(calm),
        "share_age_over_900_all": sum(a > 900 for a in ages) / len(ages),
        "max_gap_feed_vs_market_pct": max(abs(r["feed"] - r["market"]) / r["market"] * 100 for r in rows),
        **{f"max_gap_feed_lag{lag * 12}_vs_market_pct":
           max(abs(r[f"feed_lag{lag * 12}"] - r["market"]) / r["market"] * 100 for r in rows) for lag in LAGS},
        "max_gap_twap_vs_market_pct": max(abs(r["twap"] - r["market"]) / r["market"] * 100 for r in rows),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    c = compile_all()
    acct = rpc("eth_accounts")
    attack = exp_attack(c, acct)
    crash = exp_crash(c, acct)
    res = {"attack": attack, "crash_summary": summarize_crash(crash), "crash": crash}
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for k, v in attack.items():
        print(f"[attack/{k}] status={v['status']} profit={v['attacker_profit_usd']:,.2f} tUSD "
              f"debt={v['lending_debt_usd']:,.2f} collateral={v['lending_collateral_eth']} tETH "
              f"revert={v.get('revert', '-')}")
        for s in v["steps"]:
            print(f"    step {s['step']}: spot={s['spot']:,.2f} twap={s['twap']:,.2f} feed={s['feed']:,.2f} "
                  f"usd={s['usd_held']:,.2f} eth={s['eth_held']:.4f}")
    print(json.dumps(res["crash_summary"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
