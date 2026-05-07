# Project Re-Evaluation Report
**Date:** May 7, 2026
**Focus:** Full Project Systematic Review
**Previous Assessment:** Project_ReEvaluation_2026-04-28.md (deleted — superseded by this report)

---

## Executive Summary

Since the April 28 report, a significant refactor removed PE/valuation from potential stock scoring (commit `0c40b4c`). This introduced **one new critical documentation mismatch**: README.md still describes the old 70/20/10 formula with Valuation, while code and CLAUDE.md now use 80/20 without Valuation. Additionally, **two undocumented utilities** (`utils/deploy.py` and `GOOGLE_DRIVE_DEPLOY_PATH`) have been in the codebase since before the last evaluation but remain absent from both CLAUDE.md and README.md. All five issues from the April 28 report have been resolved.

---

## Status of April 28 Issues

| Issue | Status |
|-------|--------|
| README "2+ years" for potential stocks | ✅ Fixed → "3+ years" (README line 34) |
| README backtest `--output-dir` default | ✅ Fixed → "Same directory as fund file" (README line 265) |
| CLAUDE.md logs line reference (773 → 185) | ✅ Fixed |
| `utils/dedup.py` missing from CLAUDE.md directory | ✅ Added |
| `# noqa: F401` on dedup imports | ✅ Removed (build_fund.py:164) |

---

## Findings

### Documentation Accuracy

| Area | Doc Says | Code Does | File:Line | Status |
|------|----------|-----------|-----------|--------|
| FUND_WEIGHTS | `[0.18,0.16,0.16,0.10,0.10,0.10,0.06,0.06,0.04,0.04]` | Same | settings.py:108 | ✅ Match |
| BASE score weights (NI, Rev, MCap) | `40%, 35%, 25%` | `0.40, 0.35, 0.25` | settings.py:114-118 | ✅ Match |
| STABILITY_BLEND | `30%` | `0.30` | settings.py:121 | ✅ Match |
| BASE min_profitable_years | 5 | 5 | settings.py:133 | ✅ Match |
| BASE min_operating_profit_years | 4 | 4 | settings.py:134 | ✅ Match |
| BASE max_debt_to_equity | 0.60 | 0.60 | settings.py:135 | ✅ Match |
| POTENTIAL min_profitable_years | 3 (CLAUDE.md + code) | 3 | settings.py:140, stock.py:113 | ✅ Match |
| POTENTIAL score weights (CLAUDE.md) | `80% growth, 20% momentum` | `0.80, 0.20` | settings.py:126-129 | ✅ Match |
| **POTENTIAL score weights (README.md lines 48-51)** | **`70% growth, 20% momentum, 10% valuation`** | **`0.80 growth, 0.20 momentum` (no valuation)** | README.md:48-51 vs settings.py:126-129 | ❌ **MISMATCH** |
| CLI `--index`, `--quarter`, `--year`, `--no-cache`, `--debug`, `--update`, `--dry-run` | All documented | All present | build_fund.py:71-116 | ✅ Match |
| Data source fallback chains | US Fin: td→av; US Price: yf→td→av; TASE Fin: td; TASE Price: yf→td | Correct | router.py | ✅ Match |
| Backtest `--output-dir` default | "Same directory as fund file" | `args.output_dir or str(Path(args.fund_file).parent)` | backtest.py:760 | ✅ Match |

---

### Undocumented Code

| File | Purpose | In CLAUDE.md? | In README.md? | Status |
|------|---------|---------------|---------------|--------|
| `utils/deploy.py` | Copies `.md` files to Google Drive local mount path after fund build. Used by `build_fund.py` and `fund_builder/updater.py`. | **No** | **No** | ❌ **Undocumented** |
| `utils/dedup.py` | Company deduplication: skip multi-class shares | Yes (added Q1 2026) | **No** | ⚠️ Missing from README only |
| `tools/demonstrate_calculations.py` | Step-by-step scoring formula demo | Yes | **No** | ⚠️ Missing from README only |
| `scripts/` directory | Scheduling PowerShell scripts | Yes | **No** | ⚠️ Missing from README only |

