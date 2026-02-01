# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Growth Fund Builder (מערכת בניית קרן צמיחה 10)** - an automated system for building and managing investment portfolios based on stock indices. The system analyzes stocks from either the TA-125 (Israeli) or S&P500 (US) indices, scores them using multiple financial criteria, and constructs optimized portfolios.

The fund consists of:
- **6 base stocks**: Established companies with 5+ years of proven profitability
- **4 potential stocks**: High-growth candidates with 2+ years of profitability

## Commands

### Building a Fund
```bash
# Build fund for TA-125 index (Israeli stocks)
python build_fund.py --index TASE125

# Build fund for S&P500 index (US stocks)
python build_fund.py --index SP500 --quarter Q4 --year 2025

# Build without using cached data
python build_fund.py --index SP500 --no-cache

# Enable debug mode for verbose output
python build_fund.py --index TASE125 --debug
```

### Testing Data Sources
```bash
# Test EOD Historical Data API (requires EODHD_API_KEY in .env)
python test_eodhd.py

# Test Financial Modeling Prep API (requires FMP_API_KEY in .env)
python test_fmp.py

# Test Investing.com scraper (requires credentials in .env)
python test_investing.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture Overview

### Core Components

**Entry Point:**
- [build_fund.py](build_fund.py) - Main CLI application using argparse and Rich for UI

**Configuration System:**
- [config/settings.py](config/settings.py) - Centralized settings loaded from .env
- `.env` - Configuration file (not in git) containing API keys and preferences
- Settings include: data source selection, API credentials, fund parameters, scoring weights

**Data Models (Pydantic-based):**
- [models/stock.py](models/stock.py) - `Stock` model with eligibility checking methods
- [models/fund.py](models/fund.py) - `Fund` and `FundPosition` models for portfolio management
- [models/financial_data.py](models/financial_data.py) - `FinancialData` and `MarketData` for financial metrics
  - Includes methods for profitability checks, cash flow analysis, and debt ratios

**Data Sources (Abstract + Implementations):**
- [data_sources/base_data_source.py](data_sources/base_data_source.py) - Abstract base class defining the data source interface
- [data_sources/investing_scraper.py](data_sources/investing_scraper.py) - Selenium-based web scraper for Investing.com
  - Uses webdriver_manager for Chrome automation
  - Implements login, constituent fetching, and financial data scraping
  - Future: Alpha Vantage and FMP API implementations

**Utilities:**
- [utils/date_utils.py](utils/date_utils.py) - Quarter/year calculations, fund naming conventions
  - `get_quarter_and_year()` - Determines Q1-Q4 based on current month
  - `format_fund_name()` - Creates standardized fund names (e.g., "Fund_10_TASE_Q4_2025")

### Directory Structure
```
├── build_fund.py           # Main entry point
├── test_investing.py       # Scraper testing utility
├── config/                 # Configuration management
│   └── settings.py
├── models/                 # Pydantic data models
│   ├── stock.py           # Stock model with eligibility logic
│   ├── fund.py            # Fund composition model
│   └── financial_data.py  # Financial metrics models
├── data_sources/          # Data fetching implementations
│   ├── base_data_source.py
│   └── investing_scraper.py
├── utils/                 # Helper utilities
│   └── date_utils.py
├── fund_builder/          # Fund construction logic (in development)
├── cache/                 # Cached data (stocks, index constituents)
└── Fund_Docs/             # Generated fund documentation
```

## Fund Building Process

The system follows a 14-step process defined in [Fund_Update_Instructions.md](Fund_Update_Instructions.md):

1. **Fetch Index Constituents** - Get current stock list from index
2. **Filter Base Stocks** - Apply strict eligibility criteria (5 years profitability, operating profit, debt/equity < 60%)
3. **Score Base Candidates** - Calculate scores based on:
   - Net income growth: 40%
   - Revenue growth: 35%
   - Market cap: 25%
4. **Select Top 6 Base Stocks** - Highest scoring stocks become the core portfolio
5. **Prepare Potential List** - Remove base stocks from index constituents
6. **Filter Potential Stocks** - Relaxed criteria (2 years profitability)
7. **Score Potential Candidates** - Different scoring model:
   - Future growth potential: 50%
   - Momentum: 30%
   - Valuation: 20%
8. **Select Top 4 Potential Stocks**
9. **Assign Fixed Weights** - 20%, 16%, 14%, 12%, 10%, 8%, 6%, 5%, 5%, 4%
10. **Calculate Minimum Fund Cost** - Ensure whole share numbers per fund unit
11. **Generate Fund Table**
12. **Create Update Document** - With all scoring tables
13. **Create Final Fund Documents** - Separate files for TASE and SP500
14. **Validation** - Verify weights sum to 100%, no overlaps, whole shares

### Scoring System Constants

Defined in [config/settings.py](config/settings.py:46-60):
```python
FUND_WEIGHTS = [0.20, 0.16, 0.14, 0.12, 0.10, 0.08, 0.06, 0.05, 0.05, 0.04]
BASE_SCORE_WEIGHTS = {
    "net_income_growth": 0.40,
    "revenue_growth": 0.35,
    "market_cap": 0.25
}
POTENTIAL_SCORE_WEIGHTS = {
    "future_growth": 0.50,
    "momentum": 0.30,
    "valuation": 0.20
}
```

## Data Sources

The system uses a **2x2 configuration matrix** for maximum flexibility:
- **Market dimension**: US stocks (SP500) vs Israeli stocks (TASE125)
- **Data type dimension**: Financial data (fundamentals) vs Pricing data (market prices)

This allows you to optimize for cost and quality by mixing different APIs. For example:
- Use **FMP** for US fundamentals + **yfinance** for all pricing (saves money)
- Use **TASE Data Hub** for Israeli fundamentals (most accurate) + **yfinance** for pricing

### Configuration Matrix

```
              Financial Data          Pricing Data
