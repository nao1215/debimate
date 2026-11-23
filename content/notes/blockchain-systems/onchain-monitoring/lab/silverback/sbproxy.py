"""JSON-RPC fault proxy for HTTP *and* WebSocket on one port (127.0.0.1 only).

Same control and log format as ../faultproxy.py, which only speaks HTTP. Silverback's default
WebsocketRunner subscribes over WebSocket (eth_subscribe newHeads/logs), and ape-foundry derives
the WS URI from the HTTP host (http://h:p -> ws://h:p), so both must sit on the same port.

  POST /control {"fail_blocks": [n...], "mode": "error"|"timeout"|"empty", "down": bool}
- HTTP and WS requests that name a failing block get the fault (same rule as faultproxy.py).
- WS notifications (eth_subscription) whose block is in fail_blocks are dropped (logged).
- down: HTTP requests get the fault; open WS connections are closed and new ones are refused (503).

Usage: venv/bin/python sbproxy.py LISTEN_PORT UPSTREAM_HTTP UPSTREAM_WS LOG_PATH
"""
import asyncio
import json
import sys
import time

import aiohttp
from aiohttp import web

LISTEN, UP_HTTP, UP_WS, LOG = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
state = {'fail_blocks': set(), 'mode': 'error', 'down': False}
logf = open(LOG, 'a', buffering=1)
live_ws = set()


def log(d):
    logf.write(json.dumps({'t': time.time(), **d}) + '\n')


def as_int(v):
    if isinstance(v, str) and v.startswith('0x'):
        return int(v, 16)
    return None


def touched_blocks(req):
    m, p = req.get('method'), req.get('params') or []
    if m in ('eth_getBlockByNumber', 'eth_getBlockReceipts', 'trace_block', 'debug_traceBlockByNumber') and p:
        n = as_int(p[0])
        return {n} if n is not None else set()
    if m == 'eth_getLogs' and p and isinstance(p[0], dict):
        f, t = as_int(p[0].get('fromBlock')), as_int(p[0].get('toBlock'))
        if f is not None and t is not None:
            return set(range(f, t + 1))
    return set()


def fault_for(req):
    if state['down']:
        return state['mode']
    if touched_blocks(req) & state['fail_blocks']:
        return state['mode']
    return None


def fault_reply(r, f):
    if f == 'empty':
        return {'jsonrpc': '2.0', 'id': r.get('id'), 'result': [] if r.get('method') == 'eth_getLogs' else None}
    return {'jsonrpc': '2.0', 'id': r.get('id'), 'error': {'code': -32603, 'message': 'injected fault'}}


async def http_rpc(request):
    body = await request.read()
    try:
        reqs = json.loads(body)
    except ValueError:
        reqs = None
    batch = isinstance(reqs, list)
    items = reqs if batch else [reqs]
    faults = [fault_for(r) if isinstance(r, dict) else None for r in items]
    for r, f in zip(items, faults):
        if isinstance(r, dict):
            log({'via': 'http', 'method': r.get('method'), 'params': r.get('params'), 'fault': f})
    if any(f == 'timeout' for f in faults):
        await asyncio.sleep(60)
        return web.Response(status=504)
    async with aiohttp.ClientSession() as s:
        async with s.post(UP_HTTP, data=body, headers={'Content-Type': 'application/json'}) as resp:
            up = await resp.read()
    if all(f is None for f in faults):
        return web.Response(body=up, content_type='application/json')
    upj = json.loads(up)
    ups = upj if batch else [upj]
    res = [fault_reply(r, f) if f else u for r, f, u in zip(items, faults, ups)]
    return web.json_response(res if batch else res[0])


def notif_block(msg):
    res = (msg.get('params') or {}).get('result')
    if isinstance(res, dict):
        return as_int(res.get('blockNumber')) if 'blockNumber' in res else as_int(res.get('number'))
    return None


async def ws_rpc(request):
    if state['down']:
        log({'via': 'ws', 'event': 'refused (down)'})
        return web.Response(status=503)
    client = web.WebSocketResponse(max_msg_size=0)
    await client.prepare(request)
    live_ws.add(client)
    log({'via': 'ws', 'event': 'open'})
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(UP_WS, max_msg_size=0) as up:
            async def c2u():
                async for m in client:
                    if m.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                        break
                    r = json.loads(m.data)  # web3's WebSocketProvider sends binary frames
                    f = fault_for(r) if isinstance(r, dict) else None
                    log({'via': 'ws', 'dir': 'req', 'method': r.get('method') if isinstance(r, dict) else None,
                         'params': r.get('params') if isinstance(r, dict) else None, 'fault': f})
                    if f:
                        await client.send_str(json.dumps(fault_reply(r, f)))
                    elif m.type == aiohttp.WSMsgType.BINARY:
                        await up.send_bytes(m.data)
                    else:
                        await up.send_str(m.data)

            async def u2c():
                async for m in up:
                    if m.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                        break
                    d = json.loads(m.data)
                    if isinstance(d, dict) and d.get('method') == 'eth_subscription':
                        b = notif_block(d)
                        res = d['params'].get('result')
                        kind = 'log' if isinstance(res, dict) and 'logIndex' in res else 'head'
                        drop = state['down'] or (b is not None and b in state['fail_blocks'])
                        log({'via': 'ws', 'dir': 'notif', 'kind': kind, 'block': b,
                             'removed': res.get('removed') if isinstance(res, dict) else None,
                             'fault': 'dropped' if drop else None})
                        if drop:
                            continue
                    if m.type == aiohttp.WSMsgType.BINARY:
                        await client.send_bytes(m.data)
                    else:
                        await client.send_str(m.data)

            tasks = [asyncio.create_task(c2u()), asyncio.create_task(u2c())]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in tasks:
                t.cancel()
    live_ws.discard(client)
    await client.close()
    log({'via': 'ws', 'event': 'closed'})
    return client


async def root(request):
    if request.method == 'GET' and request.headers.get('Upgrade', '').lower() == 'websocket':
        return await ws_rpc(request)
    return await http_rpc(request)


async def control(request):
    cmd = await request.json()
    if 'fail_blocks' in cmd:
        state['fail_blocks'] = set(cmd['fail_blocks'])
    if 'mode' in cmd:
        state['mode'] = cmd['mode']
    if 'down' in cmd:
        state['down'] = bool(cmd['down'])
        if state['down']:
            for ws in list(live_ws):
                await ws.close(code=1011, message=b'injected down')
    snap = {'fail_blocks': sorted(state['fail_blocks']), 'mode': state['mode'], 'down': state['down'],
            'ws_open': len(live_ws)}
    log({'control': snap})
    return web.json_response(snap)


app = web.Application(client_max_size=64 * 1024 * 1024)
app.router.add_post('/control', control)
app.router.add_route('*', '/', root)
web.run_app(app, host='127.0.0.1', port=LISTEN, print=None)