---

### Stale References

| Location | Says | Reality | Impact |
|----------|------|---------|--------|
| `models/stock.py:27` | `potential_scores_detail` description includes `"valuation"` | Valuation removed in commit `0c40b4c`; `potential_scores_detail` no longer contains valuation key | ⚠️ Misleading field description |
| `README.md:512` | "Last updated: April 2026" | Current month is May 2026 | Minor |

---

### Configuration Alignment

| Variable | `.env.template` | `settings.py` | In CLAUDE.md Config Section? | Status |
|----------|-----------------|---------------|------------------------------|--------|
| US_FINANCIAL_DATA_SOURCE | Line 17 | Line 39 | Yes | ✅ |
| US_PRICING_DATA_SOURCE | Line 22 | Line 43 | Yes | ✅ |
| TASE_FINANCIAL_DATA_SOURCE | Line 31 | Line 47 | Yes | ✅ |
| TASE_PRICING_DATA_SOURCE | Line 36 | Line 51 | Yes | ✅ |
| TWELVEDATA_API_KEY | Line 117 | Line 86 | Yes | ✅ |
| ALPHAVANTAGE_API_KEY | Line 104 | Line 82 | Yes | ✅ |
| ALPHAVANTAGE_RATE_LIMIT | Line 108 | Line 83 | **No** | ⚠️ Missing from CLAUDE.md |
| TWELVEDATA_CREDITS_PER_MINUTE | Line 125 | Line 88 | **No** | ⚠️ Missing from CLAUDE.md |
| TWELVEDATA_MAX_STOCKS_PER_MINUTE | Line 126 | Line 89 | **No** | ⚠️ Missing from CLAUDE.md |
| **GOOGLE_DRIVE_DEPLOY_PATH** | Line 174 | Lines 101-105 | **No** | ❌ **Undocumented in CLAUDE.md** |
| OUTPUT_DIRECTORY | Line 132 | Line 21 | Yes | ✅ |
| USE_CACHE | Line 133 | Line 95 | Yes | ✅ |
| DEBUG_MODE | Line 134 | Line 96 | Yes | ✅ |
| FUND_QUARTER | Line 137 | Line 92 | Yes | ✅ |
| FUND_YEAR | Line 138 | Line 93 | Yes | ✅ |

**Note:** `GOOGLE_DRIVE_DEPLOY_PATH` is actively used in `settings.py`, `utils/deploy.py`, and is copied to Google Drive after every build. It deserves documentation in CLAUDE.md.

---

### Constants & Weights Verification

| Constant | Documented Value | Code Value | File:Line | Status |
|----------|-----------------|------------|-----------|--------|
| FUND_WEIGHTS | `[0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]` | Same | settings.py:108 | ✅ |
| NI growth weight | 40% | 0.40 | settings.py:115 | ✅ |
| Revenue growth weight | 35% | 0.35 | settings.py:116 | ✅ |
| Market cap weight | 25% | 0.25 | settings.py:117 | ✅ |
| STABILITY_BLEND | 30% | 0.30 | settings.py:121 | ✅ |
| POTENTIAL future_growth weight | 80% (CLAUDE.md) / **70% (README)** | 0.80 | settings.py:127 | ❌ README mismatch |
| POTENTIAL momentum weight | 20% | 0.20 | settings.py:128 | ✅ |
| POTENTIAL valuation weight | **removed (CLAUDE.md)** / **10% (README)** | **not present** | settings.py:126-129 | ❌ README mismatch |
| BASE_GROWTH_YEARS | 5 | 5 | settings.py:111 | ✅ |
| BASE min_profitable_years | 5 | 5 | settings.py:133 | ✅ |
| BASE min_operating_profit_years | 4 | 4 | settings.py:134 | ✅ |
| BASE max_debt_to_equity | 60% | 0.60 | settings.py:135 | ✅ |
| POTENTIAL min_profitable_years | 3 | 3 | settings.py:140 | ✅ |

---

### Test Coverage Analysis

