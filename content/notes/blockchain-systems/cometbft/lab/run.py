"""Stop, restart and partition validators of a local 4-node CometBFT network.

Requires Docker. Uses only the official cometbft image and the built-in kvstore
app. No host port is published and every network is internal (no internet).
All containers and networks are removed at the end.
"""

import csv
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

IMAGE = ("cometbft/cometbft:v0.38.26@sha256:"
         "08f635fe1eff3bdcbe9d9a57091811351c55de66fbaa80190b28fe436a08356f")
PREFIX = "note-cometbft"
NET, SIDE_A, SIDE_B = f"{PREFIX}-net", f"{PREFIX}-a", f"{PREFIX}-b"
NODES = [f"{PREFIX}-node{i}" for i in range(4)]
UID = f"{os.getuid()}:{os.getgid()}"


def sh(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True).stdout.strip()


def rpc(node, path):
    """Call the node's RPC from inside its own container (no published port)."""
    out = sh("docker", "exec", node, "curl", "-s", "-m", "2",
             f"http://127.0.0.1:26657/{path}", check=False)
    try:
        return json.loads(out)["result"]
    except (ValueError, KeyError):
        return None


STEPS = {"1": "NewHeight", "2": "NewRound", "3": "Propose", "4": "Prevote",
         "5": "PrevoteWait", "6": "Precommit", "7": "PrecommitWait", "8": "Commit"}


def votes(node):
    """Prevote / precommit bit arrays of the round the node is stuck in."""
    rs = rpc(node, "dump_consensus_state")["round_state"]
    r = int(rs["round"])
    v = next(x for x in rs["votes"] if int(x["round"]) == r)
    return f"{node} {rs['height']}/{r}/{STEPS[str(rs['step'])]} " \
           f"prevotes {v['prevotes_bit_array']}  precommits {v['precommits_bit_array']}"


def sample(node):
    """Return (latest committed height, 'height/round/step' being voted on)."""
    status, cons = rpc(node, "status"), rpc(node, "consensus_state")
    if status is None or cons is None:
        return None
    h, r, step = cons["round_state"]["height/round/step"].split("/")
    hrs = f"{h}/{r}/{STEPS[step]}"
    return int(status["sync_info"]["latest_block_height"]), hrs


def setup(work):
    for net in (NET, SIDE_A, SIDE_B):
        sh("docker", "network", "create", "--internal", net)
    sh("docker", "run", "--rm", "--user", UID, "-e", "CMTHOME=/net/.gen", "-v",
       f"{work}:/net", "--entrypoint", "cometbft", IMAGE, "testnet", "--v", "4", "--o", "/net",
       "--hostname-prefix", f"{PREFIX}-node", "--populate-persistent-peers")
    for i, node in enumerate(NODES):
        sh("docker", "run", "-d", "--name", node, "--network", NET, "--user", UID,
           "-e", "CMTHOME=/home", "-v", f"{work}/node{i}:/home", "--entrypoint", "cometbft", IMAGE,
           "node", "--home", "/home", "--proxy_app=kvstore")
        # Side networks used only for the 2|2 partition: {0,1} on A, {2,3} on B.
        sh("docker", "network", "connect", SIDE_A if i < 2 else SIDE_B, node)


def teardown():
    for node in NODES:
        sh("docker", "rm", "-f", node, check=False)
    for net in (NET, SIDE_A, SIDE_B):
        sh("docker", "network", "rm", net, check=False)


def wait_height(target, limit=120):
    end = time.time() + limit
    while time.time() < end:
        s = sample(NODES[0])
        if s and s[0] >= target:
            return
        time.sleep(1)
    raise RuntimeError("network did not start")


def run_phase(name, seconds, log, start):
    rows = []
    end = time.time() + seconds
    while time.time() < end:
        t = time.time() - start
        rows.append((t, [sample(n) for n in NODES]))
        log.append((name, *rows[-1]))
        time.sleep(1)
    return rows


def summarize(rows):
    """Blocks committed during the phase and the highest round seen."""
    first = [s[0] for s in rows[0][1] if s]
    last = [s[0] for s in rows[-1][1] if s]
    rounds = [int(s[1].split("/")[1]) for _, ss in rows for s in ss if s]
    return max(last) - max(first), max(rounds)


def first_progress(rows):
    """Seconds from the start of the phase until any node's height increases."""
    base = max(s[0] for s in rows[0][1] if s)
    for t, ss in rows:
        if any(s and s[0] > base for s in ss):
            return t - rows[0][0]
    return None


def chain(node, top):
    """(height, block hash, commit round) for heights 1..top on one node."""
    out = []
    for h in range(1, top + 1):
        c = rpc(node, f"commit?height={h}")
        out.append((h, c["signed_header"]["commit"]["block_id"]["hash"],
                    c["signed_header"]["commit"]["round"]))
    return out


