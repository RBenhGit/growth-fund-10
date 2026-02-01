# Growth Fund Builder - TASE125 Functionality Report

**Date:** 2026-02-01
**Index:** TASE125 (Tel Aviv 125)
**Analysis based on:** Cached run from 2025-12-19 (Q4 2025) + live execution attempt (Q1 2026)

---

## 1. Execution Summary

### Live Run Attempt (Q1 2026)
```
Command: python build_fund.py --index TASE125 --debug
Result: FAILED at connection check
Error: EODHD API returned HTTP 403 Forbidden
Root cause: EODHD API key expired/revoked
```

The system correctly detected the connection failure at the `login()` phase, before consuming any resources. However, the design **blocks all execution when the API is down**, even when cached data exists. The cache-only mode requires a valid API connection to proceed.

### Previous Successful Run (Q4 2025)
The analysis below is based on the Q4 2025 cached data (117 stocks, 2025-12-19).

---

## 2. Data Source Configuration

### Active Sources
| Data Type | Source | API Key | Status |
|-----------|--------|---------|--------|
| Financial Data (fundamentals) | EODHD API (`eodhd_api.py`) | `69298028b8f6a5.56584096` | **Expired (403)** |
| Pricing Data (market prices) | yfinance (`yfinance_source.py`) | None required | Available |

### Source Selection Flow (Router)
```
DataSourceRouter.get_financial_source("TASE125")
  -> Settings: FINANCIAL_DATA_SOURCE = "eodhd" (explicit)
  -> Returns: EODHDDataSource

DataSourceRouter.get_pricing_source("TASE125")
  -> Settings: PRICING_DATA_SOURCE = "yfinance" (explicit)
  -> Returns: YFinanceSource
```

### EODHD API Calls Per Stock
1. **Fundamentals call**: `GET /api/fundamentals/{SYMBOL}.TA` - Returns income statements, balance sheets, cash flows, highlights (market cap, P/E)
2. **Historical prices call**: `GET /api/eod/{SYMBOL}.TA?from=DATE&to=DATE` - One call per financial report date (up to 5 calls for 5 years)

### yfinance Calls Per Stock
- Current price: `yf.Ticker(SYMBOL).info['currentPrice']`
- Historical prices: `yf.Ticker(SYMBOL).history(start=..., end=...)` as fallback when EODHD price data is missing

### Total API Budget Per Run
- EODHD: ~1 fundamentals call + ~5 historical price calls = **~6 calls per stock**, ~702 calls for 117 stocks
- yfinance: 1-2 calls per stock (free, no limit)

---

## 3. Step-by-Step Flow Analysis

### Step 1: Fetch Index Constituents
- **Input:** Index name "TASE125"
- **API Call:** `GET /api/fundamentals/TA125.INDX?filter=Components`
- **Processing:** Parses EODHD response dict (keyed by `'0'`, `'1'`, ...) into standardized `{symbol, name, sector, sub_sector}` format
- **Fallback:** If TA125.INDX unavailable, falls back to `GET /api/exchange-symbol-list/TA?type=common_stock` and takes first 125
- **Output:** 117 constituents (cached at `cache/index_constituents/TASE125_Q4_2025.json`)
- **Note:** Only 117 returned instead of expected 125 — EODHD may not have complete TA-125 coverage

### Step 2: Load & Filter Base Stocks
- **Input:** 117 constituents from Step 1
- **Processing per stock:**
  1. Check cache (`cache/stocks_data/{SYMBOL}_TA.json`)
  2. If not cached: fetch fundamentals via EODHD + prices via yfinance
  3. Create `Stock` object with `FinancialData` + `MarketData`
  4. Run `stock.check_base_eligibility()`:
     - 5 consecutive years of positive net income
     - 4 out of 5 years with positive operating income (EBITDA)
     - Positive cash flow in >50% of years
     - Debt-to-equity ratio <= 60%
  5. Run `stock.check_potential_eligibility()` (2 years positive net income)
  6. Save to cache
- **Output:**
  - 117 stocks loaded into `all_loaded_stocks`
  - **Only 2 base-eligible stocks** (CRSO.TA, MGIC.TA)
  - 94 potential-eligible stocks
