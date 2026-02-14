# Growth Fund 10 — Project Implementation Assessment Report

**Date:** February 14, 2026 (Q1 2026)
**Project Root:** `C:\AsusWebStorage\ran@benhur.co\MySyncFolder\RaniStuff\קרן צמיחה 10`

---

## 1. Executive Summary

The Growth Fund 10 project is a **mature, fully operational** automated fund construction system for building investment portfolios from the S&P 500 and TA-125 indices. The system analyzes hundreds of stocks using multi-criteria scoring, constructs optimized 10-stock portfolios, and validates the results — all in a single automated run.

**Key milestones achieved:**
- Successfully generated fund compositions for **Q4 2025** and **Q1 2026** for both S&P 500 and TA-125 markets
- Full backtesting capability with 3-year, 5-year, and 10-year horizons producing performance reports and charts
- Flexible data source architecture (2x2 configuration matrix) supporting 3 providers
- Comprehensive test suite validating all components

**Remaining enhancement:** Quarterly update automation (automated rebalancing without full rebuild).

---

## 2. Project Components — Current Status

### 2.1 Documentation

| Document | Purpose | Status |
|----------|---------|--------|
| `CLAUDE.md` | Developer guide — architecture, commands, configuration, troubleshooting | **Active** — Canonical technical reference (16 KB) |
| `README.md` | User-facing guide — setup, usage, examples | **Active** — Primary user documentation (12 KB) |
| `.env.template` | Configuration template with all settings documented | **Active** |
| `2000_api_guide_eng.pdf` | TASE Data Hub API guide | **Reference** |

> **Note:** Earlier spec documents (`Growth_Fund_10Stocks_S_P500.md`, `Growth_Fund_10Stocks_TASE.md`) and instruction documents (`Fund_Update_Instructions.md`, `Fund_Update_Instructions_Checklist.md`) were removed during project reorganization. All relevant information is consolidated in `CLAUDE.md`.

### 2.2 Data Infrastructure

The system uses a **2x2 configuration matrix** allowing independent source selection per market and data type:

|  | Financial Data | Pricing Data |
|--|----------------|--------------|
| **US (SP500)** | TwelveData (primary) / AlphaVantage (backup) | yfinance (recommended, free) / TwelveData |
| **TASE (TA-125)** | TwelveData | yfinance (recommended, free) / TwelveData |

| Source | Markets | Cost | Best For |
|--------|---------|------|----------|
| **TwelveData** | US + TASE | Pro plan ($29+/mo) | Primary financial data |
| **yfinance** | US + TASE | **Free** | All pricing data (recommended) |
| **Alpha Vantage** | US only | Free (25 req/day) | Light testing / backup |

Data source routing is handled by `data_sources/router.py` with automatic fallback chains and instance caching.

### 2.3 Implementation Pipeline

| Stage | Description | Status |
|-------|-------------|--------|
| 1. Index constituent collection | Fetch stock list from S&P 500 / TA-125 | **Complete** |
| 2. Base stock eligibility filtering | Apply 5 mandatory criteria (5 years profitability) | **Complete** |
| 3. Base stock scoring | Weighted growth scores (40/35/25) | **Complete** |
| 4. Base stock selection (top 6) | Rank and select | **Complete** |
| 5. Potential stock list preparation | Remove base stocks from index | **Complete** |
| 6. Potential stock filtering | 2-year profitability criteria | **Complete** |
| 7. Potential stock scoring | Future growth / momentum / valuation (50/30/20) | **Complete** |
| 8. Potential stock selection (top 4) | Rank and select | **Complete** |
| 9. Weight allocation | Apply fixed weight tiers | **Complete** |
| 10. Minimum cost calculation | Whole-share portfolio pricing | **Complete** |
| 11–13. Document generation | Fund composition, update docs, final docs | **Complete** |
| 14. Validation | Cross-check criteria and totals | **Complete** |
| Backtesting | Historical performance verification with charts | **Complete** |
| Quarterly update automation | Automated rebalancing | **Planned** |

### 2.4 Test Suite

| Test | Purpose |
|------|---------|
| `tests/test_all_sources.py` | Comprehensive data source validation (auth, data quality, routing) |
| `tests/test_current_data.py` | Current data retrieval verification |
| `tests/test_price_alignment.py` | Price history alignment with fiscal year-ends |
| `tests/test_symbol_normalization.py` | Symbol format validation (.US, .TA suffixes) |
| `tests/test_tase_api.py` | TASE Data Hub API connectivity |
| `tests/verify_index.py` | Index constituent verification |

---

## 3. Resolved Issues & Project Evolution

### 3.1 Weight Allocation Discrepancy — Resolved

Earlier spec documents defined conflicting weight allocations (20/16/14/12/10/8 vs 18/16/16/10/10/10). This was resolved by canonicalizing the weights in `config/settings.py` and removing the conflicting documents:

