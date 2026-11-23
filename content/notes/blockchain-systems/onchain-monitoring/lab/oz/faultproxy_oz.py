"""JSON-RPC proxy in front of Anvil that injects faults (127.0.0.1 only).

Faults are controlled through a small HTTP control endpoint:
  POST /control {"fail_blocks": [5, 6], "mode": "error"|"timeout"|"empty", "down": false,
                 "fail_methods": ["eth_getLogs"] | null}
  (oz copy of ../faultproxy.py: fail_methods limits fail_blocks to the listed methods; null = all)
- fail_blocks: requests that name one of these block numbers fail
  (eth_getBlockByNumber, eth_getLogs with fromBlock/toBlock covering it,
   eth_getBlockReceipts, trace_block, debug_traceBlockByNumber).
- down: every request fails (simulates the RPC provider being unreachable).
Every request is logged to a JSONL file with time, method, params and the injected fault.

Usage: python3 faultproxy.py LISTEN_PORT UPSTREAM_URL LOG_PATH CONTROL_PORT
"""
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN, UPSTREAM, LOG, CONTROL = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
state = {"fail_blocks": set(), "mode": "error", "down": False, "fail_methods": None}
lock = threading.Lock()
logf = open(LOG, "a", buffering=1)


def as_int(v):
    if isinstance(v, str) and v.startswith("0x"):
        return int(v, 16)
    return None


def touched_blocks(req):
    m, p = req.get("method"), req.get("params") or []
    if m in ("eth_getBlockByNumber", "eth_getBlockReceipts", "trace_block",
             "debug_traceBlockByNumber") and p:
        n = as_int(p[0])
        return {n} if n is not None else set()
    if m == "eth_getLogs" and p and isinstance(p[0], dict):
        f, t = as_int(p[0].get("fromBlock")), as_int(p[0].get("toBlock"))
        if f is not None and t is not None:
            return set(range(f, t + 1))
    return set()


def fault_for(req):
    with lock:
        if state["down"]:
            return state["mode"]
        if state["fail_methods"] is not None and req.get("method") not in state["fail_methods"]:
            return None
        if touched_blocks(req) & state["fail_blocks"]:
            return state["mode"]
    return None


def forward(body):
    r = urllib.request.Request(UPSTREAM, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return resp.read()


class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            reqs = json.loads(body)
        except Exception:
            reqs = None
        batch = isinstance(reqs, list)
        items = reqs if batch else [reqs]
        faults = [fault_for(r) if isinstance(r, dict) else None for r in items]
        for r, f in zip(items, faults):
            if isinstance(r, dict):
                logf.write(json.dumps({"t": time.time(), "method": r.get("method"),
                                       "params": r.get("params"), "fault": f}) + "\n")
        if any(f == "timeout" for f in faults):
            time.sleep(60)
            self.send_response(504)
            self.end_headers()
            return
        if all(f is None for f in faults):
            out = forward(body)
        else:
            up = json.loads(forward(body))
            up_items = up if batch else [up]
            res = []
            for r, f, u in zip(items, faults, up_items):
                if f == "error":
                    res.append({"jsonrpc": "2.0", "id": r.get("id"),
                                "error": {"code": -32603, "message": "injected fault"}})
                elif f == "empty":
                    res.append({"jsonrpc": "2.0", "id": r.get("id"),
                                "result": [] if r.get("method") == "eth_getLogs" else None})
                else:
                    res.append(u)
            out = json.dumps(res if batch else res[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


class Control(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        cmd = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        with lock:
            if "fail_blocks" in cmd:
                state["fail_blocks"] = set(cmd["fail_blocks"])
            if "mode" in cmd:
                state["mode"] = cmd["mode"]
            if "down" in cmd:
                state["down"] = bool(cmd["down"])
            if "fail_methods" in cmd:
                state["fail_methods"] = cmd["fail_methods"]
            snap = {"fail_blocks": sorted(state["fail_blocks"]), "mode": state["mode"], "down": state["down"],
                    "fail_methods": state["fail_methods"]}
        logf.write(json.dumps({"t": time.time(), "control": snap}) + "\n")
        out = json.dumps(snap).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(out)


threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", CONTROL), Control).serve_forever, daemon=True).start()
ThreadingHTTPServer(("127.0.0.1", LISTEN), Proxy).serve_forever()
