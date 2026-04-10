# Project Re-Evaluation Report
**Date:** April 10, 2026
**Focus:** Full Project
**Previous Assessment:** Project_ReEvaluation_2026-02-14.md (deleted — findings resolved)

---

## Executive Summary

The Growth Fund 10 project remains well-structured and operationally sound. This re-evaluation found that **all 8 Priority 1/2 fixes from the February 2026 assessment were applied**. However, **3 new issues** emerged: a code bug causing malformed log filenames (`QQ1` instead of `Q1`), a surviving wrong-filename reference in README.md, and two undocumented new artifacts (`tools/` directory and `test_e2e_data_freshness.py`). Test coverage gaps in core modules persist unchanged.

---

## Previous Findings Status

All 8 previously flagged issues were resolved:

| # | Issue | Was | Now |
|---|-------|-----|-----|
| 1 | CLAUDE.md Step 9 weights | `20%, 16%, 14%...` | ✅ `18%, 16%, 16%...` |
| 2 | README.md weight typo | `10%, 10%, 0%, 6%` | ✅ `10%, 10%, 10%, 6%` |
| 3 | CLAUDE.md wrong filename | `fund_builder/fund_builder.py` | ✅ `fund_builder/builder.py` |
| 4 | README.md stale backtest paths | Missing `SP500/Q4_2025/` subdirectory | ✅ Correct paths |
| 5 | `.env.template` missing `ALPHAVANTAGE_RATE_LIMIT` | Absent | ✅ Line 108 |
| 6 | Dead `FUND_DATE` in settings.py | Present, unused | ✅ Removed |
| 7 | `exceptions.py` undocumented | Not in CLAUDE.md | ✅ CLAUDE.md:108 |
| 8 | `test_quarterly_update.py` undocumented | Not in CLAUDE.md | ✅ CLAUDE.md:121 |

---

## Findings

### Documentation Accuracy

