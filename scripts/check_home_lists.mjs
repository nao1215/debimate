// Run with: node --test scripts/check_home_lists.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../assets/js/home-lists.js', import.meta.url), 'utf8');
const tick = () => new Promise((resolve) => setImmediate(resolve));
function mount({ state = {}, fetcher, observer = true, brokenHistory = false, latestNext, bounds } = {}) {
  const observers = [];
  const requests = [];
  const events = {};
  const history = { state, replaceState(value) {
    if (brokenHistory) throw new Error('unavailable');
    this.state = structuredClone(value);
  } };
  const sections = ['posts', 'weeknotes', 'notes'].map((key, index) => {
    const batch = index === 0 ? 6 : 3;
    const cards = Array(batch).fill({});
    const button = { hidden: true, addEventListener(_, fn) { this.click = fn; } };
    const message = {};
    const status = {
      dataset: { total: '60', next: `/${key}/2` },
      getBoundingClientRect: () => bounds ? bounds(key, cards.length) : ({ top: 10000, bottom: 10030 }),
      querySelector: (selector) => selector === 'button' ? button : message,
    };
    return { cards, status, button, message,
      getAttribute: () => `home-${key}-title`,
      querySelectorAll: () => cards,
      querySelector: () => status,
      insertBefore: (fragment) => cards.push(...fragment.querySelectorAll()),
    };
  });
  class IntersectionObserver {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() { this.observing = true; }
    unobserve() { this.observing = false; }
    disconnect() { this.observing = false; }
  }
  const window = {
    ...(observer ? { IntersectionObserver } : {}), scrollY: 0, innerHeight: 900,
    location: { href: 'https://example.test/', reload() { this.reloaded = true; } },
    addEventListener: (name, fn) => { events[name] = fn; },
    scrollTo: (_, y) => { window.scrollY = y; },
  };
  runInNewContext(source, {
    history, window, IntersectionObserver, AbortController,
    DOMParser: class {
      parseFromString() {
        return { querySelector: () => ({ querySelector: () => ({ dataset: { next: latestNext } }) }) };
      }
    },
    setTimeout: (callback) => callback(), clearTimeout() {},
    document: {
      querySelectorAll: () => sections,
      createElement: () => {
        const template = { innerHTML: '' };
        template.content = { querySelectorAll: () => Array(Number(template.innerHTML)).fill({}) };
        return template;
      },
    },
    requestAnimationFrame: (callback) => callback(),
    fetch: async (url, options) => {
      requests.push(url);
      if (fetcher) return fetcher(url, options);
      const [, key, page] = url.split('/');
      const batch = key === 'posts' ? 6 : 3;
      return { ok: true, json: async () => ({ html: String(batch), next: Number(page) * batch < 60 ? `/${key}/${Number(page) + 1}` : '' }) };
    },
  });
  return { history, sections, requests, events, window, observers,
    counts: () => sections.map((section) => section.cards.length),
    approachEnd: (index) => observers[index].callback([{ isIntersecting: true }]),
  };
}

test('no eager requests; lists load independently and restore saved counts', async () => {
  const page = mount({ state: { unrelated: 'keep' } });
  assert.deepEqual(page.requests, []);
  assert.deepEqual(page.counts(), [6, 3, 3]);
  await page.approachEnd(0);
  await page.approachEnd(0);
  await page.approachEnd(1);
  await page.approachEnd(2);
  assert.deepEqual(page.counts(), [18, 6, 6]);
  page.window.scrollY = 1200;
  page.events.scroll();
  const restored = mount({ state: page.history.state });
  await tick();
  assert.deepEqual(restored.counts(), [18, 6, 6]);
  assert.equal(restored.window.scrollY, 1200);
  assert.equal(restored.history.state.unrelated, 'keep');
});

