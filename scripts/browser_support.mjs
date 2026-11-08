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

export async function waitForImage(image) {
  // Lazy images with sizes="auto" may select a new srcset candidate after
  // scrolling/layout. That cancels an in-flight decode(), even for valid images.
  // Retry the current source; broken images still fail within the time limit.
  await image.page().waitForFunction(async img => {
    if (!img.complete || img.naturalWidth === 0) return false;
    const source = img.currentSrc;
    try {
      await img.decode();
      return img.currentSrc === source && img.complete && img.naturalWidth > 0;
    } catch {
      return false;
    }
  }, await image.elementHandle(), { timeout: 10_000 });
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
