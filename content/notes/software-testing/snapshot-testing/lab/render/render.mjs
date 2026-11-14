// Render mermaid sources in headless Chrome with mermaid's default (strict)
// security level, and print for each one whether mermaid accepted it and which
// text the drawing contains. With --png DIR, also save a screenshot per source.
//
//   node render.mjs [--png DIR] a.mmd b.mmd ...
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { basename, dirname, join } from "node:path";
import puppeteer from "puppeteer";

const require = createRequire(import.meta.url);
const mermaidJS = join(dirname(require.resolve("mermaid/package.json")), "dist", "mermaid.min.js");

const args = process.argv.slice(2);
let pngDir = null;
if (args[0] === "--png") {
  pngDir = args[1];
  args.splice(0, 2);
}

const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const page = await browser.newPage();
await page.setViewport({ width: 520, height: 420, deviceScaleFactor: 2 });
await page.setContent("<!doctype html><html><body style='margin:0;background:#fff'><div id=out></div></body></html>");
await page.addScriptTag({ path: mermaidJS });
await page.evaluate(() => window.mermaid.initialize({ startOnLoad: false }));

for (const file of args) {
  const source = readFileSync(file, "utf8");
  const result = await page.evaluate(async (src) => {
    const out = document.getElementById("out");
    out.innerHTML = "";
    try {
      const { svg } = await window.mermaid.render("d" + Math.random().toString(36).slice(2), src);
      out.innerHTML = svg;
      const texts = [...out.querySelectorAll("text, foreignObject, span, p")]
        .map((e) => e.textContent.trim())
        .filter((t) => t !== "");
      return { ok: true, texts: [...new Set(texts)] };
    } catch (e) {
      out.innerHTML = `<pre style="font:14px monospace;color:#b00;padding:12px;white-space:pre-wrap">${String(e.message || e).replace(/</g, "&lt;")}</pre>`;
      return { ok: false, error: String(e.message || e).split("\n").slice(0, 4).join("\n") };
    }
  }, source);
  console.log(`== ${basename(file)}`);
  console.log(JSON.stringify(result, null, 2));
  if (pngDir) {
    const el = await page.$("#out > *");
    await el.screenshot({ path: join(pngDir, basename(file).replace(/\.mmd$/, ".png")) });
  }
}
await browser.close();
