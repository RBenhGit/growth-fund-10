#!/usr/bin/env python3
"""Generate a self-contained HTML "fund snapshot" for one ticker: eligibility
(base/potential) recomputed live from its cached fundamentals with a
per-criterion breakdown, its score breakdown if it was scored in the last
full build or quarterly update, and the same financial trend chart as the
stock-financials-chart skill (reused via import, not rebuilt).
"""

import argparse
import html as html_lib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CHART_SKILL_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "stock-financials-chart" / "scripts"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(CHART_SKILL_SCRIPTS))

from models.stock import Stock  # noqa: E402
from utils.cache_loader import load_cached_stock  # noqa: E402
from config import settings  # noqa: E402

from generate_chart import (  # noqa: E402
    resolve_cache_file,
    build_chart_data,
    render_chart_card_markup,
    render_chart_scripts,
    TOKENS_CSS,
    CARD_BASE_CSS,
    CHART_CSS,
    FOOTER_CSS,
)


def to_dotted_symbol(cache_file: Path) -> str:
    ticker, suffix = cache_file.stem.rsplit("_", 1)
    return f"{ticker}.{suffix}"


# ---------------------------------------------------------------- formatting

def fmt_currency_compact(value, currency: str) -> str:
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    abs_v = abs(value)
    if abs_v >= 1_000_000_000:
        return f"{sign}{currency}{abs_v / 1_000_000_000:.1f}B"
    if abs_v >= 1_000_000:
        return f"{sign}{currency}{abs_v / 1_000_000:.1f}M"
    return f"{sign}{currency}{abs_v:,.0f}"


def fmt_pct(value) -> str:
    return "—" if value is None else f"{value:.2f}%"


