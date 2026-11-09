"""A tiny tracer: three loopback HTTP services and one in-process queue.

Every span is written as one JSON line. The gateway, orders and inventory
services pass the W3C traceparent header, and the queue carries it as a
message attribute. Inventory fails the first call, and the mail worker
crashes once before acknowledging, so the same work shows up twice.
"""

import json
import os
import queue
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CLIENT_TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
LOCK = threading.Lock()


def new_id(nbytes):
    return os.urandom(nbytes).hex()


def parse_traceparent(value):
    version, trace_id, parent_id, flags = value.split("-")
    assert version == "00" and len(trace_id) == 32 and len(parent_id) == 16
    return {"trace_id": trace_id, "span_id": parent_id, "flags": flags}


def format_traceparent(ctx):
    return f"00-{ctx['trace_id']}-{ctx['span_id']}-{ctx['flags']}"


class Tracer:
    """Records spans of one service. clock_offset simulates a wrong host clock."""

    def __init__(self, service, log_path, clock_offset=0.0):
        self.service, self.log_path, self.clock_offset = service, log_path, clock_offset

    def now_ms(self):
        return (time.time() + self.clock_offset) * 1000

    def start(self, name, parent=None, **attrs):
        return {
            "trace_id": parent["trace_id"] if parent else new_id(16),
            "span_id": new_id(8),
            "parent_id": parent["span_id"] if parent else None,
            "flags": parent["flags"] if parent else "01",
            "name": name, "service": self.service,
            "start": self.now_ms(), "attrs": attrs, "status": "OK",
        }

    def end(self, span, status="OK"):
        span["end"], span["status"] = self.now_ms(), status
        with LOCK, open(self.log_path, "a") as f:
            f.write(json.dumps(span) + "\n")


def call(tracer, parent, url, name, **attrs):
    """Client span + traceparent header. Returns the HTTP status code."""
    span = tracer.start(name, parent, **attrs)
    req = Request(url, data=b"{}", method="POST",
                  headers={"traceparent": format_traceparent(span)})
    try:
        with urlopen(req, timeout=5) as res:
            code = res.status
    except HTTPError as e:
        code = e.code
    tracer.end(span, "OK" if code < 400 else "ERROR")
    return code


def serve(handler_fn):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            parent = parse_traceparent(self.headers["traceparent"])
            code = handler_fn(parent)
            self.send_response(code)
            self.end_headers()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"


def run(log_path, inventory_skew):
    gw = Tracer("gateway", log_path)
    orders = Tracer("orders", log_path)
    inventory = Tracer("inventory", log_path, clock_offset=inventory_skew)
    worker = Tracer("mailer", log_path)
    mail_queue, done = queue.Queue(), threading.Event()
    calls = {"inventory": 0, "deliveries": 0}

    def inventory_handler(parent):
        span = inventory.start("POST /reserve", parent)
        calls["inventory"] += 1
        time.sleep(0.02)
        failed = calls["inventory"] == 1          # first call: 503
        inventory.end(span, "ERROR" if failed else "OK")
        return 503 if failed else 200

    inv_server, inv_url = serve(inventory_handler)

    def orders_handler(parent):
        span = orders.start("POST /orders", parent)
        for attempt in range(2):                   # one retry
            extra = {"http.request.resend_count": attempt} if attempt else {}
            if call(orders, span, inv_url + "/reserve", "reserve", **extra) == 200:
                break
            time.sleep(0.01)
        send = orders.start("publish order.created", span)
        mail_queue.put({"order_id": 42, "attrs": {"traceparent": format_traceparent(send)}})
        orders.end(send)
        orders.end(span)
        return 201

    ord_server, ord_url = serve(orders_handler)

    def mail_worker():
        while calls["deliveries"] < 2:
            msg = mail_queue.get()
            calls["deliveries"] += 1
            parent = parse_traceparent(msg["attrs"]["traceparent"])
            span = worker.start("process order.created", parent,
                                **{"app.delivery_attempt": calls["deliveries"]})
            time.sleep(0.01)                       # "send the mail"
            if calls["deliveries"] == 1:           # crash before ack -> redelivered
                worker.end(span, "ERROR")
                mail_queue.put(msg)
                continue
            worker.end(span)
        done.set()

    threading.Thread(target=mail_worker, daemon=True).start()

    def gateway_handler(parent):
        span = gw.start("POST /checkout", parent)
        code = call(gw, span, ord_url + "/orders", "create order")
        gw.end(span)
        return code

    gw_server, gw_url = serve(gateway_handler)
    req = Request(gw_url + "/checkout", data=b"{}", method="POST",
                  headers={"traceparent": CLIENT_TRACEPARENT})
    with urlopen(req, timeout=5) as res:
        assert res.status == 201
    assert done.wait(5)
    for s in (gw_server, ord_server, inv_server):
        s.shutdown()
        s.server_close()


def print_tree(log_path):
    spans = [json.loads(line) for line in open(log_path)]
    by_parent = {}
    for s in spans:
        by_parent.setdefault(s["parent_id"], []).append(s)
    ids = {s["span_id"] for s in spans}
    roots = [s for s in spans if s["parent_id"] not in ids]
    t0 = min(s["start"] for s in roots)

    def show(span, depth, parent):
        attrs = " ".join(f"{k}={v}" for k, v in span["attrs"].items())
        line = (f"{'  ' * depth}{span['name']} [{span['service']}] "
                f"start={span['start'] - t0:+.0f}ms dur={span['end'] - span['start']:.0f}ms "
                f"{span['status']} {attrs}").rstrip()
        if parent and span["start"] < parent["start"]:
            line += f"  <-- starts {parent['start'] - span['start']:.0f}ms before parent"
        print(line)
        for child in sorted(by_parent.get(span["span_id"], []), key=lambda s: s["start"]):
            show(child, depth + 1, span)

    print(f"trace_id={spans[0]['trace_id']} spans={len(spans)}")
    for root in roots:
        show(root, 0, None)


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    skew = float(args[0]) if args else 0.0
    with tempfile.TemporaryDirectory() as d:
        log_path = Path(d) / "spans.jsonl"
        run(log_path, skew)
        print(f"# inventory clock offset = {skew * 1000:+.0f}ms")
        print_tree(log_path)
        if "--json" in sys.argv:
            print(open(log_path).readline().strip())


if __name__ == "__main__":
    main()
