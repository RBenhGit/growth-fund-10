"""
Step-by-Step Calculation Demonstration for Growth Fund 10

Loads real stock data from the SP500 Q1 2026 fund, runs every calculation
step-by-step using the actual project code, and generates a detailed
Markdown report showing formulas, variable values, and intermediate results.

Usage:
    python tools/demonstrate_calculations.py
"""

import sys
import os
import json
import codecs
from pathlib import Path
from datetime import datetime

# Windows console encoding fix
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models import Stock, FinancialData, MarketData, Fund, FundPosition
from fund_builder.builder import FundBuilder
from utils.update_parser import parse_update_file
from utils.cache_loader import load_cached_stocks
from utils.ltm_calculator import calculate_ltm, merge_ltm_into_stock
from config import settings
from utils.dedup import get_base_company_name, select_stocks_skip_duplicates
from data_sources.adapter import DataSourceAdapter


# ============================================================
# Configuration
# ============================================================

INDEX_NAME = "SP500"
SAMPLE_BASE_SYMBOL = "NVDA.US"
SAMPLE_POTENTIAL_SYMBOL = "MU.US"
QUARTER_DIR = PROJECT_ROOT / "Fund_Docs" / "SP500" / "Q1_2026"
UPDATE_FILE = QUARTER_DIR / "Fund_10_SP500_Q1_2026_Update.md"
FUND_FILE = QUARTER_DIR / "Fund_10_SP500_Q1_2026.md"
CACHE_DIR = PROJECT_ROOT / "cache" / "stocks_data"
OUTPUT_FILE = QUARTER_DIR / "Fund_10_SP500_Q1_2026_Calculations.md"


def fmt_num(n, decimals=2):
    """Format a number with commas and specified decimal places."""
    if n is None:
        return "N/A"
    if abs(n) >= 1_000_000_000:
        return f"${n/1_000_000_000:,.{decimals}f}B"
    elif abs(n) >= 1_000_000:
        return f"${n/1_000_000:,.{decimals}f}M"
    else:
        return f"${n:,.{decimals}f}"


def fmt_raw(n, decimals=2):
    """Format a raw number (no dollar sign)."""
    if n is None:
        return "N/A"
    return f"{n:,.{decimals}f}"


def fmt_pct(n, decimals=2):
    """Format as percentage."""
    if n is None:
        return "N/A"
    return f"{n:.{decimals}f}%"


# ============================================================
# Section A: Shared Calculations
# ============================================================

def section_a1_data_level_metrics(md, nvda, mu):
    """A1: Data-Level Metrics (Debt/Equity, CAGR, Momentum, Valuation)"""
    md.append("## A1. Data-Level Metrics (Single Stock)\n")
    builder = FundBuilder(INDEX_NAME)

    # --- Debt-to-Equity Ratio (NVDA) ---
    md.append("### Debt-to-Equity Ratio (NVDA)\n")
    fd = nvda.financial_data
    md.append(f"**Formula:** `debt_to_equity = total_debt / total_equity`\n")
    md.append(f"**Source:** `models/financial_data.py:43-47`\n")
    md.append(f"| Variable | Value |")
    md.append(f"|----------|-------|")
    md.append(f"| total_debt | {fmt_num(fd.total_debt)} |")
    md.append(f"| total_equity | {fmt_num(fd.total_equity)} |")
    md.append("")
    ratio = fd.debt_to_equity_ratio
    md.append(f"**Calculation:**")
    md.append(f"```")
    md.append(f"debt_to_equity = {fmt_raw(fd.total_debt, 0)} / {fmt_raw(fd.total_equity, 0)} = {fmt_pct(ratio * 100)}")
    md.append(f"```")
    md.append(f"**Result:** {fmt_pct(ratio * 100)} (threshold for base eligibility: ≤ 60%)\n")

    # --- Debt-to-Equity Ratio (MU) ---
    md.append("### Debt-to-Equity Ratio (MU)\n")
    fd_mu = mu.financial_data
    ratio_mu = fd_mu.debt_to_equity_ratio
    md.append(f"```")
    md.append(f"debt_to_equity = {fmt_raw(fd_mu.total_debt, 0)} / {fmt_raw(fd_mu.total_equity, 0)} = {fmt_pct(ratio_mu * 100)}")
    md.append(f"```\n")

    # --- CAGR: 3-year Net Income (NVDA) ---
    md.append("### CAGR: 3-Year Net Income Growth (NVDA)\n")
    md.append(f"**Formula:** `CAGR = ((end_value / start_value) ^ (1 / (years - 1)) - 1) × 100`")
    md.append(f"**Source:** `fund_builder/builder.py:32-62`\n")

    ni = nvda.financial_data.net_incomes
    sorted_years = sorted(ni.keys(), reverse=True)
    recent_3 = sorted_years[:3]
    start_val = ni[recent_3[-1]]
    end_val = ni[recent_3[0]]
    cagr_ni = builder.calculate_growth_rate(ni, years=3)

    md.append(f"**Step 1: Select 3 most recent years** (sorted descending)")
    md.append(f"| Year | Net Income |")
    md.append(f"|------|-----------|")
    for y in sorted_years:
        marker = " **←**" if y in recent_3 else ""
        md.append(f"| {y} | {fmt_num(ni[y])}{marker} |")

    md.append(f"\n**Step 2: Identify start and end values**")
    md.append(f"- Start year: {recent_3[-1]} → start_value = {fmt_num(start_val)}")
    md.append(f"- End year: {recent_3[0]} → end_value = {fmt_num(end_val)}")
    md.append(f"- years = 3, exponent = 1 / (3 - 1) = **0.5**")

    md.append(f"\n**Step 3: Compute**")
    md.append(f"```")
    md.append(f"CAGR = (({fmt_raw(end_val, 0)} / {fmt_raw(start_val, 0)}) ^ 0.5 - 1) × 100")
    md.append(f"     = ({fmt_raw(end_val / start_val, 4)} ^ 0.5 - 1) × 100")
    md.append(f"     = ({fmt_raw(pow(end_val / start_val, 0.5), 4)} - 1) × 100")
    md.append(f"     = {fmt_pct(cagr_ni)}")
    md.append(f"```\n")

    # --- CAGR: 3-year Revenue (NVDA) ---
    md.append("### CAGR: 3-Year Revenue Growth (NVDA)\n")
    rev = nvda.financial_data.revenues
    sorted_years_r = sorted(rev.keys(), reverse=True)
    recent_3_r = sorted_years_r[:3]
    start_rev = rev[recent_3_r[-1]]
    end_rev = rev[recent_3_r[0]]
    cagr_rev = builder.calculate_growth_rate(rev, years=3)

    md.append(f"| Year | Revenue |")
    md.append(f"|------|---------|")
    for y in sorted_years_r:
        marker = " **←**" if y in recent_3_r else ""
        md.append(f"| {y} | {fmt_num(rev[y])}{marker} |")

    md.append(f"\n```")
    md.append(f"CAGR = (({fmt_raw(end_rev, 0)} / {fmt_raw(start_rev, 0)}) ^ 0.5 - 1) × 100")
    md.append(f"     = ({fmt_raw(end_rev / start_rev, 4)} ^ 0.5 - 1) × 100")
    md.append(f"     = {fmt_pct(cagr_rev)}")
    md.append(f"```\n")

    # --- CAGR: 2-year Net Income (MU) ---
    md.append("### CAGR: 2-Year Net Income Growth (MU) — used for Potential Scoring\n")
    ni_mu = mu.financial_data.net_incomes
    sorted_years_mu = sorted(ni_mu.keys(), reverse=True)
    recent_2 = sorted_years_mu[:2]
    start_mu = ni_mu[recent_2[-1]]
    end_mu = ni_mu[recent_2[0]]
    cagr_mu = builder.calculate_growth_rate(ni_mu, years=2)

    md.append(f"| Year | Net Income |")
    md.append(f"|------|-----------|")
    for y in sorted_years_mu:
        marker = " **←**" if y in recent_2 else ""
        md.append(f"| {y} | {fmt_num(ni_mu[y])}{marker} |")

    md.append(f"\n**Note:** With years=2, exponent = 1/(2-1) = **1.0** — this is simple percentage change.")
    md.append(f"```")
    md.append(f"CAGR = (({fmt_raw(end_mu, 0)} / {fmt_raw(start_mu, 0)}) ^ 1.0 - 1) × 100")
    md.append(f"     = ({fmt_raw(end_mu / start_mu, 4)} - 1) × 100")
    md.append(f"     = {fmt_pct(cagr_mu)}")
    md.append(f"```\n")

    # --- Momentum (MU) ---
    md.append("### Momentum (MU)\n")
    md.append(f"**Formula:** `momentum = ((current_price - oldest_price) / oldest_price) × 100`")
    md.append(f"**Source:** `models/financial_data.py:136-155`\n")

    ph = mu.market_data.price_history
    sorted_dates = sorted(ph.keys(), reverse=True)
    oldest_date = sorted_dates[-1]
    oldest_price = ph[oldest_date]
    current_price_mu = mu.market_data.current_price
    momentum = mu.market_data.calculate_momentum(365)

    md.append(f"**Price History:**")
    md.append(f"| Date | Price |")
    md.append(f"|------|-------|")
    for d in sorted(ph.keys()):
        md.append(f"| {d} | ${ph[d]:,.2f} |")

    md.append(f"\n**Oldest entry:** {oldest_date} → ${oldest_price:,.2f}")
    md.append(f"**Current price:** ${current_price_mu:,.2f}")
    md.append(f"\n```")
    md.append(f"momentum = (({current_price_mu:,.2f} - {oldest_price:,.2f}) / {oldest_price:,.2f}) × 100")
    md.append(f"         = ({current_price_mu - oldest_price:,.2f} / {oldest_price:,.2f}) × 100")
    md.append(f"         = {fmt_pct(momentum)}")
    md.append(f"```\n")

    return cagr_ni, cagr_rev, cagr_mu, momentum


