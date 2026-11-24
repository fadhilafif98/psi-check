---
name: psi-xlsx
description: >-
  Extract unique URLs from an Excel (.xlsx) spreadsheet and write a formatted
  PageSpeed Insights result sheet back into the workbook with score comparison
  formulas, PASS/FAIL status, conditional formatting, Core Web Vitals metrics,
  and clickable report links. Use when the user wants to read URL lists from an
  Excel file for PageSpeed audits or generate a formatted PageSpeed report tab
  in .xlsx.
metadata:
  author: psi-check
  tags:
    - pagespeed
    - excel
    - xlsx
    - reporting
---

# psi-xlsx

Extract URLs from an `.xlsx` workbook and write a formatted, formula-driven PageSpeed result sheet back into the same workbook using [scripts/xlsx_tool.py](scripts/xlsx_tool.py).

Works standalone or paired with JSONL output from `psi-web` and/or raw JSON output directory from `psi-api`.

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/xlsx_tool.py` | Extract unique URLs from `.xlsx` or write a formatted PageSpeed result tab | `extract <xlsx> <urls_out> [...]` or `write <xlsx> <web_jsonl> <raw_dir> [...]` |

## Prerequisites

- **Python 3** with `openpyxl` installed:
  ```bash
  python3 -m venv .venv && .venv/bin/pip install openpyxl
  ```

## Usage

### 1. Extract URLs from `.xlsx`

```bash
python3 scripts/xlsx_tool.py extract <workbook_path> <urls_out> \
  [--sheet Sheet1] [--url-col B] [--start-row 2]
```

- Reads in `read_only` mode, extracts unique `http(s)` URLs preserving order, and writes one URL per line to `<urls_out>`.
- Always back up `<workbook_path>` before running `write`.

### 2. Write Result Sheet to `.xlsx`

```bash
python3 scripts/xlsx_tool.py write <workbook_path> <web_jsonl> <raw_dir> \
  [--sheet Sheet1] [--url-col B] [--score-col C] [--start-row 2] \
  [--target 80] [--name "PageSpeed Check YYYY-MM-DD"]
```

- Either `<web_jsonl>` or `<raw_dir>` may be empty/missing if only one data source was run; missing fields are annotated cleanly.
- Duplicate URLs in the source sheet are preserved row-for-row in the output sheet.

### Generated Columns (`A`–`S`)

| Column | Content |
|---|---|
| `A` | URL (hyperlink) |
| `B` | Old Score (formula referencing source sheet) |
| `C` / `D` | Mobile / Desktop score from PSI web JSONL output |
| `E` / `F` | Mobile delta vs Old Score, `PASS`/`FAIL` (`>= target`) |
| `G`–`M` | Mobile FCP, LCP, TBT, CLS, Speed Index; Desktop LCP, CLS (from PSI API) |
| `N` | CrUX real-user field category (mobile) |
| `O` | Main mobile issues (`score < 0.9`) or API error |
| `P` | Final URL (if redirected) |
| `Q` / `R` | Clickable permanent PSI mobile / desktop report links |
| `S` | Report timestamp |

Includes conditional formatting (`>=90` green, `50–89` yellow, `<50` red), frozen panes, auto-filter, and a bottom summary table.

## Verification

Check stdout after `write`:
- Reports `sheet "<name>" written: <N> rows -> <workbook_path>`.
- If `WARNING: X rows without PSI web result, Y rows without API data` appears, re-run the missing source and run `write` again (the sheet with the same `--name` is replaced cleanly).
- Excel formulas evaluate when opened in Excel or LibreOffice.