| Module/Feature | Has Tests | Test File | Notes |
|----------------|-----------|-----------|-------|
| `models/stock.py` | YES | test_models.py | Base + potential eligibility |
| `models/fund.py` | YES | test_models.py | Fund composition |
| `models/financial_data.py` | YES | test_models.py | Financial metrics |
| `fund_builder/builder.py` | YES | test_builder.py | Scoring, ranking, deduplication |
| `backtest.py` | YES | test_backtest.py | Metrics, report generation |
| `data_sources/twelvedata_api.py` | YES | test_all_sources.py | API + data parsing |
| `data_sources/yfinance_source.py` | YES | test_all_sources.py | Pricing data |
| `utils/date_utils.py` | YES | test_builder.py + integration | Quarter/year calculations |
| `utils/update_parser.py` | YES | test_quarterly_update.py | Parsing _Update.md |
| `utils/cache_loader.py` | YES | test_quarterly_update.py | Loading cached stock JSON |
| `utils/ltm_calculator.py` | YES | test_quarterly_update.py | LTM calculations |
| `utils/changelog.py` | YES | test_quarterly_update.py | CHANGELOG.md appending |
| `utils/dedup.py` | Partial | test_builder.py | Indirect via FundBuilder |
| `utils/deploy.py` | **NO** | — | Google Drive copy; no tests |
| `fund_builder/updater.py` | Partial | test_quarterly_update.py | Integration-level only |
| `data_sources/router.py` | Partial | test_all_sources.py | Router selection (integration) |
| `data_sources/adapter.py` | Partial | test_all_sources.py | Validation (integration) |
| `tools/demonstrate_calculations.py` | NO | — | Script-style; hard to unit test |
| `scripts/run_fund.ps1` | NO | — | Shell script; manual testing recommended |

---

## Recommendations

### Priority 1 — Documentation Correctness (Critical)

**1.1 Fix README.md lines 48-51 — Potential Stock Scoring Formula**
- **File:** README.md
- **Current text (lines 48-51):**
  ```
  - **Future Growth**: 70% (3-year CAGR)
  - **Momentum**: 20% (1-year price change)
  - **Valuation**: 10% (relative P/E)
  ```
- **Correct text:**
  ```
  - **Future Growth**: 80% (3-year CAGR)
  - **Momentum**: 20% (1-year price change)
  ```
  *(Add a note: PE/Valuation removed — high-growth stocks carry natural PE premiums)*
- **Reason:** Code uses `POTENTIAL_SCORE_WEIGHTS = {"future_growth": 0.80, "momentum": 0.20}` since commit `0c40b4c`. CLAUDE.md is already correct.
- **Effort:** < 2 min

---

### Priority 2 — Architecture Documentation (Important)

**2.1 Document `utils/deploy.py` in CLAUDE.md**
- **File:** CLAUDE.md — utils/ section in Directory Structure, plus a brief entry in Core Components utilities
- **Add to directory structure:**
  ```
  ├── deploy.py               # Google Drive deployment: copies .md files after each build
  ```
- **Reason:** File is imported and actively called in both `build_fund.py` and `fund_builder/updater.py`. Silently skips if `GOOGLE_DRIVE_DEPLOY_PATH` is not set.
- **Effort:** < 2 min

**2.2 Document `GOOGLE_DRIVE_DEPLOY_PATH` in CLAUDE.md Configuration Section**
- **File:** CLAUDE.md — `.env` configuration example
- **Add entry:**
  ```bash
  # Google Drive deployment (optional)
  GOOGLE_DRIVE_DEPLOY_PATH=  # Local Google Drive path, e.g. C:\Users\ranbe\My Drive\Fund_10
  ```
- **Reason:** Variable exists in `.env.template` and `settings.py` but is completely absent from CLAUDE.md documentation.
- **Effort:** < 1 min

---

### Priority 3 — Code Cleanup (Minor)

**3.1 Fix stale `valuation` reference in `models/stock.py:27`**
- **File:** models/stock.py
- **Current line 27:** `description="פירוט ציוני פוטנציאל: future_growth, momentum, valuation"`
- **Correct:** `description="פירוט ציוני פוטנציאל: future_growth, momentum"`
- **Reason:** PE/valuation removed in commit `0c40b4c`; field description is stale.
- **Effort:** < 1 min