US (SP500)    [Configurable API]     [Configurable API]
TASE (125)    [Configurable API]     [Configurable API]
```

Configure via `.env`:
- `US_FINANCIAL_DATA_SOURCE` - US stock fundamentals
- `US_PRICING_DATA_SOURCE` - US stock prices
- `TASE_FINANCIAL_DATA_SOURCE` - Israeli stock fundamentals
- `TASE_PRICING_DATA_SOURCE` - Israeli stock prices

### Available Data Sources

| Source | TASE | US | Cost | Rate Limit | Best For |
|--------|------|-----|------|------------|----------|
| **EODHD** | ✓ | ✓ | $80/mo | High | Production (all-in-one) |
| **TASE Data Hub** | ✓ | ✗ | Free/Paid | Medium | Israeli fundamentals (official) |
| **FMP** | ✗ | ✓ | Free tier | 250/day | US fundamentals (budget) |
| **Alpha Vantage** | ✗ | ✓ | Free tier | 25/day | Light usage |
| **yfinance** | ✓ | ✓ | FREE | Unlimited | Pricing data (recommended) |
| **Investing.com** | ✓ | ✓ | Pro req. | Slow | Not recommended |

#### 1. EODHD (EOD Historical Data)
- **Type**: Financial + Pricing
- **Markets**: US, TASE, Global
- **Key**: `EODHD_API_KEY`
- **Best for**: All-in-one solution
- **Test**: `python test_eodhd.py`

#### 2. FMP (Financial Modeling Prep)
- **Type**: Financial only
- **Markets**: US stocks
- **Key**: `FMP_API_KEY`
- **Free tier**: 250 requests/day
- **Best for**: US fundamentals on budget
- **Test**: `python test_fmp.py`

#### 3. TASE Data Hub
- **Type**: Financial only
- **Markets**: Israeli stocks (TA-125)
- **Key**: `TASE_DATA_HUB_API_KEY`
- **Best for**: Most accurate Israeli fundamentals (official exchange API)
- **Note**: Uses yfinance fallback for pricing

#### 4. Alpha Vantage
- **Type**: Financial + Pricing
- **Markets**: US stocks only
- **Key**: `ALPHAVANTAGE_API_KEY`
- **Free tier**: 25 requests/day (very limited)
- **Best for**: Light usage, testing

#### 5. yfinance (Yahoo Finance)
- **Type**: Pricing only (limited fundamentals)
- **Markets**: US, TASE, Global
- **Key**: None (free, no API key needed)
- **Best for**: All pricing data (highly recommended)
- **Note**: Unlimited requests, very reliable

#### 6. Investing.com (Web Scraper)
- **Type**: Financial + Pricing
- **Markets**: US, TASE, Global
- **Credentials**: `INVESTING_EMAIL`, `INVESTING_PASSWORD`
- **Best for**: Not recommended (slow, brittle)

### Recommended Configurations

#### Optimal (Best Quality, Low Cost)
```bash
US_FINANCIAL_DATA_SOURCE=fmp
US_PRICING_DATA_SOURCE=yfinance          # Free!
TASE_FINANCIAL_DATA_SOURCE=tase_data_hub
TASE_PRICING_DATA_SOURCE=yfinance        # Free!
```

#### Universal (One API for Everything)
```bash
US_FINANCIAL_DATA_SOURCE=eodhd
US_PRICING_DATA_SOURCE=eodhd
TASE_FINANCIAL_DATA_SOURCE=eodhd
TASE_PRICING_DATA_SOURCE=eodhd
```

#### Free Tier (Testing Only)
```bash
US_FINANCIAL_DATA_SOURCE=fmp             # 250 req/day
US_PRICING_DATA_SOURCE=yfinance          # Unlimited
TASE_FINANCIAL_DATA_SOURCE=              # Auto-select
TASE_PRICING_DATA_SOURCE=yfinance        # Unlimited
```

### Auto-Selection Fallback Chains

If you leave a source blank, the router auto-selects from these chains:

- **US Financial**: fmp → alphavantage → eodhd
- **US Pricing**: yfinance → eodhd → alphavantage
- **TASE Financial**: tase_data_hub → eodhd
- **TASE Pricing**: yfinance → eodhd

### Data Source Priority

Per [Fund_Update_Instructions.md](Fund_Update_Instructions.md:19-49):
- **Official sources first**: SEC EDGAR (US), TASE/Maya (Israel)
- **Backup sources**: Investing.com, Yahoo Finance, Google Finance
- Always document which source was used for each data point

### Testing Your Configuration

After setting up your `.env` file, test all configured sources:

```bash
python tests/test_all_sources.py
```

This will verify:
- API keys are valid
- Sources implement the correct interface
- Data returned is valid and complete
- Router correctly selects sources

### Troubleshooting

#### Problem: `AttributeError: 'FMPDataSource' object has no attribute 'get_stock_data'`

**Solution**: You're using an old version. All sources now implement `get_stock_data()`. Update your code.

#### Problem: `DataSourceAuthenticationError: Invalid API key`

**Solution**:
1. Check your `.env` file for the correct API key
2. Verify the key is active on the provider's website
3. Ensure no extra spaces or quotes around the key

#### Problem: `DataSourceRateLimitError: Rate limit exceeded`

**Solution**:
1. **Immediate**: Use cached data with `--no-cache` flag removed
2. **Short-term**: Wait for rate limit to reset (check provider docs)
3. **Long-term**: Switch to a different source or upgrade your plan

Example - switch from Alpha Vantage to FMP:
```bash
# In .env
US_FINANCIAL_DATA_SOURCE=fmp  # Changed from alphavantage
```

#### Problem: Different sources give different financial data

**Solution**: This is normal. APIs update at different times and may use different accounting standards.

To compare sources for debugging:
```python
from data_sources.adapter import DataSourceAdapter

