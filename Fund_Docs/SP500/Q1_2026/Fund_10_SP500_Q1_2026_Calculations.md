# Growth Fund 10 — Step-by-Step Calculation Report

**Generated:** 2026-02-16 00:01
**Fund:** SP500 Q1 2026
**Sample Base Stock:** NVDA.US (NVIDIA Corporation)
**Sample Potential Stock:** MU.US (Micron Technology Inc)

This report traces every calculation in the fund-building system with real data,
organized by: **A.** Shared calculations, **B.** Full-build-only, **C.** Quarterly-update-only, **D.** Differences summary.

> **Note:** The scores in this report are computed live from cached data using the actual project code.
> They may differ slightly from the `_Update.md` scores because the original fund was built using the
> **quarterly update path** (LTM-merged data + different market prices at build time). The formulas and
> calculation steps are identical — only the input data varies.

> **⚠ Historical parameters (pre-April 2026 fix):** This report was generated using the original scoring
> parameters. Current code uses corrected values: base CAGR `years=5` (4-year), potential CAGR `years=3`
> (2-year), and potential eligibility `min_profitable_years=3`. The numerical examples below reflect the
> old `years=3`/`years=2`/`min=2` parameters that were in effect when Q1 2026 was built.

---

# Section A: Shared Calculations (Both Paths)

## A1. Data-Level Metrics (Single Stock)

### Debt-to-Equity Ratio (NVDA)

**Formula:** `debt_to_equity = total_debt / total_equity`

**Source:** `models/financial_data.py:43-47`

| Variable | Value |
|----------|-------|
| total_debt | $9.48B |
| total_equity | $118.90B |

**Calculation:**
```
debt_to_equity = 9,482,000,000 / 118,897,000,000 = 7.97%
```
**Result:** 7.97% (threshold for base eligibility: ≤ 60%)

### Debt-to-Equity Ratio (MU)

```
debt_to_equity = 11,856,000,000 / 58,806,000,000 = 20.16%
```

### CAGR: 3-Year Net Income Growth (NVDA)

**Formula:** `CAGR = ((end_value / start_value) ^ (1 / (years - 1)) - 1) × 100`
**Source:** `fund_builder/builder.py:32-62`

**Step 1: Select 3 most recent years** (sorted descending)
| Year | Net Income |
|------|-----------|
| 2025 | $99.20B **←** |
| 2024 | $29.76B **←** |
| 2023 | $4.37B **←** |
| 2022 | $9.75B |
| 2021 | $4.33B |

**Step 2: Identify start and end values**
- Start year: 2023 → start_value = $4.37B
- End year: 2025 → end_value = $99.20B
- years = 3, exponent = 1 / (3 - 1) = **0.5**

**Step 3: Compute**
```
CAGR = ((99,198,000,000 / 4,368,000,000) ^ 0.5 - 1) × 100
     = (22.7102 ^ 0.5 - 1) × 100
     = (4.7655 - 1) × 100
     = 376.55%
```

### CAGR: 3-Year Revenue Growth (NVDA)

| Year | Revenue |
|------|---------|
| 2025 | $187.14B **←** |
| 2024 | $60.92B **←** |
| 2023 | $26.97B **←** |
| 2022 | $26.91B |
| 2021 | $16.68B |

```
CAGR = ((187,142,000,000 / 26,974,000,000) ^ 0.5 - 1) × 100
     = (6.9379 ^ 0.5 - 1) × 100
     = 163.40%
```

### CAGR: 2-Year Net Income Growth (MU) — used for Potential Scoring

| Year | Net Income |
|------|-----------|
| 2025 | $11.91B **←** |
| 2024 | $778.00M **←** |
| 2023 | $-5.83B |
| 2022 | $8.69B |
| 2021 | $5.86B |

**Note:** With years=2, exponent = 1/(2-1) = **1.0** — this is simple percentage change.
```
CAGR = ((11,909,000,000 / 778,000,000) ^ 1.0 - 1) × 100
     = (15.3072 - 1) × 100
     = 1430.72%
```

### Momentum (MU)

**Formula:** `momentum = ((current_price - oldest_price) / oldest_price) × 100`
**Source:** `models/financial_data.py:136-155`

**Price History:**
| Date | Price |
|------|-------|
| 2021-08-31 | $71.91 |
| 2022-08-31 | $55.48 |
| 2023-08-31 | $69.21 |
| 2024-08-31 | $95.69 |
| 2025-08-31 | $118.89 |
| 2026-02-14 | $411.66 |