- **Transition to Step 3:** `builder.base_candidates = [CRSO.TA, MGIC.TA]`

### Step 3: Score & Rank Base Stocks
- **Input:** 2 base-eligible stocks
- **Calculations per stock:**
  - Net income CAGR (3-year): `((NI_recent / NI_3yrs_ago) ^ (1/2) - 1) * 100`
  - Revenue CAGR (3-year): same formula with revenues
  - Market cap: raw value
- **Normalization:** Min-max scaling to 0-100 across the cohort
- **Weighted score:** `NI_growth * 0.40 + Rev_growth * 0.35 + Market_cap * 0.25`
- **Output:**
  | Stock | NI Growth | Rev Growth | Market Cap | Score |
  |-------|-----------|------------|------------|-------|
  | CRSO.TA | 47.9% CAGR (norm: 100) | 5.3% CAGR (norm: 100) | 1.63B (norm: 0) | **75.00** |
  | MGIC.TA | -4.5% CAGR (norm: 0) | -1.3% CAGR (norm: 0) | 4.22B (norm: 100) | **25.00** |
- **Note:** With only 2 stocks, normalization is binary (0 or 100). This degrades scoring quality.
- **Transition to Step 4:** `ranked_base = [CRSO.TA, MGIC.TA]`

### Step 4: Select Top 6 Base Stocks
- **Input:** 2 ranked base stocks
- **Processing:** `select_stocks_skip_duplicates(ranked_base, 6)` — selects up to 6 unique companies
- **Output:** Only 2 stocks selected (insufficient candidates)
- **BUG:** The system proceeds without raising an error when fewer than 6 base stocks are found. This leads to a broken fund composition downstream.
- **Transition to Step 5:** `builder.selected_base = [CRSO.TA, MGIC.TA]`

### Step 5: Prepare Potential Candidate Pool
- **Input:** 117 total stocks minus 2 selected base = 115 remaining
- **Processing:** Simple set subtraction by symbol
- **Output:** 115 stocks in potential pool
- **Transition to Step 6:** `potential_pool = [115 stocks]`

### Step 6: Filter Potential Stocks
- **Input:** 115 stocks from pool
- **Processing:** `stock.check_potential_eligibility()` — 2 years positive net income + 2 years revenue/income data
- **Output:** 92 eligible potential stocks (out of 94 total eligible minus 2 used as base)
- **Transition to Step 7:** `builder.potential_candidates = [92 stocks]`

### Step 7: Score & Rank Potential Stocks
- **Input:** 92 potential-eligible stocks + index P/E ratio
- **Index P/E:** `financial_source.get_index_pe_ratio("TASE125")` — **returns None** for TASE125 (only implemented for SP500 in `eodhd_api.py:390-413`)
- **BUG in working copy (line 499):** References `data_source.get_index_pe_ratio()` but variable is named `financial_source` — causes `NameError` on fresh runs
- **Calculations per stock:**
  - Future growth: 2-year net income CAGR
  - Momentum: `((current_price - oldest_price) / oldest_price) * 100` — **defaults to 0.0 for 88 stocks without price**
  - Valuation: `(2 - stock_pe/index_pe) * 50` — **defaults to 0.0 for all stocks** because `index_pe = None`
- **Normalization:** Min-max to 0-100, then weighted: `growth * 0.50 + momentum * 0.30 + valuation * 0.20`
- **Impact of missing data:**
  - Valuation score = 0 for ALL stocks (index P/E not available). After normalization, all get 50.0 (since all equal).
  - Momentum = 0 for 88/92 stocks (no price data). After normalization, they all get the same low normalized value (~4.76).
- **Output:** 92 scored potential stocks (top score: DUNI.TA at 61.43)
- **Transition to Step 8:** `ranked_potential = [92 stocks sorted by score]`

### Step 8: Select Top 4 Potential Stocks
- **Input:** 92 ranked potential stocks
- **Processing:** `select_stocks_skip_duplicates(ranked_potential, 4)`
- **Output:** 4 stocks: DUNI.TA, ENLT.TA, CAMT.TA, NVMI.TA
- **Transition to Step 9:** `builder.selected_potential = [4 stocks]`

