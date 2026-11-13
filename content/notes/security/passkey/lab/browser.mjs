// Chrome の仮想 authenticator（CDP の WebAuthn ドメイン）で、どの origin のページがどの rpId を使えるかを調べる。
// 前提: webauthn_page.html.txt を 18080 番で配信し、Chrome を --remote-debugging-port=9334 で起動しておく（run_browser.sh）。
const sleep = ms => new Promise(r => setTimeout(r, ms));
let list;
for (let i = 0; i < 50; i++) { try { list = await (await fetch('http://127.0.0.1:9334/json')).json(); break; } catch { await sleep(200); } }
const ws = new WebSocket(list.find(x => x.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pend = {};
ws.onmessage = e => { const m = JSON.parse(e.data); if (pend[m.id]) { pend[m.id](m); delete pend[m.id]; } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({id: i, method, params})); });
const evalJs = async expr => (await send('Runtime.evaluate', {expression: expr, awaitPromise: true, returnByValue: true})).result.result.value;
const open = async url => { await send('Page.navigate', {url}); await sleep(800); };

await send('Page.enable');
await send('WebAuthn.enable');
await send('WebAuthn.addVirtualAuthenticator', {options: {protocol: 'ctap2', transport: 'internal',
  hasResidentKey: true, hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true}});

const port = 18080;
await open(`http://app.localhost:${port}/`);
console.log('登録 app.localhost 上で rpId=app.localhost:', JSON.stringify(await evalJs('register("app.localhost")').then(r => JSON.parse(r.clientData).origin)));
const cases = [
  ['app.localhost', 'app.localhost'],
  ['uploads.app.localhost', 'app.localhost'],
  ['app-localhost.localhost', 'app.localhost'],
  ['app-localhost.localhost', 'app-localhost.localhost'],
];
for (const [host, rpId] of cases) {
  await open(`http://${host}:${port}/`);
  const r = await evalJs(`login(${JSON.stringify(rpId)})`);
  const detail = r.ok ? `成功 origin=${JSON.parse(r.clientData).origin} signCount=${r.signCount} flags=0x${r.flags.toString(16)}` : `失敗 ${r.error}`;
  console.log(`ページ ${host} / rpId ${rpId} -> ${detail}`);
}
process.exit(0);
