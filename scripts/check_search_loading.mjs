import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../assets/js/fastsearch.js', import.meta.url), 'utf8');
const data = [{ title: 'gup', url: '/gup/', date: '2026-01-01', type: 'post', content: 'Goの更新ツール', headings: [] }];
function setup(fetcher = async () => ({ ok: true, json: async () => data })) {
  const elements = {};
  for (const id of ['searchInput', 'searchResults', 'searchStatus', 'searchRetry']) {
    elements[id] = { value: '', textContent: '', innerHTML: '', hidden: true, events: {},
      addEventListener(name, fn) { this.events[name] = fn; } };
  }
  const timers = new Map(); let next = 0; let requests = 0;
  const sandbox = {
    document: { getElementById: id => elements[id], addEventListener() {} },
    window: { addEventListener() {} }, console: { error() {} },
    fetch: async (...args) => { requests++; return fetcher(...args); },
    setTimeout(fn) { timers.set(++next, fn); return next; },
    clearTimeout(id) { timers.delete(id); },
  };
  vm.runInNewContext(source, sandbox);
  return {
    elements, timers, get requests() { return requests; },
    input(value) { elements.searchInput.value = value; elements.searchInput.events.input({}); },
    async flush() { const jobs = [...timers.values()]; timers.clear(); await Promise.all(jobs.map(fn => fn())); },
  };
}

test('empty search downloads nothing; a burst of input fetches once and reuses data', async () => {
  const env = setup();
  await env.flush(); assert.equal(env.requests, 0);
  env.input('g'); env.input('gu'); env.input('gup');
  assert.equal(env.requests, 0); assert.equal(env.timers.size, 1);
  await env.flush(); assert.equal(env.requests, 1);
  assert.match(env.elements.searchResults.innerHTML, /href="\/gup\/"/);
  env.input('Go'); await env.flush(); assert.equal(env.requests, 1);
});

test('IME composition does not fetch until committed', async () => {
  const env = setup(); const input = env.elements.searchInput;
  input.events.compositionstart(); env.input('更新'); await env.flush();
  assert.equal(env.requests, 0);
  input.events.compositionend(); await env.flush(); assert.equal(env.requests, 1);
});

test('clearing a query cancels scheduled work', async () => {
  const env = setup(); env.input('gup'); env.input(''); await env.flush();
  assert.equal(env.requests, 0); assert.equal(env.elements.searchResults.innerHTML, '');
});

test('an old response cannot overwrite a cleared query or start a duplicate download', async () => {
  let release;
  const response = new Promise(resolve => { release = resolve; });
  const env = setup(() => response);
  env.input('gup'); const first = env.flush();
  env.input('Go'); const second = env.flush();
  env.input(''); await env.flush();
  release({ ok: true, json: async () => data }); await Promise.all([first, second]);
  assert.equal(env.requests, 1); assert.equal(env.elements.searchResults.innerHTML, '');
  assert.match(env.elements.searchStatus.textContent, /キーワード/);
});

test('failed requests can be retried without reloading the page', async () => {
  let attempt = 0;
  const env = setup(async () => ++attempt === 1
    ? { ok: false, status: 503 } : { ok: true, json: async () => data });
  env.input('gup'); await env.flush(); assert.equal(env.elements.searchRetry.hidden, false);
  env.input('gup'); await env.flush();
  assert.equal(env.requests, 2); assert.equal(env.elements.searchRetry.hidden, true);
  assert.match(env.elements.searchResults.innerHTML, /href="\/gup\/"/);
});
