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

The system uses **separate data sources** for different types of data:
- **Financial Data** (fundamentals, financial statements, ratios)
- **Pricing Data** (historical prices, market data)

### Default Configuration (Recommended)
- **Financial Data**: EODHD API
- **Pricing Data**: yfinance (Yahoo Finance)

This combination provides the best balance of data quality, coverage, and cost.

### Available Data Sources

#### For Financial Data (FINANCIAL_DATA_SOURCE)

1. **eodhd** - EOD Historical Data API (recommended)
   - Requires: `EODHD_API_KEY`
   - Supports both TASE (Israeli) and US stocks
   - Provides fundamentals, historical prices, and financial statements
   - Test with: `python test_eodhd.py`

2. **fmp** - Financial Modeling Prep API
   - Requires: `FMP_API_KEY`
   - Free tier: 500 requests/day (limited endpoints)
   - Supports US stocks and some international markets
   - Test with: `python test_fmp.py`

3. **investing** - Investing.com via Selenium
   - Requires: `INVESTING_EMAIL` and `INVESTING_PASSWORD` (Pro account)
   - Currently implemented in [data_sources/investing_scraper.py](data_sources/investing_scraper.py)
   - Test with: `python test_investing.py`

4. **alphavantage** - Alpha Vantage API
   - Requires: `ALPHAVANTAGE_API_KEY`
   - Free tier: 25 requests/day
   - US stocks only

5. **csv** - Manual CSV file input (future)
   - For manual data entry workflows

#### For Pricing Data (PRICING_DATA_SOURCE)

1. **yfinance** - Yahoo Finance (recommended)
   - No API key required
   - Free and reliable
   - Excellent coverage for both US and international markets
   - Provides real-time and historical price data

2. **eodhd** - EOD Historical Data API
   - Requires: `EODHD_API_KEY`
   - Use if you already have EODHD for financial data

3. **alphavantage** - Alpha Vantage API
   - Requires: `ALPHAVANTAGE_API_KEY`
   - Free tier: 25 requests/day
   - US stocks only

### Data Source Priority

Per [Fund_Update_Instructions.md](Fund_Update_Instructions.md:19-49):
- **Official sources first**: SEC EDGAR (US), TASE/Maya (Israel)
- **Backup sources**: Investing.com, Yahoo Finance, Google Finance
- Always document which source was used for each data point

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

Create a `.env` file in the project root (see [.env](.env) for template):

```bash
# ====================================================================
# Data Source Configuration
# ====================================================================
# Separate data sources for financial data and pricing data

# Financial data source (fundamentals, financial statements)
# Options: eodhd (recommended), fmp, investing, alphavantage, csv
FINANCIAL_DATA_SOURCE=eodhd

# Pricing data source (historical prices, market data)
# Options: yfinance (recommended - free, no API key), eodhd, alphavantage
PRICING_DATA_SOURCE=yfinance

# ====================================================================
# API Keys
# ====================================================================

# EOD Historical Data API (recommended - supports TASE + US)
EODHD_API_KEY=your-api-key-here

# Financial Modeling Prep API
FMP_API_KEY=your-api-key-here

# Investing.com credentials (if using investing source)
INVESTING_EMAIL=your-email@example.com
INVESTING_PASSWORD=your-password

# Alpha Vantage API (US stocks only)
ALPHAVANTAGE_API_KEY=your-api-key-here

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

### Note on Legacy Configuration
For backwards compatibility, if you set `DATA_SOURCE` in your `.env` file, it will be used for both financial and pricing data. However, the recommended approach is to use the separate `FINANCIAL_DATA_SOURCE` and `PRICING_DATA_SOURCE` settings for better flexibility.

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
