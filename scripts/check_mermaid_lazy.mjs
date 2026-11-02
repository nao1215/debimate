import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../assets/js/mermaid-lazy.js', import.meta.url), 'utf8')
  .replace(/import\('[^']+'\)/, 'loadMermaid()');
const tick = () => new Promise(resolve => setTimeout(resolve, 15));
let diagramCount = 0;
const diagram = (text = `graph TD; A${++diagramCount}-->B`, top = 0) => ({
  textContent: text, dataset: {}, isConnected: true, top,
  getClientRects() { return this.hidden ? [] : [{}]; },
  getBoundingClientRect() { return { top: this.top, bottom: this.top + 100 }; },
});
function setup(nodes, { observer = true, run, download } = {}) {
  const events = {};
  const observed = new Set();
  const calls = [];
  const ids = [];
  let callback;
  let imports = 0;
  let initialized = 0;
  const mermaid = {
    initialize(config) { assert.equal(config.startOnLoad, false); initialized++; },
    async render(id, text) {
      // render() does not receive the node; find it by its (unique) definition.
      const node = nodes.find(n => n.textContent === text && !n.dataset.processed);
      assert.ok(node, `no pending diagram for ${text}`);
      assert.ok(!ids.includes(id), `duplicate render id ${id}`);
      ids.push(id); calls.push(node);
      if (run) await run(node);
      return { svg: `<svg id="${id}"></svg>` };
    },
  };
  const sandbox = {
    document: {
      querySelectorAll() { return nodes.filter(n => !n.dataset.processed); },
      addEventListener(name, handler) { events[name] = handler; },
    },
    console: { warn() {} }, innerHeight: 800, setTimeout,
    async loadMermaid() { imports++; if (download) await download(); return { default: mermaid }; },
  };
  if (observer) sandbox.IntersectionObserver = class {
    constructor(handler, options) { callback = handler; assert.equal(options.rootMargin, '400px 0px'); }
    observe(node) { observed.add(node); }
    unobserve(node) { observed.delete(node); }
  };
  sandbox.window = sandbox;
  vm.runInNewContext(source, sandbox);
  return {
    calls, observed, events, get imports() { return imports; }, get initialized() { return initialized; },
    enter(...targets) { callback(targets.map(target => ({ target, isIntersecting: true }))); },
  };
}

test('offscreen diagrams do not download Mermaid; visible diagrams render once', async () => {
  const a = diagram(), b = diagram('graph TD; B-->C', 5000);
  const env = setup([a, b]);
  await tick(); assert.equal(env.imports, 0);
  env.enter(a); env.enter(a); await tick();
  assert.deepEqual(env.calls, [a]); assert.equal(env.imports, 1);
  assert.equal(env.initialized, 1); assert.equal(b.dataset.processed, undefined);
  b.top = 300; env.enter(b); await tick();
  assert.deepEqual(env.calls, [a, b]); assert.equal(env.imports, 1);
});

test('renders serially and yields between diagrams', async () => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const a = diagram(), b = diagram();
  const env = setup([a, b], { run: node => node === a ? gate : undefined });
  env.enter(a, b); await tick(); assert.deepEqual(env.calls, [a]);
  release(); await tick(); assert.deepEqual(env.calls, [a, b]);
});

test('scrolling away during download postpones rendering until the next intersection', async () => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const a = diagram(); const env = setup([a], { download: () => gate });
  env.enter(a); a.top = 5000; release(); await tick();
  assert.equal(env.calls.length, 0);
  a.top = 0; env.enter(a); await tick(); assert.deepEqual(env.calls, [a]);
});

test('new annual content and opened details are observed without duplicate work', async () => {
  const a = diagram(); a.hidden = true;
  const nodes = [a]; const env = setup(nodes);
  env.enter(a); await tick(); assert.equal(env.imports, 0);
  a.hidden = false; env.enter(a); await tick();
  const b = diagram(); nodes.push(b);
  env.events['annual:loaded'](); env.events['annual:loaded'](); env.enter(b); await tick();
  assert.deepEqual(env.calls, [a, b]);
});

test('a broken diagram preserves its source and does not block later diagrams', async () => {
  const a = diagram('broken'), b = diagram();
  const env = setup([a, b], { run: node => {
    if (node === a) { node.textContent = 'error SVG'; node.dataset.processed = 'true'; throw Error('syntax'); }
  } });
  env.enter(a, b); await tick();
  assert.equal(a.textContent, 'broken'); assert.equal(a.dataset.processed, undefined);
  assert.equal(a.dataset.mermaidError, 'true'); assert.equal(b.dataset.processed, 'true');
});

test('failed download leaves definitions readable', async () => {
  const a = diagram(); const source0 = a.textContent;
  const env = setup([a], { download() { throw Error('offline'); } });
  env.enter(a); await tick();
  assert.equal(a.textContent, source0); assert.equal(a.dataset.mermaidError, 'true');
});

test('without IntersectionObserver, diagrams still render serially', async () => {
  const a = diagram(), b = diagram(); const env = setup([a, b], { observer: false });
  await tick(); assert.deepEqual(env.calls, [a, b]); assert.equal(env.imports, 1);
});