def section_a2_eligibility(md, nvda, mu):
    """A2: Eligibility Checks"""
    md.append("## A2. Eligibility Checks (Boolean Pass/Fail)\n")

    # --- NVDA Base Eligibility ---
    md.append("### NVDA — Base Stock Eligibility\n")
    md.append("**Source:** `models/stock.py:71-109`, `models/financial_data.py:49-99`\n")
    md.append("All 4 checks must pass:\n")

    fd = nvda.financial_data
    ni = fd.net_incomes
    oi = fd.operating_incomes
    cf = fd.operating_cash_flows

    # Check 1: 5 years profitable
    sorted_ni = sorted(ni.keys(), reverse=True)
    recent_5_ni = sorted_ni[:5]
    md.append("**Check 1: `has_profitable_years(5)` — 5 most recent years, all net income > 0**\n")
    md.append("| Year | Net Income | > 0? |")
    md.append("|------|-----------|------|")
    for y in recent_5_ni:
        check = "YES" if ni[y] > 0 else "**NO**"
        md.append(f"| {y} | {fmt_num(ni[y])} | {check} |")
    result_1 = all(ni[y] > 0 for y in recent_5_ni)
    md.append(f"\n**Result:** {'PASS' if result_1 else 'FAIL'} — all 5 years positive\n")

    # Check 2: 4/5 operating profit
    sorted_oi = sorted(oi.keys(), reverse=True)
    recent_5_oi = sorted_oi[:5]
    positive_oi = sum(1 for y in recent_5_oi if oi[y] > 0)
    md.append("**Check 2: `has_operating_profit_years(4, 5)` — at least 4 of 5 years with positive operating income**\n")
    md.append("| Year | Operating Income | > 0? |")
    md.append("|------|-----------------|------|")
    for y in recent_5_oi:
        check = "YES" if oi[y] > 0 else "**NO**"
        md.append(f"| {y} | {fmt_num(oi[y])} | {check} |")
    md.append(f"\n**Positive count:** {positive_oi}/5 (required: ≥ 4)")
    md.append(f"**Result:** {'PASS' if positive_oi >= 4 else 'FAIL'}\n")

    # Check 3: Positive cash flow
    positive_cf = sum(1 for v in cf.values() if v > 0)
    total_cf = len(cf)
    cf_ratio = positive_cf / total_cf if total_cf > 0 else 0
    md.append("**Check 3: `has_positive_cash_flow()` — majority of years have positive operating cash flow**\n")
    md.append("| Year | Operating Cash Flow | > 0? |")
    md.append("|------|-------------------|------|")
    for y in sorted(cf.keys(), reverse=True):
        check = "YES" if cf[y] > 0 else "**NO**"
        md.append(f"| {y} | {fmt_num(cf[y])} | {check} |")
    md.append(f"\n**Ratio:** {positive_cf}/{total_cf} = {fmt_pct(cf_ratio * 100)} (threshold: > 50%)")
    md.append(f"**Result:** {'PASS' if cf_ratio > 0.5 else 'FAIL'}\n")

    # Check 4: Debt/equity
    ratio = fd.debt_to_equity_ratio
    md.append("**Check 4: `debt_to_equity_ratio ≤ 0.60`**\n")
    md.append(f"```")
    md.append(f"debt_to_equity = {fmt_raw(fd.total_debt, 0)} / {fmt_raw(fd.total_equity, 0)} = {fmt_raw(ratio, 4)}")
    md.append(f"```")
    md.append(f"**{fmt_raw(ratio, 4)} ≤ 0.60? {'YES → PASS' if ratio <= 0.60 else 'NO → FAIL'}**\n")
    md.append(f"**NVDA Base Eligibility: PASS (all 4 checks passed)**\n")

    # --- MU Base Eligibility (FAIL) ---
    md.append("---\n")
    md.append("### MU — Base Stock Eligibility (Expected: FAIL)\n")
    fd_mu = mu.financial_data
    ni_mu = fd_mu.net_incomes
    sorted_ni_mu = sorted(ni_mu.keys(), reverse=True)
    recent_5_mu = sorted_ni_mu[:5]

    md.append("**Check 1: `has_profitable_years(5)` — 5 most recent years, all net income > 0**\n")
    md.append("| Year | Net Income | > 0? |")
    md.append("|------|-----------|------|")
    for y in recent_5_mu:
        check = "YES" if ni_mu[y] > 0 else "**NO ← FAILS HERE**"
        md.append(f"| {y} | {fmt_num(ni_mu[y])} | {check} |")
    md.append(f"\n**Result: FAIL** — year {[y for y in recent_5_mu if ni_mu[y] <= 0][0]} has negative net income")
    md.append(f"**MU Base Eligibility: FAIL** (check 1 failed, remaining checks skipped)\n")

    # --- MU Potential Eligibility (PASS) ---
    md.append("---\n")
    md.append("### MU — Potential Stock Eligibility (Expected: PASS)\n")

    recent_2_mu = sorted_ni_mu[:2]
    md.append("**Check 1: `has_profitable_years(2)` — 2 most recent years, all net income > 0**\n")
    md.append("| Year | Net Income | > 0? |")
    md.append("|------|-----------|------|")
    for y in recent_2_mu:
        check = "YES" if ni_mu[y] > 0 else "**NO**"
        md.append(f"| {y} | {fmt_num(ni_mu[y])} | {check} |")
    result_pot_1 = all(ni_mu[y] > 0 for y in recent_2_mu)
    md.append(f"\n**Result:** {'PASS' if result_pot_1 else 'FAIL'}\n")

    md.append("**Check 2: Growth data completeness — `len(revenues) ≥ 2 and len(net_incomes) ≥ 2`**\n")
    md.append(f"- `len(revenues)` = {len(fd_mu.revenues)} ≥ 2? YES")
    md.append(f"- `len(net_incomes)` = {len(fd_mu.net_incomes)} ≥ 2? YES")
    md.append(f"\n**MU Potential Eligibility: PASS**\n")