**Oldest entry:** 2021-08-31 → $71.91
**Current price:** $411.66

```
momentum = ((411.66 - 71.91) / 71.91) × 100
         = (339.75 / 71.91) × 100
         = 472.47%
```

### Valuation Score (MU) — Relative P/E

**Formula:** `valuation_score = (2 - (stock_pe / index_pe)) × 50`
**Source:** `fund_builder/builder.py:152-157`

| Variable | Value |
|----------|-------|
| stock_pe (MU) | 39.06 |
| index_pe (computed) | *Shown below — depends on candidate pool (see A3 and C6)* |

The valuation formula maps P/E relative to the index average:
- P/E = index P/E → score = 50 (average)
- P/E < index P/E → score > 50 (cheap = good)
- P/E > index P/E → score < 50 (expensive = bad)
- P/E > 2× index P/E → score < 0 (penalized)

## A2. Eligibility Checks (Boolean Pass/Fail)

### NVDA — Base Stock Eligibility

**Source:** `models/stock.py:71-109`, `models/financial_data.py:49-99`

All 4 checks must pass:

**Check 1: `has_profitable_years(5)` — 5 most recent years, all net income > 0**

| Year | Net Income | > 0? |
|------|-----------|------|
| 2025 | $99.20B | YES |
| 2024 | $29.76B | YES |
| 2023 | $4.37B | YES |
| 2022 | $9.75B | YES |
| 2021 | $4.33B | YES |

**Result:** PASS — all 5 years positive

**Check 2: `has_operating_profit_years(4, 5)` — at least 4 of 5 years with positive operating income**

| Year | Operating Income | > 0? |
|------|-----------------|------|
| 2025 | $110.12B | YES |
| 2024 | $32.97B | YES |
| 2023 | $5.58B | YES |
| 2022 | $10.04B | YES |
| 2021 | $4.53B | YES |

**Positive count:** 5/5 (required: ≥ 4)
**Result:** PASS

**Check 3: `has_positive_cash_flow()` — majority of years have positive operating cash flow**

| Year | Operating Cash Flow | > 0? |
|------|-------------------|------|
| 2025 | $81.56B | YES |
| 2024 | $27.82B | YES |
| 2023 | $5.77B | YES |
| 2022 | $10.34B | YES |
| 2021 | $6.09B | YES |

**Ratio:** 5/5 = 100.00% (threshold: > 50%)
**Result:** PASS

**Check 4: `debt_to_equity_ratio ≤ 0.60`**

```
debt_to_equity = 9,482,000,000 / 118,897,000,000 = 0.0797
```
**0.0797 ≤ 0.60? YES → PASS**

**NVDA Base Eligibility: PASS (all 4 checks passed)**

---

### MU — Base Stock Eligibility (Expected: FAIL)

**Check 1: `has_profitable_years(5)` — 5 most recent years, all net income > 0**

| Year | Net Income | > 0? |
|------|-----------|------|
| 2025 | $11.91B | YES |
| 2024 | $778.00M | YES |
| 2023 | $-5.83B | **NO ← FAILS HERE** |
| 2022 | $8.69B | YES |
| 2021 | $5.86B | YES |

**Result: FAIL** — year 2023 has negative net income
**MU Base Eligibility: FAIL** (check 1 failed, remaining checks skipped)

---

### MU — Potential Stock Eligibility (Expected: PASS)

**Check 1: `has_profitable_years(2)` — 2 most recent years, all net income > 0**

| Year | Net Income | > 0? |
|------|-----------|------|
| 2025 | $11.91B | YES |
| 2024 | $778.00M | YES |

**Result:** PASS

**Check 2: Growth data completeness — `len(revenues) ≥ 2 and len(net_incomes) ≥ 2`**

- `len(revenues)` = 5 ≥ 2? YES
- `len(net_incomes)` = 5 ≥ 2? YES

**MU Potential Eligibility: PASS**

## A3. Raw Scoring Metrics (All Candidates)

These raw values were computed by `score_and_rank_base_stocks()` and `score_and_rank_potential_stocks()`
using the actual project code. The `base_scores_detail` and `potential_scores_detail` dicts on each
stock object store both raw and normalized values.

### Base Stock Raw Scores (all candidates)