adapter = DataSourceAdapter()
comparison = adapter.compare_sources(
    symbol="AAPL",
    data1=fmp_data,
    source1="FMP",
    data2=eodhd_data,
    source2="EODHD"
)
print(comparison)
```

Acceptable variances:
- Price: ±2%
- Market cap: ±5%
- Revenue/income: ±10% (due to fiscal year differences)

#### Problem: `ValueError: No financial data source available for SP500`

**Solution**: No API keys are configured or available.

1. Check which keys you have in `.env`
2. Configure at least one source for that market
3. Test the source: `python test_fmp.py` (or test_eodhd.py, etc.)

Example fix:
```bash
# Add to .env
FMP_API_KEY=your-key-here
```

## Important Implementation Notes

### Hebrew Language Support
- The codebase extensively uses Hebrew strings and documentation
- [build_fund.py](build_fund.py:18-23) includes Windows console encoding fixes:
  ```python
  if sys.platform == "win32":
      import codecs
      sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
  ```
- Apply this pattern to any new scripts that output Hebrew text

### Stock Eligibility Logic

Base stocks must meet ALL criteria (implemented in [models/stock.py](models/stock.py:67-105)):
- 5+ years of positive net income (consecutive)
- 4 out of 5 years with positive operating income
- Positive cash flow in majority of years
- Debt-to-equity ratio < 60%

Potential stocks have relaxed criteria:
- 2+ years of positive net income
- Complete growth data for 2 years

### Selenium WebDriver Setup

The [investing_scraper.py](data_sources/investing_scraper.py:52-81) uses:
- `webdriver-manager` for automatic ChromeDriver installation
- Headless mode option for automation
- Anti-detection measures (`--disable-blink-features=AutomationControlled`)
- Context manager support (`__enter__`/`__exit__`)

### Cache System

[config/settings.py](config/settings.py:91) creates cache directories:
- `cache/stocks_data/` - Individual stock financial data
- `cache/index_constituents/` - Index member lists
- Controlled by `USE_CACHE` environment variable

## Configuration

Create a `.env` file in the project root (see [.env.template](.env.template) for full template):

```bash
# ====================================================================
# Advanced Data Source Configuration (2x2 Matrix)
# ====================================================================