```python
FUND_WEIGHTS = [0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]
```

### 3.2 Potential Stock Eligibility — Resolved

The ambiguity between 2-year and 3-year profitability requirements was resolved. The system uses **2 years** of positive net income as the eligibility threshold for potential stocks, defined in `config/settings.py`.

### 3.3 Architecture Shift: Cloud to Local

The project initially included AWS deployment infrastructure (Dockerfile, docker-compose, Terraform, GitHub Actions workflows). This was removed in the project reorganization (commit `1e9d72c`), simplifying the operational model to **local execution only**. This eliminates cloud costs and operational complexity while maintaining full functionality.

---

## 4. Operational Achievements

### 4.1 Fund Outputs Generated

**Q4 2025:**
- `Fund_10_SP500_Q4_2025.md` — S&P 500 fund composition
- `Fund_10_SP500_Q4_2025_Update.md` — Detailed scoring tables
- `Fund_10_SP500_Q4_2025_Backtest_3Y/5Y/10Y.md` — Multi-horizon backtests with charts
- `Fund_10_TASE125_Q4_2025.md` — TA-125 fund composition
- `Fund_10_TASE125_Q4_2025_Update.md` — Detailed scoring tables

**Q1 2026:**
- `Fund_10_SP500_Q1_2026.md` — S&P 500 fund composition
- `Fund_10_SP500_Q1_2026_Update.md` — Detailed scoring tables (26 KB)
- `Fund_10_SP500_Q1_2026_Backtest_3Y.md` — 3-year backtest
- `Fund_10_TASE125_Q1_2026.md` — TA-125 fund composition
- `Fund_10_TASE125_Q1_2026_Update.md` — Detailed scoring tables
- `Fund_10_TASE125_Q1_2026_Backtest_3Y.md` — 3-year backtest

**Additional reports:** TASE125 functionality reports, Gemini-generated comparison documents, backtest visualization charts (PNG).

### 4.2 Latest Fund Compositions (Q1 2026)

**S&P 500 Fund** (created Feb 11, 2026) — Minimum cost: **$4,258.65**

| Stock | Type | Weight | Score |
|-------|------|--------|-------|
| NVIDIA (NVDA) | Base | 18% | 89.69 |
| Salesforce (CRM) | Base | 16% | 49.79 |
| Alphabet (GOOG) | Base | 16% | 39.97 |
| Microsoft (MSFT) | Base | 10% | 34.76 |
| Trade Desk (TTD) | Base | 10% | 31.72 |
| AMD (AMD) | Base | 10% | 29.88 |
| Coinbase (COIN) | Potential | 6% | 71.18 |
| Micron (MU) | Potential | 6% | 55.57 |
| Super Micro (SMCI) | Potential | 4% | 51.20 |
| Vistra Energy (VST) | Potential | 4% | 50.76 |

**TA-125 Fund** (created Feb 10, 2026) — Minimum cost: **₪485,540**

| Stock | Type | Weight | Score |
|-------|------|--------|-------|
| Next Vision (NXSN) | Base | 18% | 80.10 |
| Clal Insurance (CLIS) | Base | 16% | 72.54 |
| Strauss Group (STRS) | Base | 16% | 49.71 |
| Bank Leumi (LUMI) | Base | 10% | 46.74 |
| Menora Mivtachim (MMHD) | Base | 10% | 46.33 |
| Bank Hapoalim (POLI) | Base | 10% | 43.08 |
| Aura Investments (AURA) | Potential | 6% | 67.02 |
| El Al Airlines (ELAL) | Potential | 6% | 66.64 |
| Ashtrom Group (ASHG) | Potential | 4% | 63.70 |
| Tamar Petroleum (TMRP) | Potential | 4% | 57.13 |

### 4.3 Backtest Highlights (SP500 Q1 2026, 3-Year)

| Metric | Fund | S&P 500 | NASDAQ |
|--------|------|---------|--------|
| Cumulative Return | **240.76%** | 67.79% | 94.27% |
| Annualized Return | **50.97%** | 18.99% | 25.00% |
| Sharpe Ratio | **1.62** | 1.14 | 1.16 |
| Sortino Ratio | **2.32** | 1.51 | 1.58 |
| Max Drawdown | -35.06% | -18.90% | -24.32% |
| Annual Alpha vs S&P | **+20.44%** | — | — |

---

## 5. Current System State

### 5.1 Code Metrics

