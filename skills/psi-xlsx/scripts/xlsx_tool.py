"""Extract URLs from an xlsx, and write a PageSpeed result sheet back into it.

Extract:  python xlsx_tool.py extract <file.xlsx> <urls.txt> [--sheet Sheet1] [--url-col B] [--start-row 2]
Write:    python xlsx_tool.py write <file.xlsx> <psi_web.jsonl> <raw_dir> [--sheet Sheet1] [--url-col B]
                 [--score-col C] [--start-row 2] [--name "PageSpeed Check YYYY-MM-DD"] [--target 80]

Result sheet columns:
  URL | Old Score (formula to source sheet) | Mobile/Desktop score (from PSI web report) | Δ | PASS/FAIL |
  mobile FCP/LCP/TBT/CLS/SI, desktop LCP/CLS, CrUX, main issues (from PSI API run, marked *) |
  final URL | PSI mobile link | PSI desktop link | report time
Scores C/D always match the permanent links in Q/R.
"""
import argparse, datetime, hashlib, json, os
import openpyxl
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import column_index_from_string, get_column_letter


def raw_path(raw_dir, url, strategy):
    return os.path.join(raw_dir, hashlib.md5((url + strategy).encode(), usedforsecurity=False).hexdigest() + '.json')


def read_json(fn):
    try:
        with open(fn) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None

METRIC_SKIP = {'largest-contentful-paint', 'first-contentful-paint', 'speed-index', 'total-blocking-time',
               'cumulative-layout-shift', 'interactive', 'max-potential-fid', 'lcp-breakdown-insight',
               'network-dependency-tree-insight'}


def source_rows(ws, url_col, start):
    ci = column_index_from_string(url_col)
    rows = ws.iter_rows(min_row=start, min_col=ci, max_col=ci, values_only=True)  # fast, works in read_only too
    return [(r, v.strip()) for r, (v,) in enumerate(rows, start) if isinstance(v, str) and v.strip().startswith('http')]


def sheet_ref(name):
    return "'" + name.replace("'", "''") + "'"


def cmd_extract(a):
    wb = openpyxl.load_workbook(a.xlsx, read_only=True)
    if a.sheet not in wb.sheetnames:
        raise SystemExit(f'sheet "{a.sheet}" not found; available: {wb.sheetnames}')
    urls = list(dict.fromkeys(u for _, u in source_rows(wb[a.sheet], a.url_col, a.start_row)))  # dedupe, keep order
    wb.close()
    if not urls:
        raise SystemExit(f'no http(s) URLs in {a.sheet}!{a.url_col}{a.start_row}:{a.url_col}')
    with open(a.out, 'w') as f:
        f.write('\n'.join(urls) + '\n')
    print(len(urls), 'unique urls ->', a.out)


def load_api(raw_dir, url, strat):
    return read_json(raw_path(raw_dir, url, strat)) or {}


def metric(audits, key, div=1, nd=2):
    v = audits.get(key, {}).get('numericValue')
    return None if v is None else round(v / div, nd) if nd else round(v / div)