# US stocks (S&P 500) - Financial data
# Options: fmp, alphavantage, eodhd
# Leave blank for auto-selection
US_FINANCIAL_DATA_SOURCE=fmp

# US stocks (S&P 500) - Pricing data
# Options: yfinance, eodhd, alphavantage
# Recommended: yfinance (free!)
US_PRICING_DATA_SOURCE=yfinance

# Israeli stocks (TA-125) - Financial data
# Options: tase_data_hub, eodhd, investing
# Leave blank for auto-selection
TASE_FINANCIAL_DATA_SOURCE=tase_data_hub

# Israeli stocks (TA-125) - Pricing data
# Options: yfinance, eodhd, investing
# Recommended: yfinance (free!)
TASE_PRICING_DATA_SOURCE=yfinance

# ====================================================================
# API Keys
# ====================================================================

EODHD_API_KEY=your-key-here
FMP_API_KEY=your-key-here
TASE_DATA_HUB_API_KEY=your-key-here
ALPHAVANTAGE_API_KEY=your-key-here

# Investing.com (not recommended)
INVESTING_EMAIL=your-email@example.com
INVESTING_PASSWORD=your-password

# ====================================================================
# Fund Parameters (auto-calculated if blank)
# ====================================================================
FUND_QUARTER=  # Q1-Q4, auto-detected from current month
FUND_YEAR=     # Auto-detected if blank

# ====================================================================
# General Settings
# ====================================================================
OUTPUT_DIRECTORY=./Fund_Docs
USE_CACHE=true
DEBUG_MODE=false
```

### Legacy Configuration (Backwards Compatible)

For simpler configuration, you can still use the old variables:

```bash
# These work but are less flexible than the 2x2 matrix above
FINANCIAL_DATA_SOURCE=eodhd  # Used for both US and TASE
PRICING_DATA_SOURCE=yfinance  # Used for both US and TASE

# Even older - used for everything:
DATA_SOURCE=eodhd
```

The system automatically falls back to these legacy settings if the 2x2 matrix is not configured.

## Future Development Areas

Based on TODO comments in the code:

1. **EODHD Data Source Implementation** - Create [data_sources/eodhd_api.py](data_sources/eodhd_api.py) implementing `BaseDataSource`
2. **Fund Builder Implementation** - [build_fund.py](build_fund.py:122-131) has placeholder steps
3. **Financial Data Scraping** - [investing_scraper.py](data_sources/investing_scraper.py:240-245) needs full implementation
4. **Scoring Algorithms** - Implement growth, momentum, and valuation calculations
5. **LCM Calculation** - [Fund_Update_Instructions.md](Fund_Update_Instructions.md:163) minimum cost calculation

## Key Design Patterns

- **Abstract Data Source**: Plugin architecture for multiple data providers
- **Pydantic Models**: Type-safe data validation throughout
- **Rich CLI**: Beautiful terminal UI with progress bars and panels
- **Singleton Settings**: Single `settings` instance exported from config module
- **Context Managers**: Selenium driver with automatic cleanup