### Step 9: Assign Fixed Weights
- **Input:** 2 base + 4 potential = 6 total (should be 10)
- **Weight assignment:** Position-based from `FUND_WEIGHTS = [0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]`
- **Actual assignment (only 6 stocks):**
  | Position | Stock | Weight |
  |----------|-------|--------|
  | 1 | CRSO.TA | 18% |
  | 2 | MGIC.TA | 16% |
  | 3 | DUNI.TA | 16% |
  | 4 | ENLT.TA | 10% |
  | 5 | CAMT.TA | 10% |
  | 6 | NVMI.TA | 10% |
- **Total weight: 80%** (missing 20% from 4 unfilled positions)
- **BUG:** No IndexError because only 6 stocks are iterated, but weight total != 100%
- **Transition to Step 10:** `positions = [(stock, weight) for each]`

### Step 10: Calculate Minimum Fund Cost
- **Input:** 6 (stock, weight) pairs
- **Algorithm:**
  1. Find highest-priced stock: NVMI.TA at 312.78 (weight 10%)
  2. Fund cost = 312.78 / 0.10 = 3,127.80
  3. For each stock: `shares = round(fund_cost * weight / price)`
  4. CRSO.TA: price=0.00 -> division by zero protection (price > 0 check), gets 0 shares
  5. DUNI.TA: price=0.00 -> same, gets 0 shares
- **Output:** min_cost = 1,440.27, shares_dict with 0 shares for priceless stocks
- **Transition to Step 11**

### Step 11: Create Fund Table
- **Input:** 6 stocks with weights and shares
- **Processing:** Creates `FundPosition` objects, all first 6 labeled "base" (position_type = "בסיס" if i < 6)
- **BUG:** Since only 2 are actual base stocks, positions 3-6 (DUNI, ENLT, CAMT, NVMI) are potential stocks incorrectly labeled as "בסיס"
- **Output:** Fund object with 6 positions (not 10)

### Step 12-13: Generate Documents
- **Input:** Fund object, ranked lists
- **Output:** Markdown files at `Fund_Docs/Fund_10_TASE125_Q4_2025.md` and `Fund_10_TASE125_Q4_2025_Update.md`

### Step 14: Validation
- **Checks performed:**
  1. Weight sum = 80% != 100% -> **FAILS**
  2. Position count = 6 != 10 -> **FAILS**
  3. Base count = 6 != 6 -> **PASSES** (incorrectly, because potential stocks were labeled as base)
  4. Potential count = 0 != 4 -> **FAILS**
- **Result:** Fund creation "succeeds" but validation catches the errors

---

## 4. Missing Data Inventory

### 4.1 Summary Statistics
| Data Field | Missing Count | Total | Percentage |
|------------|--------------|-------|------------|
| Current Price | 88 | 117 | **75%** |
| Price History | 87 | 117 | **74%** |
| P/E Ratio | 11 | 117 | 9% |
| Revenues | 1 | 117 | <1% |
| Net Incomes | 1 | 117 | <1% |
| Operating Incomes | 1 | 117 | <1% |
| Cash Flows | 1 | 117 | <1% |
| Market Cap | 0 | 117 | 0% |
| 5 Years Financial Data | 115 | 117 | 98% have 5 years |

### 4.2 Root Cause: yfinance Symbol Mismatch
EODHD uses `.TA` suffix symbols (e.g., `LUMI.TA`). The `get_stock_data()` method in `eodhd_api.py:231` converts to yfinance format by stripping the suffix: `yf_symbol = symbol.split('.')[0]` producing `LUMI`. However, yfinance requires **TASE symbols with `.TA` suffix** for Israeli stocks. The stripped symbol `LUMI` is not recognized by yfinance, returning no price data. Only stocks that happen to have valid US tickers (dual-listed companies like NICE, CAMT, NVMI, ESLT, TEVA) get prices.

### 4.3 Stocks WITH Valid Price Data (29 stocks)
These are primarily dual-listed companies (traded on both TASE and US exchanges):

