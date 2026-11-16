"""1 台のアプリケーションサーバーの代わり。

GET /work?c=<顧客 ID>&q=<入力> に 200 を返す。q が poison の時だけ、
応答を返す前にプロセスごと落ちる（入力を解釈する所で落ちる不具合の代わり）。

Run: python3 worker.py <port>
"""

import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    def _work(self):
        q = parse_qs(urlparse(self.path).query).get("q", [""])[0]
        if q == "poison":
            os._exit(1)  # 応答を返さずにプロセスが消える
        time.sleep(0.005)
        body = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _work
    do_POST = _work

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
