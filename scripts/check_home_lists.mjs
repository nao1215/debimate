// Run with: node --test scripts/check_home_lists.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../assets/js/home-lists.js', import.meta.url), 'utf8');

function mount(history) {
  const observers = [];
  const sections = ['home-posts-title', 'home-notes-title'].map((key) => {
    const cards = Array.from({ length: 60 }, () => ({
      hidden: false, classList: { remove() {} },
    }));
    const status = { textContent: '' };
    return {
      cards, status,
      getAttribute: () => key,
      querySelectorAll: () => cards,
      querySelector: () => status,
    };
  });
  class IntersectionObserver {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  runInNewContext(source, {
    history, window: { IntersectionObserver }, IntersectionObserver,
    document: { querySelectorAll: () => sections },
    requestAnimationFrame: (callback) => callback(),
  });
  return {
    counts: () => sections.map((section) => section.cards.filter((card) => !card.hidden).length),
    approachEnd: (index) => observers[index].callback([{ isIntersecting: true }]),
  };
}

test('reload restores both lists independently and keeps unrelated history state', () => {
  const history = {
    state: { unrelated: 'keep' },
    replaceState(state) { this.state = structuredClone(state); },
  };
  const page = mount(history);
  page.approachEnd(0);
  page.approachEnd(0);
  page.approachEnd(1);
  assert.deepEqual(page.counts(), [18, 12]);
  const reloaded = mount(history);
  assert.deepEqual(reloaded.counts(), [18, 12]);
  reloaded.approachEnd(0);
  assert.deepEqual(reloaded.counts(), [24, 12]);
  assert.equal(history.state.unrelated, 'keep');
  assert.deepEqual(mount({ state: null, replaceState() {} }).counts(), [6, 6]);
});

test('saved counts tolerate content removal and invalid values', () => {
  const page = mount({
    state: { homeLists: { 'home-posts-title': 600, 'home-notes-title': -1 } },
    replaceState() {},
  });
  assert.deepEqual(page.counts(), [60, 6]);
});

test('history failures do not prevent progressive loading', () => {
  const page = mount({ state: null, replaceState() { throw new Error('unavailable'); } });
  page.approachEnd(0);
  assert.deepEqual(page.counts(), [12, 6]);
});