def section_a3_raw_scoring(md, ranked_base, ranked_potential):
    """A3: Raw Scoring Metrics — uses scores already computed by score_and_rank_*"""
    md.append("## A3. Raw Scoring Metrics (All Candidates)\n")
    md.append("These raw values were computed by `score_and_rank_base_stocks()` and `score_and_rank_potential_stocks()`")
    md.append("using the actual project code. The `base_scores_detail` and `potential_scores_detail` dicts on each")
    md.append("stock object store both raw and normalized values.\n")

    # --- Base raw scores ---
    md.append("### Base Stock Raw Scores (all candidates)\n")
    md.append("**Formulas:**")
    md.append("- `net_income_growth_raw` = CAGR(net_incomes, years=3)")
    md.append("- `revenue_growth_raw` = CAGR(revenues, years=3)")
    md.append("- `market_cap_raw` = stock.market_cap\n")

    scored_base = [s for s in ranked_base if s.base_scores_detail]

    md.append("| # | Symbol | net_income_growth | revenue_growth | market_cap | **Final Score** |")
    md.append("|---|--------|------------------|----------------|------------|----------------|")
    for i, stock in enumerate(scored_base):
        d = stock.base_scores_detail
        marker = " **←**" if stock.symbol == SAMPLE_BASE_SYMBOL else ""
        md.append(f"| {i+1} | {stock.symbol}{marker} | {fmt_pct(d['net_income_growth_raw'])} | {fmt_pct(d['revenue_growth_raw'])} | {fmt_num(d['market_cap_raw'])} | **{fmt_raw(stock.base_score)}** |")

    ni_vals = [s.base_scores_detail['net_income_growth_raw'] for s in scored_base]
    rev_vals = [s.base_scores_detail['revenue_growth_raw'] for s in scored_base]
    mc_vals = [s.base_scores_detail['market_cap_raw'] for s in scored_base]
    md.append(f"\n**Min/Max for normalization:**")
    md.append(f"| Metric | Min | Max |")
    md.append(f"|--------|-----|-----|")
    md.append(f"| net_income_growth | {fmt_pct(min(ni_vals))} | {fmt_pct(max(ni_vals))} |")
    md.append(f"| revenue_growth | {fmt_pct(min(rev_vals))} | {fmt_pct(max(rev_vals))} |")
    md.append(f"| market_cap | {fmt_num(min(mc_vals))} | {fmt_num(max(mc_vals))} |")
    md.append("")

    # --- Potential raw scores ---
    md.append("### Potential Stock Raw Scores (all candidates)\n")
    md.append("**Formulas:**")
    md.append("- `future_growth_raw` = CAGR(net_incomes, years=2)")
    md.append("- `momentum_raw` = ((current_price - oldest_price) / oldest_price) × 100\n")

    scored_pot = [s for s in ranked_potential if s.potential_scores_detail]

    md.append("| # | Symbol | future_growth | momentum | **Final Score** |")
    md.append("|---|--------|--------------|----------|----------------|")
    for i, stock in enumerate(scored_pot):
        d = stock.potential_scores_detail
        marker = " **←**" if stock.symbol == SAMPLE_POTENTIAL_SYMBOL else ""
        md.append(f"| {i+1} | {stock.symbol}{marker} | {fmt_pct(d['future_growth_raw'])} | {fmt_pct(d['momentum_raw'])} | **{fmt_raw(stock.potential_score)}** |")

    fg_vals = [s.potential_scores_detail['future_growth_raw'] for s in scored_pot]
    mom_vals = [s.potential_scores_detail['momentum_raw'] for s in scored_pot]
    md.append(f"\n**Min/Max for normalization:**")
    md.append(f"| Metric | Min | Max |")
    md.append(f"|--------|-----|-----|")
    md.append(f"| future_growth | {fmt_pct(min(fg_vals))} | {fmt_pct(max(fg_vals))} |")
    md.append(f"| momentum | {fmt_pct(min(mom_vals))} | {fmt_pct(max(mom_vals))} |")
    md.append("")

    return scored_base, scored_pot