| Symbol | Name | Price | P/E | History Entries |
|--------|------|-------|-----|----------------|
| CAMT.TA | Camtek Ltd | 101.71 | 102.43 | 6 |
| ENLT.TA | Enlight Renewable Energy Ltd | 41.17 | 43.31 | 4 |
| ESLT.TA | Elbit Systems Ltd | 541.16 | 55.23 | 6 |
| FOX.TA | Fox-Wizel Ltd | 63.41 | 23.17 | 6 |
| HARL.TA | Harel Insurance | 25.00 | 15.90 | 6 |
| ICL.TA | ICL Israel Chemicals | 4.96 | 17.35 | 6 |
| MGIC.TA | Magic Software | 24.65 | 32.59 | 6 |
| NICE.TA | Nice Ltd | 108.84 | 12.56 | 6 |
| NVMI.TA | Nova Ltd | 312.78 | 40.96 | 6 |
| ORA.TA | Ormat Technologies | 110.31 | 51.29 | 6 |
| SPNS.TA | Sapiens International | 43.45 | 37.70 | 6 |
| STRS.TA | Strauss Group | 25.59 | 16.69 | 6 |
| TEVA.TA | Teva Pharmaceutical | 30.32 | 49.31 | 6 |
| TSEM.TA | Tower Semiconductor | 116.69 | 68.59 | 6 |
| *(+15 more)* | | | | |

### 4.4 Stocks WITHOUT Valid Price Data (88 stocks)
Major Israeli companies missing price data due to the yfinance symbol issue:

| Symbol | Name | Has P/E | Impact |
|--------|------|---------|--------|
| LUMI.TA | Bank Leumi | Yes (10.57) | Momentum=0, No shares allocation |
| POLI.TA | Bank Hapoalim | Yes (10.91) | Momentum=0, No shares allocation |
| DSCT.TA | Israel Discount Bank | Yes (10.54) | Momentum=0, No shares allocation |
| MZTF.TA | Mizrahi Tefahot | Yes (11.05) | Momentum=0, No shares allocation |
| AZRG.TA | Azrieli Group | Yes (24.29) | Momentum=0, No shares allocation |
| BEZQ.TA | Bezeq Telecom | Yes (13.28) | Momentum=0, No shares allocation |
| ELAL.TA | El Al Airlines | Yes (5.96) | Momentum=0, No shares allocation |
| CRSO.TA | Carasso | Yes (4.98) | **#1 base stock has 0 shares!** |
| DUNI.TA | Duniec | Yes (107.35) | **#1 potential stock has 0 shares!** |
| *(+79 more)* | | | |

### 4.5 The Single Stock with No Financial Data
| Symbol | Name | Issue |
|--------|------|-------|
| ECP.TA | Electra Co Pr | Has some price history (2 entries) but no revenue/income/cash flow data |

---

## 5. Calculation Details

### 5.1 Base Stock Scoring

**Formula:** Weighted composite of 3 normalized metrics

```
Step 1: Raw metric calculation
  net_income_growth = CAGR(net_incomes, 3 years)
    CAGR = ((NI_year0 / NI_year2) ^ (1/2) - 1) * 100

  revenue_growth = CAGR(revenues, 3 years)
    Same formula

  market_cap = raw market cap value (no transformation)

Step 2: Normalization (per metric, across all stocks)
  normalized = ((value - min) / (max - min)) * 100
  If all values equal: normalized = 50.0

Step 3: Weighted composite
  score = NI_growth_norm * 0.40 + Rev_growth_norm * 0.35 + MCap_norm * 0.25
```

**Example: CRSO.TA**
```
NI growth: ((276,833,000 / 126,578,000) ^ 0.5 - 1) * 100 = 47.89%
Rev growth: ((4,332,457,000 / 3,907,463,000) ^ 0.5 - 1) * 100 = 5.30%
Market cap: 1,628,835,200

Normalized (across 2-stock cohort):
  NI growth: 100.0 (highest)
  Rev growth: 100.0 (highest)
  Market cap: 0.0 (smallest)

Score = 100*0.40 + 100*0.35 + 0*0.25 = 75.00
```

**Example: MGIC.TA**
```
NI growth: ((36,883,000 / 40,470,000) ^ 0.5 - 1) * 100 = -4.53%
Rev growth: ((552,520,000 / 566,792,000) ^ 0.5 - 1) * 100 = -1.27%
Market cap: 4,224,013,056

Normalized:
  NI growth: 0.0 (lowest)
  Rev growth: 0.0 (lowest)
  Market cap: 100.0 (largest)

Score = 0*0.40 + 0*0.35 + 100*0.25 = 25.00
```

