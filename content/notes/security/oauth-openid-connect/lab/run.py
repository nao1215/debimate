"""A toy OAuth 2.0 / OpenID Connect server and client on 127.0.0.1.

For learning only. Tokens are signed with HMAC instead of a public-key
signature, there is no login screen, and most checks of a real
authorization server are omitted. Do not reuse this code in production.
"""

import base64
import hashlib
import hmac
import json
import secrets
import threading
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

SIGNING_KEY = secrets.token_bytes(32)  # stands in for the server's private key
ISSUER = "http://127.0.0.1"
CLIENTS = {  # public clients: client_id -> registered redirect URI
    "photo-app": "https://photo.example/callback",
    "quiz-app": "https://quiz.example/callback",
}
codes = {}  # authorization code -> grant
DOWNGRADE_CHECK = True  # reject a code_verifier for a code issued without code_challenge
access_tokens = {}  # access token -> grant


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def s256(verifier):
    return b64(hashlib.sha256(verifier.encode()).digest())


def sign(claims):
    body = b64(json.dumps(claims).encode())
    return body + "." + b64(hmac.new(SIGNING_KEY, body.encode(), "sha256").digest())


def verify(token):
    body, mac = token.split(".")
    expected = b64(hmac.new(SIGNING_KEY, body.encode(), "sha256").digest())
    if not hmac.compare_digest(mac, expected):
        raise ValueError("bad signature")
    return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


