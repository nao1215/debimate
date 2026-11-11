// Guard page-scroll continuity, not machine-dependent FPS. Run on the built site.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { launchBrowser, saveFailure, waitForScrollToSettle } from './browser_support.mjs';
const origin = new URL(process.argv[2] || 'http://127.0.0.1:8138').origin;
const browser = await launchBrowser();
const results = [];
try {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 1440, height: 1200 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport });
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) return route.abort();
      if (url.pathname.startsWith('/assets/home/')) await new Promise(resolve => setTimeout(resolve, 200));
      return route.continue();
    });
    const page = await context.newPage();
    await page.goto(origin);
    // Let initial bounded preloading settle; no per-scroll wait for requests.
    await page.waitForTimeout(1000);
    const initialCards = await page.locator('.home-columns .post-entry').count();
    assert.ok(initialCards <= 72, `Unbounded initial preloading: ${initialCards} cards`);
    const steps = [];
    results.push({ viewport, delayMs: 200, initialCards, steps });
    for (let i = 0; i < 12; i++) {
      const before = await page.evaluate(() => ({ y: scrollY, remaining: document.documentElement.scrollHeight - innerHeight - scrollY }));
      await page.keyboard.press('Space');
      await page.waitForTimeout(350);
      await waitForScrollToSettle(page);
      const after = await page.evaluate(() => scrollY);
      const step = { remaining: before.remaining, distance: after - before.y };
      steps.push(step);
      assert.ok(step.distance >= viewport.height * 0.75,
        `${viewport.width}×${viewport.height}, Space ${i + 1}: moved ${step.distance}px; remaining before key ${step.remaining}px`);
    }
    const links = await page.locator('.home-columns .entry-link').evaluateAll(nodes => nodes.map(node => node.href));
    assert.equal(new Set(links).size, links.length, 'Duplicate cards after preloading');
    console.log(`PASS ${viewport.width}×${viewport.height}: 12 Space presses with 200ms batch latency, no shortened scrolls`);
    await context.close();
  }
} catch (error) {
  await saveFailure(browser, 'home_scroll');
  throw error;
} finally {
  await mkdir('reports/browser', { recursive: true });
  await writeFile('reports/browser/home-scroll.json', JSON.stringify(results, null, 2) + '\n');
  await browser.close();
}
