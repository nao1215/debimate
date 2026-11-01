// Usage: PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node scripts/check_archives_browser.mjs http://127.0.0.1:8141
import assert from 'node:assert/strict';
import { launchBrowser, saveFailure, localURL } from './browser_support.mjs';
const origin = new URL(process.argv[2] || 'http://127.0.0.1:8141').origin;
const browser = await launchBrowser();
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
await context.route('**/*', route => {
  const url = new URL(route.request().url());
  if (url.origin === origin) return route.continue();
  if (url.pathname.endsWith('/mermaid.esm.min.mjs')) return route.fulfill({
    contentType: 'application/javascript', headers: { 'Access-Control-Allow-Origin': '*' },
    body: 'export default { initialize() {}, async run({nodes}) { window.diagramRuns = (window.diagramRuns || 0) + nodes.length; nodes.forEach(n => n.dataset.processed = "true"); } };',
  });
  return route.abort();
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  const cases = [
    ['/post/', '.listing-card'],
    ['/post/ja/', '.listing-card'],
    ['/weeknotes/', '.weeknotes-index-week'],
    ['/weeknotes/2026/', '.weeknotes-entry'],
  ];
  const readPosition = () => page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[data-scroll-anchor]')];
    const node = nodes.find(node => node.getBoundingClientRect().top >= 0 && node.getBoundingClientRect().top < innerHeight) || nodes.filter(node => node.getBoundingClientRect().top < 0).at(-1);
    return { key: node.dataset.scrollAnchor, offset: node.getBoundingClientRect().top };
  });
  const assertPosition = async saved => {
    await page.waitForFunction(({ key, offset }) => {
      const node = [...document.querySelectorAll('[data-scroll-anchor]')].find(n => n.dataset.scrollAnchor === key);
      return node && Math.abs(node.getBoundingClientRect().top - offset) < 4;
    }, saved);
  };
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 844 });
    for (const [path, selector] of cases) {
      await page.goto(origin + path);
      await page.waitForFunction(() => document.documentElement.dataset.archiveReady === 'true');
      assert.equal(await page.locator('.archive-pagination:visible').count(), 0);
      for (let i = 0; i < 3; i++) {
        const count = await page.locator(selector).count();
        await page.locator('.archive-scroll-status').scrollIntoViewIfNeeded();
        await page.waitForFunction(({ selector, count }) => document.querySelectorAll(selector).length > count, { selector, count });
      }
      const target = page.locator('[data-scroll-anchor]').nth(-3);
      await target.evaluate(node => node.scrollIntoView({ block: 'center', behavior: 'instant' }));
      await page.waitForTimeout(250);
      // Reload immediately after changing position: no debounce delay is allowed.
      await page.evaluate(() => scrollTo({ top: scrollY - 137, behavior: 'instant' }));
      const saved = await readPosition();
      const count = await page.locator(selector).count();
      await page.reload();
      await page.waitForFunction(() => document.documentElement.dataset.archiveReady === 'true');
      assert.ok(await page.locator(selector).count() >= count);
      await assertPosition(saved);
      const urls = await page.locator('.listing-card-link').evaluateAll(links => links.map(link => link.href));
      assert.equal(new Set(urls).size, urls.length);
      const groups = await page.locator('[data-archive-group]').evaluateAll(nodes => nodes.map(node => node.dataset.archiveGroup));
      assert.equal(new Set(groups).size, groups.length);
      const destination = await page.locator('.listing-card-link, .weeknotes-entry-title a').last().getAttribute('href');
      await page.goto(localURL(destination, origin));
      await page.goBack();
      await page.waitForFunction(() => document.documentElement.dataset.archiveReady === 'true');
      await assertPosition(saved);
      console.log(`PASS ${width}px ${path}: automatic scroll, immediate reload, back, position and unique groups/cards`);
    }
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${origin}/post/ja/`);
  const secondURL = `${origin}/post/ja/page/2/`;
  await page.route(secondURL, route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.locator('.archive-scroll-status').scrollIntoViewIfNeeded();
  await page.locator('.archive-scroll-status button').waitFor({ state: 'visible' });
  assert.equal(await page.locator('.listing-card').count(), 20);
  await page.unroute(secondURL);
  await page.locator('.archive-scroll-status button').click();
  await page.waitForFunction(() => document.querySelectorAll('.listing-card').length >= 40);
  await page.locator('.listing-card').nth(25).evaluate(node => node.scrollIntoView({ block: 'center' }));
  const saved = await readPosition();
  await page.route(secondURL, route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.reload();
  await page.locator('.archive-scroll-status button').waitFor({ state: 'visible' });
  await page.unroute(secondURL);
  await page.locator('.archive-scroll-status button').click();
  await page.waitForFunction(() => document.documentElement.dataset.archiveReady === 'true');
  assert.ok(await page.locator('.listing-card').count() >= 40);
  await assertPosition(saved);
  console.log('PASS network failure/retry during both scrolling and reload restoration');

  await page.goto(`${origin}/post/ja/`);
  const oldYear = await page.locator('[data-archive-anchor]').last().getAttribute('data-archive-anchor');
  const oldYearURL = await page.locator('[data-archive-anchor]').last().getAttribute('href');
  await page.goto(`${origin}/post/ja/#${oldYear}`);
  await page.waitForURL(url => url.pathname === new URL(oldYearURL, origin).pathname);
  assert.equal(await page.locator(`.listing-year #${oldYear}`).count(), 1);
  await page.goto(`${origin}/weeknotes/2026/`);
  assert.equal(await page.locator('.annual-weeks, .annual-reading-note, .annual-load').count(), 0);
  const indexURL = await page.locator('[data-anchor-index]').getAttribute('data-anchor-index');
  const targets = await (await page.request.get(new URL(indexURL, origin).href)).json();
  const oldest = Object.keys(targets).filter(key => /^\d{8}週$/.test(key)).sort()[0];
  await page.goto(`${origin}/weeknotes/#${encodeURIComponent(oldest)}`);
  await page.waitForURL(url => url.pathname === targets[oldest]);
  assert.equal(await page.locator('.weeknotes-entry-title').first().getAttribute('id'), oldest);
  console.log('PASS removed annual controls and preserved old weekly anchors');

  const noJS = await browser.newContext({ javaScriptEnabled: false });
  await noJS.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  const staticPage = await noJS.newPage();
  for (const [path] of cases) {
    await staticPage.goto(origin + path);
    const link = staticPage.locator('.archive-pagination a[rel="next"]');
    const nextURL = new URL(await link.getAttribute('href'), origin).href;
    await link.click();
    await staticPage.waitForURL(nextURL);
    assert.equal(await staticPage.locator('.archive-pagination a[rel="prev"]').count(), 1);
  }
  await noJS.close();
  console.log('PASS no-JavaScript fallback links');

  const mediaRequests = [];
  page.on('request', request => { if (request.url().endsWith('.mp4')) mediaRequests.push(request.url()); });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`${origin}/games/`);
  await page.waitForTimeout(400);
  assert.equal(mediaRequests.length, 0);
  assert.equal(await page.locator('video[src]').count(), 0);
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.waitForFunction(() => !document.querySelector('video').paused);
  assert.equal(await page.locator('video[src]').count(), 1);
  assert.equal(await page.locator('video').last().getAttribute('poster'), null);
  await page.locator('video').nth(1).scrollIntoViewIfNeeded();
  await page.waitForFunction(() => !document.querySelectorAll('video')[1].paused && document.querySelector('video').paused);
  assert.equal(await page.locator('video[src]').count(), 2);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  console.log('PASS Games: visible autoplay, offscreen pause, deferred media, reduced-motion');
  assert.deepEqual(errors, []);
} catch (error) {
  await saveFailure(browser, 'archives');
  throw error;
} finally {
  await context.close();
  await browser.close();
}