class AuthorizationServer(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/authorize":
            if CLIENTS.get(q["client_id"]) != q["redirect_uri"]:  # exact match
                return self.reply(400, {"error": "invalid_request"})
            code = secrets.token_urlsafe(16)
            codes[code] = {
                "client_id": q["client_id"],
                "redirect_uri": q["redirect_uri"],
                "sub": q["user"],  # no login screen: the user is given directly
                "challenge": q.get("code_challenge"),
                "nonce": q.get("nonce"),
            }
            query = urlencode({"code": code, "state": q["state"]})
            self.send_response(302)
            self.send_header("Location", q["redirect_uri"] + "?" + query)
            self.end_headers()
        elif url.path == "/userinfo":
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            grant = access_tokens.get(token)
            if grant is None:
                return self.reply(401, {"error": "invalid_token"})
            self.reply(200, {"sub": grant["sub"]})

    def do_POST(self):  # /token
        length = int(self.headers["Content-Length"])
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
        grant = codes.get(form.get("code"))
        if (
            grant is None
            or grant["client_id"] != form.get("client_id")
            or grant["redirect_uri"] != form.get("redirect_uri")
        ):
            return self.reply(400, {"error": "invalid_grant"})
        verifier = form.get("code_verifier")
        if grant["challenge"] and s256(verifier or "") != grant["challenge"]:
            return self.reply(400, {"error": "invalid_grant"})
        if DOWNGRADE_CHECK and verifier and not grant["challenge"]:  # PKCE downgrade
            return self.reply(400, {"error": "invalid_grant"})
        del codes[form["code"]]  # a code is used only once
        access_token = secrets.token_urlsafe(16)
        access_tokens[access_token] = grant
        claims = {"iss": ISSUER, "sub": grant["sub"], "aud": grant["client_id"]}
        if grant["nonce"]:
            claims["nonce"] = grant["nonce"]
        self.reply(200, {"access_token": access_token, "token_type": "Bearer",
                         "id_token": sign(claims)})

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


def call(method, path, body=None, headers=None):
    conn = HTTPConnection("127.0.0.1", PORT)
    conn.request(method, path, body, headers or {})
    response = conn.getresponse()
    result = (response.status, response.getheader("Location"), response.read())
    conn.close()
    return result


def browser_authorize(url):
    """The browser follows /authorize and returns the code and state it was sent back with."""
    _, location, _ = call("GET", url)
    q = parse_qs(urlparse(location).query)
    return q["code"][0], q["state"][0]


def token_request(client_id, code, verifier=None):
    form = {"grant_type": "authorization_code", "code": code,
            "client_id": client_id, "redirect_uri": CLIENTS[client_id]}
    if verifier:
        form["code_verifier"] = verifier
    status, _, body = call("POST", "/token", urlencode(form),
                           {"Content-Type": "application/x-www-form-urlencoded"})
    return status, json.loads(body)


def userinfo(access_token):
    status, _, body = call("GET", "/userinfo", headers={"Authorization": "Bearer " + access_token})
    return status, json.loads(body)


class Client:
    def __init__(self, client_id, pkce=True, state=True, nonce=True):
        self.client_id, self.pkce, self.state, self.nonce = client_id, pkce, state, nonce

    def start(self, session, user):
        session["state"] = secrets.token_urlsafe(16)
        params = {"response_type": "code", "client_id": self.client_id,
                  "redirect_uri": CLIENTS[self.client_id], "user": user,
                  "state": session["state"]}
        if self.nonce:
            session["nonce"] = params["nonce"] = secrets.token_urlsafe(16)
        if self.pkce:
            session["verifier"] = secrets.token_urlsafe(32)  # 43 characters
            params.update(code_challenge=s256(session["verifier"]), code_challenge_method="S256")
        return "/authorize?" + urlencode(params)

    def callback(self, session, code, state):
        for key, used in (("state", self.state), ("nonce", self.nonce), ("verifier", self.pkce)):
            if used and key not in session:
                return "rejected: no login in progress"
        if self.state and state != session["state"]:
            return "rejected: state mismatch"
        status, body = token_request(self.client_id, code, session.get("verifier"))
        if status != 200:
            return "rejected: " + body["error"]
        return self.login_with_id_token(session, body["id_token"])

    def login_with_id_token(self, session, id_token):
        claims = verify(id_token)
        if claims["iss"] != ISSUER or claims["aud"] != self.client_id:
            return f"rejected: aud={claims['aud']}"
        if self.nonce and claims.get("nonce") != session["nonce"]:
            return "rejected: nonce mismatch"
        session["user"] = claims["sub"]
        return "logged in as " + claims["sub"]

    def login_with_access_token(self, session, access_token):
        """The broken pattern: whoever owns the token according to /userinfo logs in."""
        status, body = userinfo(access_token)
        if status != 200:
            return "rejected: " + body["error"]
        session["user"] = body["sub"]
        return "logged in as " + body["sub"]


def main():
    photo = Client("photo-app", pkce=False)
    url = photo.start({}, "alice")
    code, _ = browser_authorize(url)  # the attacker's app intercepts this redirect
    status, body = token_request("photo-app", code)
    print("(a) no PKCE, stolen code:   token", status, "-> userinfo", userinfo(body["access_token"])[1])

    photo = Client("photo-app", pkce=True)
    session = {}
    code, state = browser_authorize(photo.start(session, "alice"))
    status, body = token_request("photo-app", code)  # attacker has no code_verifier
    print("(b) PKCE, stolen code:      token", status, body)
    print("    legitimate client:     ", photo.callback(session, code, state))

    global DOWNGRADE_CHECK
    cases = [  # (client, attacker sends code_challenge?, AS checks downgrade?)
        (Client("photo-app", pkce=False, state=False, nonce=False), True, True),
        (Client("photo-app", pkce=False, state=True, nonce=False), True, True),
        (Client("photo-app", pkce=True, state=False, nonce=False), True, True),
        (Client("photo-app", pkce=False, state=False, nonce=True), True, True),
        (Client("photo-app", pkce=True, state=False, nonce=False), False, False),
        (Client("photo-app", pkce=True, state=False, nonce=False), False, True),
    ]
    for client, with_challenge, DOWNGRADE_CHECK in cases:
        mallory_session = {}
        url = client.start(mallory_session, "mallory")  # the attacker logs in as himself
        if not with_challenge:  # the attacker strips PKCE from his own request
            url = "/authorize?" + urlencode({k: v[0] for k, v in parse_qs(urlparse(url).query).items()
                                             if not k.startswith("code_challenge")})
        mallory_code, mallory_state = browser_authorize(url)  # and stops before the callback
        victim_session = {}
        client.start(victim_session, "victim")  # the victim has started a login of their own
        result = client.callback(victim_session, mallory_code, mallory_state)
        flags = f"pkce={client.pkce:d} state={client.state:d} nonce={client.nonce:d}"
        extra = "" if with_challenge else f" challenge=0 as_check={DOWNGRADE_CHECK:d}"
        print(f"(c) {flags}{extra}:", result)
    DOWNGRADE_CHECK = True
    print("(c) empty victim session:  ", Client("photo-app", pkce=False, state=True, nonce=False)
          .callback({}, mallory_code, None))

    quiz = Client("quiz-app")
    quiz_session = {}
    code, _ = browser_authorize(quiz.start(quiz_session, "alice"))  # alice uses quiz-app once
    _, quiz_tokens = token_request("quiz-app", code, quiz_session["verifier"])
    photo = Client("photo-app")  # quiz-app's operator sends alice's tokens to photo-app
    print("(d) access token -> photo-app:", photo.login_with_access_token({}, quiz_tokens["access_token"]))
    print("    ID Token     -> photo-app:", photo.login_with_id_token({}, quiz_tokens["id_token"]))

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 0), AuthorizationServer)
    PORT = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        main()
    finally:
        server.shutdown()
        server.server_close()