**Formulas:**
- `net_income_growth_raw` = CAGR(net_incomes, years=3)
- `revenue_growth_raw` = CAGR(revenues, years=3)
- `market_cap_raw` = stock.market_cap

| # | Symbol | net_income_growth | revenue_growth | market_cap | **Final Score** |
|---|--------|------------------|----------------|------------|----------------|
| 1 | NVDA.US **←** | 376.55% | 163.40% | $4,450.88B | **90.30** |
| 2 | CRM.US | 489.25% | 13.40% | $180.61B | **45.23** |
| 3 | GOOGL.US | 33.83% | 14.48% | $3,853.86B | **26.95** |
| 4 | GOOG.US | 33.83% | 14.48% | $3,701.92B | **26.10** |
| 5 | MSFT.US | 28.38% | 20.06% | $2,982.76B | **22.72** |
| 6 | TTD.US | 171.35% | 24.48% | $13.75B | **19.21** |
| 7 | TKO.US | 83.69% | 60.96% | $16.98B | **19.15** |
| 8 | AMD.US | 125.30% | 23.58% | $338.02B | **16.89** |
| 9 | WELL.US | 146.15% | 16.61% | $137.84B | **16.13** |
| 10 | META.US | 24.35% | 22.05% | $1,696.62B | **15.54** |
| 11 | STE.US | 141.29% | 9.71% | $23.99B | **13.65** |
| 12 | NWS.US | 167.69% | -7.50% | $15.09B | **12.35** |
| 13 | NWSA.US | 167.69% | -7.50% | $13.70B | **12.34** |
| 14 | ACGL.US | 70.57% | 32.41% | $36.52B | **12.29** |
| 15 | MPWR.US | 102.05% | 10.91% | $55.63B | **10.70** |
| 16 | ANET.US | 45.22% | 26.43% | $180.64B | **9.69** |
| 17 | DIS.US | 99.05% | 3.06% | $195.00B | **9.62** |
| 18 | XYL.US | 58.34% | 24.52% | $31.39B | **9.59** |
| 19 | WMT.US | 33.61% | 5.55% | $1,010.16B | **9.09** |
| 20 | PTC.US | 72.90% | 14.29% | $19.36B | **8.68** |
| 21 | NFLX.US | 42.50% | 15.75% | $348.73B | **8.22** |
| 22 | EME.US | 57.48% | 14.68% | $34.79B | **7.52** |
| 23 | BKNG.US | 38.69% | 17.86% | $138.75B | **7.14** |
| 24 | AIZ.US | 65.78% | 7.95% | $11.90B | **6.73** |
| 25 | ISRG.US | 25.81% | 18.86% | $175.84B | **6.45** |
| 26 | PWR.US | 34.62% | 17.75% | $76.14B | **6.42** |
| 27 | ERIE.US | 41.80% | 16.39% | $14.56B | **6.41** |
| 28 | LULU.US | 45.70% | 14.26% | $21.41B | **6.35** |
| 29 | DECK.US | 36.72% | 17.24% | $16.83B | **6.16** |
| 30 | CB.US | 35.56% | 14.20% | $128.33B | **6.06** |

**Min/Max for normalization:**
| Metric | Min | Max |
|--------|-----|-----|
| net_income_growth | 24.35% | 489.25% |
| revenue_growth | -7.50% | 163.40% |
| market_cap | $11.90B | $4,450.88B |

### Potential Stock Raw Scores (all candidates)

**Formulas:**
- `future_growth_raw` = CAGR(net_incomes, years=2)
- `momentum_raw` = ((current_price - oldest_price) / oldest_price) × 100
- `valuation_raw` = (2 - (stock_pe / index_pe)) × 50, where **index_pe = 43.53**

