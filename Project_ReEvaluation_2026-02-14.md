# Project Re-Evaluation Report
**Date:** February 14, 2026
**Focus:** Full Project
**Previous Assessment:** Growth_Fund_10_Project_Assessment_Q1_2026.md

## Executive Summary

The Growth Fund 10 project is well-structured and largely consistent between documentation and implementation. However, this re-evaluation uncovered **3 documentation errors** (including a critical weight mismatch in CLAUDE.md), **1 filename discrepancy**, **2 missing .env.template entries**, **1 dead config variable**, and significant **test coverage gaps** in core modules. The quarterly update system added since the last assessment is properly implemented and documented.

---

## Findings

### 1. Documentation Accuracy

| Area | Doc Says | Code Does | Status |
|------|----------|-----------|--------|
| FUND_WEIGHTS (settings.py) | `[0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]` | Same | **Match** |
| FUND_WEIGHTS (CLAUDE.md Step 9) | `20%, 16%, 14%, 12%, 10%, 8%, 6%, 5%, 5%, 4%` | Code: `18%, 16%, 16%, 10%, 10%, 10%, 6%, 6%, 4%, 4%` | **MISMATCH** |
| FUND_WEIGHTS (README.md) | `18%, 16%, 16%, 10%, 10%, 0%, 6%, 6%, 4%, 4%` | Code: 6th position is 10%, not 0% | **TYPO** |
| BASE_SCORE_WEIGHTS | `{0.40, 0.35, 0.25}` | Same in `config/settings.py:104-108` | **Match** |
| POTENTIAL_SCORE_WEIGHTS | `{0.50, 0.30, 0.20}` | Same in `config/settings.py:111-115` | **Match** |
| Base eligibility: 5yr profit | 5+ years positive net income | `models/stock.py:92` checks `min_profitable_years: 5` | **Match** |
| Base eligibility: operating | 4/5 years positive operating income | `models/stock.py:96` | **Match** |
| Base eligibility: debt/equity | < 60% | `models/stock.py:105` checks `< 0.60` | **Match** |
| Potential eligibility | 2+ years positive net income | `models/stock.py:132` checks `min_profitable_years: 2` | **Match** |
| CLI args (build_fund.py) | 7 args documented | All 7 present in argparse | **Match** |
| CLI args (backtest.py) | fund_file, --years (10), --output-dir | All present, defaults match | **Match** |
| Fallback chains (router.py) | US Fin: td→av, US Price: yf→td→av, TASE Fin: td, TASE Price: yf→td | All match at `router.py:55-105` | **Match** |
| Legacy config fallback | DATA_SOURCE → FINANCIAL/PRICING → 2x2 matrix | `settings.py:56-75` implements correctly | **Match** |
| Fund composition | 6 base + 4 potential = 10 stocks | Code confirms | **Match** |
| Quarterly update steps | 10-step LTM process | `fund_builder/updater.py` implements all 10 | **Match** |
| Output dir structure | `Fund_Docs/{INDEX}/{Q}_{YEAR}/` | `date_utils.py:161-174` confirms | **Match** |
| date_utils functions | 5 functions documented | All 5 exist + 7 undocumented helpers | **Match** (partial) |

### 2. Critical Documentation Errors

#### 2.1 CLAUDE.md Step 9 — Wrong Weight Values
**Location:** `CLAUDE.md:153`
**Doc says:** "Assign Fixed Weights — 20%, 16%, 14%, 12%, 10%, 8%, 6%, 5%, 5%, 4%"
**Code says:** `[0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]` = 18%, 16%, 16%, 10%, 10%, 10%, 6%, 6%, 4%, 4%
**Impact:** These are completely different weight distributions. The Step 9 description appears to be from an older version.
**Note:** The "Scoring System Constants" section of the same file (line 200) correctly shows the actual values.

#### 2.2 README.md — Typo in Weights
**Location:** `README.md:34`
**Doc says:** "Fixed Weights: 18%, 16%, 16%, 10%, 10%, **0%**, 6%, 6%, 4%, 4%"
**Should be:** "18%, 16%, 16%, 10%, 10%, **10%**, 6%, 6%, 4%, 4%"
**Impact:** The documented weights sum to 90% instead of 100%. The "0%" is clearly a typo for "10%".

#### 2.3 CLAUDE.md — Wrong Filename Reference
**Location:** `CLAUDE.md:109`
**Doc says:** `fund_builder/fund_builder.py`
**Actual file:** `fund_builder/builder.py`
**Impact:** Misleading for developers looking for the fund construction module.

### 3. Undocumented Code

| File | Purpose | In CLAUDE.md? | In README? |
|------|---------|---------------|------------|
| `data_sources/exceptions.py` | Custom exception classes (8 exception types) | No | No |
| `tests/test_current_data.py` | API data freshness verification | No | No |
| `tests/test_price_alignment.py` | Fiscal year-end price alignment tests | No | No |
| `tests/test_symbol_normalization.py` | Symbol format normalization tests | No | No |
| `tests/test_tase_api.py` | TASE Data Hub API connection testing | No | No |
| `tests/verify_index.py` | S&P 500 constituents verification | No | No |
| `utils/date_utils.py` — 7 helper functions | `get_current_quarter()`, `get_current_year()`, `quarter_to_month()`, `get_quarters_elapsed()`, `get_current_date_string()`, `get_years_range()`, `_quarter_sort_key()` | No | No |