### 5.2 Potential Stock Scoring

**Formula:** Weighted composite of 3 metrics

```
Step 1: Raw metric calculation
  future_growth = CAGR(net_incomes, 2 years)

  momentum = ((current_price - oldest_price) / oldest_price) * 100
    Uses price_history dict, oldest vs current
    Default: 0.0 if no price history

  valuation = (2 - stock_pe / index_pe) * 50
    Default: 0.0 if no P/E or no index P/E

Step 2: Normalization to 0-100

Step 3: Weighted composite
  score = growth_norm * 0.50 + momentum_norm * 0.30 + valuation_norm * 0.20
```

**Example: DUNI.TA (Top potential, score 61.43)**
```
Growth: NI went from 485,000 (2023) to 30,343,000 (2024)
  CAGR = ((30,343,000 / 485,000) ^ (1/1) - 1) * 100 = 6,156.3%
  (Extreme growth from near-zero base)
  Normalized: 100.0 (highest)

Momentum: No price data -> 0.0
  Normalized: 4.76 (near bottom, some stocks had even lower)

Valuation: index_pe = None -> 0.0
  Normalized: 50.0 (all equal, all get 50)

Score = 100.0*0.50 + 4.76*0.30 + 50.0*0.20 = 61.43
```

**Example: ENLT.TA (Score 40.00)**
```
Growth: NI went negative -> CAGR = -82.7%
  Normalized: 0.0 (worst growth)

Momentum: (41.17 - 1.87) / 1.87 * 100 = 2,100.5%
  Normalized: 100.0 (highest momentum)

Valuation: index_pe = None -> 0.0
  Normalized: 50.0

Score = 0.0*0.50 + 100.0*0.30 + 50.0*0.20 = 40.00
```

### 5.3 Minimum Fund Cost Calculation

```
Algorithm:
  1. Find max_price among selected stocks: NVMI.TA at 312.78
  2. max_weight = 0.10 (NVMI's weight)
  3. fund_cost = 312.78 / 0.10 = 3,127.80
  4. Per stock:
     CRSO.TA: price=0 -> skipped (0 shares)
     MGIC.TA: round(3127.80 * 0.16 / 24.65) = round(20.3) = 20 shares
     DUNI.TA: price=0 -> skipped (0 shares)
     ENLT.TA: round(3127.80 * 0.10 / 41.17) = round(7.6) = 8 shares
     CAMT.TA: round(3127.80 * 0.10 / 101.71) = round(3.07) = 3 shares
     NVMI.TA: round(3127.80 * 0.10 / 312.78) = round(1.0) = 1 share
  5. actual_cost = 0 + 20*24.65 + 0 + 8*41.17 + 3*101.71 + 1*312.78 = 1,440.27
```

**Problem:** 2 of 6 positions (CRSO.TA, DUNI.TA) have 0 shares because current_price = 0. The fund is **unbuyable** as composed.

---

## 6. Critical Bugs and Issues Found

### 6.1 CRITICAL: yfinance Symbol Conversion Bug
**File:** `data_sources/eodhd_api.py:231`
```python
yf_symbol = symbol.split('.')[0]  # LUMI.TA -> LUMI (wrong!)
```
Israeli stocks on yfinance require `.TA` suffix. This should be:
```python
yf_symbol = symbol  # Keep LUMI.TA as-is for yfinance
```
**Impact:** 75% of TASE stocks have no current price and no price history.

### 6.2 CRITICAL: EODHD EBITDA vs Operating Income
**File:** `data_sources/eodhd_api.py:202`
```python
ebitda = stmt.get("ebitda", 0)
operating_incomes[year_int] = float(ebitda) if ebitda is not None else 0.0
```
EODHD's `ebitda` field is used as operating income. For many TASE companies (especially banks, insurance, real estate), EBITDA is reported as 0 or null. This causes 111/117 stocks to fail the "4 out of 5 years positive operating income" base eligibility test.
**Impact:** Only 2 stocks pass base eligibility instead of an expected 30-50+.

