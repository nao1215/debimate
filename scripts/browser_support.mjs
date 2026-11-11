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

// Space のスクロールはアニメーションで進み、CI では始まりが遅れる事がある。
// 押してから決まった時間で測ると途中の値を拾う（2026-11-10 に 738px 動く所を
// 415px・491px と測って archive_scroll が落ちた）。止まってから測る。
// 末尾に当たって短く止まった場合は、止まった位置がそのまま短い値として残る
export async function waitForScrollToSettle(page, timeout = 3000) {
  await page.waitForFunction(() => new Promise(resolve => {
    const y = scrollY;
    requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(() => resolve(scrollY === y), 100)));
  }), null, { timeout });
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
