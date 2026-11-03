// Exercise the real production pages, including footer caching and CSS.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { launchBrowser, saveFailure } from './browser_support.mjs';

const origin = new URL(process.argv[2] || 'http://127.0.0.1:8138').origin;
const browser = await launchBrowser();
try {
  for (const width of [390, 1440]) {
    for (const path of ['/weeknotes/', '/post/', '/']) {
      const html = await readFile(`public${path}index.html`, 'utf8');
      const date = html.match(/data-new-date=["']?(\d{4}-\d{2}-\d{2})/)?.[1];
      assert.ok(date, `${path}: missing badge date`);
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
      const page = await context.newPage();
      // Use a real article's creation day so the regression never ages out.
      await page.clock.install({ time: new Date(`${date}T12:00:00+09:00`) });
      await page.goto(origin + path);
      const badge = page.locator(`[data-new-date="${date}"]`).first();
      await badge.waitFor({ state: 'visible', timeout: 5000 });
      const position = await badge.evaluate(node => {
        const card = node.closest('article').getBoundingClientRect();
        const rect = node.getBoundingClientRect();
        return { right: card.right - rect.right, bottom: card.bottom - rect.bottom };
      });
      assert.ok(Math.abs(position.right - 13) <= 2, `${path}: right offset ${position.right}`);
      assert.ok(Math.abs(position.bottom - 13) <= 2, `${path}: bottom offset ${position.bottom}`);
      const days = path === '/weeknotes/' ? 21 : 14;
      assert.equal(await badge.getAttribute('data-new-days'), String(days));
      const start = Date.parse(`${date}T00:00:00+09:00`);
      await page.clock.setSystemTime(new Date(start + days * 86400000 - 1000));
      await page.evaluate(() => window.dispatchEvent(new Event('pageshow')));
      assert.equal(await badge.isVisible(), true, `${path}: expires too early`);
      await page.clock.setSystemTime(new Date(start + days * 86400000));
      await page.evaluate(() => window.dispatchEvent(new Event('pageshow')));
      assert.equal(await badge.isVisible(), false, `${path}: did not expire`);
      console.log(`PASS ${width}px ${path}: visible, bottom-right, ${days}-day expiry`);
      await context.close();
    }
  }
} catch (error) {
  await saveFailure(browser, 'new_badges');
  throw error;
} finally {
  await browser.close();
}
