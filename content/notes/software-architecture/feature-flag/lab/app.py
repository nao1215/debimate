"""The same flag check served by gunicorn (WSGI) and uvicorn (ASGI).

GET /?user=u-00042 -> {"pid": 1234, "on": true}

FLAG_RULE selects how a user is put into the 10%:
  builtin  hash(user) % 100 < 10        Python's built-in hash
  crc32    zlib.crc32(user) % 100 < 10   the same value in every process
"""

import json
import os
import zlib
from urllib.parse import parse_qs

RULE = os.environ.get("FLAG_RULE", "builtin")
PERCENT = 10


def is_on(user: str) -> bool:
    if RULE == "builtin":
        return hash(user) % 100 < PERCENT
    return zlib.crc32(user.encode()) % 100 < PERCENT


def answer(query: str) -> bytes:
    user = parse_qs(query)["user"][0]
    return json.dumps({"pid": os.getpid(), "on": is_on(user)}).encode()


def wsgi(environ, start_response):  # gunicorn app:wsgi
    body = answer(environ.get("QUERY_STRING", ""))
    start_response("200 OK", [("Content-Type", "application/json")])
    return [body]


async def asgi(scope, receive, send):  # uvicorn app:asgi
    body = answer(scope["query_string"].decode())
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})