| Component | Lines | Purpose |
|-----------|-------|---------|
| `build_fund.py` | 1,115 | Main CLI + orchestration |
| `backtest.py` | 775 | Historical performance analysis |
| `fund_builder/builder.py` | 390 | Fund construction logic |
| `config/settings.py` | 208 | Configuration management |
| `data_sources/twelvedata_api.py` | ~785 | Primary financial data source |
| `data_sources/yfinance_source.py` | ~254 | Free pricing data |
| `data_sources/alphavantage_api.py` | ~385 | Backup US data source |
| `data_sources/router.py` | ~201 | Intelligent source selection |
| `data_sources/adapter.py` | ~228 | Validation & normalization |

### 5.2 Commands

```bash
# Build fund for TA-125 or S&P 500
python build_fund.py --index TASE125
python build_fund.py --index SP500 --quarter Q1 --year 2026

# Run backtest
python backtest.py Fund_Docs/Fund_10_SP500_Q1_2026.md --years 3

# Test all data sources
python tests/test_all_sources.py
```

### 5.3 Dependencies

9 packages: `selenium`, `webdriver-manager`, `pandas`, `yfinance`, `python-dotenv`, `pydantic`, `rich`, `loguru`, `pytest`

### 5.4 Cache Strategy

- **Index constituents**: Cached per quarter in `cache/index_constituents/` (reused between builds)
- **Stock data**: Always fetched fresh from APIs (cache files saved for debugging only, never loaded)

---

## 6. Upcoming Work

### 6.1 Quarterly Update Automation (Priority: High)

The sole remaining major enhancement. This function will:
- Track ~30–50 stocks per index (previous eligible + new candidates)
- Refresh financial and pricing data from APIs
- Re-score and re-rank all candidates
- Detect composition changes vs previous quarter
- Generate diff/changelog comparing old vs new fund
- Automated validation of new composition

This automates the 14-step process for ongoing rebalancing rather than requiring a full rebuild each quarter.

### 6.2 Future Considerations (Low Priority)

- API credit usage logging/dashboard
- Historical fund composition versioning (CHANGELOG.md)
- Performance attribution analysis
- Multi-year backtest batch processing

---

## 7. Recommendations

### 7.1 Previously Identified — Now Complete

- ~~Resolve weight allocation discrepancy~~ — Canonicalized in `config/settings.py`
- ~~Standardize eligibility criteria~~ — 2 years for potential stocks
- ~~Fix file naming conventions~~ — Removed conflicting documents
- ~~Document the implementation~~ — CLAUDE.md (16 KB) + README.md (12 KB)
- ~~Complete backtest functionality~~ — 775 lines, fully operational
- ~~Add version control~~ — Git repository with meaningful commit history

### 7.2 Remaining

1. **Build the quarterly update function** — Primary next deliverable
2. **Add CHANGELOG.md** — Track fund composition changes across quarters
3. **Commit pending changes** — CLAUDE.md and README.md have uncommitted modifications

---

## 8. Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                     Data Sources                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │TwelveData│  │ yfinance │  │AlphaVntge│  │Wikipedia│ │
│  │(financl) │  │ (pricing)│  │ (backup) │  │(SP500)  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
└───────┼──────────────┼─────────────┼─────────────┼──────┘
        └──────────────┴─────────────┴─────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Router (2x2 Matrix Config) │
         │  + Adapter (Validation)     │
         └──────────────┬──────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          Fund Construction Pipeline (14 steps)           │
│                                                          │
│  Steps 1–2:   Fetch constituents → Filter base (5 yrs)  │
│  Steps 3–4:   Score base (40/35/25) → Select top 6      │
│  Steps 5–8:   Filter potential (2 yrs) → Select top 4   │
│  Steps 9–10:  Apply weights → Calculate minimum cost     │
│  Steps 11–14: Generate documents → Validate              │
│                                                          │
│  build_fund.py (1,115 loc) + builder.py (390 loc)       │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐    ┌────────────────┐
│  Fund Outputs │    │   Backtest     │
│               │    │  (775 loc)     │
│ - Fund .md    │    │                │
│ - Update .md  │    │ - Metrics      │
│ - Cache files │    │ - Charts (PNG) │
└───────────────┘    │ - Reports .md  │
                     └────────────────┘
```

---

## 9. Scoring Methodology Reference

### Base Stocks (Steps 2–4)

**Eligibility** (ALL required):
- 5 consecutive years of positive net income
- 4 out of 5 years with positive operating income
- Positive operating cash flow in majority of years
- Debt-to-equity ratio < 60%
- Index membership

**Scoring:**
```
Final = (Net Income Growth × 0.40) + (Revenue Growth × 0.35) + (Market Cap × 0.25)
```

### Potential Stocks (Steps 6–8)

**Eligibility:**
- Index membership
- 2 years of positive net income
- Complete growth data for 2 years
- Not in base stock list

**Scoring:**
```
Potential = (Future Growth × 0.50) + (Momentum × 0.30) + (Valuation × 0.20)
```

---

*Report updated: February 14, 2026*
