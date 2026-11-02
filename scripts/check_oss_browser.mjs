import { launchBrowser, saveFailure } from './browser_support.mjs';
import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
const catalog = JSON.parse(await readFile('data/oss_catalog.json', 'utf8'));
const origin = new URL(process.argv[2] || 'http://127.0.0.1:8138').origin;
const browser = await launchBrowser();
try {
  for (const width of [1440, 390, 320]) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${origin}/oss/`);
    await page.locator('[data-oss-filters]:visible').waitFor();
    const projects = page.locator('[data-oss-project]:visible');
    assert.equal(await projects.count(), 4);
    const menu = (await page.locator('#menu a').allTextContents()).map(text => text.trim());
    assert.equal(menu[menu.indexOf('Weeknotes') + 1], 'OSS');
    assert.equal(menu[menu.indexOf('OSS') + 1], 'Games');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(await projects.locator('h3').allTextContents(), [...catalog.projects].sort((a, b) => b.stars - a.stars).slice(0, 4).map(p => p.name));
    assert.equal(await projects.locator('.oss-card-header').count(), 4);
    assert.equal(await projects.locator('a[href$="#readme"]').count(), 4);
    assert.equal(await projects.getByRole('link', { name: '紹介記事 →' }).count(), [...catalog.projects].sort((a, b) => b.stars - a.stars).slice(0, 4).filter(p => p.article).length);
    await page.getByLabel('言語', { exact: true }).selectOption('Go');
    assert.equal(await page.getByRole('searchbox').inputValue(), '');
    assert.equal(await projects.count(), catalog.projects.filter(p => p.language === 'Go').length);
    assert.equal(await page.getByRole('button', { name: 'すべて', exact: true }).getAttribute('aria-pressed'), 'true');
    await page.getByRole('button', { name: 'リセット' }).click();
    await page.waitForFunction(() => document.querySelector('select[name="language"]').value === '');
    await page.getByRole('button', { name: 'すべて', exact: true }).click();
    assert.equal(await projects.count(), catalog.projects.length);
    await page.getByLabel('言語', { exact: true }).selectOption('Shell');
    assert.equal(await projects.count(), catalog.projects.filter(p => p.language === 'Shell').length);
    await page.getByRole('button', { name: 'リセット' }).click();
    await page.waitForFunction(() => document.querySelectorAll('[data-oss-project]:not([hidden])').length === document.querySelectorAll('[data-oss-project]').length);
    const search = page.getByRole('searchbox');
    await search.fill('ＳＱＬ');
    assert.ok(await projects.count() >= 3);
    await page.getByLabel('言語', { exact: true }).selectOption('Gleam');
    assert.deepEqual(await projects.locator('h3').allTextContents(), ['sqlode']);
    await search.fill('no-match-123456');
    assert.equal(await projects.count(), 0);
    assert.equal(await page.locator('[data-oss-empty]').isVisible(), true);
    await page.getByRole('button', { name: 'リセット' }).click();
    await page.waitForFunction(() => !document.querySelector('[data-oss-empty]').checkVisibility());
    assert.equal(await projects.count(), catalog.projects.length);
    await page.locator('[data-oss-tabs] [data-category="games"]').click();
    assert.equal(await projects.count(), catalog.projects.filter(p => p.category === 'games').length);
    assert.equal(await page.locator('[data-oss-games]').isVisible(), true);
    await page.getByRole('button', { name: '人気のある OSS', exact: true }).click();
    assert.equal(await projects.count(), 4);
    assert.equal(await page.locator('.oss-support').count(), 0);
    await page.evaluate(() => window.scrollTo(0, 0));
    await mkdir('reports/browser', { recursive: true });
    await page.screenshot({ path: `reports/browser/oss-${width}.png`, fullPage: width === 390 });
    assert.deepEqual(errors, []);
    console.log(`PASS OSS ${width}px: menu, filtering, reset, category navigation, images, overflow`);
    await context.close();
  }
  const context = await browser.newContext({ javaScriptEnabled: false });
  await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  const page = await context.newPage();
  await page.goto(`${origin}/oss/`);
  assert.equal(await page.locator('[data-oss-project]:visible').count(), catalog.projects.length);
  assert.equal(await page.locator('[data-oss-filters]').isVisible(), false);
  for (const project of catalog.projects.filter(project => project.website)) {
    assert.equal(await page.locator(`#project-${project.name}`).getByRole('link', { name: '公式サイト ↗' }).getAttribute('href'), project.website);
  }
  assert.equal(await page.locator('a[href="https://github.com/sponsors/nao1215"]').count(), 1);
  for (const href of await page.locator('main a').evaluateAll(links => links.map(link => link.href))) {
    const url = new URL(href);
    if (url.origin === origin && !url.hash) assert.equal((await context.request.get(url.href)).ok(), true, href);
  }
  console.log('PASS OSS without JavaScript: full catalog, Sponsors, article links');
  await context.close();
} catch (error) {
  await saveFailure(browser, 'oss');
  throw error;
} finally { await browser.close(); }