### 6.3 CRITICAL: No Minimum Stock Count Enforcement
**File:** `build_fund.py:464`
```python
builder.selected_base = select_stocks_skip_duplicates(ranked_base, 6)
```
No check that 6 stocks were actually found. The system continues with fewer stocks, producing a broken fund (80% weight, 6/10 positions, wrong position types).

### 6.4 BUG: Undefined Variable `data_source`
**File:** `build_fund.py:499` (working copy)
```python
index_pe = data_source.get_index_pe_ratio(index_name)
```
Should be `financial_source.get_index_pe_ratio(index_name)`. The variable `data_source` does not exist in the current code. This causes `NameError` on fresh runs.

### 6.5 BUG: Index P/E Returns None for TASE125
**File:** `data_sources/eodhd_api.py:390-413`
The `get_index_pe_ratio()` method only handles SP500. For TASE125, it silently returns `None`, which causes ALL valuation scores to default to 0.0 for all stocks, making the valuation component meaningless.

### 6.6 BUG: Position Type Mislabeling
**File:** `build_fund.py:555`
```python
position_type = "בסיס" if i < 6 else "פוטנציאל"
```
With only 2 base stocks, positions 3-6 are potential stocks labeled as "base". The labeling assumes exactly 6 base stocks exist.

---

## 7. Data Flow Diagram

```
.env Configuration
    |
    v
DataSourceRouter
    |-> get_financial_source("TASE125") -> EODHDDataSource
    |-> get_pricing_source("TASE125")  -> YFinanceSource
    |
    v
Step 1: EODHD GET /fundamentals/TA125.INDX?filter=Components
    |-> 117 constituents [{symbol, name, sector}]
    |-> Cached: cache/index_constituents/TASE125_Q4_2025.json
    |
    v
Step 2: For each of 117 stocks:
    |-> EODHD GET /fundamentals/{SYM}.TA -> FinancialData
    |   (revenues, net_incomes, operating_incomes, cash_flows, debt, equity)
    |-> EODHD GET /eod/{SYM}.TA?from=DATE&to=DATE -> price_history (per report date)
    |-> yfinance Ticker(SYM).info -> current_price (FAILS for 88 stocks: symbol bug)
    |-> check_base_eligibility() -> 2 pass, 115 fail (EBITDA=0 bug)
    |-> check_potential_eligibility() -> 94 pass
    |-> Cached: cache/stocks_data/{SYM}_TA.json
    |
    v
Step 3: score_and_rank_base_stocks(2 stocks)
    |-> CAGR calculations -> normalize -> weighted composite
    |-> CRSO.TA: 75.00, MGIC.TA: 25.00
    |
    v
Step 4: select top 6 -> only 2 available
    |
    v
Step 5: 117 - 2 = 115 in potential pool
    |
    v
Step 6: filter potential -> 92 eligible
    |
    v
Step 7: score_and_rank_potential_stocks(92, index_pe=None)
    |-> Valuation=0 for all (no index P/E)
    |-> Momentum=0 for 88 stocks (no price data)
    |-> Top: DUNI.TA (61.43), ENLT.TA (40.00)
    |
    v
Step 8: select top 4 potential
    |
    v
Step 9: assign weights (only 6 stocks, total=80%)
    |
    v
Step 10: calculate min cost -> 1,440.27 (2 stocks with 0 shares)
    |
    v
Steps 11-13: generate markdown documents
    |
    v
Step 14: validate -> FAILS (weight!=100%, count!=10, potential!=4)
```

---

## 8. Recommendations

1. **Fix yfinance symbol handling** - Keep `.TA` suffix for Israeli stocks when calling yfinance
2. **Replace EBITDA with operating income** - Use `operatingIncome` field from EODHD instead of `ebitda`
3. **Add minimum stock count checks** - Abort or warn when fewer than 6 base or 4 potential stocks found
4. **Implement TASE125 P/E ratio** - Calculate from weighted constituent P/E values
5. **Fix `data_source` variable reference** - Change to `financial_source` on line 499
6. **Fix position type labeling** - Use actual stock count, not hardcoded index `< 6`
7. **Add offline/cache-only mode** - Allow fund building from cache when API is unavailable