test('failure retains cards and next URL; explicit retry works', async () => {
  let fail = true;
  const page = mount({ fetcher: async () => ({ ok: !fail, status: 503, json: async () => ({ html: '6', next: '' }) }) });
  await page.approachEnd(0);
  assert.deepEqual(page.counts(), [6, 3, 3]);
  assert.equal(page.sections[0].button.textContent, '再試行');
  assert.equal(page.observers[0].observing, false);
  fail = false;
  await page.sections[0].button.click();
  assert.deepEqual(page.counts(), [12, 3, 3]);
  assert.equal(page.sections[0].button.hidden, true);
  assert.deepEqual(page.requests, ['/posts/2', '/posts/2']);
});

test('overlapping observer and button events do not duplicate a batch', async () => {
  let complete;
  const page = mount({ fetcher: () => new Promise((resolve) => { complete = resolve; }) });
  const pending = page.approachEnd(0);
  await page.approachEnd(0);
  await page.sections[0].button.click();
  complete({ ok: true, json: async () => ({ html: '6', next: '' }) });
  await pending;
  assert.equal(page.requests.length, 1);
  assert.equal(page.counts()[0], 12);
});

test('buttons work without IntersectionObserver or writable history', async () => {
  const page = mount({ observer: false, brokenHistory: true });
  await page.sections[0].button.click();
  assert.deepEqual(page.counts(), [12, 3, 3]);
});

test('stale/invalid saved counts are bounded; user interaction prevents scroll jump', async () => {
  const page = mount({ state: { homeLists: { 'home-posts-title': 600, 'home-notes-title': -1 }, homeScrollY: 900 } });
  page.events.wheel();
  await tick();
  assert.deepEqual(page.counts(), [60, 3, 3]);
  assert.equal(page.window.scrollY, 0);
  assert.equal(page.sections[0].button.hidden, true);
});


test('leaving during note loading does not retain an error after back navigation', async () => {
  let attempts = 0;
  const page = mount({ fetcher: (url, { signal }) => {
    attempts++;
    if (attempts > 1) return { ok: true, json: async () => ({ html: '3', next: '/notes/3' }) };
    return new Promise((resolve, reject) => {
      signal.addEventListener('abort', () => reject(new Error('Navigation cancelled request')));
    });
  } });
  const pending = page.approachEnd(2);
  page.events.pagehide({ persisted: true });
  // Resume before the cancelled request's rejection is processed.
  page.events.pageshow({ persisted: true });
  await pending;
  await tick();
  assert.equal(attempts, 2);
  assert.equal(page.counts()[2], 6);
  assert.equal(page.sections[2].button.textContent, 'もっと見る');
  assert.equal(page.observers[2].observing, true);
});


test('back to an old deployment refreshes only when the homepage batch URL changed', async () => {
  for (const latestNext of ['/notes/2', '/notes/new-deployment']) {
    const page = mount({ latestNext, fetcher: async (url) => url === 'https://example.test/'
      ? { ok: true, text: async () => '<html></html>' }
      : { ok: false, status: 404 } });
    await page.approachEnd(2);
    assert.equal(Boolean(page.window.location.reloaded), latestNext !== '/notes/2');
    assert.deepEqual(page.requests, ['/notes/2', 'https://example.test/']);
    if (latestNext === '/notes/2') assert.equal(page.sections[2].button.textContent, '再試行');
  }
});

test('a freshness check finishing after navigation must not reload the hidden document', async () => {
  let finish;
  const page = mount({ latestNext: '/notes/new-deployment', fetcher: async (url) => url === 'https://example.test/'
    ? { ok: true, text: () => new Promise(resolve => { finish = resolve; }) }
    : { ok: false, status: 404 } });
  const pending = page.approachEnd(2);
  await tick();
  page.events.pagehide({ persisted: true });
  finish('<html></html>');
  await pending;
  assert.equal(page.window.location.reloaded, undefined);
  assert.notEqual(page.sections[2].button.textContent, '再試行');
});


test('short batches fill the preload area without another intersection event', async () => {
  const page = mount({ bounds: (key, count) => ({ top: key === 'notes' && count < 9 ? 2000 : 10000, bottom: 10030 }) });
  await tick();
  assert.deepEqual(page.counts(), [6, 3, 9]);
  assert.deepEqual(page.requests, ['/notes/2', '/notes/3']);
  assert.equal(page.observers[2].observing, true);
});
