import assert from 'node:assert/strict';
import { launchBrowser, saveFailure } from './browser_support.mjs';

const origin = new URL(process.argv[2] || 'http://127.0.0.1:8138').origin;
const browser = await launchBrowser();
try {
  for (const width of [390, 1440]) {
    const context = await browser.newContext({ viewport: { width, height: 844 } });
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let requests = 0;
    let fail = true;
    await page.route('**/index.json', route => {
      requests++;
      if (fail) {
        fail = false;
        return route.fulfill({ status: 503, body: 'Unavailable' });
      }
      return route.continue();
    });
    await page.goto(origin + '/search/');
    // Negative assertions need to wait longer than the 200ms debounce window.
    await page.waitForTimeout(400);
    assert.equal(requests, 0);
    const input = page.locator('#searchInput');
    await input.dispatchEvent('compositionstart');
    await input.fill('更新');
    await page.waitForTimeout(300);
    assert.equal(requests, 0);
    await input.dispatchEvent('compositionend');
    await page.locator('#searchRetry').waitFor({ state: 'visible' });
    assert.equal(requests, 1);
    await page.locator('#searchRetry').click();
    await page.waitForFunction(() => document.querySelectorAll('#searchResults li').length > 0);
    assert.equal(requests, 2);
    await input.fill('g');
    await input.fill('gu');
    await input.fill('gup');
    await page.waitForFunction(() => document.querySelector('#searchStatus').textContent.includes('「gup」の検索結果'));
    assert.equal(requests, 2);
    assert.ok(await page.locator('#searchResults li').count() <= 30);
    await input.press('Escape');
    assert.equal(await page.locator('#searchResults li').count(), 0);
    await page.waitForTimeout(250);
    assert.equal(requests, 2);
    assert.deepEqual(errors, []);
    console.log(`PASS ${width}px: zero eager index requests, IME, retry button, cache reuse, clear query`);
    await context.close();
  }
} catch (error) {
  await saveFailure(browser, 'search');
  throw error;
} finally { await browser.close(); }
