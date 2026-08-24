#!/usr/bin/env python3
"""Generate a self-contained HTML chart of a stock's revenue, net income,
operating income, and operating cash flow from its cached fundamentals in
cache/stocks_data/. The output is a standalone artifact-ready HTML file
(grouped bar chart, zero baseline, legend, hover tooltips, table-view toggle,
light/dark aware) with no external dependencies.

CSS/markup/script pieces below are also imported directly by the sibling
`stock-snapshot` skill to compose the same chart into a larger page — keep
render_html()'s output stable when editing them.
"""

import argparse
import html as html_lib
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CACHE_DIR = REPO_ROOT / "cache" / "stocks_data"

SERIES_DEFS = [
    ("revenues", "Revenue", "--series-1"),
    ("net_incomes", "Net Income", "--series-2"),
    ("operating_incomes", "Operating Income", "--series-3"),
    ("operating_cash_flows", "Operating Cash Flow", "--series-4"),
]


def resolve_cache_file(ticker: str) -> Path:
    ticker = ticker.strip().upper()
    if ticker.endswith("_US") or ticker.endswith("_TA"):
        candidate = CACHE_DIR / f"{ticker}.json"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"No cache file at {candidate}")
    for suffix in ("US", "TA"):
        candidate = CACHE_DIR / f"{ticker}_{suffix}.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No cache file for '{ticker}' (looked for {ticker}_US.json / "
        f"{ticker}_TA.json in {CACHE_DIR})"
    )


def nice_ticks(raw_min: float, raw_max: float, target_count: int = 6):
    """Round (min, max) out to clean tick steps, always including zero."""
    lo = min(0.0, raw_min)
    hi = max(0.0, raw_max)
    span = hi - lo
    if span == 0:
        span = max(abs(hi), 1.0)
    step_raw = span / target_count
    magnitude = 10 ** math.floor(math.log10(step_raw))
    residual = step_raw / magnitude
    if residual > 5:
        step = 10 * magnitude
    elif residual > 2:
        step = 5 * magnitude
    elif residual > 1:
        step = 2 * magnitude
    else:
        step = magnitude
    nice_min = math.floor(lo / step) * step
    nice_max = math.ceil(hi / step) * step
    n_steps = round((nice_max - nice_min) / step)
    ticks = [round(nice_min + i * step, 6) for i in range(n_steps + 1)]
    return ticks, nice_min, nice_max, step


def build_chart_data(cache_file: Path) -> dict:
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    fin = data.get("financial_data", {})
    symbol = data.get("symbol", cache_file.stem)
    ticker = symbol.split(".")[0]
    company_name = data.get("name", ticker)
    currency = "₪" if cache_file.stem.endswith("_TA") else "$"
    currency_name = "NIS" if currency == "₪" else "USD"

    all_years = set()
    for key, _, _ in SERIES_DEFS:
        all_years.update(fin.get(key, {}).keys())
    if not all_years:
        raise ValueError(f"No financial data found in {cache_file}")
    years = sorted(int(y) for y in all_years)

    series_millions = []
    all_values_m = []
    for key, label, var_name in SERIES_DEFS:
        raw = fin.get(key, {})
        values = []
        for y in years:
            v = raw.get(str(y))
            if v is None:
                values.append(None)
            else:
                vm = v / 1_000_000.0
                values.append(vm)
                all_values_m.append(vm)
        series_millions.append({"key": key, "label": label, "varName": var_name, "values": values})

    if not all_values_m:
        raise ValueError(f"No numeric financial values found in {cache_file}")

    use_billions = max(abs(v) for v in all_values_m) >= 1000
    unit_suffix = "B" if use_billions else "M"
    unit_label = "billions" if use_billions else "millions"
    divisor = 1000.0 if use_billions else 1.0

    series = []
    all_values_unit = []
    for s in series_millions:
        vals = [None if v is None else round(v / divisor, 4) for v in s["values"]]
        series.append({"key": s["key"], "label": s["label"], "varName": s["varName"], "values": vals})
        all_values_unit.extend(v for v in vals if v is not None)

    ticks, nice_min, nice_max, step = nice_ticks(min(all_values_unit), max(all_values_unit))
    pad = step * 0.15
    y_min = nice_min - pad
    y_max = nice_max + pad

    try:
        rel_source = str(cache_file.relative_to(REPO_ROOT))
    except ValueError:
        rel_source = str(cache_file)

    return {
        "ticker": ticker,
        "companyName": company_name,
        "currency": currency,
        "currencyName": currency_name,
        "unitSuffix": unit_suffix,
        "unitLabel": unit_label,
        "sourceFile": rel_source,
        "years": years,
        "series": series,
        "yMin": y_min,
        "yMax": y_max,
        "ticks": ticks,
    }


