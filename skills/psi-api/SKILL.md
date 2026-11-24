---
name: psi-api
description: >-
  Query the Google PageSpeed Insights API v5 (mobile and desktop) in parallel
  for a list of URLs to collect Core Web Vitals lab metrics (FCP, LCP, TBT,
  CLS, Speed Index), CrUX real-user field data, final redirected URLs, and
  failing performance audit issues. Uses Python standard library only (no
  external packages or browser required). Use when the user wants detailed
  PageSpeed API metrics or Core Web Vitals diagnostics.
metadata:
  author: psi-check
  tags:
    - pagespeed
    - performance
    - core-web-vitals
    - api
---

# psi-api

Batch-query the **Google PageSpeed Insights API v5** (mobile + desktop) using [scripts/psi_api.py](scripts/psi_api.py) with Python's standard library only (no `pip` packages or Chrome needed).

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/psi_api.py` | Batch-fetch PSI API v5 mobile & desktop metrics into slim JSON files | `<urls_file> <raw_dir> [--workers 6] [--key-file PATH]` |

## Prerequisites

- **Python 3**
- **Google PageSpeed Insights API key** (from Google Cloud Console), supplied via:
  1. Environment variable `PSI_API_KEY`, or
  2. `--key-file <path>` pointing to a single-line key file

Before running, verify an API key is available. If missing, ask the user to supply `PSI_API_KEY`.

## Usage

1. Prepare a plain-text file with one `http(s)` URL per line.
2. Run the script:
   ```bash
   python3 scripts/psi_api.py <urls_file> <raw_dir> [--workers 6] [--key-file /path/to/key]
   ```
   - `--workers`: parallel request threads (default `6`).
   - Requests gzip + partial `fields` and strips audit `details` (screenshots/thumbnails), saving ~7 KB per file.

## Output Format

One atomically-written JSON file per `(url, strategy)` in `<raw_dir>` named `<md5(url + strategy)>.json`:
- Success: `{"url": "...", "strategy": "mobile|desktop", "data": {"loadingExperience": ..., "lighthouseResult": {"finalUrl": ..., "audits": ...}}}`
- Failure: `{"url": "...", "strategy": "mobile|desktop", "error": "..."}`

## Resuming & Error Handling

- **Resumable**: Files that already contain `"data"` are skipped; files with `"error"` are retried on the next run.
- **`HTTP 400`**: Invalid URL — not retried.
- **`HTTP 401` / `HTTP 403`**: Invalid key, API disabled, or quota exceeded — aborts immediately with exit code `1`.
- **`HTTP 429` / network errors**: Retries up to 4 attempts with backoff.