| Area | Doc Says | Code Does | Status |
|------|----------|-----------|--------|
| FUND_WEIGHTS (settings.py) | `[0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]` | Same at `config/settings.py:99` | **Match** |
| FUND_WEIGHTS (CLAUDE.md Step 9 :158) | `18%, 16%, 16%, 10%, 10%, 10%, 6%, 6%, 4%, 4%` | Same | **Match** |
| FUND_WEIGHTS (README.md :34) | `18%, 16%, 16%, 10%, 10%, 10%, 6%, 6%, 4%, 4%` | Same | **Match** |
| BASE_SCORE_WEIGHTS | `{0.40, 0.35, 0.25}` | Same at `config/settings.py:102-106` | **Match** |
| POTENTIAL_SCORE_WEIGHTS | `{0.50, 0.30, 0.20}` | Same at `config/settings.py:109-113` | **Match** |
| BASE min_profitable_years | 5 | `config/settings.py:117`, `models/stock.py:73` | **Match** |
| BASE min_operating_profit_years | 4 | `config/settings.py:118`, `models/stock.py:96` | **Match** |
| BASE max_debt_to_equity | 0.60 | `config/settings.py:119`, `models/stock.py:105` | **Match** |
| POTENTIAL min_profitable_years | 3 | `config/settings.py:123`, `models/stock.py:113` | **Match** |
| CLI: `--index`, `--quarter`, `--year`, `--no-cache`, `--debug`, `--update`, `--dry-run` | All 7 args | `build_fund.py:60-103` all present | **Match** |
| Fallback chains (router.py) | US Fin: td→av, US Price: yf→td→av, TASE Fin: td, TASE Price: yf→td | `router.py:55-133` | **Match** |
| Legacy config fallback | DATA_SOURCE → FINANCIAL/PRICING → 2x2 | `settings.py:56-79` | **Match** |
| `fund_builder/builder.py` (CLAUDE.md :109) | builder.py | File is `fund_builder/builder.py` | **Match** |
| `fund_builder/fund_builder.py` (README.md :296) | fund_builder.py | File is `builder.py` | **MISMATCH** |
| `logs/` created by `config/settings.py:91` | settings.py creates logs/ | Actually `build_fund.py:773` | **MISMATCH** |
| Cache note: "never loaded during builds" | Never loaded | Quarterly `--update` DOES load from cache | **AMBIGUOUS** |
| Hebrew console fix: stdout only | `build_fund.py:18-23` | Also fixes stderr (line 26) | **Underdocumented** |
| `backtest.py --output-dir` default | README.md ~:224 says `Fund_Docs` | Code: `default=None` (uses fund file's own directory) | **MISMATCH** |

---

### Bug: Log Filename Double-Q

**Location:** `build_fund.py:775`

```python
log_file = log_dir / f'data_failures_{index_name}_Q{quarter}_{year}.json'
```

**Problem:** The `quarter` parameter is already a string like `"Q1"`, `"Q2"`, etc. Prepending `Q` creates `QQ1`, `QQ2`, etc.

**Evidence:** Actual files in `logs/` are:
- `logs/data_failures_SP500_QQ1_2026.json`
- `logs/data_failures_TASE125_QQ1_2026.json`

**Expected:** `data_failures_SP500_Q1_2026.json`

**Fix:** Change line 775 to:
```python
log_file = log_dir / f'data_failures_{index_name}_{quarter}_{year}.json'
```

---

### Undocumented Code

| File | Purpose | In CLAUDE.md? | In README? |
|------|---------|---------------|------------|
| `tools/demonstrate_calculations.py` | Step-by-step calculation demonstration, loads SP500 Q1 2026 fund from cache and generates detailed Markdown report of formulas/results | **No** | **No** |
| `tests/test_e2e_data_freshness.py` | End-to-end data freshness test mimicking build_fund.py logic, tests AAPL/MSFT/NDAQ/AEP against live APIs | **No** | **No** |
| `Fund_Docs/SP500/Q1_2026/Fund_10_SP500_Q1_2026_Calculations.md` | Detailed calculations output — a new output file type not mentioned in documented output file list | **No** | **No** |
| `models/financial_data.py` — `PricePoint` class | Third class in financial_data.py alongside `FinancialData` and `MarketData`; used for fiscal-date price snapshots | **No** (CLAUDE.md only mentions 2 classes) | **No** |

---

### Dead References / Stale Content

| Reference | Location | Status |
|-----------|----------|--------|
| `fund_builder/fund_builder.py` | README.md:296 | File is `builder.py` — CLAUDE.md was fixed but README was not |
| Quarterly update "Planned / Remaining enhancement" | `Growth_Fund_10_Project_Assessment_Q1_2026.md:18,69,214` | Quarterly update is fully implemented since Feb 2026 |
| Old TASE125 fund file | `Fund_Docs/TASE125/Q1_2026/Fund_10_TASE125_Q1_2026 old.md` | Untracked file — should be removed or committed |
| README footer | `README.md:471` "Last updated: February 2026" | Now April 2026 |
| Backtest command in Assessment | `Growth_Fund_10_Project_Assessment_Q1_2026.md:194` | Still shows old flat path `Fund_Docs/Fund_10_SP500_Q1_2026.md` (should be `Fund_Docs/SP500/Q1_2026/...`) |
| Deleted backtest file | `Fund_Docs/TASE125/Q1_2026/Fund_10_TASE125_Q1_2026_Backtest_3Y.md` | Appears as deleted (D) in git status — not committed |

---

### Configuration Alignment

| Variable | `.env.template` | `settings.py` | Code Usage | Status |
|----------|-----------------|---------------|------------|--------|
| `US_FINANCIAL_DATA_SOURCE` | Line 17 (blank) | Line 39, default `""` | `router.py:56` | **Match** |
| `US_PRICING_DATA_SOURCE` | Line 22 (`yfinance`) | Line 43, default `"yfinance"` | `router.py:101` | **Match** |
| `TASE_FINANCIAL_DATA_SOURCE` | Line 31 (blank) | Line 47, default `""` | `router.py:59` | **Match** |
| `TASE_PRICING_DATA_SOURCE` | Line 36 (`yfinance`) | Line 51, default `"yfinance"` | `router.py:104` | **Match** |
| `FINANCIAL_DATA_SOURCE` | Line 89 (commented) | Line 26, default `"twelvedata"` | `settings.py:58-61` | **Match** |
| `PRICING_DATA_SOURCE` | Line 90 (commented) | Line 28, default `"twelvedata"` | `settings.py:64-67` | **Match** |
| `DATA_SOURCE` | Line 93 (commented) | Lines 70-75 (fallback) | `settings.py:70-75` | **Match** |
| `ALPHAVANTAGE_API_KEY` | Line 104 | Line 82 | `alphavantage_api.py` | **Match** |
| `ALPHAVANTAGE_RATE_LIMIT` | Line 108 (`paid`) | Line 83, default `"paid"` | `alphavantage_api.py` | **Match** |
| `TWELVEDATA_API_KEY` | Line 117 | Line 86 | `twelvedata_api.py` | **Match** |
| `TWELVEDATA_CREDITS_PER_MINUTE` | Line 125 (0) | Line 88, default `0` | `twelvedata_api.py` | **Match** |
| `TWELVEDATA_MAX_STOCKS_PER_MINUTE` | Line 126 (0) | Line 89, default `0` | `twelvedata_api.py` | **Match** |
| `OUTPUT_DIRECTORY` | Line 132 | Line 21, default `"./Fund_Docs"` | `build_fund.py` | **Match** |
| `USE_CACHE` | Line 133 | Line 95, default `"true"` | `build_fund.py` | **Match** |
| `DEBUG_MODE` | Line 134 | Line 96, default `"false"` | `build_fund.py` | **Match** |
| `FUND_QUARTER` | Line 137 | Line 92, default `None` | `build_fund.py` | **Match** |
| `FUND_YEAR` | Line 138 | Line 93, default `None` | `build_fund.py` | **Match** |

All 17 active configuration variables are fully aligned between `.env.template`, `settings.py`, and usage in code.

---

### Constants & Weights Verification

| Constant | Documented Value | Code Value | File:Line | Status |
|----------|-----------------|------------|-----------|--------|
| FUND_WEIGHTS | `[0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]` | Same | `config/settings.py:99` | **Match** |
| BASE_SCORE net_income_growth | 0.40 | 0.40 | `config/settings.py:103` | **Match** |
| BASE_SCORE revenue_growth | 0.35 | 0.35 | `config/settings.py:104` | **Match** |
| BASE_SCORE market_cap | 0.25 | 0.25 | `config/settings.py:105` | **Match** |
| POTENTIAL_SCORE future_growth | 0.50 | 0.50 | `config/settings.py:110` | **Match** |
| POTENTIAL_SCORE momentum | 0.30 | 0.30 | `config/settings.py:111` | **Match** |
| POTENTIAL_SCORE valuation | 0.20 | 0.20 | `config/settings.py:112` | **Match** |
| BASE min_profitable_years | 5 | 5 | `config/settings.py:117` | **Match** |
| BASE min_operating_profit_years | 4 | 4 | `config/settings.py:118` | **Match** |
| BASE max_debt_to_equity | 0.60 | 0.60 | `config/settings.py:119` | **Match** |
| POTENTIAL min_profitable_years | 3 | 3 | `config/settings.py:123` | **Match** |

All 11 constants verified correct.

---

### Test Coverage Gaps

| Module/Feature | Has Tests | Notes |
|----------------|-----------|-------|
| `fund_builder/builder.py` | **NO** | 14-step fund construction — zero unit test coverage |
| `models/stock.py` (eligibility) | **NO** | `check_base_eligibility()`, `check_potential_eligibility()` untested |
| `models/fund.py` | **NO** | Fund/FundPosition models untested |
| `models/financial_data.py` | **NO** | FinancialData/MarketData validation untested |
| `backtest.py` | **NO** | Entire backtesting engine — zero test coverage |
| `tools/demonstrate_calculations.py` | **NO** | New tool, untested |
| `data_sources/adapter.py` | Partial | Integration only, no unit tests |
| `data_sources/router.py` | Partial | Integration only in `test_all_sources.py` |
| `fund_builder/updater.py` | Partial | Integration tests in `test_quarterly_update.py` |
| `utils/date_utils.py` | YES | Well covered in `test_quarterly_update.py` |
| `utils/update_parser.py` | YES | Covered in `test_quarterly_update.py` |
| `utils/cache_loader.py` | YES | Covered in `test_quarterly_update.py` |
| `utils/ltm_calculator.py` | YES | Covered in `test_quarterly_update.py` |
| `utils/changelog.py` | YES | Covered in `test_quarterly_update.py` |
| `data_sources/twelvedata_api.py` | YES | `test_all_sources.py` + `test_price_alignment.py` |
| `data_sources/yfinance_source.py` | YES | `test_all_sources.py` |

New untracked test file `tests/test_e2e_data_freshness.py` exists but is not documented in CLAUDE.md.

---

## Recommendations

### Priority 1 — Code Bug (5 min fix)

1. **Fix log filename double-Q bug** — `build_fund.py:775`
   ```python
   # Change from:
   log_file = log_dir / f'data_failures_{index_name}_Q{quarter}_{year}.json'
   # To:
   log_file = log_dir / f'data_failures_{index_name}_{quarter}_{year}.json'
   ```
   Existing files `logs/data_failures_*_QQ1_2026.json` should be renamed to `*_Q1_2026.json`.

### Priority 2 — Documentation Fixes (< 10 min each)

2. **Fix README.md:296** — Change `fund_builder/fund_builder.py` → `fund_builder/builder.py`

3. **Fix CLAUDE.md Cache System note** — The "logs/ — Data acquisition failure logs" bullet (under "cache directories created by settings.py") is wrong on two counts: (a) `logs/` is created by `build_fund.py:773`, not `settings.py`, and (b) "never loaded during fund builds" should clarify it applies to full builds only — quarterly `--update` does load from cache.

4. **Add `tools/` to CLAUDE.md directory structure** — `tools/demonstrate_calculations.py` is a useful developer utility that should be documented.

5. **Add `tests/test_e2e_data_freshness.py` to CLAUDE.md test list** — New test file is untracked and undocumented.

### Priority 3 — Housekeeping (< 5 min each)

6. **Remove or commit `Fund_Docs/TASE125/Q1_2026/Fund_10_TASE125_Q1_2026 old.md`** — Untracked stale file cluttering the working tree.

7. **Commit `Fund_Docs/TASE125/Q1_2026/Fund_10_TASE125_Q1_2026_Backtest_3Y.md` deletion** — File is deleted but not staged/committed.

8. **Update README.md footer** — Change "Last updated: February 2026" to "April 2026".

9. **Document `_Calculations.md` as an output file type** — `Fund_10_SP500_Q1_2026_Calculations.md` is a new output file variant. Add it to the output files list in CLAUDE.md.

### Priority 4 — Test Coverage (Ongoing)

10. **Add unit tests for `models/stock.py`** — Eligibility logic is the core filter; targeted tests would catch regressions
11. **Add unit tests for `fund_builder/builder.py`** — 14-step scoring/selection algorithm with zero test coverage
12. **Add unit tests for `backtest.py`** — Entire backtesting engine untested
13. **Add unit tests for `models/financial_data.py` and `models/fund.py`**

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Documented files verified | 24/24 exist |
| Previous issues resolved | 8/8 |
| New bugs found | 1 (log filename double-Q) |
| New documentation errors | 3 (README.md wrong filename, CLAUDE.md logs/ attribution, backtest --output-dir default) |
| New undocumented artifacts | 4 (tools/, test_e2e_data_freshness.py, _Calculations.md, PricePoint class) |
| Stale content items | 4 (assessment report, old fund file, deleted file, README footer) |
| Config variables aligned | 17/17 |
| Constants verified correct | 11/11 |
| Modules with no unit tests | 5 (builder, stock, fund, financial_data, backtest) |
| Modules with partial tests | 3 (adapter, router, updater) |
| Modules well tested | 7 |
