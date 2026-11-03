// Usage: node scripts/check_home_browser.mjs http://127.0.0.1:8138
// Requires Playwright; PLAYWRIGHT_MODULE can point to a temporary installation.
import { launchBrowser, saveFailure, localURL } from './browser_support.mjs';
import assert from 'node:assert/strict';
const browser = await launchBrowser();
const origin = new URL(process.argv[2] || 'http://127.0.0.1:8138').origin;
try {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport });
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin);
    await page.waitForTimeout(300);
    const section = page.locator('.home-posts');
    const initial = await section.locator('.post-entry').count();
    assert.ok(initial >= 6 && initial <= 36, `Initial preload must be bounded: ${initial}`);
    const buttons = section.locator('button');
    // Scroll to the end of the first list; automatic fetch must add cards.
    await buttons.scrollIntoViewIfNeeded();
    await page.waitForFunction(count => document.querySelectorAll('.home-posts .post-entry').length > count, initial);
    const before = await section.locator('.post-entry').count();
    await page.evaluate(() => window.scrollTo(0, 1000));
    await page.waitForTimeout(200);
    await page.reload();
    await page.waitForTimeout(500);
    await page.waitForFunction(count => document.querySelectorAll('.home-posts .post-entry').length >= count, before);
    await page.waitForFunction(() => Math.abs(window.scrollY - 1000) < 10);
    const href = await section.locator('.post-entry .entry-link').first().getAttribute('href');
    await page.goto(localURL(href, origin));
    await page.goBack();
    await page.waitForFunction(count => document.querySelectorAll('.home-posts .post-entry').length >= count, before);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(errors, []);
    console.log(`PASS ${viewport.width}px: scroll, reload, back, no overflow/errors`);
    await context.close();
  }
  const noJS = await browser.newContext({ javaScriptEnabled: false });
  await noJS.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  const staticPage = await noJS.newPage();
  await staticPage.goto(origin);
  assert.equal(await staticPage.locator('.home-columns .post-entry').count(), 12);
  assert.equal(await staticPage.getByRole('link', { name: '全記事 →' }).count(), 1);
  assert.equal(await staticPage.locator('.home-list-status button:visible').count(), 0);
  await noJS.close();
  console.log('PASS JavaScript disabled: cards and archive links remain');
  const context = await browser.newContext();
  await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  // Disable automatic observation to exercise explicit retries deterministically.
  await context.addInitScript(() => { delete window.IntersectionObserver; });
  let fail = true;
  await context.route('**/assets/home/*', route => fail ? route.fulfill({ status: 503, body: 'Unavailable' }) : route.continue());
  const page = await context.newPage();
  await page.goto(origin);
  const section = page.locator('.home-posts');
  const total = Number(await section.locator('.home-list-status').getAttribute('data-total'));
  await section.getByRole('button', { name: 'もっと見る' }).click();
  await section.getByRole('button', { name: '再試行' }).waitFor();
  assert.equal(await section.locator('.post-entry').count(), 6);
  fail = false;
  await section.getByRole('button', { name: '再試行' }).click();
  await page.waitForFunction(() => document.querySelectorAll('.home-posts .post-entry').length === 12);
  // Follow every remaining batch through the real DOM.
  while (await section.locator('button:visible').count()) {
    const count = await section.locator('.post-entry').count();
    await section.locator('button').click();
    await page.waitForFunction(n => document.querySelectorAll('.home-posts .post-entry').length > n, count);
  }
  const urls = await section.locator('.entry-link').evaluateAll(links => links.map(a => a.href));
  assert.equal(urls.length, total);
  assert.equal(new Set(urls).size, urls.length);
  console.log(`PASS failed request/retry and all ${total} posts without duplicates`);
  // A cached homepage may still point at batches removed by a new deployment.
  let homeRequests = 0;
  await context.route(origin + '/', async route => {
    homeRequests++;
    const response = await route.fetch();
    let body = await response.text();
    if (homeRequests === 1) {
      const original = body;
      body = body.replace(/\/assets\/home\/notes-2\.[a-f0-9]+\.json/g, '/assets/home/obsolete-notes.json');
      assert.notEqual(body, original, 'Expected homepage note batch URL');
    }
    await route.fulfill({ response, body });
  });
  await context.route('**/assets/home/obsolete-notes.json', route => route.fulfill({ status: 404, body: 'Removed' }));
  await page.goto(origin);
  await page.locator('.home-notes').getByRole('button', { name: 'もっと見る' }).click();
  await page.waitForFunction(() => !document.querySelector('.home-notes .home-list-status').dataset.next.includes('obsolete'));
  assert.equal(homeRequests, 3, 'Old document, freshness check, then one reload');
  await page.locator('.home-notes').getByRole('button', { name: 'もっと見る' }).click();
  await page.waitForFunction(() => document.querySelectorAll('.home-notes .post-entry').length === 6);
  console.log('PASS stale note batch after deployment: refresh and successful loading');

  await context.close();
} catch (error) {
  await saveFailure(browser, 'home');
  throw error;
} finally { await browser.close(); }