def fmt_ratio(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def fmt_rank(value) -> str:
    return "—" if value is None else f"{value:.1f} / 100"


def fmt2(value) -> str:
    return "—" if value is None else f"{value:.2f}"


# --------------------------------------------------------------- eligibility

def recompute_eligibility(stock: Stock) -> dict:
    # Snapshot the cached flags BEFORE calling check_*_eligibility() — those
    # methods mutate is_eligible_for_base/potential in place, so reading
    # afterward would always show "no mismatch".
    stored_base = stock.is_eligible_for_base
    stored_potential = stock.is_eligible_for_potential
    recomputed_base = stock.check_base_eligibility(**settings.BASE_ELIGIBILITY)
    recomputed_potential = stock.check_potential_eligibility(**settings.POTENTIAL_ELIGIBILITY)
    return {
        "stored_base": stored_base,
        "stored_potential": stored_potential,
        "base": recomputed_base,
        "potential": recomputed_potential,
        "base_mismatch": stored_base != recomputed_base,
        "potential_mismatch": stored_potential != recomputed_potential,
    }


def base_criteria_rows(fd, currency: str) -> list:
    if fd is None:
        return []
    cfg = settings.BASE_ELIGIBILITY
    min_years = cfg["min_profitable_years"]
    op_required = cfg["min_operating_profit_years"]
    max_dte = cfg["max_debt_to_equity"]

    rows = []

    sorted_ni_years = sorted(fd.net_incomes.keys(), reverse=True)
    recent_ni = sorted_ni_years[:min_years]
    ni_pass_count = sum(1 for y in recent_ni if fd.net_incomes[y] > 0)
    ok = len(fd.net_incomes) >= min_years and ni_pass_count == len(recent_ni)
    rows.append({
        "label": f"{min_years} consecutive profitable years (net income &gt; 0)",
        "detail": f"{ni_pass_count}/{len(recent_ni)} of the most recent years positive" if recent_ni else "no net income history",
        "status": "pass" if ok else "fail",
    })

    ok = len(fd.revenues) >= min_years
    rows.append({
        "label": f"≥{min_years} years of revenue history",
        "detail": f"{len(fd.revenues)} years on file",
        "status": "pass" if ok else "fail",
    })

    sorted_oi_years = sorted(fd.operating_incomes.keys(), reverse=True)
    recent_oi = sorted_oi_years[:min_years]
    oi_pass_count = sum(1 for y in recent_oi if fd.operating_incomes[y] > 0)
    ok = len(fd.operating_incomes) >= min_years and oi_pass_count >= op_required
    rows.append({
        "label": f"Operating profit in ≥{op_required} of last {min_years} years",
        "detail": f"{oi_pass_count}/{len(recent_oi)} years positive" if recent_oi else "no operating income history",
        "status": "pass" if ok else "fail",
    })

    cfs = fd.operating_cash_flows
    if cfs:
        cf_pass_count = sum(1 for v in cfs.values() if v > 0)
        frac = cf_pass_count / len(cfs)
        ok = frac > 0.5
        detail = f"{cf_pass_count}/{len(cfs)} years positive ({frac * 100:.0f}%)"
    else:
        ok = False
        detail = "no cash flow history"
    rows.append({
        "label": "Positive operating cash flow in a majority of years",
        "detail": detail,
        "status": "pass" if ok else "fail",
    })

    eq = fd.total_equity
    if eq is None:
        rows.append({"label": "Positive shareholders' equity", "detail": "no equity data on file", "status": "na"})
    else:
        rows.append({
            "label": "Positive shareholders' equity",
            "detail": fmt_currency_compact(eq, currency),
            "status": "pass" if eq > 0 else "fail",
        })

    ratio = fd.debt_to_equity_ratio
    if ratio is None:
        rows.append({"label": f"Debt/Equity ratio &lt; {max_dte * 100:.0f}%", "detail": "no equity data on file", "status": "na"})
    else:
        rows.append({
            "label": f"Debt/Equity ratio &lt; {max_dte * 100:.0f}%",
            "detail": f"{ratio * 100:.1f}%",
            "status": "pass" if ratio <= max_dte else "fail",
        })

    return rows


def potential_criteria_rows(fd) -> list:
    if fd is None:
        return []
    min_years = settings.POTENTIAL_ELIGIBILITY["min_profitable_years"]

    rows = []
    sorted_ni_years = sorted(fd.net_incomes.keys(), reverse=True)
    recent_ni = sorted_ni_years[:min_years]
    ni_pass_count = sum(1 for y in recent_ni if fd.net_incomes[y] > 0)
    ok = len(fd.net_incomes) >= min_years and ni_pass_count == len(recent_ni)
    rows.append({
        "label": f"{min_years} most-recent years profitable (net income &gt; 0)",
        "detail": f"{ni_pass_count}/{len(recent_ni)} of the most recent years positive" if recent_ni else "no net income history",
        "status": "pass" if ok else "fail",
    })

    ok = len(fd.revenues) >= 3 and len(fd.net_incomes) >= 3
    rows.append({
        "label": "Complete growth data (≥3 years revenue &amp; net income)",
        "detail": f"revenue: {len(fd.revenues)} years, net income: {len(fd.net_incomes)} years",
        "status": "pass" if ok else "fail",
    })

    return rows


def render_criteria_table(rows: list) -> str:
    if not rows:
        return ""
    badge_class = {"pass": "badge-pass", "fail": "badge-fail", "na": "badge-na"}
    badge_text = {"pass": "PASS", "fail": "FAIL", "na": "N/A"}
    body_rows = []
    for r in rows:
        body_rows.append(
            f'<tr><td>{r["label"]}<div class="criterion-detail">{html_lib.escape(r["detail"])}</div></td>'
            f'<td><span class="badge {badge_class[r["status"]]}">{badge_text[r["status"]]}</span></td></tr>'
        )
    return (
        '<table class="data-table criteria-table"><thead><tr><th>Criterion</th><th>Result</th></tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table>'
    )


# --------------------------------------------------------------------- score

def render_score_summary(stock: Stock) -> str:
    """The headline numbers shown right under the eligibility badges — just the
    stated score, not the breakdown (that lives further down, see
    render_base_score_components / render_potential_score_components)."""
    lines = []
    if stock.base_score is not None:
        lines.append(f'<p class="score-headline">Base Score: <strong>{stock.base_score:.2f}</strong> / 100</p>')
    else:
        lines.append('<p class="score-muted">Base Score: not scored as a Base candidate in the last full build or quarterly update.</p>')
    if stock.potential_score is not None:
        lines.append(f'<p class="score-headline">Potential Score: <strong>{stock.potential_score:.2f}</strong> / 100</p>')
    else:
        lines.append('<p class="score-muted">Potential Score: not scored as a Potential candidate in the last full build or quarterly update.</p>')
    return "".join(lines)


def render_base_score_components(stock: Stock, currency: str) -> str:
    """The Base Score breakdown table. Empty string if there's no score to break
    down — the null case is already covered by render_score_summary() above."""
    if stock.base_score is None or not stock.base_scores_detail:
        return ""
    d = stock.base_scores_detail
    w = settings.BASE_SCORE_WEIGHTS
    stability = settings.STABILITY_BLEND
    cagr_w = 1 - stability

    ni_blended = d.get("ni_blended")
    rev_blended = d.get("rev_blended")
    mcap_rank = d.get("mcap_rank")

    ni_contrib = w["net_income_growth"] * ni_blended if ni_blended is not None else None
    rev_contrib = w["revenue_growth"] * rev_blended if rev_blended is not None else None
    mcap_contrib = w["market_cap"] * mcap_rank if mcap_rank is not None else None
    contribs = [c for c in (ni_contrib, rev_contrib, mcap_contrib) if c is not None]
    total = sum(contribs) if contribs else None

    rows = (
        '<tr><td>Net Income Growth<div class="criterion-detail">'
        f'CAGR {fmt_pct(d.get("net_income_growth_raw"))} (rank {fmt_rank(d.get("ni_cagr_rank"))}) &middot; '
        f'Stability R&sup2; {fmt_ratio(d.get("net_income_stability_raw"))} (rank {fmt_rank(d.get("ni_stab_rank"))})'
        f'</div></td><td>{fmt_rank(ni_blended)}</td><td>{w["net_income_growth"] * 100:.0f}%</td><td>{fmt2(ni_contrib)}</td></tr>'
        '<tr><td>Revenue Growth<div class="criterion-detail">'
        f'CAGR {fmt_pct(d.get("revenue_growth_raw"))} (rank {fmt_rank(d.get("rev_cagr_rank"))}) &middot; '
        f'Stability R&sup2; {fmt_ratio(d.get("revenue_stability_raw"))} (rank {fmt_rank(d.get("rev_stab_rank"))})'
        f'</div></td><td>{fmt_rank(rev_blended)}</td><td>{w["revenue_growth"] * 100:.0f}%</td><td>{fmt2(rev_contrib)}</td></tr>'
        '<tr><td>Market Cap (size)<div class="criterion-detail">'
        f'{fmt_currency_compact(d.get("market_cap_raw"), currency)}'
        f'</div></td><td>{fmt_rank(mcap_rank)}</td><td>{w["market_cap"] * 100:.0f}%</td><td>{fmt2(mcap_contrib)}</td></tr>'
        f'<tr class="total-row"><td>Base Score</td><td></td><td>100%</td><td>{fmt2(total)}</td></tr>'
    )

    stored = stock.base_score
    note = ""
    if total is not None and abs(total - stored) > 0.05:
        note = (
            f'<p class="score-note">Recomputed total ({total:.2f}) differs from the stored score ({stored:.2f}) '
            '&mdash; weights or sub-scores may have changed since this was last written.</p>'
        )

    return (
        '<h2>Base Score Components</h2>\n'
        f'<p class="score-formula-note">Blended = {cagr_w * 100:.0f}% CAGR rank + {stability * 100:.0f}% stability rank.</p>'
        '<table class="data-table score-table"><thead><tr>'
        '<th>Component</th><th>Blended Rank</th><th>Weight</th><th>Contribution</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        f'{note}'
        '<p class="score-caption">Ranks are percentiles within the candidate pool as of the last full build or '
        'quarterly update &mdash; not recomputed live from this cache file alone.</p>'
    )


def render_potential_score_components(stock: Stock) -> str:
    """The Potential Score breakdown table. Empty string if there's no score to
    break down — the null case is already covered by render_score_summary()."""
    if stock.potential_score is None or not stock.potential_scores_detail:
        return ""
    d = stock.potential_scores_detail
    w = settings.POTENTIAL_SCORE_WEIGHTS

    growth_rank = d.get("growth_rank")
    momentum_rank = d.get("momentum_rank")
    growth_contrib = w["future_growth"] * growth_rank if growth_rank is not None else None
    momentum_contrib = w["momentum"] * momentum_rank if momentum_rank is not None else None
    contribs = [c for c in (growth_contrib, momentum_contrib) if c is not None]
    total = sum(contribs) if contribs else None

    rows = (
        '<tr><td>Future Growth (2yr Net Income CAGR)<div class="criterion-detail">'
        f'{fmt_pct(d.get("future_growth_raw"))}'
        f'</div></td><td>{fmt_rank(growth_rank)}</td><td>{w["future_growth"] * 100:.0f}%</td><td>{fmt2(growth_contrib)}</td></tr>'
        '<tr><td>Momentum (~12mo price change)<div class="criterion-detail">'
        f'{fmt_pct(d.get("momentum_raw"))}'
        f'</div></td><td>{fmt_rank(momentum_rank)}</td><td>{w["momentum"] * 100:.0f}%</td><td>{fmt2(momentum_contrib)}</td></tr>'
        f'<tr class="total-row"><td>Potential Score</td><td></td><td>100%</td><td>{fmt2(total)}</td></tr>'
    )

    stored = stock.potential_score
    note = ""
    if total is not None and abs(total - stored) > 0.05:
        note = (
            f'<p class="score-note">Recomputed total ({total:.2f}) differs from the stored score ({stored:.2f}) '
            '&mdash; weights or sub-scores may have changed since this was last written.</p>'
        )

    return (
        '<h2>Potential Score Components</h2>\n'
        '<table class="data-table score-table"><thead><tr>'
        '<th>Component</th><th>Rank</th><th>Weight</th><th>Contribution</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        f'{note}'
        '<p class="score-caption">Ranks are percentiles within the candidate pool as of the last full build or '
        'quarterly update &mdash; not recomputed live from this cache file alone.</p>'
    )


# --------------------------------------------------------------------- CSS

SCORE_CSS = """  .viz-root { --status-ok: #0ca30c; }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) .viz-root { --status-ok: #22c55e; }
  }
  :root[data-theme="dark"] .viz-root { --status-ok: #22c55e; }

  h2 {
    font-size: 14px;
    font-weight: 600;
    margin: 22px 0 10px;
    color: var(--text-primary);
  }
  h2:first-of-type { margin-top: 4px; }

  .badge-row {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
  }
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.02em;
    white-space: nowrap;
  }
  .badge-pass { background: color-mix(in srgb, var(--status-ok) 16%, transparent); color: var(--status-ok); }
  .badge-fail { background: color-mix(in srgb, var(--status-critical) 16%, transparent); color: var(--status-critical); }
  .badge-na { background: var(--gridline); color: var(--text-muted); }

  .criteria-table td:first-child, .score-table td:first-child {
    white-space: normal;
  }
  .criterion-detail {
    font-size: 11.5px;
    color: var(--text-muted);
    font-weight: 400;
    margin-top: 2px;
    white-space: normal;
  }
  .criteria-table, .score-table { margin-bottom: 4px; }
  .score-table tbody tr.total-row td {
    font-weight: 700;
    border-top: 1px solid var(--baseline);
    border-bottom: none;
  }
  .score-formula-note {
    margin: 0 0 8px;
    font-size: 11.5px;
    color: var(--text-muted);
  }
  .score-headline {
    margin: 10px 0 2px;
    font-size: 13px;
    color: var(--text-primary);
  }
  .score-note {
    margin: 4px 0;
    font-size: 12px;
    color: var(--status-critical);
  }
  .score-caption, .score-muted {
    margin: 6px 0 0;
    font-size: 11.5px;
    color: var(--text-muted);
  }
  .mismatch-note {
    margin: 0 0 12px;
    font-size: 12px;
    color: var(--status-critical);
  }

  .viz-root > .card + .card {
    margin-top: 16px;
  }"""


# ---------------------------------------------------------------- assembly

def render_results_card_markup(stock: Stock, chart_data: dict, elig: dict) -> str:
    """Title, badges, and the headline score numbers — the full score breakdowns
    live further down, in the bottom card, below the eligibility tables."""
    ticker = html_lib.escape(chart_data["ticker"])
    company_name = html_lib.escape(stock.name)
    index_name = html_lib.escape(stock.index)

    base_badge = "badge-pass" if elig["base"] else "badge-fail"
    base_text = "Base: PASS" if elig["base"] else "Base: FAIL"
    potential_badge = "badge-pass" if elig["potential"] else "badge-fail"
    potential_text = "Potential: PASS" if elig["potential"] else "Potential: FAIL"

    mismatch_notes = []
    if elig["base_mismatch"]:
        mismatch_notes.append(
            f'<p class="mismatch-note">Recomputed Base eligibility ({elig["base"]}) differs from the cached record '
            f'({elig["stored_base"]}) &mdash; criteria or the cached figures may have changed since this was last written.</p>'
        )
    if elig["potential_mismatch"]:
        mismatch_notes.append(
            f'<p class="mismatch-note">Recomputed Potential eligibility ({elig["potential"]}) differs from the cached record '
            f'({elig["stored_potential"]}) &mdash; criteria or the cached figures may have changed since this was last written.</p>'
        )

    return (
        '  <div class="card">\n'
        f'    <h1>{company_name} ({ticker}) &mdash; Fund Snapshot</h1>\n'
        f'    <p class="subtitle">{index_name} &middot; eligibility recomputed live from cached fundamentals; score as of the last build/update</p>\n\n'
        '    <div class="badge-row">\n'
        f'      <span class="badge {base_badge}">{base_text}</span>\n'
        f'      <span class="badge {potential_badge}">{potential_text}</span>\n'
        '    </div>\n'
        f'    {"".join(mismatch_notes)}\n\n'
        f'    {render_score_summary(stock)}\n'
        '  </div>'
    )


def render_eligibility_card_markup(stock: Stock, chart_data: dict) -> str:
    """Eligibility breakdown tables, then the score component breakdowns below
    them — supporting detail, below the chart."""
    source_file = html_lib.escape(chart_data["sourceFile"])
    fd = stock.financial_data
    currency = chart_data["currency"]

    base_rows = base_criteria_rows(fd, currency)
    potential_rows = potential_criteria_rows(fd)
    base_components = render_base_score_components(stock, currency)
    potential_components = render_potential_score_components(stock)

    return (
        '  <div class="card">\n'
        '    <h2>Base Eligibility</h2>\n'
        f'    {render_criteria_table(base_rows)}\n\n'
        '    <h2>Potential Eligibility</h2>\n'
        f'    {render_criteria_table(potential_rows)}\n\n'
        f'    {base_components}\n\n'
        f'    {potential_components}\n\n'
        f'    <p class="footer-note">Eligibility recomputed live from cached fundamentals ({source_file}). '
        'Scores are read as stored from the last full build or quarterly update.</p>\n'
        '  </div>'
    )


def render_html(stock: Stock, chart_data: dict, elig: dict) -> str:
    ticker = html_lib.escape(chart_data["ticker"])
    title = f"{ticker} Fund Snapshot"
    style = (
        TOKENS_CSS + "\n\n" + CARD_BASE_CSS + "\n\n" + SCORE_CSS + "\n\n"
        + CHART_CSS + "\n\n" + FOOTER_CSS
    )
    results_card = render_results_card_markup(stock, chart_data, elig)
    chart_card = render_chart_card_markup(chart_data)
    eligibility_card = render_eligibility_card_markup(stock, chart_data)
    return (
        f"<title>{title}</title>\n<style>\n{style}\n</style>\n\n"
        f'<div class="viz-root">\n{results_card}\n{chart_card}\n{eligibility_card}\n</div>\n\n'
        f"{render_chart_scripts(chart_data)}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="Ticker symbol, e.g. PLTR, AAPL, or ACKR_TA / MTRX_TA for TASE stocks")
    parser.add_argument("--output", "-o", help="Output HTML path (default: <ticker>_snapshot.html in cwd)")
    args = parser.parse_args()

    try:
        cache_file = resolve_cache_file(args.ticker)
        chart_data = build_chart_data(cache_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    dotted_symbol = to_dotted_symbol(cache_file)
    stock = load_cached_stock(dotted_symbol, cache_file.parent)
    if stock is None:
        print(f"Error: cache file {cache_file} could not be loaded as a Stock model.", file=sys.stderr)
        sys.exit(1)

    elig = recompute_eligibility(stock)
    html_out = render_html(stock, chart_data, elig)

    if args.output:
        output_path = Path(args.output)
    else:
        safe_ticker = chart_data["ticker"].replace(".", "_")
        output_path = Path.cwd() / f"{safe_ticker}_snapshot.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_out, encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