| # | Symbol | future_growth | momentum | valuation | **Final Score** |
|---|--------|--------------|----------|-----------|----------------|
| 1 | COIN.US | 2618.50% | -35.61% | 83.87 | **70.00** |
| 2 | MU.US **←** | 1430.72% | 472.47% | 55.14 | **62.48** |
| 3 | TRGP.US | 17.00% | 842.32% | 65.30 | **49.22** |
| 4 | SMCI.US | -24.28% | 768.11% | 74.40 | **46.67** |
| 5 | VST.US | 88.47% | 802.69% | 34.06 | **46.60** |
| 6 | STX.US | 488.06% | 460.99% | 44.78 | **43.38** |
| 7 | AVGO.US | 292.30% | 595.76% | 18.19 | **42.05** |
| 8 | HWM.US | 50.98% | 697.73% | 27.58 | **41.76** |
| 9 | APP.US | 342.87% | 401.72% | 35.87 | **37.86** |
| 10 | GE.US | 32.47% | 448.08% | 54.87 | **35.17** |
| 11 | RCL.US | 69.95% | 375.86% | 74.33 | **35.04** |
| 12 | CMI.US | 384.29% | 192.38% | 67.07 | **34.11** |
| 13 | LDOS.US | 501.44% | 97.72% | 79.10 | **34.10** |
| 14 | MCK.US | 10.16% | 392.76% | 68.99 | **34.04** |
| 15 | KLAC.US | 47.06% | 363.09% | 52.26 | **32.32** |
| 16 | TPL.US | 11.91% | 428.76% | 33.05 | **32.29** |
| 17 | PLTR.US | 115.26% | 492.40% | -154.33 | **20.68** |

**Min/Max for normalization:**
| Metric | Min | Max |
|--------|-----|-----|
| future_growth | -24.28% | 2618.50% |
| momentum | -35.61% | 842.32% |
| valuation | -154.33 | 83.87 |

## A4. Min-Max Normalization (Cross-Stock)

**Formula:** `normalized = ((value - min) / (max - min)) × 100`
**Source:** `fund_builder/builder.py:64-83`
**Special case:** if max == min → all values = 50.0

### NVDA — Base Score Normalization

**net_income_growth:**
```
raw = 376.55%, min = 24.35%, max = 489.25%
normalized = ((376.55 - 24.35) / (489.25 - 24.35)) × 100
           = (352.20 / 464.90) × 100
           = 75.76
```

**revenue_growth:**
```
raw = 163.40%, min = -7.50%, max = 163.40%
normalized = ((163.40 - -7.50) / (163.40 - -7.50)) × 100
           = (170.90 / 170.90) × 100
           = 100.00
```

**market_cap:**
```
raw = $4,450.88B, min = $11.90B, max = $4,450.88B
normalized = ((4,450,875,342,848.00 - 11,904,817,152.00) / (4,450,875,342,848.00 - 11,904,817,152.00)) × 100
           = (4,438,970,525,696.00 / 4,438,970,525,696.00) × 100
           = 100.00
```

### MU — Potential Score Normalization

**future_growth:**
```
raw = 1,430.72, min = -24.28, max = 2,618.50
normalized = ((1,430.72 - -24.28) / (2,618.50 - -24.28)) × 100
           = (1,455.00 / 2,642.78) × 100
           = 55.06
```

**momentum:**
```
raw = 472.47, min = -35.61, max = 842.32
normalized = ((472.47 - -35.61) / (842.32 - -35.61)) × 100
           = (508.08 / 877.92) × 100
           = 57.87
```

**valuation:**
```
raw = 55.14, min = -154.33, max = 83.87
normalized = ((55.14 - -154.33) / (83.87 - -154.33)) × 100
           = (209.48 / 238.20) × 100
           = 87.94
```

## A5. Final Weighted Scores

### NVDA — Base Score

**Weights:** net_income_growth=0.4, revenue_growth=0.35, market_cap=0.25
**Source:** `config/settings.py:102-106`

```
base_score = (75.76 × 0.4) + (100.00 × 0.35) + (100.00 × 0.25)
           = 30.30 + 35.00 + 25.00
           = 90.30
```

### MU — Potential Score

**Weights:** future_growth=0.5, momentum=0.3, valuation=0.2
**Source:** `config/settings.py:109-113`

```
potential_score = (55.06 × 0.5) + (57.87 × 0.3) + (87.94 × 0.2)
               = 27.53 + 17.36 + 17.59
               = 62.48
```

## A6. Duplicate-Company Filtering

**Source:** `utils/dedup.py` (`get_base_company_name`, `select_stocks_skip_duplicates`) — re-exported from `build_fund.py` for backwards compatibility

This step removes duplicate share classes (e.g., GOOG Class C vs GOOGL Class A) — only the higher-ranked one is kept.

**Demonstration with top 10 ranked base stocks:**