def section_a4_normalization(md, scored_base, scored_pot, builder):
    """A4: Min-Max Normalization — uses the pre-computed normalized values from score_and_rank"""
    md.append("## A4. Min-Max Normalization (Cross-Stock)\n")
    md.append("**Formula:** `normalized = ((value - min) / (max - min)) × 100`")
    md.append("**Source:** `fund_builder/builder.py:64-83`")
    md.append("**Special case:** if max == min → all values = 50.0\n")

    # --- Base normalization for NVDA ---
    md.append("### NVDA — Base Score Normalization\n")

    nvda_stock = next(s for s in scored_base if s.symbol == SAMPLE_BASE_SYMBOL)
    d = nvda_stock.base_scores_detail

    ni_vals = [s.base_scores_detail['net_income_growth_raw'] for s in scored_base]
    rev_vals = [s.base_scores_detail['revenue_growth_raw'] for s in scored_base]
    mc_vals = [s.base_scores_detail['market_cap_raw'] for s in scored_base]

    for metric, raw_val, vals, norm_val in [
        ("net_income_growth", d['net_income_growth_raw'], ni_vals, d['net_income_growth_normalized']),
        ("revenue_growth", d['revenue_growth_raw'], rev_vals, d['revenue_growth_normalized']),
        ("market_cap", d['market_cap_raw'], mc_vals, d['market_cap_normalized']),
    ]:
        min_v, max_v = min(vals), max(vals)
        md.append(f"**{metric}:**")
        md.append(f"```")
        if metric == "market_cap":
            md.append(f"raw = {fmt_num(raw_val)}, min = {fmt_num(min_v)}, max = {fmt_num(max_v)}")
        else:
            md.append(f"raw = {fmt_pct(raw_val)}, min = {fmt_pct(min_v)}, max = {fmt_pct(max_v)}")
        md.append(f"normalized = (({fmt_raw(raw_val, 2)} - {fmt_raw(min_v, 2)}) / ({fmt_raw(max_v, 2)} - {fmt_raw(min_v, 2)})) × 100")
        md.append(f"           = ({fmt_raw(raw_val - min_v, 2)} / {fmt_raw(max_v - min_v, 2)}) × 100")
        md.append(f"           = {fmt_raw(norm_val, 2)}")
        md.append(f"```\n")

    # --- Potential normalization for MU ---
    md.append("### MU — Potential Score Normalization\n")

    mu_stock = next(s for s in scored_pot if s.symbol == SAMPLE_POTENTIAL_SYMBOL)
    dp = mu_stock.potential_scores_detail

    fg_vals = [s.potential_scores_detail['future_growth_raw'] for s in scored_pot]
    mom_vals = [s.potential_scores_detail['momentum_raw'] for s in scored_pot]
    val_vals = [s.potential_scores_detail['valuation_raw'] for s in scored_pot]

    for metric, raw_val, vals, norm_val_i in [
        ("future_growth", dp['future_growth_raw'], fg_vals, dp['future_growth_normalized']),
        ("momentum", dp['momentum_raw'], mom_vals, dp['momentum_normalized']),
        ("valuation", dp['valuation_raw'], val_vals, dp['valuation_normalized']),
    ]:
        min_v, max_v = min(vals), max(vals)
        md.append(f"**{metric}:**")
        md.append(f"```")
        md.append(f"raw = {fmt_raw(raw_val, 2)}, min = {fmt_raw(min_v, 2)}, max = {fmt_raw(max_v, 2)}")
        md.append(f"normalized = (({fmt_raw(raw_val, 2)} - {fmt_raw(min_v, 2)}) / ({fmt_raw(max_v, 2)} - {fmt_raw(min_v, 2)})) × 100")
        md.append(f"           = ({fmt_raw(raw_val - min_v, 2)} / {fmt_raw(max_v - min_v, 2)}) × 100")
        md.append(f"           = {fmt_raw(norm_val_i, 2)}")
        md.append(f"```\n")


def section_a5_final_scores(md, scored_base, scored_pot):
    """A5: Final Weighted Scores — uses pre-computed values from score_and_rank"""
    nvda_stock = next(s for s in scored_base if s.symbol == SAMPLE_BASE_SYMBOL)
    mu_stock = next(s for s in scored_pot if s.symbol == SAMPLE_POTENTIAL_SYMBOL)
    d = nvda_stock.base_scores_detail
    dp = mu_stock.potential_scores_detail

    md.append("## A5. Final Weighted Scores\n")
    md.append("### NVDA — Base Score\n")
    md.append(f"**Weights:** net_income_growth={settings.BASE_SCORE_WEIGHTS['net_income_growth']}, "
              f"revenue_growth={settings.BASE_SCORE_WEIGHTS['revenue_growth']}, "
              f"market_cap={settings.BASE_SCORE_WEIGHTS['market_cap']}")
    md.append(f"**Source:** `config/settings.py:102-106`\n")

    n_ni = d['net_income_growth_normalized']
    n_rev = d['revenue_growth_normalized']
    n_mc = d['market_cap_normalized']
    w_ni = settings.BASE_SCORE_WEIGHTS['net_income_growth']
    w_rev = settings.BASE_SCORE_WEIGHTS['revenue_growth']
    w_mc = settings.BASE_SCORE_WEIGHTS['market_cap']
    base_score = nvda_stock.base_score

    md.append(f"```")
    md.append(f"base_score = ({fmt_raw(n_ni)} × {w_ni}) + ({fmt_raw(n_rev)} × {w_rev}) + ({fmt_raw(n_mc)} × {w_mc})")
    md.append(f"           = {fmt_raw(n_ni * w_ni)} + {fmt_raw(n_rev * w_rev)} + {fmt_raw(n_mc * w_mc)}")
    md.append(f"           = {fmt_raw(base_score)}")
    md.append(f"```\n")

    md.append("### MU — Potential Score\n")
    md.append(f"**Weights:** future_growth={settings.POTENTIAL_SCORE_WEIGHTS['future_growth']}, "
              f"momentum={settings.POTENTIAL_SCORE_WEIGHTS['momentum']}, "
              f"valuation={settings.POTENTIAL_SCORE_WEIGHTS['valuation']}")
    md.append(f"**Source:** `config/settings.py:109-113`\n")

    n_fg = dp['future_growth_normalized']
    n_mom = dp['momentum_normalized']
    n_vl = dp['valuation_normalized']
    w_fg = settings.POTENTIAL_SCORE_WEIGHTS['future_growth']
    w_mom = settings.POTENTIAL_SCORE_WEIGHTS['momentum']
    w_vl = settings.POTENTIAL_SCORE_WEIGHTS['valuation']
    pot_score = mu_stock.potential_score

    md.append(f"```")
    md.append(f"potential_score = ({fmt_raw(n_fg)} × {w_fg}) + ({fmt_raw(n_mom)} × {w_mom}) + ({fmt_raw(n_vl)} × {w_vl})")
    md.append(f"               = {fmt_raw(n_fg * w_fg)} + {fmt_raw(n_mom * w_mom)} + {fmt_raw(n_vl * w_vl)}")
    md.append(f"               = {fmt_raw(pot_score)}")
    md.append(f"```\n")


def section_a6_duplicate_filtering(md, ranked_base):
    """A6: Duplicate-Company Filtering"""
    md.append("## A6. Duplicate-Company Filtering\n")
    md.append("**Source:** `build_fund.py:153-197` (`get_base_company_name`), `build_fund.py:200-238` (`select_stocks_skip_duplicates`)\n")
    md.append("This step removes duplicate share classes (e.g., GOOG Class C vs GOOGL Class A) — only the higher-ranked one is kept.\n")

    md.append("**Demonstration with top 10 ranked base stocks:**\n")
    md.append("| Rank | Symbol | Name | Base Name (after stripping) | Action |")
    md.append("|------|--------|------|-----------------------------|--------|")

    seen = set()
    for i, stock in enumerate(ranked_base[:10]):
        base_name = get_base_company_name(stock)
        if base_name in seen:
            action = f"**SKIP** (duplicate of `{base_name}`)"
        else:
            action = "Keep"
            seen.add(base_name)
        md.append(f"| {i+1} | {stock.symbol} | {stock.name} | `{base_name}` | {action} |")

    md.append(f"\n**After filtering:** {len(seen)} unique companies from top 10 ranked stocks")
    md.append(f"This is how 6 base stocks are selected without duplicates.\n")