def cmd_write(a):
    web = {}
    if os.path.exists(a.jsonl):
        with open(a.jsonl) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    web[r['url']] = r
                except (ValueError, KeyError):
                    pass  # blank / partially written line
    wb = openpyxl.load_workbook(a.xlsx)
    src = wb[a.sheet]
    name = (a.name or f'PageSpeed Check {datetime.date.today():%Y-%m-%d}').translate(str.maketrans('[]:*?/\\', '()-----'))[:31]
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)

    F = Font(name='Arial', size=10)
    HF = Font(name='Arial', size=10, bold=True, color='FFFFFF')
    HFill = PatternFill('solid', fgColor='305496')
    LINK = Font(name='Arial', size=10, color='0563C1', underline='single')

    ws['A1'] = f'PageSpeed Insights check — {datetime.date.today():%d %b %Y} (pagespeed.web.dev)'
    ws['A1'].font = Font(name='Arial', size=12, bold=True)
    ws['A2'] = (f"Old score = {sheet_ref(a.sheet)}!{a.score_col}. Target ≥ {a.target}. Scores C/D come from the PSI report "
                f"in Q/R (permanent links). Columns marked * come from a separate PSI API run on the same day.")
    ws['A2'].font = Font(name='Arial', size=9, italic=True)

    hdr = ['URL', 'Old Score', 'Mobile Score (PSI link)', 'Desktop Score (PSI link)', 'Mobile Δ vs Old',
           'Mobile Status', 'Mobile FCP (s) *', 'Mobile LCP (s) *', 'Mobile TBT (ms) *', 'Mobile CLS *',
           'Mobile Speed Index (s) *', 'Desktop LCP (s) *', 'Desktop CLS *', 'CrUX Field (mobile)',
           'Main Mobile Issues *', 'Final URL (if redirected)', 'PSI Mobile Link', 'PSI Desktop Link',
           'PSI Report Time']
    R0 = 4
    for i, h in enumerate(hdr, 1):
        c = ws.cell(R0, i, h)
        c.font, c.fill = HF, HFill
        c.alignment = Alignment(wrap_text=True, vertical='center')

    qs = sheet_ref(a.sheet)
    r = R0
    missing_web = missing_api = 0
    for sr, u in source_rows(src, a.url_col, a.start_row):
        r += 1
        w = web.get(u, {})
        mj, dj = load_api(a.raw_dir, u, 'mobile'), load_api(a.raw_dir, u, 'desktop')
        m, d = mj.get('data'), dj.get('data')
        vals = [u, f'={qs}!{a.score_col}{sr}' if a.score_col else None,
                w.get('mobile'), w.get('desktop'), f'=IF(AND(ISNUMBER(B{r}),ISNUMBER(C{r})),C{r}-B{r},"")',
                f'=IF(C{r}="","",IF(C{r}>={a.target},"PASS","FAIL"))']
        if m and d:
            ml, dl = m.get('lighthouseResult') or {}, d.get('lighthouseResult') or {}
            ma, da = ml.get('audits') or {}, dl.get('audits') or {}
            issues = [v.get('title', k) for k, v in ma.items() if k not in METRIC_SKIP and v.get('score') is not None
                      and v['score'] < 0.9 and v.get('scoreDisplayMode') in ('numeric', 'binary', 'metricSavings')]
            for lr in (ml, dl):
                if (lr.get('runtimeError') or {}).get('code') not in (None, 'NO_ERROR'):
                    issues.insert(0, 'Lighthouse error: ' + lr['runtimeError'].get('message', lr['runtimeError']['code']))
                    break
            le = m.get('loadingExperience', {})
            if le.get('origin_fallback'):
                crux = 'No URL data (origin: %s)' % le.get('overall_category', '-')
            else:
                crux = le.get('overall_category') or 'No data'
            fu = ml.get('finalDisplayedUrl') or ml.get('finalUrl')
            vals += [metric(ma, 'first-contentful-paint', 1000), metric(ma, 'largest-contentful-paint', 1000),
                     metric(ma, 'total-blocking-time', 1, 0), metric(ma, 'cumulative-layout-shift', 1, 3),
                     metric(ma, 'speed-index', 1000), metric(da, 'largest-contentful-paint', 1000),
                     metric(da, 'cumulative-layout-shift', 1, 3),
                     crux, '; '.join(issues), '' if not fu or fu == u else fu]
        else:
            missing_api += 1
            err = mj.get('error') or dj.get('error')
            vals += [None] * 7 + ['API error' if err else 'API data missing', err or '', '']
        vals += [w.get('mobileLink'), w.get('desktopLink'), w.get('reportTime')]
        for i, v in enumerate(vals, 1):
            ws.cell(r, i, v).font = F
        ws.cell(r, 1).hyperlink = u
        ws.cell(r, 1).font = LINK
        for col in (17, 18):
            if ws.cell(r, col).value:
                ws.cell(r, col).hyperlink = ws.cell(r, col).value
                ws.cell(r, col).font = LINK
        ws.cell(r, 5).number_format = '+0;-0;0'
        ws.cell(r, 15).alignment = Alignment(wrap_text=True, vertical='top')
        if not w:
            missing_web += 1
            ws.cell(r, 3).comment = Comment('PSI web run failed — re-run psi_web.mjs', 'psi-check')
    last = r

    s = last + 2
    rng = lambda col: f'{col}{R0 + 1}:{col}{last}'
    summ = [('URLs checked', f'=COUNTA({rng("A")})', None),
            (f'Mobile PASS (≥{a.target})', f'=COUNTIF({rng("F")},"PASS")', None),
            (f'Mobile FAIL (<{a.target})', f'=COUNTIF({rng("F")},"FAIL")', None),
            ('Avg old score', f'=AVERAGE({rng("B")})', '0.0'),
            ('Avg mobile score', f'=AVERAGE({rng("C")})', '0.0'),
            ('Avg desktop score', f'=AVERAGE({rng("D")})', '0.0'),
            ('Avg mobile Δ', f'=AVERAGE({rng("E")})', '+0.0;-0.0'),
            ('Lowest mobile score', f'=MIN({rng("C")})', None)]
    ws.cell(s, 1, 'Summary').font = Font(name='Arial', size=11, bold=True)
    for i, (k, f, nf) in enumerate(summ, 1):
        ws.cell(s + i, 1, k).font = F
        c = ws.cell(s + i, 2, f)
        c.font = Font(name='Arial', size=10, bold=True)
        if nf:
            c.number_format = nf
    ws.cell(s + len(summ) + 2, 1, 'Note: lab scores vary ±5 per run. Mobile = throttled 4G emulation; '
                                  'Desktop = no throttling.').font = Font(name='Arial', size=9, italic=True)

    grn, yel, red = (PatternFill('solid', fgColor=c) for c in ('C6EFCE', 'FFE699', 'F8CBAD'))
    for col in 'BCD':
        ws.conditional_formatting.add(rng(col), CellIsRule(operator='greaterThanOrEqual', formula=['90'], fill=grn))
        ws.conditional_formatting.add(rng(col), CellIsRule(operator='between', formula=['50', '89'], fill=yel))
        ws.conditional_formatting.add(rng(col), CellIsRule(operator='lessThan', formula=['50'], fill=red))
    ws.conditional_formatting.add(rng('F'), CellIsRule(operator='equal', formula=['"FAIL"'], fill=red))
    ws.conditional_formatting.add(rng('F'), CellIsRule(operator='equal', formula=['"PASS"'], fill=grn))
    widths = [70, 9, 10, 10, 10, 10, 9, 9, 9, 9, 11, 9, 9, 22, 80, 30, 40, 40, 26]
    for i, wdt in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = wdt
    ws.row_dimensions[R0].height = 42
    ws.freeze_panes = f'B{R0 + 1}'
    ws.auto_filter.ref = f'A{R0}:S{last}'
    wb.save(a.xlsx)
    print(f'sheet "{name}" written: {last - R0} rows ->', a.xlsx)
    if missing_web or missing_api:
        print(f'WARNING: {missing_web} rows without PSI web result, {missing_api} rows without API data. '
              'Re-run the same command (same day) to retry only those.')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('extract')
    e.add_argument('xlsx'); e.add_argument('out')
    w = sub.add_parser('write')
    w.add_argument('xlsx'); w.add_argument('jsonl'); w.add_argument('raw_dir')
    for p in (e, w):  # same options on both so run.sh can pass "$@" to each
        p.add_argument('--score-col', default='C')
        p.add_argument('--name')
        p.add_argument('--target', type=int, default=80)
        p.add_argument('--sheet', default='Sheet1')
        p.add_argument('--url-col', default='B')
        p.add_argument('--start-row', type=int, default=2)
    a = ap.parse_args()
    {'extract': cmd_extract, 'write': cmd_write}[a.cmd](a)


if __name__ == '__main__':
    main()