| Rank | Symbol | Name | Base Name (after stripping) | Action |
|------|--------|------|-----------------------------|--------|
| 1 | NVDA.US | NVIDIA Corporation | `NVIDIA CORPORATION` | Keep |
| 2 | CRM.US | Salesforce.com Inc | `SALESFORCE.COM` | Keep |
| 3 | GOOGL.US | Alphabet Inc Class A | `ALPHABET` | Keep |
| 4 | GOOG.US | Alphabet Inc Class C | `ALPHABET` | **SKIP** (duplicate of `ALPHABET`) |
| 5 | MSFT.US | Microsoft Corporation | `MICROSOFT CORPORATION` | Keep |
| 6 | TTD.US | Trade Desk Inc | `TRADE DESK` | Keep |
| 7 | TKO.US | TKO Group Holdings, Inc. | `TKO GROUP HOLDINGS,` | Keep |
| 8 | AMD.US | Advanced Micro Devices Inc | `ADVANCED MICRO DEVICES` | Keep |
| 9 | WELL.US | Welltower Inc | `WELLTOWER` | Keep |
| 10 | META.US | Meta Platforms Inc. | `META PLATFORMS` | Keep |

**After filtering:** 9 unique companies from top 10 ranked stocks
This is how 6 base stocks are selected without duplicates.

## A7. Weight Assignment (Portfolio Level)

**Source:** `config/settings.py:99`
**Fixed weights:** `[0.18, 0.16, 0.16, 0.1, 0.1, 0.1, 0.06, 0.06, 0.04, 0.04]`

| Position | Type | Weight |
|----------|------|--------|
| 1 (rank 1 base) | Base | 18% |
| 2 (rank 2 base) | Base | 16% |
| 3 (rank 3 base) | Base | 16% |
| 4 (rank 4 base) | Base | 10% |
| 5 (rank 5 base) | Base | 10% |
| 6 (rank 6 base) | Base | 10% |
| 7 (rank 1 potential) | Potential | 6% |
| 8 (rank 2 potential) | Potential | 6% |
| 9 (rank 3 potential) | Potential | 4% |
| 10 (rank 4 potential) | Potential | 4% |
| **Total** | | **100%** |

## A8. Minimum Fund Cost & Share Allocation

**Source:** `fund_builder/builder.py:296-347`

### Step 1: Find most expensive stock by price

| Symbol | Price | Weight |
|--------|-------|--------|
| NVDA.US | $182.81 | 18% |
| CRM.US | $189.72 | 16% |
| GOOGL.US | $318.58 | 16% |
| MSFT.US | $401.32 | 10% |
| TTD.US | $28.13 | 10% |
| TKO.US | $206.75 | 10% |
| COIN.US | $162.51 | 6% |
| MU.US | $411.66 | 6% |
| TRGP.US | $223.89 | 4% |
| SMCI.US | $30.54 | 4% |

**Most expensive:** MU.US at $411.66 (weight: 6%)

### Step 2: Derive theoretical fund cost

**Logic:** The most expensive stock gets exactly 1 share, so:
```
1 share × $411.66 = fund_cost × 0.06
fund_cost = $411.66 / 0.06 = $6,861.00
```

### Step 3: Calculate shares per stock

**Formula:** `shares = round(fund_cost × weight / price)`, minimum 1

| Symbol | fund_cost × weight | ÷ price | raw | round() | shares |
|--------|-------------------|---------|-----|---------|--------|
| NVDA.US | $1,234.98 | ÷ $182.81 | 6.756 | 7 | 7 |
| CRM.US | $1,097.76 | ÷ $189.72 | 5.786 | 6 | 6 |
| GOOGL.US | $1,097.76 | ÷ $318.58 | 3.446 | 3 | 3 |
| MSFT.US | $686.10 | ÷ $401.32 | 1.710 | 2 | 2 |
| TTD.US | $686.10 | ÷ $28.13 | 24.390 | 24 | 24 |
| TKO.US | $686.10 | ÷ $206.75 | 3.319 | 3 | 3 |
| COIN.US | $411.66 | ÷ $162.51 | 2.533 | 3 | 3 |
| MU.US | $411.66 | ÷ $411.66 | 1.000 | 1 | 1 |
| TRGP.US | $274.44 | ÷ $223.89 | 1.226 | 1 | 1 |
| SMCI.US | $274.44 | ÷ $30.54 | 8.986 | 9 | 9 |

### Step 4: Actual fund cost (sum of shares × price)

