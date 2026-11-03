import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../assets/js/new-badges.js', import.meta.url), 'utf8');
const badge = date => ({ dataset: { newDate: date }, hidden: true, matches: () => true });
function setup(dates, clock) {
  const badges = dates.map(badge);
  let now = Date.parse(clock), mutation, timer;
  const events = {};
  const document = {
    body: {}, hidden: false, querySelectorAll: () => badges,
    addEventListener: (name, fn) => { events[name] = fn; },
  };
  vm.runInNewContext(source, {
    document, window: { addEventListener: (name, fn) => { events[name] = fn; } },
    Date: class extends Date { static now() { return now; } },
    MutationObserver: class { constructor(fn) { mutation = fn; } observe() {} },
    setTimeout(fn, delay) { timer = { fn, delay }; return 1; }, clearTimeout() {},
  });
  return { badges, events, document, get timer() { return timer; },
    setClock(value) { now = Date.parse(value); },
    add(date) { const item = badge(date); badges.push(item); mutation([{ addedNodes: [item] }]); return item; },
  };
}

test('Japan calendar days: today and day fourteen visible; old, future and missing dates hidden', () => {
  const env = setup(['2026-11-03', '2026-10-21', '2026-10-20', '2026-11-04', '', undefined], '2026-11-02T15:00:00Z');
  assert.deepEqual(env.badges.map(b => b.hidden), [false, false, true, true, true, true]);
});

test('inserted cards, midnight expiry and restored tabs use the current date', () => {
  const env = setup([], '2026-11-16T23:59:59+09:00');
  const item = env.add('2026-11-03');
  assert.equal(item.hidden, false);
  assert.equal(env.timer.delay, 1050);
  env.setClock('2026-11-17T00:00:00+09:00');
  env.timer.fn();
  assert.equal(item.hidden, true);
  const recent = env.add('2026-11-17');
  assert.equal(recent.hidden, false);
  env.setClock('2026-12-01T00:00:00+09:00');
  env.events.pageshow();
  assert.equal(recent.hidden, true);
  const latest = env.add('2026-12-01');
  env.setClock('2026-12-15T00:00:00+09:00');
  env.events.visibilitychange();
  assert.equal(latest.hidden, true);
});

test('Weeknotes can stay NEW for 21 days while other cards expire after 14', () => {
  const env = setup(['2026-11-03'], '2026-11-23T23:59:59+09:00');
  assert.equal(env.badges[0].hidden, true);
  env.badges[0].dataset.newDays = '21';
  env.events.pageshow();
  assert.equal(env.badges[0].hidden, false);
  env.setClock('2026-11-24T00:00:00+09:00');
  env.timer.fn();
  assert.equal(env.badges[0].hidden, true);
});
