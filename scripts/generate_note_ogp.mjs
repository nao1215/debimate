// Render the same SVG lettering and background as the homepage into social PNGs.
import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { launchBrowser } from './browser_support.mjs';

const root = path.resolve('public');
const directory = path.join(root, 'assets/note-ogp');
// Only render images referenced by the current site, ignoring stale Hugo outputs.
const referenced = new Set();
async function collect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory() && file !== path.join(root, 'assets')) await collect(file);
    else if (entry.isFile() && entry.name === 'index.html') {
      for (const match of (await readFile(file, 'utf8')).matchAll(/assets\/note-ogp\/([a-f0-9]+)\.png/g)) {
        referenced.add(match[1] + '.html');
      }
    }
  }
}
await collect(root);
const files = [...referenced];
if (!files.length) throw new Error('No note OGP references found');
const browser = await launchBrowser();
try {
  const page = await browser.newPage({ viewport: { width: 960, height: 540 }, deviceScaleFactor: 1 });
  // Resolve all assets against the build artifact, without accessing the network.
  await page.route('**/*', async route => {
    const pathname = decodeURIComponent(new URL(route.request().url()).pathname);
    const file = path.resolve(root, '.' + pathname);
    if (!file.startsWith(root + path.sep)) return route.abort();
    try { await route.fulfill({ path: file }); }
    catch { await route.abort(); }
  });
  for (const name of files) {
    const failures = [];
    const failed = request => failures.push(request.url());
    page.on('requestfailed', failed);
    await page.goto(`https://note-ogp.invalid/assets/note-ogp/${name}`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    if (failures.length) throw new Error(`Missing OGP assets: ${failures.join(', ')}`);
    const overflow = await page.locator('svg text').evaluateAll(elements => elements
      .filter(element => { const box = element.getBBox(); return box.x + box.width > 960 || box.y + box.height > 540; })
      .map(element => element.textContent));
    if (overflow.length) throw new Error(`OGP text overflow: ${overflow.join(', ')}`);
    const output = path.join(directory, name.replace(/\.html$/, '.png'));
    await page.locator('figure').screenshot({ path: output });
    const png = await readFile(output);
    if (png.readUInt32BE(16) !== 960 || png.readUInt32BE(20) !== 540 || (await stat(output)).size < 10000) {
      throw new Error(`Invalid note image: ${output}`);
    }
    page.off('requestfailed', failed);
  }
  console.log(`Generated ${files.length} note OGP images (960 × 540).`);
} finally {
  await browser.close();
}