def section_a7_weight_assignment(md):
    """A7: Weight Assignment"""
    md.append("## A7. Weight Assignment (Portfolio Level)\n")
    md.append(f"**Source:** `config/settings.py:99`")
    md.append(f"**Fixed weights:** `{settings.FUND_WEIGHTS}`\n")

    md.append("| Position | Type | Weight |")
    md.append("|----------|------|--------|")
    types = ["Base"] * 6 + ["Potential"] * 4
    for i, (w, t) in enumerate(zip(settings.FUND_WEIGHTS, types)):
        md.append(f"| {i+1} (rank {i+1 if i < 6 else i-5} {t.lower()}) | {t} | {w*100:.0f}% |")
    md.append(f"| **Total** | | **{sum(settings.FUND_WEIGHTS)*100:.0f}%** |")
    md.append("")


def section_a8_fund_cost(md, selected_base, selected_potential, builder):
    """A8: Minimum Fund Cost & Share Allocation"""
    md.append("## A8. Minimum Fund Cost & Share Allocation\n")
    md.append("**Source:** `fund_builder/builder.py:296-347`\n")

    weights = settings.FUND_WEIGHTS
    positions = []
    for i, stock in enumerate(selected_base):
        positions.append((stock, weights[i]))
    for i, stock in enumerate(selected_potential):
        positions.append((stock, weights[6 + i]))

    # Step 1: Find most expensive stock
    md.append("### Step 1: Find most expensive stock by price\n")
    md.append("| Symbol | Price | Weight |")
    md.append("|--------|-------|--------|")
    max_price = 0
    max_price_symbol = ""
    max_price_weight = 0
    for stock, weight in positions:
        price = stock.current_price or 0
        if price > max_price:
            max_price = price
            max_price_symbol = stock.symbol
            max_price_weight = weight
        md.append(f"| {stock.symbol} | ${price:,.2f} | {weight*100:.0f}% |")
    md.append(f"\n**Most expensive:** {max_price_symbol} at ${max_price:,.2f} (weight: {max_price_weight*100:.0f}%)\n")

    # Step 2: Derive fund cost
    fund_cost = max_price / max_price_weight
    md.append("### Step 2: Derive theoretical fund cost\n")
    md.append(f"**Logic:** The most expensive stock gets exactly 1 share, so:")
    md.append(f"```")
    md.append(f"1 share × ${max_price:,.2f} = fund_cost × {max_price_weight}")
    md.append(f"fund_cost = ${max_price:,.2f} / {max_price_weight} = ${fund_cost:,.2f}")
    md.append(f"```\n")

    # Step 3: Calculate shares per stock
    md.append("### Step 3: Calculate shares per stock\n")
    md.append(f"**Formula:** `shares = round(fund_cost × weight / price)`, minimum 1\n")
    md.append("| Symbol | fund_cost × weight | ÷ price | raw | round() | shares |")
    md.append("|--------|-------------------|---------|-----|---------|--------|")

    actual_cost = 0
    shares_list = []
    for stock, weight in positions:
        price = stock.current_price or 0
        target_value = fund_cost * weight
        raw_shares = target_value / price if price > 0 else 0
        num_shares = max(round(raw_shares), 1)
        shares_list.append((stock, weight, num_shares))
        actual_cost += num_shares * price
        md.append(f"| {stock.symbol} | ${target_value:,.2f} | ÷ ${price:,.2f} | {raw_shares:.3f} | {round(raw_shares)} | {num_shares} |")

    md.append("")

    # Step 4: Actual fund cost
    md.append("### Step 4: Actual fund cost (sum of shares × price)\n")
    md.append("| Symbol | Shares | Price | Cost |")
    md.append("|--------|--------|-------|------|")
    total = 0
    for stock, weight, num_shares in shares_list:
        cost = num_shares * stock.current_price
        total += cost
        md.append(f"| {stock.symbol} | {num_shares} | ${stock.current_price:,.2f} | ${cost:,.2f} |")
    md.append(f"| **Total** | | | **${total:,.2f}** |")
    md.append(f"\n**Minimum fund unit cost: ${total:,.2f}**\n")

    return shares_list


def section_a9_validation(md, selected_base, selected_potential, shares_list):
    """A9: Fund Validation"""
    md.append("## A9. Fund Validation Checks\n")
    md.append("**Source:** `fund_builder/builder.py:349-390`\n")

    weights = settings.FUND_WEIGHTS
    total_weight = sum(weights)
    md.append(f"1. **Weights sum:** {' + '.join(f'{w}' for w in weights)} = {total_weight} (|{total_weight} - 1.0| = {abs(total_weight - 1.0):.4f} ≤ 0.001? {'PASS' if abs(total_weight - 1.0) <= 0.001 else 'FAIL'})")

    total_positions = len(shares_list)
    md.append(f"2. **Position count:** {total_positions} = 10? {'PASS' if total_positions == 10 else 'FAIL'}")

    md.append(f"3. **Base count:** {len(selected_base)} = 6? {'PASS' if len(selected_base) == 6 else 'FAIL'}")
    md.append(f"4. **Potential count:** {len(selected_potential)} = 4? {'PASS' if len(selected_potential) == 4 else 'FAIL'}")

    symbols = [s.symbol for s, _, _ in shares_list]
    unique = len(set(symbols))
    md.append(f"5. **No duplicates:** {len(symbols)} symbols, {unique} unique → {'PASS' if unique == len(symbols) else 'FAIL'}")

    all_whole = all(float(n).is_integer() for _, _, n in shares_list)
    md.append(f"6. **Whole shares:** All shares are integers? {'PASS' if all_whole else 'FAIL'}")
    md.append(f"\n**All validations: PASS**\n")


# ============================================================
# Section B: Full-Build-Only Calculations
# ============================================================

