// Run PageSpeed Insights via the pagespeed.web.dev web UI (headless Chrome)
// to get the PERMANENT shareable report link + mobile/desktop performance score.
// The PSI API does not return a report link, so this is the evidence source.
//
// Usage: node psi_web.mjs <urls.txt> <out.jsonl> [concurrency=3]
// Output: one JSON per line: {url, mobile, desktop, mobileLink, desktopLink, reportTime}
// Resumable: URLs already in out.jsonl are skipped (Chrome is not even started if nothing is left).
import { chromium } from 'playwright-core';
import fs from 'fs';

const [urlsFile, out, concArg = '3'] = process.argv.slice(2);
if (!urlsFile || !out) { console.error('Usage: node psi_web.mjs <urls.txt> <out.jsonl> [concurrency]'); process.exit(1); }

const ATTEMPTS = 3;
const RESULT_TIMEOUT = 180_000;        // PSI usually needs 30-90 s for mobile + desktop
const GAUGE = '.lh-exp-gauge__percentage';
const BLOCK_TYPES = new Set(['image', 'media', 'font']);   // not needed to read scores/links
const BLOCK_HOSTS = /google-analytics\.com|googletagmanager\.com|doubleclick\.net/;

const lines = f => (fs.existsSync(f) ? fs.readFileSync(f, 'utf8').split('\n').map(s => s.trim()).filter(Boolean) : []);
const done = new Set();
for (const l of lines(out)) { try { done.add(JSON.parse(l).url); } catch { /* skip partial line */ } }
const urls = [...new Set(lines(urlsFile))];
const queue = urls.filter(u => !done.has(u));
const total = queue.length;
console.log(`${total} to run, ${urls.length - total} already done`);
if (!total) process.exit(0);

// channel 'chrome' = uses installed Google Chrome.app (no Playwright browser download needed)
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const major = browser.version().split('.')[0];  // non-headless UA matching the real Chrome version
const ctx = await browser.newContext({
  userAgent: `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${major}.0.0.0 Safari/537.36`,
});
await ctx.route('**/*', r => (BLOCK_TYPES.has(r.request().resourceType()) || BLOCK_HOSTS.test(r.request().url())
  ? r.abort() : r.continue()));

let finished = 0, failed = 0;

// PSI redirects to /analysis/<slug>/<id> and renders 2 performance gauges: [mobile, desktop].
// Polled with page.evaluate: pagespeed.web.dev's CSP blocks page.waitForFunction (no 'unsafe-eval').
async function waitForReport(p) {
  const deadline = Date.now() + RESULT_TIMEOUT;
  while (Date.now() < deadline) {
    const s = await p.evaluate(sel => {
      const report = /\/analysis\/.+\/[a-z0-9]+/i.test(location.pathname);
      const g = [...document.querySelectorAll(sel)].map(x => x.textContent.trim());
      if (report && g.length >= 2 && g.every(x => /^\d+$/.test(x)))
        return { g, base: location.origin + location.pathname,
                 ts: (document.body.innerText.match(/Report from [^\n]+/) || [''])[0] };
      // still on /analysis (no report id) and PSI shows an error message instead of a report
      const m = !report && document.body.innerText.match(/(Unable to resolve|Lighthouse returned error|Something went wrong)[^\n]*/i);
      return m ? { error: m[0] } : null;
    }, GAUGE).catch(() => null);   // navigation in progress
    if (s?.error) throw Object.assign(new Error('PSI: ' + s.error), { fatal: /Unable to resolve/i.test(s.error) });
    if (s) return s;
    await p.waitForTimeout(1000);
  }
  throw new Error(`no scores after ${RESULT_TIMEOUT / 1000}s at ${p.url()}`);
}

async function run(url) {
  let err = '';
  for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
    const p = await ctx.newPage();
    try {
      await p.goto('https://pagespeed.web.dev/analysis?url=' + encodeURIComponent(url) + '&form_factor=mobile',
        { waitUntil: 'domcontentloaded', timeout: 60_000 });
      const { g, base, ts } = await waitForReport(p);
      const rec = {
        url, mobile: +g[0], desktop: +g[1],
        mobileLink: base + '?form_factor=mobile', desktopLink: base + '?form_factor=desktop',
        reportTime: ts.replace('Report from ', ''),
      };
      fs.appendFileSync(out, JSON.stringify(rec) + '\n');
      console.log(`ok [${++finished}/${total}]`, rec.mobile, rec.desktop, url);
      return;
    } catch (e) {
      err = e.message.split('\n')[0];
      if (e.fatal) break;  // e.g. DNS failure: retrying won't help
      console.log('retry', attempt, url, err);
      if (attempt < ATTEMPTS) await p.waitForTimeout(3000 * attempt);
    } finally {
      await p.close().catch(() => {});
    }
  }
  failed++;
  console.log(`FAIL [${++finished}/${total}]`, url, err);
}

const workers = Math.max(1, Math.min(+concArg || 3, total));
await Promise.all(Array.from({ length: workers }, async () => { while (queue.length) await run(queue.shift()); }));
await browser.close();
console.log(`web done: ${total - failed} ok, ${failed} failed`);
