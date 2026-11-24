---
name: psi-web
description: >-
  Run Google PageSpeed Insights via the pagespeed.web.dev web UI in headless
  Chrome to capture mobile and desktop performance scores along with permanent
  shareable report links. No API key required. Use when the user wants
  PageSpeed scores with verifiable permanent evidence links for one or more
  URLs.
metadata:
  author: psi-check
  tags:
    - pagespeed
    - performance
    - core-web-vitals
    - chrome
---

# psi-web

Capture mobile and desktop Google PageSpeed Insights performance scores plus **permanent shareable report URLs** using [scripts/psi_web.mjs](scripts/psi_web.mjs).

Because the PageSpeed Insights API does not return a shareable report link, this skill uses local Google Chrome via `playwright-core` to collect official evidence links directly from `pagespeed.web.dev`. **No Google API key is required.**

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/psi_web.mjs` | Run headless Chrome checks on `pagespeed.web.dev` and append JSONL results | `<urls_file> <out_jsonl> [concurrency=3]` |

## Prerequisites

- **Node.js** and **Google Chrome** installed locally (`playwright-core` uses the system Chrome via `channel: 'chrome'`).
- Install Node dependency once inside the `scripts` directory:
  ```bash
  npm --prefix scripts install
  ```

## Usage

1. Prepare a plain-text file with one `http(s)` URL per line.
2. Run the script:
   ```bash
   node scripts/psi_web.mjs <urls_file> <out_jsonl> [concurrency=3]
   ```
   - `concurrency`: number of parallel Chrome tabs (default `3`).
   - Images, media, fonts, and analytics are blocked to speed up checks.

## Output Format

One JSON object per line written to `<out_jsonl>`:

```json
{"url":"https://example.com","mobile":92,"desktop":99,"mobileLink":"https://pagespeed.web.dev/analysis/...?form_factor=mobile","desktopLink":"https://pagespeed.web.dev/analysis/...?form_factor=desktop","reportTime":"Nov 24, 2026, 4:00:00 PM"}
```

## Resuming & Retrying

- **Resumable**: URLs already present in `<out_jsonl>` are skipped automatically. If all URLs are done, Chrome is not launched.
- **Retry failures**: Run the exact same command a second time to retry only failed URLs.
- **Re-test a single URL**: Lab scores vary ±5 per run. Delete that URL's line from `<out_jsonl>` and re-run.

## Troubleshooting

- **`Unable to resolve`**: DNS failure for the target domain; fails immediately without retrying.
- **All URLs time out or fail**: `pagespeed.web.dev` DOM may have changed. Check selector `.lh-exp-gauge__percentage` and report path pattern in [scripts/psi_web.mjs](scripts/psi_web.mjs). Do not replace `page.evaluate` polling with `page.waitForFunction` (blocked by CSP).