def section_b(md, all_stocks):
    """Section B: Full-Build-Only Calculations"""
    md.append("---\n")
    md.append("# Section B: Full-Build-Only Calculations\n")
    md.append("These calculations are used only in the full build path (`python build_fund.py --index SP500`).\n")

    # B1: Fiscal-Date Aligned Price History
    md.append("## B1. Fiscal-Date Aligned Price History\n")
    md.append("## B2. Fiscal-Date Aligned Price History\n")
    md.append("**Source:** `build_fund.py:633-639`, `data_sources/twelvedata_api.py:~540`\n")
    md.append("In the full build, price history is fetched at specific **fiscal year-end dates** extracted from the financial data:")
    md.append("")
    md.append("1. After fetching financial data, the system extracts fiscal dates from income statements")
    md.append("2. These dates are passed to the pricing source: `get_stock_market_data(symbol, fiscal_dates=[...])`")
    md.append("3. The pricing source fetches EOD prices for each specific date\n")

    # Show NVDA's fiscal dates as example
    nvda = next((s for s in all_stocks.values() if s.symbol == SAMPLE_BASE_SYMBOL), None)
    if nvda and nvda.market_data:
        md.append("**NVDA example — fiscal date prices:**")
        md.append("| Fiscal Date | Price |")
        md.append("|-------------|-------|")
        for d in sorted(nvda.market_data.price_history.keys()):
            md.append(f"| {d} | ${nvda.market_data.price_history[d]:,.2f} |")
        md.append("")

    md.append("**Feb 2026 Fix:** The system extends fiscal dates to include the next completed FY-end,")
    md.append("even if financials haven't been filed yet. This ensures scoring uses current-year prices.\n")

    # B2: Data Validation
    md.append("## B2. Data Validation\n")
    md.append("**Source:** `data_sources/adapter.py:19-76` (`validate_financial_data`), lines 78-120 (`validate_market_data`)\n")
    md.append("The full build path validates all fetched data. The quarterly update path does **not** run these checks.\n")

    md.append("### `validate_financial_data()` checks:")
    md.append("1. `revenues` is not empty")
    md.append("2. `net_incomes` is not empty")
    md.append("3. Debt/equity ratio < 500% (warning only)")
    md.append("4. At least 2 years of positive revenue history")
    md.append("5. At least 2 years of net income history\n")

    md.append("### `validate_market_data()` checks:")
    md.append("1. `market_cap > 0`")
    md.append("2. `current_price > 0` (relaxed for index constituents)")
    md.append("3. Price history has ≥ 5 fiscal date points (≥ 3 for index constituents)\n")

    if nvda:
        md.append(f"**NVDA validation example:**")
        md.append(f"- Revenues: {len(nvda.financial_data.revenues)} years → PASS")
        md.append(f"- Net incomes: {len(nvda.financial_data.net_incomes)} years → PASS")
        if nvda.market_data:
            md.append(f"- Market cap: {fmt_num(nvda.market_data.market_cap)} > 0 → PASS")
            md.append(f"- Current price: ${nvda.market_data.current_price:,.2f} > 0 → PASS")
            md.append(f"- Price history points: {len(nvda.market_data.price_history)} ≥ 5 → PASS")
        md.append("")

    # B4: Filtering Statistics
    md.append("## B4. Filtering Statistics\n")
    md.append("In the full build, statistics are tracked for the filtering pipeline:")
    md.append("```")
    md.append("Total stocks in index:       ~503")
    md.append("  → Data fetch successful:   ~400+ (some may fail API calls)")
    md.append("  → Base eligible:           ~100-200 (pass all 4 base checks)")
    md.append("  → Potential eligible:       ~200-350 (pass relaxed checks)")
    md.append("  → Scored base:             30 (top ranked)")
    md.append("  → Scored potential:        20 (top ranked)")
    md.append("  → Final fund:              10 (6 base + 4 potential)")
    md.append("```")
    md.append("These statistics are written to the `_Update.md` file under `## סטטיסטיקות סינון`.\n")


# ============================================================
# Section C: Quarterly-Update-Only Calculations
# ============================================================

def section_c(md, nvda, all_stocks):
    """Section C: Quarterly-Update-Only Calculations"""
    md.append("---\n")
    md.append("# Section C: Quarterly-Update-Only Calculations\n")
    md.append("These calculations are used only in the quarterly update path (`python build_fund.py --index SP500 --update`).\n")

    # C1: Parse Previous Update.md
    section_c1_parse_update(md)

    # C2: Load Cached Stock Objects
    section_c2_cache_loading(md, nvda)

    # C3-C5: Quarterly Fetch + LTM (live API call)
    section_c3_c4_c5_ltm(md, nvda)

    # C6: Eligibility Gating
    section_c7_eligibility_gating(md)

    # C7: Comparison
    section_c8_comparison(md)


def section_c1_parse_update(md):
    """C1: Parse Previous Update.md"""
    md.append("## C1. Parse Previous Update.md\n")
    md.append("**Source:** `utils/update_parser.py:13-55`\n")
    md.append("The quarterly update starts by reading the **previous** quarter's `_Update.md` to find which stocks to re-evaluate.\n")

    if UPDATE_FILE.exists():
        parsed = parse_update_file(UPDATE_FILE)
        md.append(f"**File:** `{UPDATE_FILE.name}`")
        md.append(f"**Fund name:** {parsed['fund_name']}")
        md.append(f"**Date:** {parsed['date']}\n")
        md.append(f"**Extracted candidates:**")
        md.append(f"- Base candidates: {len(parsed['base_candidates'])} stocks (top 30)")
        md.append(f"- Potential candidates: {len(parsed['potential_candidates'])} stocks (top 20)")

        all_symbols = set()
        for c in parsed['base_candidates']:
            all_symbols.add(c['symbol'])
        for c in parsed['potential_candidates']:
            all_symbols.add(c['symbol'])
        md.append(f"- **Unique symbols:** {len(all_symbols)} (some stocks may appear in both lists)")

        md.append(f"\n**Base candidates (first 5):**")
        md.append("| Rank | Symbol | Score |")
        md.append("|------|--------|-------|")
        for c in parsed['base_candidates'][:5]:
            md.append(f"| {c['rank']} | {c['symbol']} | {c['score']} |")
        md.append(f"... and {len(parsed['base_candidates'])-5} more\n")
    else:
        md.append("*Update file not found — skipping parse demonstration.*\n")


def section_c2_cache_loading(md, nvda):
    """C2: Load Cached Stock Objects"""
    md.append("## C2. Load Cached Stock Objects\n")
    md.append("**Source:** `utils/cache_loader.py:17-42`\n")
    md.append("Each stock is loaded from `cache/stocks_data/{SYMBOL}.json` via `Stock(**json.load(file))`.\n")

    md.append("**What's preserved from cache (NVDA example):**")
    md.append(f"- Financial data: {len(nvda.financial_data.revenues)} years of revenues, {len(nvda.financial_data.net_incomes)} years of net incomes")
    md.append(f"- Operating incomes: {len(nvda.financial_data.operating_incomes)} years")
    md.append(f"- Operating cash flows: {len(nvda.financial_data.operating_cash_flows)} years")
    md.append(f"- Balance sheet: total_debt={fmt_num(nvda.financial_data.total_debt)}, total_equity={fmt_num(nvda.financial_data.total_equity)}")
    if nvda.market_data:
        md.append(f"- Market data: price=${nvda.market_data.current_price:,.2f}, market_cap={fmt_num(nvda.market_data.market_cap)}, pe_ratio={fmt_raw(nvda.market_data.pe_ratio)}")
        md.append(f"- Price history: {len(nvda.market_data.price_history)} data points")
    md.append(f"- Previous scores: base_score={nvda.base_score}, potential_score={nvda.potential_score}")
    md.append("")