TOKENS_CSS = """  .viz-root {
    color-scheme: light;
    --surface-1:      #fcfcfb;
    --page-plane:     #f9f9f7;
    --text-primary:   #0b0b0b;
    --text-secondary: #52514e;
    --text-muted:     #898781;
    --gridline:       #e1e0d9;
    --baseline:       #c3c2b7;
    --border:         rgba(11,11,11,0.10);
    --series-1:       #2a78d6; /* revenue */
    --series-2:       #eb6834; /* net income */
    --series-3:       #1baf7a; /* operating income */
    --series-4:       #eda100; /* operating cash flow */
    --status-critical:#d03b3b; /* negative-value indicator, not a series color */
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--page-plane);
    color: var(--text-primary);
    min-height: 100vh;
    box-sizing: border-box;
    padding: 28px 20px 40px;
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) .viz-root {
      color-scheme: dark;
      --surface-1:      #1a1a19;
      --page-plane:     #0d0d0d;
      --text-primary:   #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted:     #898781;
      --gridline:       #2c2c2a;
      --baseline:       #383835;
      --border:         rgba(255,255,255,0.10);
      --series-1:       #3987e5;
      --series-2:       #d95926;
      --series-3:       #199e70;
      --series-4:       #c98500;
      --status-critical:#e66767;
    }
  }
  :root[data-theme="dark"] .viz-root {
    color-scheme: dark;
    --surface-1:      #1a1a19;
    --page-plane:     #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:     #898781;
    --gridline:       #2c2c2a;
    --baseline:       #383835;
    --border:         rgba(255,255,255,0.10);
    --series-1:       #3987e5;
    --series-2:       #d95926;
    --series-3:       #199e70;
    --series-4:       #c98500;
    --status-critical:#e66767;
  }"""


CARD_BASE_CSS = """  .viz-root * { box-sizing: border-box; }

  .card {
    max-width: 980px;
    margin: 0 auto;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px 28px 28px;
  }
  h1 {
    font-size: 19px;
    font-weight: 600;
    margin: 0 0 4px;
    color: var(--text-primary);
  }
  .subtitle {
    font-size: 13px;
    color: var(--text-secondary);
    margin: 0 0 18px;
  }"""


