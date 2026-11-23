"""Webhook sink: records every POST body with the receive time to a JSONL file (127.0.0.1 only).

Usage: python3 sink.py PORT LOG_PATH [FAIL_FIRST_N]
FAIL_FIRST_N: answer HTTP 500 to the first N requests (to see whether a monitor retries).
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
fail_left = [int(sys.argv[3]) if len(sys.argv) > 3 else 0]
logf = open(LOG, "a", buffering=1)


class Sink(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode(errors="replace")
        try:
            payload = json.loads(body)
        except Exception:
            payload = body
        status = 200
        if fail_left[0] > 0:
            fail_left[0] -= 1
            status = 500
        logf.write(json.dumps({"t": time.time(), "path": self.path, "status": status, "body": payload}) + "\n")
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b"{}")


ThreadingHTTPServer(("127.0.0.1", PORT), Sink).serve_forever()