**3.2 Update README.md Project Structure to include missing items**
- **File:** README.md — Project Structure section
- **Missing entries:**
  - `utils/dedup.py` — Company deduplication (multi-class share filtering)
  - `utils/deploy.py` — Google Drive deployment
  - `scripts/` directory and its two PowerShell files
  - `tools/` directory with `demonstrate_calculations.py`
- **Effort:** ~3 min

**3.3 Update README.md "Last updated" footer**
- **File:** README.md, line 512
- **Current:** `*Last updated: April 2026*`
- **Correct:** `*Last updated: May 2026*`
- **Effort:** < 1 min

---

### Priority 4 — Optional Improvements

**4.1 Add advanced config variables to CLAUDE.md**
- Variables in `.env.template` but missing from CLAUDE.md config section:
  - `ALPHAVANTAGE_RATE_LIMIT` (default: "paid")
  - `TWELVEDATA_CREDITS_PER_MINUTE` (default: 0 = auto-detect)
  - `TWELVEDATA_MAX_STOCKS_PER_MINUTE` (default: 0 = auto-detect)
- These are advanced/optional and self-explanatory in the template, so low priority.
- **Effort:** ~2 min

---

## Files Verified

### ✅ All Architecture Components Present and Correct
- Entry point: `build_fund.py`
- Configuration: `config/settings.py`
- Data models: `models/stock.py`, `models/fund.py`, `models/financial_data.py`
- Data sources: all four sources + router + adapter + exceptions
- Fund builder: `fund_builder/builder.py`, `fund_builder/updater.py`
- All 8 utils files exist and function as documented
- Tools: `tools/demonstrate_calculations.py`
- Backtest: `backtest.py`
- Tests: 11 test files
- Scripts: `scripts/run_fund.ps1`, `scripts/schedule_tasks.ps1`

### ✅ All CLI Arguments Present and Correct
`--index`, `--quarter`, `--year`, `--no-cache`, `--debug`, `--update`, `--dry-run`

---

## Summary Table

| Category | Count | Status |
|----------|-------|--------|
| **Documentation Mismatches** | 1 | ❌ README.md potential scoring weights (70/20/10 vs 80/20) |
| **Undocumented Code** | 1 critical | ❌ `utils/deploy.py` completely undocumented |
| **Undocumented Config** | 1 critical | ❌ `GOOGLE_DRIVE_DEPLOY_PATH` missing from CLAUDE.md |
| **Stale Field Description** | 1 | ⚠️ `stock.py:27` mentions removed "valuation" key |
| **README Structure Gaps** | 4 | ⚠️ Missing: dedup.py, deploy.py, scripts/, tools/ |
| **Minor Config Docs** | 3 | ⚠️ ALPHAVANTAGE_RATE_LIMIT, TWELVEDATA_CREDITS_PER_MINUTE, TWELVEDATA_MAX_STOCKS_PER_MINUTE not in CLAUDE.md |
| **Test Coverage Gaps** | 1 | ⚠️ `utils/deploy.py` has no unit tests |
| **Configuration Mismatches** | 0 | ✅ All values correct where documented |
| **Constant Mismatches** | 0 (in code+CLAUDE.md) | ✅ All weights match; README is the outlier |

---

## Effort Estimate

Total fix time: **~10 minutes**
- Priority 1 (1 fix): 2 minutes
- Priority 2 (2 fixes): 3 minutes
- Priority 3 (3 fixes): 5 minutes

---

## Conclusion

The scoring algorithm refactor (commit `0c40b4c`, PE removal) correctly updated `settings.py` and `CLAUDE.md` but **missed updating `README.md`**. This is the highest-priority fix. The `utils/deploy.py` utility (Google Drive file sync) and its configuration variable `GOOGLE_DRIVE_DEPLOY_PATH` are production features silently absent from all developer documentation — they should be added to CLAUDE.md. All other architecture, constants, CLI arguments, and eligibility criteria remain correctly aligned between code and documentation.