def scenario():
    work = tempfile.mkdtemp(prefix="cometbft-lab-")
    os.chmod(work, 0o775)
    teardown()
    log, result = [], {}
    try:
        setup(work)
        wait_height(3)
        start = time.time()
        phases = [
            ("all 4 up", 20, None),
            ("node3 stopped", 30, lambda: sh("docker", "stop", NODES[3])),
            ("node2,3 stopped", 45, lambda: sh("docker", "stop", NODES[2])),
            ("node2,3 restarted", 45, lambda: sh("docker", "start", NODES[2], NODES[3])),
            ("partition 0,1 | 2,3", 45, lambda: [
                sh("docker", "network", "disconnect", NET, n) for n in NODES[2:]]),
            ("partition healed", 45, lambda: [
                sh("docker", "network", "connect", NET, n) for n in NODES[2:]]),
        ]
        for name, seconds, action in phases:
            if action:
                action()
            if name == "node2,3 stopped":
                time.sleep(3)
                tx = rpc(NODES[0], 'broadcast_tx_sync?tx="halted=yes"')
            rows = run_phase(name, seconds, log, start)
            result[name] = (*summarize(rows), first_progress(rows))
            if name == "node2,3 stopped":
                q = rpc(NODES[0], 'abci_query?data="halted"')
                result["tx"] = tx["hash"], tx["code"], q["response"].get("value")
                result["halt_log"] = sh("docker", "logs", "--since", "25s", NODES[0])
                result["halt_votes"] = [votes(NODES[0])]
            if name == "partition 0,1 | 2,3":
                result["split_votes"] = [votes(NODES[0]), votes(NODES[2])]
            if name == "node2,3 restarted":
                result["resume_log"] = sh("docker", "logs", "--since", f"{seconds + 2}s",
                                          NODES[0])
        q = rpc(NODES[0], 'abci_query?data="halted"')
        found = rpc(NODES[0], f'tx?hash=0x{result["tx"][0]}')
        result["tx_after"] = q["response"].get("value"), found and found["height"]
        top = min(sample(n)[0] for n in NODES)
        chains = [chain(n, top) for n in NODES]
        result["same_chain"] = all(c == chains[0] for c in chains)
        result["top"] = top
        result["late_rounds"] = [(h, r) for h, _, r in chains[0] if r > 0]
    finally:
        teardown()
        subprocess.run(["rm", "-rf", work], check=False)
    return log, result


def trim(line):
    """Drop the long hash fields so a log line fits on screen."""
    keep = [w for w in line.split() if not w.startswith(("hash=", "root=", "module="))]
    return " ".join(keep)


def show(sample_):
    return "-" if sample_ is None else f"{sample_[0]:>4} {sample_[1]:<24}"


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"image: {IMAGE}")
    results = []
    for i in range(runs):
        log, res = scenario()
        results.append(res)
        if i == 0:
            with open("timeline.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t", "phase"] + [f"{c}{k}" for k in range(4) for c in "hr"])
                for name, t, ss in log:
                    cells = [x for s in ss for x in
                             ((s[0], s[1].split("/")[1]) if s else ("", ""))]
                    w.writerow([f"{t:.1f}", name] + cells)
            print("== run 1 timeline (every 5 s): committed height, height/round/step")
            for k, (name, t, ss) in enumerate(log):
                if k % 5 == 0:
                    cells = " | ".join(f"{show(s):<29}" for s in ss)
                    print(f"{t:6.1f}s {name:<20} {cells}")
            print("== run 1 node0 log while 2 of 4 validators are stopped (last lines)")
            halt = [trim(l) for l in res["halt_log"].splitlines() if "consensus" in l]
            print("\n".join(halt[-6:]) or "(no consensus log lines in the last 25 s)")
            print("\n".join(res["halt_votes"]))
            print("== run 1 votes during the 2|2 partition")
            print("\n".join(res["split_votes"]))
            print("== run 1 node0 log after restarting node2,3 (up to the first commit)")
            lines = [trim(l) for l in res["resume_log"].splitlines()
                     if "Timed out" in l or "finalizing commit" in l]
            first = next((k for k, l in enumerate(lines) if "finalizing" in l), 0)
            print("\n".join(lines[max(0, first - 4):first + 2]))
    print("== per phase over", runs, "runs: blocks committed / max round / s to first block")
    for name in results[0]:
        if not isinstance(results[0][name], tuple) or len(results[0][name]) != 3 \
                or name.startswith("tx"):
            continue
        cells = [results[i][name] for i in range(runs)]
        print(f"{name:<20} " + "  ".join(
            f"{b:>3} / r{r:<2} / {'-' if p is None else f'{p:4.1f}'}" for b, r, p in cells))
    for i, res in enumerate(results, 1):
        print(f"run {i}: tx during halt hash={res['tx'][0][:12]} code={res['tx'][1]} "
              f"query_during_halt={res['tx'][2]} query_after={res['tx_after'][0]} "
              f"included_at_height={res['tx_after'][1]}")
        print(f"run {i}: heights 1..{res['top']} identical on 4 nodes: {res['same_chain']}; "
              f"heights decided after round 0: {res['late_rounds']}")
    rec = [r["node2,3 restarted"][2] for r in results if r["node2,3 restarted"][2]]
    heal = [r["partition healed"][2] for r in results if r["partition healed"][2]]
    for label, xs in (("restart -> first block", rec), ("heal -> first block", heal)):
        if xs:
            print(f"{label}: median {statistics.median(xs):.1f} s "
                  f"(min {min(xs):.1f}, max {max(xs):.1f}, n={len(xs)})")


if __name__ == "__main__":
    main()
