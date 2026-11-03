// Exercise real pagination boundaries; long annual pages need more than 12
// Space presses from the top to reach the first additional request.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { launchBrowser, saveFailure } from './browser_support.mjs';
const origin = new URL(process.argv[2] || 'http://127.0.0.1:8138').origin;
const browser = await launchBrowser();
const results = [];
try {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 1440, height: 1200 }, { width: 390, height: 844 }]) {
    for (const path of ['/post/', '/post/ja/', '/weeknotes/', '/weeknotes/2026/']) {
      const context = await browser.newContext({ viewport });
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin !== origin) return route.abort();
        if (route.request().resourceType() === 'fetch' && /\/page\/\d+\//.test(url.pathname)) {
          await new Promise(resolve => setTimeout(resolve, 200));
        }
        return route.continue();
      });
      const page = await context.newPage();
      const errors = [];
      const fetchedPages = new Set();
      page.on('response', response => {
        if (response.ok() && response.request().resourceType() === 'fetch' && /\/page\/\d+\//.test(new URL(response.url()).pathname)) fetchedPages.add(response.url());
      });
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(origin + path);
      await page.waitForFunction(() => document.documentElement.dataset.archiveReady === 'true');
      const steps = [];
      results.push({ viewport, path, delayMs: 200, steps });
      boundaries: for (let boundary = 0; boundary < 3; boundary++) {
        if (await page.locator('.archive-scroll-status [role="status"]').textContent() === 'すべて読み込みました') break;
        const count = await page.locator('.listing-card, .weeknotes-entry').count();
        // Start outside the old 500px margin, but inside a two-screen buffer.
        await page.locator('.archive-scroll-status').evaluate(node => {
          scrollTo({ top: scrollY + node.getBoundingClientRect().top - innerHeight * 2.4, behavior: 'instant' });
        });
        await page.waitForTimeout(500);
        for (let key = 0; key < 3; key++) {
          const before = await page.evaluate(() => ({ y: scrollY, remaining: document.documentElement.scrollHeight - innerHeight - scrollY }));
          // Reaching the real end of a finite archive is not a loading stall.
          if (before.remaining < viewport.height && await page.locator('.archive-scroll-status [role="status"]').textContent() === 'すべて読み込みました') break boundaries;
          await page.keyboard.press('Space');
          await page.waitForTimeout(350);
          const distance = await page.evaluate(y => scrollY - y, before.y);
          steps.push({ boundary, key, remaining: before.remaining, distance });
          assert.ok(distance >= viewport.height * 0.75,
            `${path} ${viewport.width}×${viewport.height}, boundary ${boundary + 1}, Space ${key + 1}: ${distance}px (remaining ${before.remaining}px)`);
        }
        assert.ok(await page.locator('.listing-card, .weeknotes-entry').count() > count, `${path}: did not load another page`);
      }
      assert.ok(fetchedPages.size >= 3, `${path}: must exercise at least 3 actual pagination requests`);
      assert.ok(steps.length >= 3, `${path}: must exercise multiple Space presses`);
      const urls = await page.locator('.listing-card-link').evaluateAll(nodes => nodes.map(node => node.href));
      assert.equal(new Set(urls).size, urls.length, `${path}: duplicate cards`);
      assert.deepEqual(errors, []);
      console.log(`PASS ${path} ${viewport.width}×${viewport.height}: ${fetchedPages.size} additional pages, 200ms latency, no shortened Space scrolls`);
      await context.close();
    }
  }
} catch (error) {
  await saveFailure(browser, 'archive_scroll');
  throw error;
} finally {
  await mkdir('reports/browser', { recursive: true });
  await writeFile('reports/browser/archive-scroll.json', JSON.stringify(results, null, 2) + '\n');
  await browser.close();
}
