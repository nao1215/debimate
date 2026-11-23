"""Webhook sink with a switch (127.0.0.1 only). Copy of ../sink.py plus a time-based failure switch.

Usage: python3 sink_ctl.py PORT LOG_PATH
POST /__control {"fail": true|false}: while fail is on, every other POST gets HTTP 500.
Every POST (including the 500s) is logged with the receive time, path, status and body.
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
state = {'fail': False}
logf = open(LOG, 'a', buffering=1)


class Sink(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode(errors='replace')
        try:
            payload = json.loads(body)
        except Exception:
            payload = body
        if self.path == '/__control':
            state['fail'] = bool(payload.get('fail'))
            logf.write(json.dumps({'t': time.time(), 'control': state}) + '\n')
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{}')
            return
        status = 500 if state['fail'] else 200
        hdr = {k.lower(): v for k, v in self.headers.items() if k.lower().startswith('x-')}
        logf.write(json.dumps({'t': time.time(), 'path': self.path, 'status': status, 'headers': hdr, 'body': payload}) + '\n')
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b'{}')


ThreadingHTTPServer(('127.0.0.1', PORT), Sink).serve_forever()