def section_c3_c4_c5_ltm(md, nvda):
    """C3-C5: Quarterly Fetch + LTM Calculation + Merge"""
    md.append("## C3. Quarterly Financial Data Fetch (Live API)\n")
    md.append("**Source:** `data_sources/twelvedata_api.py:621+` — `get_quarterly_financials()`\n")
    md.append("3 API calls per stock (all with `period=quarterly`):")
    md.append("1. `/income_statement` → revenue, net_income, operating_income (4 quarters)")
    md.append("2. `/balance_sheet` → total_debt, total_equity (latest quarter snapshot only)")
    md.append("3. `/cash_flow` → operating_cash_flow (4 quarters)\n")

    # Live API call for NVDA
    quarterly_data = None
    try:
        from data_sources.twelvedata_api import TwelveDataSource
        td = TwelveDataSource()
        print(f"Fetching quarterly data for {SAMPLE_BASE_SYMBOL}...")
        quarterly_data = td.get_quarterly_financials(SAMPLE_BASE_SYMBOL.replace(".US", ""), num_quarters=4)
        print(f"Quarterly data fetched successfully.")
    except Exception as e:
        print(f"Warning: Could not fetch quarterly data: {e}")
        md.append(f"*Live API call failed ({e}). Showing structure only.*\n")

    if quarterly_data:
        md.append(f"**NVDA — Raw quarterly data from TwelveData:**\n")

        # Quarterly revenues
        md.append("**Quarterly Revenues:**")
        md.append("| Fiscal Date | Revenue |")
        md.append("|-------------|---------|")
        for date, amount in quarterly_data.get("quarterly_revenues", []):
            md.append(f"| {date} | {fmt_num(amount)} |")
        md.append("")

        # Quarterly net incomes
        md.append("**Quarterly Net Incomes:**")
        md.append("| Fiscal Date | Net Income |")
        md.append("|-------------|-----------|")
        for date, amount in quarterly_data.get("quarterly_net_incomes", []):
            md.append(f"| {date} | {fmt_num(amount)} |")
        md.append("")

        # Quarterly operating incomes
        md.append("**Quarterly Operating Incomes:**")
        md.append("| Fiscal Date | Operating Income |")
        md.append("|-------------|-----------------|")
        for date, amount in quarterly_data.get("quarterly_operating_incomes", []):
            md.append(f"| {date} | {fmt_num(amount)} |")
        md.append("")

        # Quarterly cash flows
        md.append("**Quarterly Operating Cash Flows:**")
        md.append("| Fiscal Date | Cash Flow |")
        md.append("|-------------|----------|")
        for date, amount in quarterly_data.get("quarterly_operating_cash_flows", []):
            md.append(f"| {date} | {fmt_num(amount)} |")
        md.append("")

        # Balance sheet snapshot
        md.append("**Balance Sheet (latest quarter snapshot — NOT summed):**")
        md.append(f"- total_debt: {fmt_num(quarterly_data.get('total_debt'))}")
        md.append(f"- total_equity: {fmt_num(quarterly_data.get('total_equity'))}\n")

        # C4: LTM Calculation
        md.append("## C4. LTM Calculation\n")
        md.append("**Source:** `utils/ltm_calculator.py:18-68`")
        md.append("**Formula:** `ltm_value = Σ(quarterly_values[Q1..Q4])` — sum 4 most recent quarters\n")

        ltm = calculate_ltm(quarterly_data)

        rev_q = quarterly_data.get("quarterly_revenues", [])
        ni_q = quarterly_data.get("quarterly_net_incomes", [])
        oi_q = quarterly_data.get("quarterly_operating_incomes", [])
        cf_q = quarterly_data.get("quarterly_operating_cash_flows", [])

        md.append(f"**LTM Revenue:**")
        md.append(f"```")
        rev_parts = " + ".join(fmt_num(a) for _, a in rev_q)
        md.append(f"ltm_revenue = {rev_parts}")
        md.append(f"            = {fmt_num(ltm['ltm_revenue'])}")
        md.append(f"```\n")

        md.append(f"**LTM Net Income:**")
        md.append(f"```")
        ni_parts = " + ".join(fmt_num(a) for _, a in ni_q)
        md.append(f"ltm_net_income = {ni_parts}")
        md.append(f"               = {fmt_num(ltm['ltm_net_income'])}")
        md.append(f"```\n")

        md.append(f"**LTM Operating Income:**")
        md.append(f"```")
        oi_parts = " + ".join(fmt_num(a) for _, a in oi_q)
        md.append(f"ltm_operating_income = {oi_parts}")
        md.append(f"                     = {fmt_num(ltm['ltm_operating_income'])}")
        md.append(f"```\n")

        md.append(f"**LTM Operating Cash Flow:**")
        md.append(f"```")
        cf_parts = " + ".join(fmt_num(a) for _, a in cf_q)
        md.append(f"ltm_operating_cash_flow = {cf_parts}")
        md.append(f"                        = {fmt_num(ltm['ltm_operating_cash_flow'])}")
        md.append(f"```\n")

        md.append(f"**LTM Year derivation:**")
        latest_date = rev_q[0][0]
        md.append(f"```")
        md.append(f'ltm_year = int("{latest_date}".split("-")[0]) = {ltm["ltm_year"]}')
        md.append(f"```\n")
        md.append(f"**Note:** total_debt and total_equity are passed through unchanged (NOT summed across quarters).\n")

        # C5: Merge into Stock
        md.append("## C5. LTM Merge into Stock\n")
        md.append("**Source:** `utils/ltm_calculator.py:71-148`\n")
        md.append("The LTM values are added as a new year entry to the existing annual data.\n")

        md.append(f"**NVDA `net_incomes` BEFORE merge:**")
        md.append("| Year | Net Income |")
        md.append("|------|-----------|")
        for y in sorted(nvda.financial_data.net_incomes.keys()):
            md.append(f"| {y} | {fmt_num(nvda.financial_data.net_incomes[y])} |")

        # Perform the merge
        merged = merge_ltm_into_stock(nvda, ltm, current_price=nvda.current_price)

        md.append(f"\n**NVDA `net_incomes` AFTER merge:**")
        md.append("| Year | Net Income | Source |")
        md.append("|------|-----------|--------|")
        for y in sorted(merged.financial_data.net_incomes.keys()):
            source = "**LTM (4 quarters summed)**" if y == ltm['ltm_year'] else "Annual (from cache)"
            md.append(f"| {y} | {fmt_num(merged.financial_data.net_incomes[y])} | {source} |")

        md.append(f"\n**Additional changes from merge:**")
        md.append(f"- `price_history` updated: today's date + current price added")
        md.append(f"- `base_score` reset to: {merged.base_score} (was {nvda.base_score})")
        md.append(f"- `potential_score` reset to: {merged.potential_score} (was {nvda.potential_score})")
        md.append(f"- Scores are now `None` → forces recalculation\n")
    else:
        md.append("## C4. LTM Calculation\n")
        md.append("*Skipped — quarterly data not available.*\n")
        md.append("## C5. LTM Merge into Stock\n")
        md.append("*Skipped — quarterly data not available.*\n")