### 4. Dead References

| Reference | Location | Status |
|-----------|----------|--------|
| `fund_builder/fund_builder.py` | CLAUDE.md:109 | File is actually `fund_builder/builder.py` |
| `FUND_DATE` env var | config/settings.py:94 | Read from env but never used anywhere in codebase |
| Previous assessment says "Remaining enhancement: Quarterly update automation" | Growth_Fund_10_Project_Assessment_Q1_2026.md:18 | Now implemented — assessment is outdated |
| `Fund_Docs/Fund_10_SP500_Q4_2025.md` in README examples | README.md:216, 232, 237, 429 | File moved to `Fund_Docs/SP500/Q4_2025/` — paths are stale |

### 5. Configuration Alignment

| Variable | .env.template | settings.py | Code Usage | Status |
|----------|---------------|-------------|------------|--------|
| `US_FINANCIAL_DATA_SOURCE` | Line 17 (blank) | Line 39, default `""` | router.py:55 | **Match** |
| `US_PRICING_DATA_SOURCE` | Line 22 (`yfinance`) | Line 43, default `"yfinance"` | router.py:100 | **Match** |
| `TASE_FINANCIAL_DATA_SOURCE` | Line 31 (blank) | Line 47, default `""` | router.py:58 | **Match** |
| `TASE_PRICING_DATA_SOURCE` | Line 36 (`yfinance`) | Line 51, default `"yfinance"` | router.py:103 | **Match** |
| `FINANCIAL_DATA_SOURCE` | Line 89 (commented) | Line 26, default `"twelvedata"` | settings.py:58-61 | **Match** |
| `PRICING_DATA_SOURCE` | Line 90 (commented) | Line 28, default `"twelvedata"` | settings.py:64-67 | **Match** |
| `DATA_SOURCE` | Line 93 (commented) | Line 70-75 (fallback) | settings.py:70-75 | **Match** |
| `ALPHAVANTAGE_API_KEY` | Line 104 | Line 82 | alphavantage_api.py | **Match** |
| `TWELVEDATA_API_KEY` | Line 113 | Line 86 | twelvedata_api.py | **Match** |
| `TWELVEDATA_CREDITS_PER_MINUTE` | Line 121 | Line 88, default `0` | twelvedata_api.py | **Match** |
| `TWELVEDATA_MAX_STOCKS_PER_MINUTE` | Line 122 | Line 89, default `0` | twelvedata_api.py | **Match** |
| `OUTPUT_DIRECTORY` | Line 128 | Line 21, default `"./Fund_Docs"` | build_fund.py | **Match** |
| `USE_CACHE` | Line 129 | Line 97, default `"true"` | build_fund.py | **Match** |
| `DEBUG_MODE` | Line 130 | Line 98, default `"false"` | build_fund.py | **Match** |
| `FUND_QUARTER` | Line 133 | Line 92, default `None` | build_fund.py | **Match** |
| `FUND_YEAR` | Line 134 | Line 93, default `None` | build_fund.py | **Match** |
| `ALPHAVANTAGE_RATE_LIMIT` | **MISSING** | Line 83, default `"paid"` | alphavantage_api.py:32 | **Missing from template** |
| `FUND_DATE` | **MISSING** | Line 94, default `None` | **Never used** | **Dead code** |
| `TASE_DATA_HUB_API_KEY` | **MISSING** | N/A (test only) | tests/test_tase_api.py:19 | **Test-only, minor** |

### 6. Constants & Weights Verification

| Constant | Documented Value | Code Value | File:Line | Status |
|----------|-----------------|------------|-----------|--------|
| FUND_WEIGHTS | `[0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]` | Same | config/settings.py:101 | **Match** |
| BASE_SCORE net_income_growth | 0.40 | 0.40 | config/settings.py:105 | **Match** |
| BASE_SCORE revenue_growth | 0.35 | 0.35 | config/settings.py:106 | **Match** |
| BASE_SCORE market_cap | 0.25 | 0.25 | config/settings.py:107 | **Match** |
| POTENTIAL_SCORE future_growth | 0.50 | 0.50 | config/settings.py:112 | **Match** |
| POTENTIAL_SCORE momentum | 0.30 | 0.30 | config/settings.py:113 | **Match** |
| POTENTIAL_SCORE valuation | 0.20 | 0.20 | config/settings.py:114 | **Match** |
| BASE min_profitable_years | 5 | 5 | config/settings.py:119 | **Match** |
| BASE min_operating_profit_years | 4 | 4 | config/settings.py:120 | **Match** |
| BASE max_debt_to_equity | 0.60 | 0.60 | config/settings.py:121 | **Match** |
| POTENTIAL min_profitable_years | 2 | 2 | config/settings.py:126 | **Match** |
| Step 9 weights (CLAUDE.md) | 20/16/14/12/10/8/6/5/5/4 | 18/16/16/10/10/10/6/6/4/4 | CLAUDE.md:153 | **MISMATCH** |
| Fixed Weights (README.md) | 18/16/16/10/10/0/6/6/4/4 | 18/16/16/10/10/10/6/6/4/4 | README.md:34 | **TYPO** |

