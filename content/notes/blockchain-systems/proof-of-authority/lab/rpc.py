"""Tiny JSON-RPC client and helpers shared by the QBFT and Clique scenarios."""

import json
import urllib.request


def call(ip, method, params=None, timeout=2):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                       "params": params or []}).encode()
    req = urllib.request.Request(f"http://{ip}:8545", body,
                                 {"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.load(res).get("result")
    except OSError:
        return None  # stopped node or timeout


def head(ip):
    """Return (number, hash) of the node's latest block, or None."""
    b = call(ip, "eth_getBlockByNumber", ["latest", False])
    return (int(b["number"], 16), b["hash"]) if b else None


def block(ip, number):
    return call(ip, "eth_getBlockByNumber", [hex(number), False])


def rlp_items(data):
    """Decode one RLP list into Python lists/bytes (enough for extraData)."""
    def item(i):
        b = data[i]
        if b < 0x80:
            return data[i:i + 1], i + 1
        if b < 0xb8:
            n = b - 0x80
            return data[i + 1:i + 1 + n], i + 1 + n
        if b < 0xc0:
            ln = b - 0xb7
            n = int.from_bytes(data[i + 1:i + 1 + ln], "big")
            s = i + 1 + ln
            return data[s:s + n], s + n
        if b < 0xf8:
            n, s = b - 0xc0, i + 1
        else:
            ln = b - 0xf7
            n, s = int.from_bytes(data[i + 1:i + 1 + ln], "big"), i + 1 + ln
        out, j = [], s
        while j < s + n:
            v, j = item(j)
            out.append(v)
        return out, s + n
    return item(0)[0]


def qbft_extra(extra_hex):
    """QBFT extraData = RLP[vanity, validators, vote, round, seals]."""
    vanity, validators, vote, rnd, seals = rlp_items(bytes.fromhex(extra_hex[2:]))
    return {"round": int.from_bytes(rnd, "big"), "seals": len(seals),
            "validators": len(validators)}
