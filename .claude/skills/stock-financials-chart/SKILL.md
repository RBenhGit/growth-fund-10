---
name: stock-financials-chart
description: This skill should be used when the user wants to see, chart, plot, graph, or visualize a stock's revenue, net income, operating income, and/or operating cash flow trend from this project's cached fundamentals (cache/stocks_data/*.json) — for any ticker in either index (SP500 or TASE125), not just current fund holdings.
version: 0.1.0
disable-model-invocation: false
---

# Stock Financials Chart

Generates a self-contained, dataviz-guideline-compliant HTML chart of one
stock's four core fundamentals — Revenue, Net Income, Operating Income, and
Operating Cash Flow — over every fiscal year available in its cache file, then
publishes it as an Artifact.

The chart is a grouped bar chart with a zero baseline (so loss years read
correctly below the line), hover/focus tooltips, a legend, dark/light theme
support, and a "Show data table" toggle for full precision and accessibility.
Colors, ticks, and unit scaling (millions vs. billions) are computed
automatically — there is no manual chart design step.

## When to use this

Any time the user asks to see, chart, plot, or visualize a ticker's revenue /
net income / operating income / operating cash flow — whether the stock is a
current fund holding or not, on either TASE125 or SP500. The only requirement
is a cache file at `cache/stocks_data/{TICKER}_US.json` or `_TA.json`.

If the user also wants to know whether the ticker is fund-eligible or how it
scored, use `stock-snapshot` instead — it includes this same chart plus a
Fund Status card, rather than the chart alone.

## How to run it

```bash
python3 .claude/skills/stock-financials-chart/scripts/generate_chart.py <TICKER> --output <path>.html
```

- `<TICKER>` — bare ticker (`PLTR`, `AAPL`) auto-resolves `_US.json` then
  `_TA.json`. For a TASE stock whose ticker also happens to exist on the US
  side, pass the suffix explicitly (`MTRX_TA`).
- `--output` — always pass an explicit path into the current scratchpad
  directory (e.g. `<scratchpad>/<TICKER>_financials_chart.html`). Without it,
  the script writes to the current working directory using the resolved
  ticker as the filename.
- The script exits 1 with a clear message if no cache file matches, or if the
  file has no usable financial data — surface that message to the user rather
  than retrying blindly (it usually means the ticker was never fetched into
  `cache/stocks_data/`, not a bug in the chart).

Then publish the output file with the Artifact tool directly — **do not**
reload the `dataviz` or `artifact-design` skills for this; the template
already encodes their rules (validated palette slots, mark specs, zero
baseline, accessible table view, light/dark tokens). Use:
- `title`: `"<TICKER> Financial Trends"`
- `description`: one sentence naming the metrics and fiscal-year range shown
- `favicon`: `📊`

## What the script does

1. Resolves the ticker to a `cache/stocks_data/*.json` file and reads
   `financial_data.revenues` / `net_incomes` / `operating_incomes` /
   `operating_cash_flows`.
2. Converts raw dollar/shekel figures to millions, then auto-upgrades the
   whole chart to billions if the largest magnitude value is ≥ 1000M (keeps
   mega-caps like AAPL readable; small caps stay in millions).
3. Picks the currency symbol from the cache suffix: `$`/USD for `_US`,
   `₪`/NIS for `_TA`. TASE fundamentals in this cache are already in shekel
   units (unlike TASE *prices*, which are agorot — see the `tase-stocks`
   skill), so no /100 conversion is applied here.
4. Computes "nice" axis ticks from the actual data range (always including
   zero) instead of hardcoding a domain — this is what makes the same
   template work unmodified from a small TASE cap to a mega-cap.
5. Renders one embedded JSON blob of chart data into a static HTML/CSS/JS
   template (categorical slots 1–4 of the project's validated palette:
   blue/orange/aqua/yellow, sequenced for a 4-series adjacent grouped-bar
   layout; negative values are colored with the reserved status-critical red,
   never a series color, everywhere a number turns negative).
6. A year missing from one series (but present in another) renders as a gap
   in that bar's group rather than a fabricated zero.

## Known limits

- Single ticker per chart — this does not build side-by-side ticker
  comparisons. If asked for that, treat it as a new request rather than
  stretching this skill (different layout: small multiples or one bar chart
  per company, not a mechanical extension of this script).
- Reads only the four fundamentals above. Price, market cap, PE, and score
  fields in the cache are out of scope for this skill.