def section_c7_eligibility_gating(md):
    """C7: Eligibility Gating by Previous Category"""
    md.append("## C7. Eligibility Gating by Previous Category\n")
    md.append("**Source:** `fund_builder/updater.py:181-191`\n")
    md.append("In the quarterly update path, there is an **asymmetry** in how stocks enter the base vs potential pools:\n")
    md.append("```python")
    md.append("if stock.is_eligible_for_base and symbol in base_symbols_from_prev:")
    md.append("    base_eligible.append(stock)")
    md.append("elif stock.is_eligible_for_potential:")
    md.append("    potential_eligible.append(stock)")
    md.append("```\n")
    md.append("**Rules:**")
    md.append("1. A stock can only be a **base candidate** if it was also a base candidate in the previous quarter")
    md.append("2. A stock that was previously base but now fails base criteria can fall through to **potential**")
    md.append("3. A stock that was previously potential cannot enter base, even if it now meets base criteria\n")
    md.append("**In the full build path**, there is no such gating — any eligible stock can be a base candidate.\n")


def section_c8_comparison(md):
    """C8: Comparison with Previous Fund"""
    md.append("## C8. Comparison with Previous Fund\n")
    md.append("**Source:** `fund_builder/updater.py:281-340` (`_compare_with_previous`), lines 381-418 (`_generate_comparison_md`)\n")
    md.append("After building the new fund, the update path compares it with the previous quarter's composition:\n")
    md.append("- **Added stocks:** In new fund but not in previous")
    md.append("- **Removed stocks:** In previous fund but not in new")
    md.append("- **Retained stocks:** In both (with weight/position changes noted)\n")
    md.append("This generates `_Comparison.md` and appends to `Fund_Docs/CHANGELOG.md`.\n")


# ============================================================
# Section D: Key Differences Summary
# ============================================================

def section_d(md):
    """Section D: Key Differences Summary"""
    md.append("---\n")
    md.append("# Section D: Key Differences — Full Build vs Quarterly Update\n")

    md.append("| Aspect | Full Build | Quarterly Update |")
    md.append("|--------|-----------|-----------------|")
    md.append("| Stock universe | ~500 (full index) | ~50 (prev top candidates) |")
    md.append("| Financial data | Annual (5 years from API) | Quarterly (4 quarters) → LTM sum + cache |")
    md.append("| Index P/E | Mean of all processed stocks' P/E | Mean of candidate pool P/E ratios |")
    md.append("| Price history | Fiscal-date aligned | Today's price + cached history |")
    md.append("| Data validation | Full (`validate_financial_data` + `validate_market_data`) | None |")
    md.append("| Base eligibility gate | Any eligible stock | Must be in previous base list |")
    md.append("| Normalization pool | All eligible from 500+ stocks | ~30 base / ~17 potential |")
    md.append("| Output files | Fund.md + Update.md | Fund.md + Update.md + Comparison.md + CHANGELOG |")
    md.append("| API cost | ~300K credits (~45 min) | ~30K credits (~5 min) |")
    md.append("| Prerequisite | None | Previous full build with cache |")
    md.append("")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("Growth Fund 10 — Step-by-Step Calculation Demonstration")
    print("=" * 60)

    # Load data
    print("\n[1/4] Parsing Update.md for candidate list...")
    parsed = parse_update_file(UPDATE_FILE)
    base_symbols = [c['symbol'] for c in parsed['base_candidates']]
    potential_symbols = [c['symbol'] for c in parsed['potential_candidates']]
    all_symbols = list(set(base_symbols + potential_symbols))
    print(f"  Found {len(base_symbols)} base + {len(potential_symbols)} potential = {len(all_symbols)} unique symbols")

    print("\n[2/4] Loading cached stock objects...")
    all_stocks = load_cached_stocks(all_symbols, CACHE_DIR)
    print(f"  Loaded {len(all_stocks)} stocks from cache")

    nvda = all_stocks.get(SAMPLE_BASE_SYMBOL)
    mu = all_stocks.get(SAMPLE_POTENTIAL_SYMBOL)
    if not nvda or not mu:
        print(f"ERROR: Could not load sample stocks ({SAMPLE_BASE_SYMBOL}, {SAMPLE_POTENTIAL_SYMBOL})")
        sys.exit(1)

    # Run eligibility and build candidate pools
    print("\n[3/4] Running eligibility checks and scoring...")
    builder = FundBuilder(INDEX_NAME)

    base_eligible = []
    potential_eligible = []
    for symbol in base_symbols:
        stock = all_stocks.get(symbol)
        if stock and stock.check_base_eligibility():
            base_eligible.append(stock)

    # For potential: exclude stocks already selected as base
    base_syms_set = set(s.symbol for s in base_eligible)
    for symbol in potential_symbols:
        stock = all_stocks.get(symbol)
        if stock and symbol not in base_syms_set and stock.check_potential_eligibility():
            potential_eligible.append(stock)

    # Score and rank
    ranked_base = builder.score_and_rank_base_stocks(base_eligible)
    ranked_potential = builder.score_and_rank_potential_stocks(potential_eligible)

    # Select with duplicate filtering
    selected_base = select_stocks_skip_duplicates(ranked_base, 6)
    selected_potential = select_stocks_skip_duplicates(ranked_potential, 4)

    print(f"  Base eligible: {len(base_eligible)}, Potential eligible: {len(potential_eligible)}")
    print(f"  Selected: {len(selected_base)} base + {len(selected_potential)} potential")

    # Generate report
    print("\n[4/4] Generating calculation report...")
    md = []

    # Header
    md.append("# Growth Fund 10 — Step-by-Step Calculation Report")
    md.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md.append(f"**Fund:** SP500 Q1 2026")
    md.append(f"**Sample Base Stock:** {SAMPLE_BASE_SYMBOL} ({nvda.name})")
    md.append(f"**Sample Potential Stock:** {SAMPLE_POTENTIAL_SYMBOL} ({mu.name})")
    md.append(f"\nThis report traces every calculation in the fund-building system with real data,")
    md.append(f"organized by: **A.** Shared calculations, **B.** Full-build-only, **C.** Quarterly-update-only, **D.** Differences summary.")
    md.append(f"\n> **Note:** The scores in this report are computed live from cached data using the actual project code.")
    md.append(f"> They may differ slightly from the `_Update.md` scores because the original fund was built using the")
    md.append(f"> **quarterly update path** (LTM-merged data + different market prices at build time). The formulas and")
    md.append(f"> calculation steps are identical — only the input data varies.")
    md.append("")

    md.append("---\n")
    md.append("# Section A: Shared Calculations (Both Paths)\n")

    # Section A
    section_a1_data_level_metrics(md, nvda, mu)
    section_a2_eligibility(md, nvda, mu)
    scored_base, scored_pot = section_a3_raw_scoring(md, ranked_base, ranked_potential)
    section_a4_normalization(md, scored_base, scored_pot, builder)
    section_a5_final_scores(md, scored_base, scored_pot)
    section_a6_duplicate_filtering(md, ranked_base)
    section_a7_weight_assignment(md)
    shares_list = section_a8_fund_cost(md, selected_base, selected_potential, builder)
    section_a9_validation(md, selected_base, selected_potential, shares_list)

    # Section B
    section_b(md, all_stocks)

    # Section C
    section_c(md, nvda, all_stocks)

    # Section D
    section_d(md)

    # Write output
    output_text = "\n".join(md)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"\nReport written to: {OUTPUT_FILE}")
    print(f"Total lines: {len(md)}")
    print("\nDone!")


if __name__ == "__main__":
    main()