CHART_CSS = """  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 14px;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 12.5px;
    color: var(--text-secondary);
  }
  .legend-swatch {
    width: 11px;
    height: 11px;
    border-radius: 3px;
    flex: none;
  }

  .view-toggle {
    font-size: 12.5px;
    font-weight: 500;
    color: var(--text-secondary);
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 6px 12px;
    cursor: pointer;
    font-family: inherit;
  }
  .view-toggle:hover {
    color: var(--text-primary);
    border-color: var(--baseline);
  }
  .view-toggle:focus-visible {
    outline: 2px solid var(--series-1);
    outline-offset: 2px;
  }

  .chart-wrap {
    position: relative;
  }
  svg.chart {
    width: 100%;
    height: auto;
    display: block;
    overflow: visible;
  }

  .gridline { stroke: var(--gridline); stroke-width: 1; }
  .baseline-axis { stroke: var(--baseline); stroke-width: 1.5; }
  .tick-label {
    fill: var(--text-muted);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }
  .cat-label {
    fill: var(--text-secondary);
    font-size: 12px;
    font-weight: 500;
    text-anchor: middle;
  }
  .value-label {
    fill: var(--text-primary);
    font-size: 11px;
    font-weight: 600;
    text-anchor: middle;
    font-variant-numeric: tabular-nums;
  }

  .bar {
    cursor: pointer;
    transition: opacity 0.12s ease;
  }
  .bar:hover, .bar:focus-visible {
    opacity: 0.82;
  }
  .bar:focus-visible {
    outline: none;
  }

  .tooltip {
    position: absolute;
    pointer-events: none;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 11px;
    font-size: 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.16);
    opacity: 0;
    transform: translate(-50%, calc(-100% - 10px));
    transition: opacity 0.08s ease;
    white-space: nowrap;
    z-index: 5;
  }
  .tooltip.visible { opacity: 1; }
  .tooltip-year {
    color: var(--text-muted);
    font-size: 11px;
    margin-bottom: 3px;
  }
  .tooltip-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tooltip-key {
    width: 9px;
    height: 9px;
    border-radius: 2px;
    flex: none;
  }
  .tooltip-label {
    color: var(--text-secondary);
  }
  .tooltip-value {
    color: var(--text-primary);
    font-weight: 700;
    margin-left: auto;
    padding-left: 10px;
    font-variant-numeric: tabular-nums;
  }

  table.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  table.data-table th, table.data-table td {
    text-align: right;
    padding: 9px 10px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  table.data-table th:first-child, table.data-table td:first-child {
    text-align: left;
    font-variant-numeric: normal;
  }
  table.data-table thead th {
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 12px;
    border-bottom: 1px solid var(--baseline);
    padding-bottom: 10px;
  }
  table.data-table th .th-swatch {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
    margin-right: 6px;
    vertical-align: middle;
  }
  table.data-table tbody td {
    color: var(--text-primary);
    border-bottom: 1px solid var(--gridline);
  }
  table.data-table tbody tr:last-child td {
    border-bottom: none;
  }
  .negative { color: var(--status-critical); }"""


FOOTER_CSS = """  .footer-note {
    margin-top: 16px;
    font-size: 11.5px;
    color: var(--text-muted);
  }

  [hidden] { display: none !important; }"""


CHART_CARD_TEMPLATE = """  <div class="card">
    <h1>{company_name} ({ticker}) &mdash; Annual Financials</h1>
    <p class="subtitle">Revenue, net income, operating income &amp; operating cash flow &middot; FY{year_min}&ndash;FY{year_max} &middot; {currency_name}, {currency} {unit_label}</p>

    <div class="toolbar">
      <div class="legend" id="legend"></div>
      <button class="view-toggle" id="viewToggle" type="button" aria-pressed="false">Show data table</button>
    </div>

    <div class="chart-wrap" id="chartWrap">
      <svg class="chart" id="chart" viewBox="0 0 900 500" role="img" aria-label="Grouped bar chart of {ticker} revenue, net income, operating income and operating cash flow from {year_min} to {year_max}"></svg>
      <div class="tooltip" id="tooltip"></div>
    </div>

    <div id="tableWrap" hidden></div>

    <p class="footer-note">Source: cached fundamentals ({source_file}), fiscal-year figures.</p>
  </div>"""


