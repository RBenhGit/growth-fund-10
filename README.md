# Growth Fund Builder (מערכת בניית קרן צמיחה 10)

An automated system for building and managing investment portfolios based on stock indices. The system analyzes stocks from the TA-125 (Israeli) or S&P500 (US) indices, scores them using multiple financial criteria, and constructs optimized portfolios.

## 📋 Table of Contents

- [Features](#features)
- [Fund Composition](#fund-composition)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Backtesting](#backtesting)
- [Testing Data Sources](#testing-data-sources)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- **Dual-Market Support**: Works with both Israeli (TA-125) and US (S&P500) stocks
- **Hybrid Data Sources**: Uses EODHD API for financial data and yfinance for pricing
- **Automated Scoring**: Multi-factor scoring system for stock selection
- **Smart Caching**: Reduces API calls and improves performance
- **Beautiful CLI**: Rich terminal UI with progress bars and tables
- **Hebrew Support**: Full Hebrew language support for Israeli market

## 📊 Fund Composition

Each fund consists of **10 stocks**:
- **6 Base Stocks**: Established companies with 5+ years of proven profitability
- **4 Potential Stocks**: High-growth candidates with 2+ years of profitability

**Fixed Weights**: 20%, 16%, 14%, 12%, 10%, 8%, 6%, 5%, 5%, 4%

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "קרן צמיחה 10"
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `yfinance` - Yahoo Finance data
- `pandas` - Data processing
- `pydantic` - Data validation
- `python-dotenv` - Configuration
- `rich` - Terminal UI
- `requests` - API calls

### 3. Set Up Environment Variables

Copy the example `.env` file and configure it:

```bash
# Create .env file with your API keys
```

**Required configuration in `.env`:**

```bash
# Data Sources
FINANCIAL_DATA_SOURCE=eodhd     # Financial statements source
PRICING_DATA_SOURCE=yfinance     # Price history source

# API Keys
EODHD_API_KEY=your-api-key-here  # Get from https://eodhd.com/

# Optional Settings
USE_CACHE=true
DEBUG_MODE=false
```

**Get your EODHD API Key:**
1. Visit https://eodhd.com/
2. Sign up for a free or paid plan
3. Copy your API key to `.env`

## ⚙️ Configuration

### Data Source Options

The system uses **separate data sources** for different data types:

**Financial Data (FINANCIAL_DATA_SOURCE):**
- `eodhd` - EOD Historical Data API (**recommended**)
- `fmp` - Financial Modeling Prep API
- `alphavantage` - Alpha Vantage API
- `investing` - Investing.com (via Selenium)

**Pricing Data (PRICING_DATA_SOURCE):**
- `yfinance` - Yahoo Finance (**recommended** - free, no API key needed)
- `eodhd` - EOD Historical Data API
- `alphavantage` - Alpha Vantage API

### Recommended Configuration

```bash
FINANCIAL_DATA_SOURCE=eodhd      # Best for fundamentals
PRICING_DATA_SOURCE=yfinance     # Free, reliable pricing
```

## 🎯 Running the App

### Basic Usage

**Build a fund for the TA-125 index (Israeli stocks):**

```bash
python build_fund.py --index TASE125
```

**Build a fund for the S&P500 index (US stocks):**

```bash
python build_fund.py --index SP500
```

### Advanced Options

**Specify quarter and year:**

```bash
python build_fund.py --index SP500 --quarter Q4 --year 2025
```

**Disable cache (force refresh all data):**

```bash
python build_fund.py --index TASE125 --no-cache
```

**Enable debug mode (verbose output):**

```bash
python build_fund.py --index SP500 --debug
```

**Combine multiple options:**

```bash
python build_fund.py --index SP500 --quarter Q1 --year 2025 --no-cache --debug
```

### Command Line Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--index` | Index name (`TASE125` or `SP500`) | Yes | - |
| `--quarter` | Quarter (`Q1`, `Q2`, `Q3`, `Q4`) | No | Auto-detected |
| `--year` | Year (e.g., `2025`) | No | Current year |
| `--no-cache` | Force refresh all data | No | Use cache |
| `--debug` | Enable verbose output | No | Disabled |

### Output

The app generates two markdown files in the `Fund_Docs/` directory:

1. **`Fund_10_[INDEX]_[Q]_[YEAR].md`** - Final fund composition
2. **`Fund_10_[INDEX]_[Q]_[YEAR]_Update.md`** - Detailed scoring tables

**Example output:**
```
Fund_Docs/
├── Fund_10_SP500_Q4_2025.md
└── Fund_10_SP500_Q4_2025_Update.md
```

## 📈 Backtesting

Backtest a fund's historical performance to validate the strategy.

### Running a Backtest

First, build a fund:

```bash
python build_fund.py --index SP500 --quarter Q4 --year 2025
```

Then backtest it:

```bash
python backtest.py Fund_Docs/Fund_10_SP500_Q4_2025.md --years 10
```

### Backtest Parameters

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `fund_file` | Path to fund markdown file | *Required* | `Fund_Docs/Fund_10_SP500_Q4_2025.md` |
| `--years` | Number of years to backtest | 10 | `5`, `10`, `15` |
| `--output-dir` | Directory for reports/charts | `Fund_Docs` | `Backtest_Results` |

### Backtest Examples

**Standard 10-year backtest:**

```bash
python backtest.py Fund_Docs/Fund_10_SP500_Q4_2025.md
```

**5-year backtest:**

```bash
python backtest.py Fund_Docs/Fund_10_SP500_Q4_2025.md --years 5
```

**Custom output directory:**

```bash
python backtest.py Fund_Docs/Fund_10_TASE125_Q1_2025.md --years 10 --output-dir Backtest_Results
```

### Backtest Output

The backtest generates:
1. **Performance metrics** - Total return, annualized return, Sharpe ratio, max drawdown
2. **Comparison charts** - Fund vs. benchmark performance
3. **Trade log** - All buy/sell transactions with dates and prices
4. **Detailed report** - Saved to `Fund_Docs/Backtest_[INDEX]_[DATE].md`

### Key Metrics Explained

- **Total Return**: Overall percentage gain/loss
- **Annualized Return**: Average yearly return (CAGR)
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable positions

## 🧪 Testing Data Sources

Before running a full fund build, verify your data sources are working:

### Test EODHD API

```bash
python test_eodhd.py
```

Tests:
- API connection and authentication
- Fundamentals data (Apple example)
- Income statements
- Israeli stocks (TASE)
- S&P 500 constituents list

### Test yfinance

```bash
python test_price_history.py
```

Tests:
- Price history retrieval
- US stocks (AAPL, MSFT, GOOGL)
- Israeli stocks (TEVA.TA, NICE.TA)

### Test Full Integration (QA)

```bash
python test_data_sources_qa.py
```

Runs comprehensive QA testing:
- EODHD financial data for 3 US stocks
- yfinance pricing data for 3 US stocks
- EODHD financial data for 2 Israeli stocks
- yfinance pricing data for 2 Israeli stocks
- Validates both data sources work together

**Expected output:**
```
✓ בדיקת QA עברה בהצלחה!
  האינטגרציה בין EODHD ל-yfinance עובדת כראוי
```

## 📁 Project Structure

```
קרן צמיחה 10/
├── build_fund.py              # Main application entry point
├── backtest.py                # Backtesting engine
├── config/
│   └── settings.py            # Configuration management
├── models/
│   ├── stock.py               # Stock data model
│   ├── fund.py                # Fund composition model
│   └── financial_data.py      # Financial metrics models
├── data_sources/
│   ├── base_data_source.py    # Abstract data source interface
│   ├── eodhd_api.py           # EODHD API implementation
│   ├── fmp_api.py             # FMP API implementation
│   └── investing_scraper.py   # Investing.com scraper
├── fund_builder/
│   └── fund_builder.py        # Fund construction logic
├── utils/
│   └── date_utils.py          # Date/quarter utilities
├── cache/                     # Cached data (auto-created)
│   ├── stocks_data/           # Individual stock data
│   └── index_constituents/    # Index member lists
├── Fund_Docs/                 # Generated fund documents
├── test_*.py                  # Test scripts
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (create from template)
└── README.md                  # This file
```

## 🔧 Troubleshooting

### Common Issues

**Problem: "EODHD_API_KEY must be set in .env"**

Solution:
```bash
# Add your API key to .env file
EODHD_API_KEY=your-actual-api-key-here
```

**Problem: "No module named 'yfinance'"**

Solution:
```bash
pip install yfinance
```

**Problem: Hebrew characters display incorrectly on Windows**

Solution: The app automatically handles Windows console encoding. If issues persist, run:
```bash
chcp 65001  # Set console to UTF-8
python build_fund.py --index SP500
```

**Problem: API rate limit exceeded**

Solution:
```bash
# Use cache to reduce API calls
python build_fund.py --index SP500  # Cache enabled by default

# Or wait and retry (EODHD limits: varies by plan)
```

**Problem: "No data found for symbol"**

Solution:
- Verify the stock symbol is correct
- Check if the stock is included in the index
- Try with `--no-cache` to force fresh data
- Check the stock is still trading

### Debug Mode

Enable detailed logging to diagnose issues:

```bash
python build_fund.py --index SP500 --debug
```

This shows:
- API request/response details
- Data parsing steps
- Scoring calculations
- Cache operations

### Cache Management

**Clear cache to force fresh data:**

```bash
# Windows
rmdir /s cache

# Linux/Mac
rm -rf cache
```

**Or use the `--no-cache` flag:**

```bash
python build_fund.py --index SP500 --no-cache
```

## 📚 Additional Resources

### Documentation

- **[CLAUDE.md](CLAUDE.md)** - Developer guide for Claude Code
- **[Fund_Update_Instructions.md](Fund_Update_Instructions.md)** - Detailed fund building process

### API Documentation

- **EODHD API**: https://eodhd.com/financial-apis/
- **yfinance**: https://github.com/ranaroussi/yfinance
- **FMP API**: https://financialmodelingprep.com/developer/docs/
- **Alpha Vantage**: https://www.alphavantage.co/documentation/

### Market Data Sources

- **S&P 500**: https://www.spglobal.com/spdji/en/indices/equity/sp-500/
- **TA-125**: https://info.tase.co.il/eng/MarketData/Indices/

## 📝 Example Workflow

### First Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env
# Add your EODHD_API_KEY

# 3. Test data sources
python test_data_sources_qa.py

# 4. Build your first fund
python build_fund.py --index SP500

# 5. Review output
# Open Fund_Docs/Fund_10_SP500_Q4_2025.md
```

### Regular Usage

```bash
# Monthly: Update fund for new quarter
python build_fund.py --index SP500 --quarter Q1 --year 2025

# Weekly: Refresh data without cache
python build_fund.py --index TASE125 --no-cache

# Quarterly: Run backtest on latest fund
python backtest.py Fund_Docs/Fund_10_SP500_Q4_2025.md --years 10
```

## 🤝 Contributing

This is a personal investment research tool. For questions or issues:

1. Check [CLAUDE.md](CLAUDE.md) for technical details
2. Review existing test scripts for examples
3. Enable `--debug` mode to diagnose issues

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice. Always:
- Perform your own due diligence
- Consult with a licensed financial advisor
- Understand the risks of investing
- Verify all data before making investment decisions

Past performance does not guarantee future results.

## 📄 License

Private research project. Not for distribution or commercial use.

---

**Made with ❤️ for systematic investing**

*Last updated: December 2025*
