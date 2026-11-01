import { mkdir } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');

export function launchBrowser() {
  return chromium.launch({
    // Default to the version installed by Playwright; allow a local Chrome override.
    executablePath: process.env.CHROME_PATH || undefined,
    headless: true,
    args: ['--no-sandbox'],
  });
}

export function localURL(href, origin) {
  const url = new URL(href, origin);
  return origin + url.pathname + url.search + url.hash;
}

export async function saveFailure(browser, suite) {
  await mkdir('reports/browser', { recursive: true });
  let index = 0;
  for (const context of browser.contexts()) {
    for (const page of context.pages()) {
      await page.screenshot({ path: `reports/browser/${suite}-${index++}.png`, timeout: 5000 })
        .catch(error => console.error('Could not capture screenshot:', error.message));
    }
  }
}