CHART_SCRIPTS_TEMPLATE = """<script type="application/json" id="chart-data">{chart_json}</script>
<script>
(function () {{
  var CHART = JSON.parse(document.getElementById('chart-data').textContent);
  var YEARS = CHART.years;
  var SERIES = CHART.series;
  var CURRENCY = CHART.currency;
  var UNIT_SUFFIX = CHART.unitSuffix;

  var root = document.querySelector('.viz-root');
  var svg = document.getElementById('chart');
  var tooltip = document.getElementById('tooltip');
  var chartWrap = document.getElementById('chartWrap');
  var legendEl = document.getElementById('legend');
  var tableWrap = document.getElementById('tableWrap');
  var viewToggle = document.getElementById('viewToggle');

  var svgNS = 'http://www.w3.org/2000/svg';

  function fmtM(v) {{
    if (v === null || v === undefined) return '—';
    var sign = v < 0 ? '−' : '';
    var abs = Math.abs(v);
    return sign + CURRENCY + abs.toLocaleString('en-US', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}) + UNIT_SUFFIX;
  }}
  function fmtTick(v) {{
    return (v < 0 ? '−' : '') + Math.abs(v).toLocaleString('en-US');
  }}

  function buildLegend() {{
    legendEl.textContent = '';
    SERIES.forEach(function (s) {{
      var item = document.createElement('div');
      item.className = 'legend-item';
      var sw = document.createElement('span');
      sw.className = 'legend-swatch';
      sw.style.background = 'var(' + s.varName + ')';
      var label = document.createElement('span');
      label.textContent = s.label;
      item.appendChild(sw);
      item.appendChild(label);
      legendEl.appendChild(item);
    }});
  }}

  var W = 900, H = 500;
  var plotLeft = 88, plotRight = 878, plotTop = 26, plotBottom = 412;
  var plotWidth = plotRight - plotLeft, plotHeight = plotBottom - plotTop;

  var yMin = CHART.yMin, yMax = CHART.yMax;
  var ticks = CHART.ticks;

  function yScale(v) {{
    return plotBottom - (v - yMin) / (yMax - yMin) * plotHeight;
  }}

  var barW = 22, barGap = 2, groupGap = 40;
  var groupW = SERIES.length * barW + (SERIES.length - 1) * barGap;
  var contentW = YEARS.length * groupW + (YEARS.length - 1) * groupGap;
  var sideMargin = (plotWidth - contentW) / 2;

  function groupX(i) {{
    return plotLeft + sideMargin + i * (groupW + groupGap);
  }}

  function el(tag, attrs) {{
    var e = document.createElementNS(svgNS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }}

  function buildChart() {{
    svg.textContent = '';
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

    ticks.forEach(function (t) {{
      var y = yScale(t);
      if (t !== 0) {{
        svg.appendChild(el('line', {{
          class: 'gridline', x1: plotLeft, x2: plotRight, y1: y, y2: y
        }}));
      }}
      var label = el('text', {{
        class: 'tick-label', x: plotLeft - 12, y: y + 3.5, 'text-anchor': 'end'
      }});
      label.textContent = fmtTick(t);
      svg.appendChild(label);
    }});

    var y0 = yScale(0);
    svg.appendChild(el('line', {{
      class: 'baseline-axis', x1: plotLeft, x2: plotRight, y1: y0, y2: y0
    }}));

    var globalMax = null, globalMin = null;
    SERIES.forEach(function (s, j) {{
      s.values.forEach(function (v, i) {{
        if (v === null || v === undefined) return;
        if (globalMax === null || v > globalMax.v) globalMax = {{ v: v, i: i, j: j }};
        if (globalMin === null || v < globalMin.v) globalMin = {{ v: v, i: i, j: j }};
      }});
    }});

    YEARS.forEach(function (year, i) {{
      var gx = groupX(i);

      var catLabel = el('text', {{
        class: 'cat-label', x: gx + groupW / 2, y: plotBottom + 24
      }});
      catLabel.textContent = String(year);
      svg.appendChild(catLabel);

      SERIES.forEach(function (s, j) {{
        var v = s.values[i];
        if (v === null || v === undefined) return;
        var bx = gx + j * (barW + barGap);
        var yTip = yScale(v);
        var barPxHeight = Math.abs(yTip - y0);
        var r = Math.min(4, barPxHeight / 2);

        var d;
        if (v >= 0) {{
          d = 'M ' + bx + ' ' + y0 +
              ' L ' + bx + ' ' + (yTip + r) +
              ' Q ' + bx + ' ' + yTip + ' ' + (bx + r) + ' ' + yTip +
              ' L ' + (bx + barW - r) + ' ' + yTip +
              ' Q ' + (bx + barW) + ' ' + yTip + ' ' + (bx + barW) + ' ' + (yTip + r) +
              ' L ' + (bx + barW) + ' ' + y0 + ' Z';
        }} else {{
          d = 'M ' + bx + ' ' + y0 +
              ' L ' + bx + ' ' + (yTip - r) +
              ' Q ' + bx + ' ' + yTip + ' ' + (bx + r) + ' ' + yTip +
              ' L ' + (bx + barW - r) + ' ' + yTip +
              ' Q ' + (bx + barW) + ' ' + yTip + ' ' + (bx + barW) + ' ' + (yTip - r) +
              ' L ' + (bx + barW) + ' ' + y0 + ' Z';
        }}

        var path = el('path', {{
          class: 'bar', d: d, fill: 'var(' + s.varName + ')',
          tabindex: '0', role: 'img',
          'aria-label': s.label + ', ' + year + ': ' + fmtM(v)
        }});

        var titleEl = el('title', {{}});
        titleEl.textContent = s.label + ' ' + year + ': ' + fmtM(v);
        path.appendChild(titleEl);

        path.addEventListener('pointerenter', function (evt) {{ showTooltip(evt, s, year, v); }});
        path.addEventListener('pointermove', function (evt) {{ positionTooltip(evt); }});
        path.addEventListener('pointerleave', hideTooltip);
        path.addEventListener('focus', function () {{ showTooltipAt(bx + barW / 2, yTip, s, year, v); }});
        path.addEventListener('blur', hideTooltip);

        svg.appendChild(path);
      }});
    }});

    // Sparse direct labels on the dataset's two extremes only.
    [globalMax, globalMin].forEach(function (extreme, idx) {{
      if (!extreme) return;
      if (idx === 1 && globalMin && globalMax && globalMin.i === globalMax.i && globalMin.j === globalMax.j) return;
      var s = SERIES[extreme.j];
      var bx = groupX(extreme.i) + extreme.j * (barW + barGap) + barW / 2;
      var yTip = yScale(extreme.v);
      var label = el('text', {{
        class: 'value-label', x: bx, y: extreme.v >= 0 ? yTip - 8 : yTip + 15
      }});
      label.textContent = fmtM(extreme.v);
      svg.appendChild(label);
    }});
  }}

  function showTooltip(evt, s, year, v) {{
    fillTooltip(s, year, v);
    positionTooltip(evt);
    tooltip.classList.add('visible');
  }}
  function showTooltipAt(cx, cy, s, year, v) {{
    fillTooltip(s, year, v);
    var rect = svg.getBoundingClientRect();
    var wrapRect = chartWrap.getBoundingClientRect();
    var scale = rect.width / W;
    tooltip.style.left = (rect.left - wrapRect.left + cx * scale) + 'px';
    tooltip.style.top = (rect.top - wrapRect.top + cy * scale) + 'px';
    tooltip.classList.add('visible');
  }}
  function fillTooltip(s, year, v) {{
    tooltip.textContent = '';
    var yearEl = document.createElement('div');
    yearEl.className = 'tooltip-year';
    yearEl.textContent = 'FY' + year;
    tooltip.appendChild(yearEl);

    var row = document.createElement('div');
    row.className = 'tooltip-row';
    var key = document.createElement('span');
    key.className = 'tooltip-key';
    key.style.background = 'var(' + s.varName + ')';
    var label = document.createElement('span');
    label.className = 'tooltip-label';
    label.textContent = s.label;
    var value = document.createElement('span');
    value.className = 'tooltip-value';
    value.textContent = fmtM(v);
    row.appendChild(key);
    row.appendChild(label);
    row.appendChild(value);
    tooltip.appendChild(row);
  }}
  function positionTooltip(evt) {{
    var wrapRect = chartWrap.getBoundingClientRect();
    tooltip.style.left = (evt.clientX - wrapRect.left) + 'px';
    tooltip.style.top = (evt.clientY - wrapRect.top) + 'px';
  }}
  function hideTooltip() {{
    tooltip.classList.remove('visible');
  }}

  function buildTable() {{
    var table = document.createElement('table');
    table.className = 'data-table';

    var thead = document.createElement('thead');
    var headRow = document.createElement('tr');
    var thYear = document.createElement('th');
    thYear.textContent = 'Fiscal Year';
    headRow.appendChild(thYear);
    SERIES.forEach(function (s) {{
      var th = document.createElement('th');
      var sw = document.createElement('span');
      sw.className = 'th-swatch';
      sw.style.background = 'var(' + s.varName + ')';
      th.appendChild(sw);
      th.appendChild(document.createTextNode(s.label));
      headRow.appendChild(th);
    }});
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    YEARS.forEach(function (year, i) {{
      var tr = document.createElement('tr');
      var tdYear = document.createElement('td');
      tdYear.textContent = String(year);
      tr.appendChild(tdYear);
      SERIES.forEach(function (s) {{
        var v = s.values[i];
        var td = document.createElement('td');
        if (v !== null && v !== undefined && v < 0) td.className = 'negative';
        td.textContent = fmtM(v);
        tr.appendChild(td);
      }});
      tbody.appendChild(tr);
    }});
    table.appendChild(tbody);

    tableWrap.textContent = '';
    tableWrap.appendChild(table);
  }}

  var showingTable = false;
  viewToggle.addEventListener('click', function () {{
    showingTable = !showingTable;
    chartWrap.hidden = showingTable;
    tableWrap.hidden = !showingTable;
    viewToggle.textContent = showingTable ? 'Show chart' : 'Show data table';
    viewToggle.setAttribute('aria-pressed', String(showingTable));
  }});

  buildLegend();
  buildChart();
  buildTable();
}})();
</script>
"""




