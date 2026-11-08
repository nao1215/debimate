import assert from 'node:assert/strict';
import { launchBrowser, saveFailure, waitForImage } from './browser_support.mjs';

const origin = new URL(process.argv[2] || 'http://127.0.0.1:8138').origin;
const browser = await launchBrowser();
try {
  for (const width of [390, 1440]) {
    const context = await browser.newContext({ viewport: { width, height: 844 }, reducedMotion: 'no-preference' });
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin);
    const section = page.locator('.home-weeknotes');
    // Include deferred home cards when checking image animation.
    const status = section.locator('.home-list-status');
    const total = Number(await status.getAttribute('data-total'));
    while (await section.locator('.post-entry').count() < total) {
      const count = await section.locator('.post-entry').count();
      // Scroll-triggered loading may finish between locating and clicking.
      await status.locator('button').evaluate(button => {
        if (!button.hidden && !button.disabled) button.click();
      });
      await page.waitForFunction(n => document.querySelectorAll('.home-weeknotes .post-entry').length > n, count);
    }
    assert.equal(await page.locator('video').count(), 0);
    const demos = section.locator('img[src*="-demo"]');
    const count = await demos.count();
    assert.ok(count > 0, 'No animated demo images found in weeknote cards');
    for (const demo of await demos.all()) {
      await demo.scrollIntoViewIfNeeded();
      await waitForImage(demo);
      const first = await demo.screenshot();
      let changed = false;
      for (let attempt = 0; attempt < 8 && !changed; attempt++) {
        await page.waitForTimeout(500);
        changed = !first.equals(await demo.screenshot());
      }
      assert.ok(changed, `Card image does not animate: ${await demo.getAttribute('src')}`);
    }
    assert.deepEqual(errors, []);
    console.log(`PASS ${width}px: all ${count} home demo images load and animate without video players`);
    await context.close();
  }
} catch (error) {
  await saveFailure(browser, 'home-media');
  throw error;
} finally { await browser.close(); }