### 7. Test Coverage Gaps

| Module/Feature | Has Tests | Notes |
|----------------|-----------|-------|
| `fund_builder/builder.py` | **NO** | Core 14-step fund construction — ZERO test coverage |
| `models/stock.py` (eligibility) | **NO** | `check_base_eligibility()`, `check_potential_eligibility()` untested |
| `models/fund.py` | **NO** | Fund/FundPosition composition models untested |
| `models/financial_data.py` | **NO** | FinancialData/MarketData validation untested |
| `backtest.py` | **NO** | Entire backtesting engine — ZERO test coverage |
| `data_sources/adapter.py` | **Partial** | Used in integration tests, no dedicated unit tests |
| `data_sources/router.py` | **Partial** | Tested in test_all_sources.py integration, no unit tests |
| `fund_builder/updater.py` | **Partial** | Integration tests only in test_quarterly_update.py |
| `utils/date_utils.py` | **YES** | Well covered in test_quarterly_update.py |
| `utils/update_parser.py` | **YES** | Covered in test_quarterly_update.py |
| `utils/cache_loader.py` | **YES** | Covered in test_quarterly_update.py |
| `utils/ltm_calculator.py` | **YES** | Covered in test_quarterly_update.py |
| `utils/changelog.py` | **YES** | Covered in test_quarterly_update.py |
| `data_sources/twelvedata_api.py` | **YES** | Covered in test_all_sources.py + test_price_alignment.py |
| `data_sources/yfinance_source.py` | **YES** | Covered in test_all_sources.py |

---

## Recommendations

### Priority 1 — Fix Documentation Errors (< 5 min each)

1. **Fix CLAUDE.md:153** — Replace Step 9 weights `20%, 16%, 14%, 12%, 10%, 8%, 6%, 5%, 5%, 4%` with `18%, 16%, 16%, 10%, 10%, 10%, 6%, 6%, 4%, 4%`

2. **Fix README.md:34** — Change `10%, 10%, 0%, 6%` to `10%, 10%, 10%, 6%`

3. **Fix CLAUDE.md:109** — Rename `fund_builder/fund_builder.py` to `fund_builder/builder.py`

4. **Fix README.md backtest examples** — Update paths from `Fund_Docs/Fund_10_SP500_Q4_2025.md` to `Fund_Docs/SP500/Q4_2025/Fund_10_SP500_Q4_2025.md` (lines 216, 232, 237)

### Priority 2 — Configuration Cleanup (< 10 min)

5. **Add `ALPHAVANTAGE_RATE_LIMIT` to .env.template** — Currently used in code but undocumented. Add after line 104:
   ```
   ALPHAVANTAGE_RATE_LIMIT=paid  # "free" (5 req/min) or "paid" (75 req/min)
   ```

6. **Remove `FUND_DATE` from settings.py** — Read from env but never used anywhere. Dead code.

### Priority 3 — Documentation Completeness (< 15 min)

7. **Add `data_sources/exceptions.py` to CLAUDE.md directory listing** — Used throughout the codebase but not mentioned

8. **Add undocumented test files to CLAUDE.md** — 5 test files not listed: `test_current_data.py`, `test_price_alignment.py`, `test_symbol_normalization.py`, `test_tase_api.py`, `verify_index.py`

9. **Update previous assessment report** — `Growth_Fund_10_Project_Assessment_Q1_2026.md:18` states quarterly update is a "remaining enhancement" — it's now implemented

### Priority 4 — Test Coverage (Ongoing)

10. **Add unit tests for `models/stock.py`** — Eligibility logic is core to correctness; should have dedicated tests

11. **Add unit tests for `fund_builder/builder.py`** — The 14-step scoring/selection algorithm is the heart of the system with zero test coverage

12. **Add basic tests for `backtest.py`** — Entire backtesting engine is untested

13. **Add unit tests for `models/financial_data.py` and `models/fund.py`** — Data validation models should have dedicated coverage

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Documented files verified | 23/23 exist |
| Documentation errors found | 3 (2 weight mismatches, 1 wrong filename) |
| Stale path references | 3 (README backtest examples) |
| Undocumented source files | 2 (exceptions.py + 5 test files) |
| Config variables matched | 15/15 match |
| Missing from .env.template | 2 (ALPHAVANTAGE_RATE_LIMIT, FUND_DATE) |
| Dead config variables | 1 (FUND_DATE) |
| Constants verified correct | 11/11 match code |
| Modules with no tests | 5 (builder, stock, fund, financial_data, backtest) |
| Modules with partial tests | 3 (adapter, router, updater) |
| Modules well tested | 7 |