| Symbol | Shares | Price | Cost |
|--------|--------|-------|------|
| NVDA.US | 7 | $182.81 | $1,279.67 |
| CRM.US | 6 | $189.72 | $1,138.32 |
| GOOGL.US | 3 | $318.58 | $955.74 |
| MSFT.US | 2 | $401.32 | $802.64 |
| TTD.US | 24 | $28.13 | $675.12 |
| TKO.US | 3 | $206.75 | $620.25 |
| COIN.US | 3 | $162.51 | $487.53 |
| MU.US | 1 | $411.66 | $411.66 |
| TRGP.US | 1 | $223.89 | $223.89 |
| SMCI.US | 9 | $30.54 | $274.86 |
| **Total** | | | **$6,869.68** |

**Minimum fund unit cost: $6,869.68**

## A9. Fund Validation Checks

**Source:** `fund_builder/builder.py:349-390`

1. **Weights sum:** 0.18 + 0.16 + 0.16 + 0.1 + 0.1 + 0.1 + 0.06 + 0.06 + 0.04 + 0.04 = 1.0 (|1.0 - 1.0| = 0.0000 ≤ 0.001? PASS)
2. **Position count:** 10 = 10? PASS
3. **Base count:** 6 = 6? PASS
4. **Potential count:** 4 = 4? PASS
5. **No duplicates:** 10 symbols, 10 unique → PASS
6. **Whole shares:** All shares are integers? PASS

**All validations: PASS**

---

# Section B: Full-Build-Only Calculations

These calculations are used only in the full build path (`python build_fund.py --index SP500`).

## B1. Index P/E Ratio (via API)

**Source:** `data_sources/twelvedata_api.py` — `get_index_pe_ratio()`

In the full build path, the index P/E is fetched from the API:

- **SP500:** API call to `/statistics?symbol=SPX` → reads `valuations_metrics.trailing_pe`
- **TASE125:** Hardcoded estimate → returns `14.0`

This value is used in the potential stock valuation formula:
```
valuation_score = (2 - (stock_pe / index_pe)) × 50
```
**Contrast with Quarterly Update:** The update path computes index_pe as the arithmetic mean of all candidates' P/E ratios (see Section C6).

## B2. Fiscal-Date Aligned Price History

**Source:** `build_fund.py:633-639`, `data_sources/twelvedata_api.py:~540`

In the full build, price history is fetched at specific **fiscal year-end dates** extracted from the financial data:

1. After fetching financial data, the system extracts fiscal dates from income statements
2. These dates are passed to the pricing source: `get_stock_market_data(symbol, fiscal_dates=[...])`
3. The pricing source fetches EOD prices for each specific date

**NVDA example — fiscal date prices:**
| Fiscal Date | Price |
|-------------|-------|
| 2021-01-31 | $12.95 |
| 2022-01-31 | $24.44 |
| 2023-01-31 | $19.52 |
| 2024-01-31 | $61.49 |
| 2025-01-31 | $120.04 |
| 2026-01-31 | $191.13 |
| 2026-02-14 | $182.81 |

**Feb 2026 Fix:** The system extends fiscal dates to include the next completed FY-end,
even if financials haven't been filed yet. This ensures scoring uses current-year prices.

## B3. Data Validation

**Source:** `data_sources/adapter.py:19-76` (`validate_financial_data`), lines 78-120 (`validate_market_data`)

The full build path validates all fetched data. The quarterly update path does **not** run these checks.

### `validate_financial_data()` checks:
1. `revenues` is not empty
2. `net_incomes` is not empty
3. Debt/equity ratio < 500% (warning only)
4. At least 2 years of positive revenue history
5. At least 2 years of net income history

### `validate_market_data()` checks:
1. `market_cap > 0`
2. `current_price > 0` (relaxed for index constituents)
3. Price history has ≥ 5 fiscal date points (≥ 3 for index constituents)

**NVDA validation example:**
- Revenues: 5 years → PASS
- Net incomes: 5 years → PASS
- Market cap: $4,450.88B > 0 → PASS
- Current price: $182.81 > 0 → PASS
- Price history points: 7 ≥ 5 → PASS

## B4. Filtering Statistics

In the full build, statistics are tracked for the filtering pipeline:
```
Total stocks in index:       ~503
  → Data fetch successful:   ~400+ (some may fail API calls)
  → Base eligible:           ~100-200 (pass all 4 base checks)
  → Potential eligible:       ~200-350 (pass relaxed checks)
  → Scored base:             30 (top ranked)
  → Scored potential:        20 (top ranked)
  → Final fund:              10 (6 base + 4 potential)
```
These statistics are written to the `_Update.md` file under `## סטטיסטיקות סינון`.

