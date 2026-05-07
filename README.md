# Growth Fund Builder (מערכת בניית קרן צמיחה 10)

An automated system for building and managing investment portfolios based on stock indices. The system analyzes stocks from the TA-125 (Israeli) or S&P500 (US) indices, scores them using multiple financial criteria, and constructs optimized portfolios.

## 📋 Table of Contents

- [Features](#features)
- [Fund Composition](#fund-composition)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Quarterly Updates](#quarterly-update-ltm-based-rebalancing)
- [Automated Scheduling](#-automated-scheduling)
- [Backtesting](#backtesting)
- [Testing Data Sources](#testing-data-sources)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- **Dual-Market Support**: Works with both Israeli (TA-125) and US (S&P500) stocks
- **Hybrid Data Sources**: Uses TwelveData API for financial data and yfinance for pricing
- **Automated Scoring**: Multi-factor scoring system for stock selection
- **Quarterly Updates**: LTM-based rebalancing using cached data (~10x cheaper than full rebuild)
- **Automated Scheduling**: Windows Task Scheduler integration for annual unattended runs (Feb 25, May 25, Aug 25, Nov 25)
- **Smart Caching**: Reduces API calls and improves performance
- **Beautiful CLI**: Rich terminal UI with progress bars and tables
- **Hebrew Support**: Full Hebrew language support for Israeli market

## 📊 Fund Composition

Each fund consists of **10 stocks**:
- **6 Base Stocks**: Established companies with 5+ years of proven profitability
- **4 Potential Stocks**: High-growth candidates with 3+ years of profitability

**Fixed Weights**: 18%, 16%, 16%, 10%, 10%, 10%, 6%, 6%, 4%, 4%

### Scoring Formula

**Base Stocks (Steady Growers):**
Each stock is scored using a **blended growth-stability model**:
- **CAGR**: 4-year compound annual growth rate over 5 fiscal years
- **R² Stability**: Measures consistency of log-linear growth (1.0 = perfect compounder, 0 = chaotic)
- **Blended per axis**: Net Income = 70% CAGR + 30% R²; Revenue = 70% CAGR + 30% R²
- **Final score**: 40% NI blended + 35% Revenue blended + 25% Market cap (rank-percentile)

**Potential Stocks (High Growth):**
Growth-focused ranking (no stability blend):
- **Future Growth**: 80% (3-year CAGR)
- **Momentum**: 20% (1-year price change)

*(PE/Valuation excluded — high-growth stocks naturally carry PE premiums; penalizing P/E would systematically disadvantage the stocks this model targets)*

All metrics use **rank-percentile normalization** (0–100 scale, distribution-agnostic).

For detailed formulas, see [CLAUDE.md](CLAUDE.md#scoring-formulas).

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
FINANCIAL_DATA_SOURCE=twelvedata  # Financial statements source
PRICING_DATA_SOURCE=yfinance      # Price history source

# API Keys
TWELVEDATA_API_KEY=your-api-key-here  # Get from https://twelvedata.com/

# Optional Settings
USE_CACHE=true
DEBUG_MODE=false
```

**Get your TwelveData API Key:**
1. Visit https://twelvedata.com/
2. Sign up for a Pro plan (610+ credits/min recommended)
3. Copy your API key to `.env`

## ⚙️ Configuration

### Data Source Options

The system uses **separate data sources** for different data types:

**Financial Data (FINANCIAL_DATA_SOURCE):**
- `twelvedata` - TwelveData API (**recommended**)
- `alphavantage` - Alpha Vantage API (US only)

**Pricing Data (PRICING_DATA_SOURCE):**
- `yfinance` - Yahoo Finance (**recommended** - free, no API key needed)
- `twelvedata` - TwelveData API
- `alphavantage` - Alpha Vantage API

### Recommended Configuration

```bash
FINANCIAL_DATA_SOURCE=twelvedata  # Best for fundamentals
PRICING_DATA_SOURCE=yfinance      # Free, reliable pricing
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

### Quarterly Update (LTM-based Rebalancing)

Instead of rebuilding from scratch (500+ stocks), update an existing fund using the top ~50 candidates:

```bash
# Update fund using latest quarterly (LTM) data
python build_fund.py --index SP500 --update

# Preview changes without saving
python build_fund.py --index SP500 --update --dry-run

# Update for a specific quarter
python build_fund.py --index SP500 --quarter Q2 --year 2026 --update
```

**How it works**: Parses the previous `_Update.md` to identify top candidates, loads cached financial data, fetches 4 quarters of financial reports from TwelveData, computes LTM (Last Twelve Months) values, and re-scores all candidates.

**Cost**: ~30K API credits vs ~300K for a full rebuild.

### ⏰ Automated Scheduling

Run fund builds automatically on a schedule aligned with earnings seasons using **Windows Task Scheduler**:

```powershell
# One-time setup (from Administrator PowerShell):
cd "d:\python\finance\קרן צמיחה 10"
.\scripts\schedule_tasks.ps1
```

This registers **4 annual tasks**:
- **Feb 25 @ 7:00 AM**: Full rebuild (all 500+ stocks) + LTM update (~2 hours, ~600K credits)
- **May 25 @ 7:00 AM**: LTM update only (~10 min, ~60K credits)
- **Aug 25 @ 7:00 AM**: LTM update only (~10 min, ~60K credits)
- **Nov 25 @ 7:00 AM**: LTM update only (~10 min, ~60K credits)

All runs log to `logs/scheduled_YYYY-MM-DD.log` for monitoring.

**For detailed setup, monitoring, and troubleshooting, see [SCHEDULING.md](SCHEDULING.md).**

### Command Line Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--index` | Index name (`TASE125` or `SP500`) | Yes | - |
| `--quarter` | Quarter (`Q1`, `Q2`, `Q3`, `Q4`) | No | Auto-detected |
| `--year` | Year (e.g., `2025`) | No | Current year |
| `--update` | Run quarterly LTM update instead of full build | No | Full build |
| `--dry-run` | Preview update changes without saving | No | Disabled |
| `--no-cache` | Force refresh all data | No | Use cache |
| `--debug` | Enable verbose output | No | Disabled |

### Output

Fund documents are organized by index and quarter:

```
Fund_Docs/
├── CHANGELOG.md
├── SP500/
│   ├── Q1_2026/
│   │   ├── Fund_10_SP500_Q1_2026.md           # Fund composition
│   │   ├── Fund_10_SP500_Q1_2026_Update.md    # Scoring tables
│   │   └── Fund_10_SP500_Q1_2026_Comparison.md  # Diff vs previous
│   └── Q4_2025/
│       └── ...
└── TASE125/
    └── ...
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
python backtest.py Fund_Docs/SP500/Q4_2025/Fund_10_SP500_Q4_2025.md --years 10
```

### Backtest Parameters

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `fund_file` | Path to fund markdown file | *Required* | `Fund_Docs/SP500/Q4_2025/Fund_10_SP500_Q4_2025.md` |
| `--years` | Number of years to backtest | 10 | `5`, `10`, `15` |
| `--output-dir` | Directory for reports/charts | Same directory as fund file | `Backtest_Results` |

### Backtest Examples

**Standard 10-year backtest:**

```bash
python backtest.py Fund_Docs/SP500/Q4_2025/Fund_10_SP500_Q4_2025.md
```

**5-year backtest:**

```bash
python backtest.py Fund_Docs/SP500/Q4_2025/Fund_10_SP500_Q4_2025.md --years 5
```

**Custom output directory:**

```bash
python backtest.py Fund_Docs/TASE125/Q1_2025/Fund_10_TASE125_Q1_2025.md --years 10 --output-dir Backtest_Results
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

### Test All Data Sources

```bash
python tests/test_all_sources.py
```

Tests:
- API connection and authentication
- Financial data retrieval (fundamentals)
- Pricing data retrieval (market prices)
- US stocks (AAPL, MSFT, GOOGL)
- Israeli stocks (TEVA.TA, NICE.TA)
- Router source selection

## 📁 Project Structure

```
קרן צמיחה 10/
├── build_fund.py              # Main entry point (full build + --update)
├── backtest.py                # Backtesting engine
├── config/
│   └── settings.py            # Configuration management
├── models/
│   ├── stock.py               # Stock data model
│   ├── fund.py                # Fund composition model
│   └── financial_data.py      # Financial metrics models
├── data_sources/
│   ├── base_data_source.py    # Abstract data source interface
│   ├── twelvedata_api.py      # TwelveData API (recommended)
│   ├── yfinance_source.py     # Yahoo Finance (free pricing)
│   └── alphavantage_api.py    # Alpha Vantage API (US only)
├── fund_builder/
│   ├── builder.py             # Full fund construction logic
│   └── updater.py             # Quarterly LTM-based update
├── utils/
│   ├── date_utils.py          # Date/quarter/folder utilities
│   ├── update_parser.py       # Parse _Update.md for candidates
│   ├── cache_loader.py        # Load Stock objects from cache
│   ├── ltm_calculator.py      # LTM calculation & merging
│   ├── changelog.py           # CHANGELOG.md management
│   ├── dedup.py               # Company deduplication (multi-class share filtering)
│   └── deploy.py              # Google Drive deployment: copies .md files after each build
├── tools/
│   └── demonstrate_calculations.py  # Step-by-step scoring formula demo
├── scripts/
│   ├── run_fund.ps1           # Execution wrapper (called by scheduled tasks)
│   └── schedule_tasks.ps1     # Task registration (run as Admin one-time to set up)
├── tests/                     # Test suite
│   ├── test_all_sources.py
│   ├── test_quarterly_update.py
│   └── ...
├── cache/                     # Cached data (auto-created)
├── Fund_Docs/                 # Generated fund documents (by index/quarter)
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (create from template)
└── README.md                  # This file
```

## 🔧 Troubleshooting

### Common Issues

**Problem: "TWELVEDATA_API_KEY must be set in .env"**

Solution:
```bash
# Add your API key to .env file
TWELVEDATA_API_KEY=your-actual-api-key-here
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

# Or wait and retry (TwelveData limits: varies by plan)
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

### API Documentation

- **TwelveData**: https://twelvedata.com/
- **yfinance**: https://github.com/ranaroussi/yfinance
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
# Add your TWELVEDATA_API_KEY

# 3. Test data sources
python tests/test_all_sources.py

# 4. Build your first fund
python build_fund.py --index SP500

# 5. Review output
# Open Fund_Docs/SP500/Q4_2025/Fund_10_SP500_Q4_2025.md
```

### Regular Usage

```bash
# Quarterly: Run lightweight LTM-based update
python build_fund.py --index SP500 --update

# Quarterly: Full rebuild from scratch (when needed)
python build_fund.py --index SP500 --quarter Q2 --year 2026

# Quarterly: Run backtest on latest fund
python backtest.py Fund_Docs/SP500/Q1_2026/Fund_10_SP500_Q1_2026.md --years 10
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

*Last updated: May 2026*
