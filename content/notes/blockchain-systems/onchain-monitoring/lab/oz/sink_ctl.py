"""Webhook sink with a switch (oz copy of ../sink.py, 127.0.0.1 only).

Usage: python3 sink_ctl.py PORT LOG_PATH
POST /control {"fail": true|false} switches every answer to HTTP 500 (S4) and back.
Every request, including the 500 ones, is logged with time, status and body.
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
state = {"fail": False}
lock = threading.Lock()
logf = open(LOG, "a", buffering=1)


class Sink(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode(errors="replace")
        if self.path == "/control":
            cmd = json.loads(body)
            with lock:
                state["fail"] = bool(cmd.get("fail", False))
            logf.write(json.dumps({"t": time.time(), "control": dict(state)}) + "\n")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")
            return
        try:
            payload = json.loads(body)
        except Exception:
            payload = body
        with lock:
            status = 500 if state["fail"] else 200
            logf.write(json.dumps({"t": time.time(), "path": self.path, "status": status, "body": payload}) + "\n")
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b"{}")


ThreadingHTTPServer(("127.0.0.1", PORT), Sink).serve_forever()