---

# Section C: Quarterly-Update-Only Calculations

These calculations are used only in the quarterly update path (`python build_fund.py --index SP500 --update`).

## C1. Parse Previous Update.md

**Source:** `utils/update_parser.py:13-55`

The quarterly update starts by reading the **previous** quarter's `_Update.md` to find which stocks to re-evaluate.

**File:** `Fund_10_SP500_Q1_2026_Update.md`
**Fund name:** Fund_10_SP500_Q1_2026
**Date:** 2026-02-14

**Extracted candidates:**
- Base candidates: 30 stocks (top 30)
- Potential candidates: 17 stocks (top 20)
- **Unique symbols:** 47 (some stocks may appear in both lists)

**Base candidates (first 5):**
| Rank | Symbol | Score |
|------|--------|-------|
| 1 | NVDA.US | 91.07 |
| 2 | CRM.US | 45.29 |
| 3 | GOOG.US | 29.26 |
| 4 | GOOGL.US | 29.24 |
| 5 | MSFT.US | 25.92 |
... and 25 more

## C2. Load Cached Stock Objects

**Source:** `utils/cache_loader.py:17-42`

Each stock is loaded from `cache/stocks_data/{SYMBOL}.json` via `Stock(**json.load(file))`.

**What's preserved from cache (NVDA example):**
- Financial data: 5 years of revenues, 5 years of net incomes
- Operating incomes: 5 years
- Operating cash flows: 5 years
- Balance sheet: total_debt=$9.48B, total_equity=$118.90B
- Market data: price=$182.81, market_cap=$4,450.88B, pe_ratio=45.25
- Price history: 7 data points
- Previous scores: base_score=90.3036483493226, potential_score=None

## C3. Quarterly Financial Data Fetch (Live API)

**Source:** `data_sources/twelvedata_api.py:621+` — `get_quarterly_financials()`

3 API calls per stock (all with `period=quarterly`):
1. `/income_statement` → revenue, net_income, operating_income (4 quarters)
2. `/balance_sheet` → total_debt, total_equity (latest quarter snapshot only)
3. `/cash_flow` → operating_cash_flow (4 quarters)

**NVDA — Raw quarterly data from TwelveData:**

**Quarterly Revenues:**
| Fiscal Date | Revenue |
|-------------|---------|
| 2025-10-31 | $57.01B |
| 2025-07-31 | $46.74B |
| 2025-04-30 | $44.06B |
| 2025-01-31 | $39.33B |

**Quarterly Net Incomes:**
| Fiscal Date | Net Income |
|-------------|-----------|
| 2025-10-31 | $31.91B |
| 2025-07-31 | $26.42B |
| 2025-04-30 | $18.77B |
| 2025-01-31 | $22.09B |

**Quarterly Operating Incomes:**
| Fiscal Date | Operating Income |
|-------------|-----------------|
| 2025-10-31 | $36.01B |
| 2025-07-31 | $28.44B |
| 2025-04-30 | $21.64B |
| 2025-01-31 | $24.03B |

**Quarterly Operating Cash Flows:**
| Fiscal Date | Cash Flow |
|-------------|----------|
| 2025-10-31 | $24.06B |
| 2025-07-31 | $21.28B |
| 2025-04-30 | $19.55B |
| 2025-01-31 | $16.67B |

**Balance Sheet (latest quarter snapshot — NOT summed):**
- total_debt: $9.48B
- total_equity: $118.90B

## C4. LTM Calculation

**Source:** `utils/ltm_calculator.py:18-68`
**Formula:** `ltm_value = Σ(quarterly_values[Q1..Q4])` — sum 4 most recent quarters

**LTM Revenue:**
```
ltm_revenue = $57.01B + $46.74B + $44.06B + $39.33B
            = $187.14B
```

**LTM Net Income:**
```
ltm_net_income = $31.91B + $26.42B + $18.77B + $22.09B
               = $99.20B
```

**LTM Operating Income:**
```
ltm_operating_income = $36.01B + $28.44B + $21.64B + $24.03B
                     = $110.12B
```

**LTM Operating Cash Flow:**
```
ltm_operating_cash_flow = $24.06B + $21.28B + $19.55B + $16.67B
                        = $81.56B
```

**LTM Year derivation:**
```
ltm_year = int("2025-10-31".split("-")[0]) = 2025
```

**Note:** total_debt and total_equity are passed through unchanged (NOT summed across quarters).

