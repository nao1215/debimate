import assert from 'node:assert/strict';
import { launchBrowser, saveFailure } from './browser_support.mjs';

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
    // The video may move into an older batch as new weeknotes are published.
    while (!await section.locator('video').count()) {
      const status = section.locator('.home-list-status');
      assert.ok(await status.locator('button:visible').count(), 'No video found in weeknote batches');
      const count = await section.locator('.post-entry').count();
      await status.scrollIntoViewIfNeeded();
      await page.waitForFunction(n => document.querySelectorAll('.home-weeknotes .post-entry').length > n, count);
    }
    const video = section.locator('video').first();
    await video.scrollIntoViewIfNeeded();
    await page.waitForFunction(() => {
      const video = document.querySelector('.home-weeknotes video');
      return !video.paused && video.currentTime > 0 && video.videoWidth > 0;
    });
    await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
    await page.waitForFunction(() => document.querySelector('.home-weeknotes video').paused);
    assert.deepEqual(errors, []);
    console.log(`PASS ${width}px: home weeknote video loads, plays frames in viewport, pauses offscreen`);
    await context.close();
  }
} catch (error) {
  await saveFailure(browser, 'home-media');
  throw error;
} finally { await browser.close(); }
