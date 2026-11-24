<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/psi-check-banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/psi-check-banner-light.svg">
    <img src="assets/psi-check-banner-light.svg" alt="psi-check" width="100%" />
  </picture>
</p>

<div align="center">

# PageSpeed Insights Skills for AI Agents

<code>npx skills@latest add fadhilafif98/psi-check</code>

[Why](#why-use-it) · [Install](#install) · [Usage](#usage) · [Skills](#skills) · [Output Columns](#output-columns) · [Proving It Works](#proving-it-works) · [FAQ](#faq)

[![Skills](https://img.shields.io/badge/skills-3_modular-111318?style=flat-square)](#skills)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?style=flat-square&logo=nodedotjs&logoColor=white)](skills/psi-web/scripts/package.json)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](skills/psi-api/scripts/psi_api.py)
[![Metrics](https://img.shields.io/badge/Metrics-CWV_%C2%B7_CrUX_%C2%B7_Evidence_Links-0CCE6B?style=flat-square)](#output-columns)
[![SkillEvaluator](https://img.shields.io/badge/SkillEvaluator-Grade_A-111318?style=flat-square)](#proving-it-works)

</div>

---

**psi-check** turns an AI coding agent into a batch **Google PageSpeed Insights** auditor. Instead of one monolithic script, it ships **3 independent, composable skills** so you install only what you need: capture **permanent shareable `pagespeed.web.dev` evidence links** without an API key (`psi-web`), query **PSI API v5** for full Core Web Vitals, CrUX field data, and failing audit issues using Python stdlib only (`psi-api`), or extract URLs from an Excel workbook and write back a formatted, formula-driven report tab (`psi-xlsx`).

## Why use it

Google's PageSpeed Insights API gives you detailed lab metrics, but **never returns a shareable report link**. Meanwhile, clicking through `pagespeed.web.dev` manually for 30+ URLs and copying numbers into Excel is slow, error-prone, and impossible to resume when a tab times out.

These 3 skills split the workflow into clean, resumable building blocks:

```text
Extract (.xlsx) → PSI Web (permanent links + scores) + PSI API (CWV + CrUX + issues) → Report (.xlsx)
```

- **Pick only what you need.** Need just a permanent evidence link for one URL without setting up GCP? Install `psi-web` alone. Need pure API diagnostics without Chrome? Install `psi-api` alone. Need Excel reporting? Add `psi-xlsx`.
- **Permanent evidence links, no API key required (`psi-web`).** Launches your installed Google Chrome via `playwright-core`, blocks images/fonts/analytics for speed, polls safely without `eval` (CSP-compliant), and records both mobile and desktop `/analysis/...` shareable links.
- **Zero-dependency API client (`psi-api`).** Uses Python's standard library (`http.client.HTTPSConnection`), sends your API key via the `X-Goog-Api-Key` header (never in query URLs), requests gzip + partial `fields`, and strips screenshots to save slim ~7 KB JSON files atomically.
- **Resumable by design.** Interrupted halfway through 100 URLs? Re-run the exact same command—already-completed URLs in `psi_web.jsonl` and `raw/*.json` are skipped automatically, while failures retry cleanly.
- **Client-ready Excel output (`psi-xlsx`).** Writes a formatted tab with live `Old Score` formulas, mobile delta (`+0;-0;0`), `PASS`/`FAIL` rules against your target, conditional formatting (`≥90` green, `50–89` yellow, `<50` red), clickable report hyperlinks, and a bottom summary table.

## Install

Install interactively and choose which skills to add:

```bash
npx skills@latest add fadhilafif98/psi-check
```

Or install individual skills directly:

```bash
npx skills@latest add fadhilafif98/psi-check --skill psi-web
npx skills@latest add fadhilafif98/psi-check --skill psi-api
npx skills@latest add fadhilafif98/psi-check --skill psi-xlsx
```

### Manual install

Clone the repository and symlink whichever skills you want into your agent's skills directory (e.g. `~/.agents/skills` or `~/.claude/skills`):

```bash
ln -s "$PWD/skills/psi-web"  ~/.agents/skills/psi-web
ln -s "$PWD/skills/psi-api"  ~/.agents/skills/psi-api
ln -s "$PWD/skills/psi-xlsx" ~/.agents/skills/psi-xlsx
```

Start a new session afterwards so your agent loads the skills.

**Requirements per skill:**
- `psi-web`: Node.js 18+, local Google Chrome, `npm --prefix skills/psi-web/scripts install` (once). **No API key.**
- `psi-api`: Python 3.9+ (stdlib only) + your own Google PageSpeed Insights API key via `PSI_API_KEY` or `--key-file`.
- `psi-xlsx`: Python 3.9+ with `openpyxl` (`pip install openpyxl`).

## Usage

Ask your agent directly in natural language:

```text
check PageSpeed mobile and desktop scores with permanent report links for https://example.com
```

```text
run psi-api to audit Core Web Vitals and top mobile issues for the URLs in urls.txt
```

```text
extract URLs from audit.xlsx, run psi-web and psi-api, and write the report tab back to audit.xlsx
```

Or chain all 3 scripts directly from the terminal:

```bash
# 1. Extract unique URLs from Excel (psi-xlsx)
python3 skills/psi-xlsx/scripts/xlsx_tool.py extract "audit.xlsx" urls.txt

# 2. Run web evidence + API diagnostics (independently or in parallel)
node skills/psi-web/scripts/psi_web.mjs urls.txt psi_web.jsonl 3
PSI_API_KEY="YOUR_KEY" python3 skills/psi-api/scripts/psi_api.py urls.txt raw/

# 3. Write formatted result tab back to Excel (psi-xlsx)
python3 skills/psi-xlsx/scripts/xlsx_tool.py write "audit.xlsx" psi_web.jsonl raw/ --target 80
```

## Skills

| Skill | Role | Pick it for |
|---|---|---|
| [`psi-web`](skills/psi-web/SKILL.md) | Web UI Evidence (Headless Chrome) | Mobile/desktop scores + permanent shareable `pagespeed.web.dev` report links—**no API key needed** |
| [`psi-api`](skills/psi-api/SKILL.md) | API Diagnostics (PSI v5) | Detailed Core Web Vitals (FCP, LCP, TBT, CLS, SI), CrUX field data, redirects, and failing audit issues |
| [`psi-xlsx`](skills/psi-xlsx/SKILL.md) | Excel I/O & Reporting | Extracting unique URLs from `.xlsx` and writing a formatted, formula-driven PageSpeed result sheet |

<details>
<summary><strong>What's inside <code>psi-web</code></strong></summary>

- [`scripts/psi_web.mjs`](skills/psi-web/scripts/psi_web.mjs): Launches installed Google Chrome (`channel: 'chrome'`), blocks images/media/fonts/analytics, polls `.lh-exp-gauge__percentage` via `page.evaluate` (CSP-safe), and appends `{url, mobile, desktop, mobileLink, desktopLink, reportTime}` per line to JSONL.
- Skips already-completed URLs on re-run (doesn't even launch Chrome if nothing remains) and fails fast on DNS errors (`Unable to resolve`).

</details>

<details>
<summary><strong>What's inside <code>psi-api</code></strong></summary>

- [`scripts/psi_api.py`](skills/psi-api/scripts/psi_api.py): Multi-threaded (`--workers 6`) HTTPS client to `www.googleapis.com/pagespeedonline/v5/runPagespeed` using Python stdlib only.
- Sends `X-Goog-Api-Key` header, requests gzip + partial `fields`, strips audit screenshots, and writes atomic JSON files (`<md5>.json`).
- Fails fast on `HTTP 400` (invalid URL), aborts immediately on `HTTP 401`/`403` (bad key or quota), and backs off on `HTTP 429`.

</details>

<details>
<summary><strong>What's inside <code>psi-xlsx</code></strong></summary>

- [`scripts/xlsx_tool.py`](skills/psi-xlsx/scripts/xlsx_tool.py): Standalone tool (zero coupling to `psi-api`) with two subcommands:
  - `extract`: Streams unique `http(s)` URLs in `read_only` mode.
  - `write`: Builds a styled `PageSpeed Check YYYY-MM-DD` tab with cross-sheet `Old Score` formulas, `PASS`/`FAIL`, conditional formatting, frozen panes, auto-filter, and summary metrics. Works with both `psi-web` + `psi-api`, or either source alone.

</details>

## Output columns

Columns `A`–`S` generated by `psi-xlsx write`:

| Column | Content | Source |
|---|---|---|
| `A` | URL (clickable hyperlink) | Source `.xlsx` |
| `B` | Old Score (live formula referencing source sheet) | Source `.xlsx` |
| `C` / `D` | Mobile / Desktop performance score (matches links `Q`/`R`) | `psi-web` |
| `E` / `F` | Mobile Δ vs Old Score, `PASS`/`FAIL` (`>= target`) | Excel formula |
| `G`–`K` | Mobile FCP (s), LCP (s), TBT (ms), CLS, Speed Index (s) | `psi-api` |
| `L`–`M` | Desktop LCP (s), Desktop CLS | `psi-api` |
| `N` | CrUX real-user field category (mobile) | `psi-api` |
| `O` | Main mobile issues (`score < 0.9`) or API error | `psi-api` |
| `P` | Final URL (if redirected) | `psi-api` |
| `Q` / `R` | Permanent PSI mobile / desktop report links (clickable) | `psi-web` |
| `S` | Report timestamp | `psi-web` |

## Proving it works

```bash
# 1. Syntax checks across all 3 skills
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ('skills/psi-api/scripts/psi_api.py', 'skills/psi-xlsx/scripts/xlsx_tool.py')]"
node --check skills/psi-web/scripts/psi_web.mjs

# 2. Quick smoke test for psi-web (no API key needed)
printf 'https://example.com\n' > /tmp/urls.txt
node skills/psi-web/scripts/psi_web.mjs /tmp/urls.txt /tmp/out.jsonl 1 && cat /tmp/out.jsonl

# 3. Static quality, security & 6-harness validation with NVIDIA SkillEvaluator
uvx skillevaluator validate skills/psi-web  --tiers 1
uvx skillevaluator validate skills/psi-api  --tiers 1
uvx skillevaluator validate skills/psi-xlsx --tiers 1
```

## FAQ

**Do I need a Google API key?**
Only for `psi-api`. If you only want mobile/desktop performance scores and permanent shareable `pagespeed.web.dev` links, `psi-web` works with zero API keys.

**Why separate `psi-web` and `psi-api`?**
The PageSpeed Insights API does not return a shareable report URL, while the web UI doesn't expose raw structured audit JSON cleanly. Keeping them as separate skills lets you pick whichever source your task needs—or run both in parallel.

**Why do lab scores differ slightly between runs?**
PageSpeed lab runs naturally vary by ±5 points due to network/CPU jitter. If a single URL looks anomalous, delete its line from `psi_web.jsonl` (or its file in `raw/`) and re-run to re-test only that URL.

**Which AI coding agents are supported?**
Any agent that supports the Agent Skills standard (`SKILL.md`), verified 6/6 by `skillevaluator harness-check`: Claude Code, Codex, GitHub Copilot CLI, Hermes, OpenClaw, and OpenCode (as well as Antigravity and Cursor).

<hr>

<p align="center"><em>“Measure in the real tool, keep the permanent link as proof,<br>
and never copy-paste 50 PageSpeed scores into Excel by hand again.”</em></p>

<hr>

## Disclaimer & License

- **Responsible use:** `psi-web` automates the `pagespeed.web.dev` web UI in a local browser. Users are responsible for complying with the Google Terms of Service, keeping concurrency low, and auditing only websites they own or have permission to test. For strictly API-based usage, use `psi-api` with your own Google API key under the Google APIs Terms of Service.
- **Trademarks:** This project is an independent open-source tool and is not affiliated with, endorsed by, or sponsored by Google LLC. Google, PageSpeed Insights, Chrome, Lighthouse, and Core Web Vitals are trademarks of Google LLC.

MIT: [LICENSE](LICENSE)