## C5. LTM Merge into Stock

**Source:** `utils/ltm_calculator.py:71-148`

The LTM values are added as a new year entry to the existing annual data.

**NVDA `net_incomes` BEFORE merge:**
| Year | Net Income |
|------|-----------|
| 2021 | $4.33B |
| 2022 | $9.75B |
| 2023 | $4.37B |
| 2024 | $29.76B |
| 2025 | $99.20B |

**NVDA `net_incomes` AFTER merge:**
| Year | Net Income | Source |
|------|-----------|--------|
| 2021 | $4.33B | Annual (from cache) |
| 2022 | $9.75B | Annual (from cache) |
| 2023 | $4.37B | Annual (from cache) |
| 2024 | $29.76B | Annual (from cache) |
| 2025 | $99.20B | **LTM (4 quarters summed)** |

**Additional changes from merge:**
- `price_history` updated: today's date + current price added
- `base_score` reset to: None (was 90.3036483493226)
- `potential_score` reset to: None (was None)
- Scores are now `None` → forces recalculation

## C6. Index P/E via Candidate Mean

**Source:** `fund_builder/updater.py:202-203`

In the quarterly update path, index P/E is computed as the **arithmetic mean** of all candidates' P/E ratios:

```python
pe_values = [s.pe_ratio for s in updated_stocks.values() if s.pe_ratio and s.pe_ratio > 0]
index_pe = sum(pe_values) / len(pe_values)
```

**Sample P/E values (first 10 of 47):**
| Symbol | P/E |
|--------|-----|
| ACGL.US | 8.44 |
| AIZ.US | 14.39 |
| AMD.US | 79.43 |
| ANET.US | 54.34 |
| APP.US | 55.83 |
| AVGO.US | 71.23 |
| BKNG.US | 27.84 |
| CB.US | 12.70 |
| CMI.US | 28.67 |
| COIN.US | 14.05 |

```
index_pe = sum(47 P/E values) / 47 = 43.53
```

**Key difference from full build:**
- Full build SP500: API call to `/statistics?symbol=SPX` for the true market P/E
- Full build TASE125: Hardcoded `14.0`
- Quarterly update: Mean of ~47 candidates' P/E = 43.53

## C7. Eligibility Gating by Previous Category

**Source:** `fund_builder/updater.py:181-191`

In the quarterly update path, there is an **asymmetry** in how stocks enter the base vs potential pools:

```python
if stock.is_eligible_for_base and symbol in base_symbols_from_prev:
    base_eligible.append(stock)
elif stock.is_eligible_for_potential:
    potential_eligible.append(stock)
```

**Rules:**
1. A stock can only be a **base candidate** if it was also a base candidate in the previous quarter
2. A stock that was previously base but now fails base criteria can fall through to **potential**
3. A stock that was previously potential cannot enter base, even if it now meets base criteria

**In the full build path**, there is no such gating — any eligible stock can be a base candidate.

## C8. Comparison with Previous Fund

**Source:** `fund_builder/updater.py:281-340` (`_compare_with_previous`), lines 381-418 (`_generate_comparison_md`)

After building the new fund, the update path compares it with the previous quarter's composition:

- **Added stocks:** In new fund but not in previous
- **Removed stocks:** In previous fund but not in new
- **Retained stocks:** In both (with weight/position changes noted)

This generates `_Comparison.md` and appends to `Fund_Docs/CHANGELOG.md`.

---

# Section D: Key Differences — Full Build vs Quarterly Update

| Aspect | Full Build | Quarterly Update |
|--------|-----------|-----------------|
| Stock universe | ~500 (full index) | ~50 (prev top candidates) |
| Financial data | Annual (5 years from API) | Quarterly (4 quarters) → LTM sum + cache |
| Index P/E | API call (SPX) or hardcoded (14.0) | Mean of candidate pool P/E ratios |
| Price history | Fiscal-date aligned | Today's price + cached history |
| Data validation | Full (`validate_financial_data` + `validate_market_data`) | None |
| Base eligibility gate | Any eligible stock | Must be in previous base list |
| Normalization pool | All eligible from 500+ stocks | ~30 base / ~17 potential |
| Output files | Fund.md + Update.md | Fund.md + Update.md + Comparison.md + CHANGELOG |
| API cost | ~300K credits (~45 min) | ~30K credits (~5 min) |
| Prerequisite | None | Previous full build with cache |