def render_chart_card_markup(chart_data: dict) -> str:
    """Just the chart's <div class="card">...</div> fragment — no .viz-root
    wrapper, no <style>, no <title>. Composable into a larger page."""
    ticker = html_lib.escape(chart_data["ticker"])
    company_name = html_lib.escape(chart_data["companyName"])
    source_file = html_lib.escape(chart_data["sourceFile"])
    return CHART_CARD_TEMPLATE.format(
        company_name=company_name,
        ticker=ticker,
        year_min=chart_data["years"][0],
        year_max=chart_data["years"][-1],
        currency_name=chart_data["currencyName"],
        currency=html_lib.escape(chart_data["currency"]),
        unit_label=chart_data["unitLabel"],
        source_file=source_file,
    )


def render_chart_scripts(chart_data: dict) -> str:
    """The chart's <script> blocks: the embedded JSON data blob plus the
    rendering/interaction JS. Composable into a larger page."""
    chart_json = json.dumps(chart_data, ensure_ascii=False).replace("</", "<\\/")
    return CHART_SCRIPTS_TEMPLATE.format(chart_json=chart_json)


def render_html(chart_data: dict) -> str:
    ticker = html_lib.escape(chart_data["ticker"])
    title = f"{ticker} Financial Trends"
    style = TOKENS_CSS + "\n\n" + CARD_BASE_CSS + "\n\n" + CHART_CSS + "\n\n" + FOOTER_CSS
    return (
        f"<title>{title}</title>\n<style>\n{style}\n</style>\n\n"
        f'<div class="viz-root">\n{render_chart_card_markup(chart_data)}\n</div>\n\n'
        f"{render_chart_scripts(chart_data)}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="Ticker symbol, e.g. PLTR, AAPL, or ACKR_TA / MTRX_TA for TASE stocks")
    parser.add_argument("--output", "-o", help="Output HTML path (default: <ticker>_financials_chart.html in cwd)")
    args = parser.parse_args()

    try:
        cache_file = resolve_cache_file(args.ticker)
        chart_data = build_chart_data(cache_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    html_out = render_html(chart_data)

    if args.output:
        output_path = Path(args.output)
    else:
        safe_ticker = chart_data["ticker"].replace(".", "_")
        output_path = Path.cwd() / f"{safe_ticker}_financials_chart.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_out, encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
