"""429 Too Many Requests と Retry-After、RateLimit ヘッダーを返す最小の HTTP サーバー。

固定窓で「10 秒あたり 5 件」を数える（数は 1 つだけで、利用者は区別しない）。
ヘッダーの形は draft-ietf-httpapi-ratelimit-headers-11（2026-05-23、Internet-Draft）に合わせた。
127.0.0.1 だけで待ち受ける。

  python3 server.py &
  for i in 1 2 3 4 5 6; do curl -si http://127.0.0.1:18080/ | head -6; done
"""
import math
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

LIMIT, WINDOW = 5, 10
state = {"window": None, "count": 0}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        now = time.time()
        w = math.floor(now / WINDOW)
        if w != state["window"]:
            state["window"], state["count"] = w, 0
        reset = math.ceil((w + 1) * WINDOW - now)      # 今の窓が終わるまでの秒数

        allowed = state["count"] < LIMIT
        if allowed:
            state["count"] += 1
        remaining = LIMIT - state["count"]

        self.send_response(200 if allowed else 429)
        self.send_header("RateLimit-Policy", f'"default";q={LIMIT};w={WINDOW}')
        self.send_header("RateLimit", f'"default";r={remaining};t={reset}')
        if not allowed:
            self.send_header("Retry-After", str(reset))
        body = b"ok\n" if allowed else b"too many requests\n"
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 18080), Handler).serve_forever()
