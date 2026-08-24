# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Growth Fund Builder (מערכת בניית קרן צמיחה 10)** - an automated system for building and managing investment portfolios based on stock indices. The system analyzes stocks from either the TA-125 (Israeli) or S&P500 (US) indices, scores them using multiple financial criteria, and constructs optimized portfolios.

The fund consists of two sleeves with deliberately different mandates:
- **6 base stocks (80% of capital)** — the *"Quality Growth at Scale"* sleeve: established, large companies with 5+ years of proven profitability. Their score blends growth **CAGR with R² stability** and rewards size (market-cap rank), so this sleeve intentionally selects steady large-cap compounders rather than the fastest growers. It is a quality/scale-tilted growth sleeve, not a pure growth sleeve.
- **4 potential stocks (20% of capital)** — the pure-growth sleeve: candidates with 3+ years of profitability scored on growth and momentum only (no stability blend, no valuation penalty).

This split is by design: most of the fund is anchored in durable large-cap compounders, with a smaller high-growth satellite.

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

### Quarterly Update (LTM-based)
```bash
# Update fund using LTM data (requires previous full build)
python build_fund.py --index SP500 --update

# Preview changes without saving files
python build_fund.py --index SP500 --update --dry-run

# Update for specific quarter
python build_fund.py --index SP500 --quarter Q2 --year 2026 --update
```

### Deploying to Google Drive (without rebuilding)
```bash
# Push already-generated docs for a quarter to Google Drive (no API credits)
python build_fund.py --index SP500 --quarter Q3 --year 2026 --deploy-only

# Push the newest quarter of both indexes
./scripts/run_fund.sh deploy

# Push EVERYTHING — full mirror including historical quarters
./scripts/run_fund.sh deploy-all
```
Deployment also runs automatically at the end of every build and every `--update`.
See the `utils/deploy.py` entry under Utilities for the backend selection rules.

### Global Commands (run from any directory)

Four wrappers around `build_fund.py`, installed as symlinks in `~/.local/bin`:

```bash
./scripts/install_commands.sh            # install / update the symlinks (idempotent)
./scripts/install_commands.sh --remove   # uninstall

fund-build-tase        # full build, TASE125     (~45 min, ~300K credits)
fund-update-tase       # LTM quarterly update, TASE125
fund-build-sp500       # full build, SP500       (~45 min, ~300K credits)
fund-update-sp500      # LTM quarterly update, SP500
```

Any unrecognised argument is passed straight through to `build_fund.py`
(`--dry-run`, `--quarter Q3 --year 2026`, `--no-cache`, `--debug`). Two flags are consumed
by the wrapper itself: `-y` skips the confirmation the *full* builds ask for (they're the
expensive path; the prompt is skipped automatically when stdin isn't a TTY), and `--log`
tees output to `logs/manual_<tag>_<timestamp>.log` — without it, output goes straight to the
terminal so Rich keeps its live progress bars.

- [scripts/_fund_lib.sh](scripts/_fund_lib.sh) — shared logic: resolves `PROJECT_ROOT` via
  `readlink -f` (so it works through the `~/.local/bin` symlink from any cwd), sets UTF-8 for
  Hebrew output, prefers `venv/bin/python`.
- [scripts/install_commands.sh](scripts/install_commands.sh) — symlink installer; warns if
  `~/.local/bin` isn't on `PATH`.

These are for manual runs. `scripts/run_fund.sh` remains the cron entry point and covers
both indexes per invocation.

### Testing Data Sources
```bash
# Run comprehensive data source tests
python tests/test_all_sources.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Automated Scheduling

The fund builder runs on an automated annual schedule aligned with earnings seasons:
- **Feb 25**: Full rebuild of both indexes (SP500 + TASE125) + follow-up LTM update
- **May 25, Aug 25, Nov 25**: Quarterly LTM updates only

Every run deploys to Google Drive on completion.

### Linux (cron) — CURRENT production setup

The machine this repo runs on is Linux, so **cron is the live scheduler**. The Windows Task
Scheduler section below is legacy and does not run here.

```bash
./scripts/install_cron.sh            # install or update (idempotent, no sudo)
./scripts/install_cron.sh --remove   # uninstall
crontab -l                           # inspect
```

Installed entries:

| Schedule | Command | Purpose | Cost |
|---|---|---|---|
| Feb 25, 07:00 | `run_fund.sh full` | Full rebuild of both indexes + LTM update | ~2h, ~600K credits |
| May/Aug/Nov 25, 07:00 | `run_fund.sh update` | LTM update only | ~10 min, ~60K credits |
| Daily, 07:30 | `run_fund.sh deploy` | Catch-up sync to Google Drive | Free (no financial API calls) |

The **daily deploy job is what makes deployment self-healing**. `rclone` skips files that are
already in sync, so a normal day is a cheap no-op; but if a deploy ever failed (expired token,
network outage, a build that ran while Drive was unreachable), the next daily run completes it
with no manual step. It deploys the *latest existing quarter* per index, found via
`find_latest_fund_dir()`.

**Implementation:**
- [scripts/run_fund.sh](scripts/run_fund.sh) — execution wrapper; modes `full` | `update` | `deploy`. Sets `PYTHONIOENCODING=utf-8` and `LANG` explicitly because cron runs with a minimal environment that would otherwise break Hebrew output. Activates `venv/` if present. Logs to `logs/scheduled_YYYY-MM-DD.log`.
- [scripts/deploy_latest.py](scripts/deploy_latest.py) — deploys the newest quarter of each index; exit 1 if any index fails. With `--all`, deploys the **entire** `Fund_Docs` tree instead — every quarter plus `Gemini/` and `Reports/`. Folders with a space in the name (e.g. `Q2_2026 - Copy`) are skipped as manual copies. `--all` exists because routine deployment only ever touches the *current* quarter, so historical quarters produced before deployment was working — Q4 2025, in this repo — would otherwise never reach Drive.
- [scripts/install_cron.sh](scripts/install_cron.sh) — idempotent crontab management via `# >>> FundBuilder (managed) >>>` markers; leaves any other crontab entries untouched.

**Monitoring:**
```bash
cat logs/deploy_status.txt          # one line: is the Drive sync healthy?
tail -50 logs/scheduled_$(date +%F).log
grep -l "COMPLETED WITH ERRORS" logs/scheduled_*.log
```

`logs/deploy_status.txt` is rewritten on every deploy attempt with a timestamp and `OK` /
`FAILED`. It exists because a cron failure otherwise only lands in a dated log file nobody
opens — a silently broken sync is exactly the failure mode this whole subsystem was built
to eliminate.

**Authorising rclone (one-time, requires a human):**

Google OAuth requires interactive consent and **cannot be automated** — this is the single
manual step in the whole pipeline. One command does consent, verification, and the first
deploy:

```bash
./scripts/authorize_drive.sh
```

[scripts/authorize_drive.sh](scripts/authorize_drive.sh) reads the remote name from `.env`
(so it never drifts from the deploy config), skips the consent step if already authorised,
then verifies reachability, deploys, and prints the resulting Drive tree.

Headless / over SSH: answer `n` to the browser prompt. rclone prints an
`rclone authorize "drive" "<blob>"` command to run on any machine that *does* have a
browser; paste the result back. **No display is needed on the server.**

Re-authorisation is only needed if the token is revoked (Google password change, app access
revoked). `logs/deploy_status.txt` will read `FAILED` if that happens.

### Windows (Task Scheduler) — legacy

> Retained for reference only. These PowerShell scripts assume paths under `d:\python\finance\`
> and do not run on the current Linux host.

### Setup (One-time)

1. **Run from Administrator PowerShell prompt:**
```powershell
cd "d:\python\finance\קרן צמיחה 10"
.\scripts\schedule_tasks.ps1
```

2. **Verify the tasks registered:**
```powershell
Get-ScheduledTask -TaskPath "\FundBuilder\" | Format-Table TaskName, State, NextRunTime
```

### Scheduled Tasks Created

| Task Name | Date | Mode | Runtime | Credits |
|---|---|---|---|---|
| `FundBuild_Feb25` | Feb 25 @ 7:00 AM | full + update | ~2 hours | ~600K |
| `FundUpdate_May25` | May 25 @ 7:00 AM | update | ~10 min | ~60K |
| `FundUpdate_Aug25` | Aug 25 @ 7:00 AM | update | ~10 min | ~60K |
| `FundUpdate_Nov25` | Nov 25 @ 7:00 AM | update | ~10 min | ~60K |

**Why these dates?**
- **Feb 25**: Q4 earnings season ends → annual data is complete
- **May 25**: Q1 earnings season ends → run quarterly update (earliest time after earnings close)
- **Aug 25**: Q2 earnings season ends
- **Nov 25**: Q3 earnings season ends

### Implementation Files

**`scripts/run_fund.ps1`** — Main execution wrapper
- Called by each scheduled task
- Parameters: `-Mode "full"` or `-Mode "update"`
- Logs output to `logs/scheduled_YYYY-MM-DD.log`
- Handles Hebrew text encoding for Windows console
- Gracefully activates venv if present

**`scripts/schedule_tasks.ps1`** — Task registration utility
- Creates 4 tasks in `\FundBuilder\` Task Scheduler folder
- Idempotent (safe to re-run)
- Requires Administrator privileges

### Manual Testing

Before relying on automated runs, test the wrapper:

```powershell
cd "d:\python\finance\קרן צמיחה 10\scripts"

# Test update mode (cheap: ~5 min, ~30K credits)
.\run_fund.ps1 -Mode update

# Verify success
Get-Content ..\logs\scheduled_*.log -Tail 50
```

### Monitoring & Logs

After each scheduled date, check the run:

```powershell
# View latest log
Get-Item "d:\python\finance\קרן צמיחה 10\logs\scheduled_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Search for completion status
Select-String "COMPLETED SUCCESSFULLY\|COMPLETED WITH ERRORS" logs\scheduled*.log

# View specific task's last run
(Get-ScheduledTask -TaskName "FundBuild_Feb25" -TaskPath "\FundBuilder\") | Select-Object LastRunTime, LastTaskResult
```

### Troubleshooting

**Task didn't run on scheduled date:**
- Check: Is the computer on and logged in at 7:00 AM on that date?
- Task Scheduler with `LogonType = Interactive` only runs when user is logged in
- Setting `StartWhenAvailable = True` means it will run ASAP next time computer is available

**Task ran but failed:**
- Check the log file: `logs/scheduled_YYYY-MM-DD.log`
- Most common issues: API rate limit, network error, or missing `.env` file
- The task logs all Python output to the log file for debugging

**Need to modify a task:**
```powershell
# Remove and re-create:
Unregister-ScheduledTask -TaskName "FundBuild_Feb25" -TaskPath "\FundBuilder\" -Confirm:$false
.\scripts\schedule_tasks.ps1  # Re-register all 4 tasks
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
- [models/financial_data.py](models/financial_data.py) - `FinancialData`, `MarketData`, and `PricePoint` for financial metrics
  - `PricePoint`: fiscal-date price snapshots used for price-history alignment
  - Includes methods for profitability checks, cash flow analysis, and debt ratios

**Data Sources (Abstract + Implementations):**
- [data_sources/base_data_source.py](data_sources/base_data_source.py) - Abstract base class defining the data source interface
- [data_sources/twelvedata_api.py](data_sources/twelvedata_api.py) - TwelveData API (recommended primary source)
- [data_sources/yfinance_source.py](data_sources/yfinance_source.py) - Yahoo Finance wrapper (free, recommended for pricing)

**Quarterly Update Components:**
- [fund_builder/updater.py](fund_builder/updater.py) - `QuarterlyUpdater` orchestrator for LTM-based rebalancing
- [utils/update_parser.py](utils/update_parser.py) - Parses previous `_Update.md` to extract candidate stocks
- [utils/cache_loader.py](utils/cache_loader.py) - Loads cached `Stock` objects from `cache/stocks_data/*.json`
- [utils/ltm_calculator.py](utils/ltm_calculator.py) - Converts quarterly data to LTM values, merges into Stock
- [utils/changelog.py](utils/changelog.py) - Appends entries to `Fund_Docs/CHANGELOG.md`

**Utilities:**
- [utils/date_utils.py](utils/date_utils.py) - Quarter/year calculations, fund naming conventions
  - `get_quarter_and_year()` - Determines Q1-Q4 based on current month
  - `format_fund_name()` - Creates standardized fund names (e.g., "Fund_10_TASE_Q4_2025")
  - `get_fund_output_dir()` - Returns `Fund_Docs/{INDEX}/{Q}_{YEAR}/` path
  - `find_latest_fund_dir()` - Scans for most recent quarter folder
  - `find_previous_fund_dir()` - Finds the quarter folder before the current one
- [utils/deploy.py](utils/deploy.py) - Copies generated `.md` files to Google Drive after each build or update. Called by both `build_fund.py` and `fund_builder/updater.py`. Two backends, checked in order:
  - `GOOGLE_DRIVE_RCLONE_REMOTE` (e.g. `Home_Computer:Fund_10`) → `rclone copy`. **This is the backend used on Linux** — it works headless from cron/systemd with no mounted filesystem.
  - `GOOGLE_DRIVE_DEPLOY_PATH` → plain `shutil.copy2` into a locally-mounted Drive folder (Drive for Desktop on Windows, or an `rclone mount`).
  - Neither set → silent no-op.
  - Returns `bool`; a failed deploy is **non-fatal** (a full build costs ~2h / ~600K credits) but is reported as a red `✗ Google Drive deploy FAILED` panel, never as success. Re-run just the deploy with `--deploy-only`.
  - The local backend validates before writing: rejects relative paths, rejects a Windows `C:\...` path on non-Windows, and requires the parent directory to already exist. Without this, `Path("C:\\Users\\...")` on Linux is a *relative* path and `mkdir(parents=True)` silently creates a stray folder inside the repo while reporting success.

**Scheduling & Automation (Windows Task Scheduler):**
- [scripts/run_fund.ps1](scripts/run_fund.ps1) - PowerShell wrapper that executes fund builds/updates
  - Called by Windows Task Scheduler on 4 annual dates (Feb 25, May 25, Aug 25, Nov 25)
  - Logs all output with timestamps to `logs/scheduled_YYYY-MM-DD.log`
  - Handles Hebrew text encoding, venv activation, and error tracking
  - Parameters: `-Mode "full"` for full rebuild + update, `-Mode "update"` for LTM update only
- [scripts/schedule_tasks.ps1](scripts/schedule_tasks.ps1) - One-time setup script to register scheduled tasks
  - Must be run as Administrator
  - Creates 4 tasks in `\FundBuilder\` Task Scheduler folder
  - Idempotent — safe to re-run if tasks need to be updated

### Directory Structure
```
├── .claude/
│   └── skills/                         # Ad hoc Claude Code lookup tools (see below)
│       ├── stock-financials-chart/     # Ticker financial trend chart
│       └── stock-snapshot/             # Ticker fund eligibility + score + chart
├── build_fund.py           # Main entry point (full build + --update)
├── backtest.py             # Backtesting engine
├── config/
│   └── settings.py         # Configuration management
├── models/
│   ├── stock.py            # Stock model with eligibility logic
│   ├── fund.py             # Fund composition model
│   └── financial_data.py   # Financial metrics models
├── data_sources/
│   ├── base_data_source.py     # Abstract interface
│   ├── router.py               # Data source routing system
│   ├── adapter.py              # Validation & normalization
│   ├── twelvedata_api.py       # TwelveData (recommended)
│   ├── yfinance_source.py      # Yahoo Finance (free pricing)
│   ├── alphavantage_api.py     # Alpha Vantage (US only)
│   └── exceptions.py          # Custom exception classes
├── fund_builder/
│   ├── builder.py              # Full fund construction logic
│   └── updater.py              # Quarterly LTM-based update
├── utils/
│   ├── date_utils.py           # Date/quarter/folder utilities
│   ├── update_parser.py        # Parse _Update.md for candidates
│   ├── cache_loader.py         # Load Stock objects from cache
│   ├── ltm_calculator.py       # LTM calculation & merging
│   ├── changelog.py            # CHANGELOG.md management
│   ├── dedup.py                # Company deduplication: skip multi-class shares
│   ├── deploy.py               # Google Drive deployment: copies .md files after each build
│   └── migrate_fund_docs.py    # One-time folder migration
├── scripts/
│   ├── run_fund.sh             # Linux execution wrapper: full | update | deploy  (CURRENT)
│   ├── deploy_latest.py        # Deploys newest quarter per index to Google Drive (CURRENT)
│   ├── install_cron.sh         # Idempotent cron installer, no sudo               (CURRENT)
│   ├── run_fund.ps1            # Windows execution wrapper                        (legacy)
│   └── schedule_tasks.ps1      # Windows Task Scheduler registration              (legacy)
├── tests/
│   ├── test_all_sources.py
│   ├── test_quarterly_update.py
│   ├── test_current_data.py
│   ├── test_price_alignment.py
│   ├── test_symbol_normalization.py
│   ├── test_tase_api.py
│   ├── test_e2e_data_freshness.py  # E2E freshness test (AAPL/MSFT/NDAQ/AEP vs live APIs)
│   ├── test_models.py              # Unit tests: FinancialData, MarketData, Stock, Fund
│   ├── test_builder.py             # Unit tests: FundBuilder scoring and ranking
│   ├── test_backtest.py            # Unit tests: FundBacktest metrics and parsing
│   └── verify_index.py
├── tools/
│   └── demonstrate_calculations.py # Step-by-step scoring/formula demo (loads cache, outputs Markdown)
├── cache/
│   ├── stocks_data/        # Stock JSON files (598+ files)
│   └── index_constituents/ # Index member lists
└── Fund_Docs/              # Generated fund documentation
    ├── CHANGELOG.md        # Fund composition changes log
    ├── SP500/
    │   ├── Q1_2026/        # Fund_10_SP500_Q1_2026*.md
    │   └── Q4_2025/        # Fund_10_SP500_Q4_2025*.md
    └── TASE125/
        ├── Q1_2026/
        └── Q4_2025/
```

## Fund Building Process

The system follows a 14-step process:

1. **Fetch Index Constituents** - Get current stock list from index
2. **Filter Base Stocks** - Apply strict eligibility criteria (5 years profitability, operating profit, debt/equity < 60%)
3. **Score Base Candidates** - Calculate 4-year CAGR over 5 data points for net income and revenue; compute R² stability; blend per axis (70% CAGR + 30% R²); final score:
   - NI blended: 40%
   - Revenue blended: 35%
   - Market cap (rank-percentile): 25%
4. **Select Top 6 Base Stocks** - Highest scoring stocks become the core portfolio
5. **Prepare Potential List** - Remove base stocks from index constituents
6. **Filter Potential Stocks** - Relaxed criteria (3 years profitability)
7. **Score Potential Candidates** - Growth-focused model (no stability blend):
   - Future growth: 80% (historical 2-year net-income CAGR over 3 data points — a backward-looking growth proxy, not a forecast)
   - Momentum: 20% (see momentum definition below)
   - Valuation (PE) is intentionally excluded — high-growth stocks carry PE premiums, so penalizing PE would disadvantage exactly the stocks this sleeve targets
8. **Select Top 4 Potential Stocks**
9. **Assign Fixed Weights** - 18%, 16%, 16%, 10%, 10%, 10%, 6%, 6%, 4%, 4%
10. **Calculate Minimum Fund Cost** - Ensure whole share numbers per fund unit
11. **Generate Fund Table**
12. **Create Update Document** - With all scoring tables
13. **Create Final Fund Documents** - Separate files for TASE and SP500
14. **Validation** - Verify weights sum to 100%, no overlaps, whole shares

## Quarterly Update Process (LTM-based)

The `--update` flag runs a lighter rebalancing instead of a full 500+ stock rebuild:

1. **Find Previous Update.md** — Locates latest `_Update.md` from `Fund_Docs/{INDEX}/`
2. **Parse Candidates** — Extracts top 30 base + top 20 potential stocks (~50 unique symbols)
3. **Load Cached Stocks** — Reads full `Stock` objects from `cache/stocks_data/*.json`
4. **Fetch Quarterly Data** — Calls TwelveData with `period=quarterly` for 4 quarters
5. **Calculate LTM** — Sums last 4 quarters: revenue, net income, operating income, cash flow
6. **Merge LTM into Stocks** — Writes the LTM values **over the most recent annual slot** (it does *not* append a new year), refreshes pricing via yfinance. Overwriting keeps the CAGR/R² window at a fixed 5 points so scores don't swing on a pure date-window shift. Debt/equity are only overwritten when the quarterly balance sheet actually returns them; otherwise the cached annual values are preserved. Note: this means the re-saved cache files for fund holdings hold LTM-adjusted figures in the latest annual slot, not the raw annual report.
7. **Re-check Eligibility** — Applies same base/potential criteria
8. **Re-score and Rank** — Uses identical scoring weights as full build
9. **Build Fund** — Select 6 base + 4 potential, assign weights, calculate minimum cost
10. **Compare & Report** — Generate Comparison.md, append to CHANGELOG.md

**Cost**: ~50 stocks x ~600 credits = ~30K credits (vs ~300K for full rebuild)

### Update vs Full Build

| | Full Build (`--index SP500`) | Quarterly Update (`--update`) |
|---|---|---|
| Stocks processed | 500+ (full index) | ~50 (top candidates) |
| Data source | Annual financials from API | Quarterly LTM from API + cache |
| API cost | ~300K credits | ~30K credits |
| Runtime | ~45 min | ~5 min |
| Prerequisite | None | Previous full build with cache |

### Output Files (per quarter)

```
Fund_Docs/{INDEX}/{Q}_{YEAR}/
  Fund_10_{INDEX}_{Q}_{YEAR}.md                # Final fund composition
  Fund_10_{INDEX}_{Q}_{YEAR}_Update.md         # Detailed scoring tables
  Fund_10_{INDEX}_{Q}_{YEAR}_Comparison.md     # Diff vs previous quarter
  Fund_10_{INDEX}_{Q}_{YEAR}_Calculations.md   # Step-by-step formula breakdown (generated by tools/demonstrate_calculations.py)
```

### Scoring System Constants

Defined in [config/settings.py](config/settings.py:99-124):
```python
FUND_WEIGHTS = [0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]
BASE_GROWTH_YEARS = 5                        # CAGR over 4 periods (5 data points)
BASE_SCORE_WEIGHTS = {
    "net_income_growth": 0.40,
    "revenue_growth": 0.35,
    "market_cap": 0.25
}
STABILITY_BLEND = 0.30                      # Weight of R² in blended sub-score
POTENTIAL_SCORE_WEIGHTS = {
    "future_growth": 0.80,                  # growth-first: 80%
    "momentum": 0.20,
    # valuation (PE) removed: high-growth stocks naturally carry high PE premiums,
    # penalizing PE systematically disadvantages the stocks this model targets.
}
```

### Scoring Formulas

**CAGR (4-period compound annual growth rate, 5 data points):**
```
CAGR = (end_value / start_value) ^ (1 / (years - 1)) − 1
```
With `years = 5`, this always produces a **4-year CAGR** using 5 data points (period = 4).
The formula is explicit and independent of calendar year gaps, ensuring consistent annualization even after LTM merging adds non-consecutive years.
Returns `None` when `start_value ≤ 0` or fewer than 5 data points.

**Growth Stability (R² of log-linear regression):**
```
Fit: log(value) ~ year_index  over the 5 most-recent data points
R² = 1.0  →  perfect steady compounder
R² ≈ 0    →  chaotic / boom-bust path
```
Measures how consistently a company compounds: a steady 10% annual grower scores high (R²≈0.99), while a company with volatile earnings scores lower.
Returns `None` when fewer than 2 positive values (coerced to 0.0 in scoring).

**Rank-percentile normalization (replaces min-max):**
```
1. Sort candidates by metric value.
2. Assign rank 0 (lowest) … n−1 (highest); tied values share the average rank.
3. percentile = rank / (n − 1) × 100
```
Boundary behavior: lowest → 0.0, highest → 100.0, all-equal → 50.0.

**Base stock final score (blended growth-stability per axis):**
```
NI_blended  = 0.70 × NI_CAGR_percentile  + 0.30 × NI_R²_percentile
Rev_blended = 0.70 × Rev_CAGR_percentile + 0.30 × Rev_R²_percentile
base_score  = 0.40 × NI_blended + 0.35 × Rev_blended + 0.25 × MarketCap_percentile
```
The 30% R² weight ensures **long-term consistent compounders are preferred**: two stocks with identical CAGR but different volatility patterns will score differently (steady grower scores higher). This penalizes boom-bust patterns and rewards steady geometric growth.

**Potential stock final score (growth-maximizing, no stability blend, no valuation):**
```
potential_score = 0.80 × FutureGrowth_percentile
               + 0.20 × Momentum_percentile
```
- `FutureGrowth` is the **historical** 2-year net-income CAGR (3 data points). Despite the name it is backward-looking, not a forecast, and — because CAGR is endpoint-only — a one-time item in the first or last year moves it fully.
- PE/valuation is excluded from potential scoring: high-growth stocks naturally command PE premiums, so penalizing PE would systematically disadvantage the stocks this model is designed to select.

**Momentum (implemented in [models/financial_data.py](models/financial_data.py) `calculate_momentum`):**
```
momentum = (current_price / ref_price − 1) × 100
ref_price = the price snapshot whose date is closest to (latest_snapshot_date − days_ago)
```
`days_ago` defaults to 365, giving a **consistent ~12-month window across all stocks**. The window is anchored to the most recent snapshot date (deterministic, independent of the run clock), not to "since the oldest price on file" — the latter varied per stock with the length of available history and overlapped the growth factor. Returns `None` with fewer than 2 dated price points (coerced to 0.0 in scoring).

## Algorithm Consistency

The fund building algorithm treats **SP500 and TASE125 stocks identically**:

- **Same eligibility criteria**: 5 years profitability for base (plus 5 years of revenue history, positive cash flow, non-negative equity, debt/equity < 60%), 3 years profitability for potential
- **Same scoring weights**: 40% net income, 35% revenue, 25% market cap
- **Same fund weights**: [0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]
- **Same validation rules**: Strict validation for all stocks (require valid prices, 5+ price history points)

**Intentional differences** (necessary for API compatibility):
- Symbol suffixes: `.US` for SP500, `.TA` for TASE125
- Data source chains: Different APIs for different markets

## Data Sources

The system uses a **2x2 configuration matrix** for maximum flexibility:
- **Market dimension**: US stocks (SP500) vs Israeli stocks (TASE125)
- **Data type dimension**: Financial data (fundamentals) vs Pricing data (market prices)

This allows you to optimize for cost and quality by mixing different APIs. For example:
- Use **TwelveData** for fundamentals + **yfinance** for all pricing (saves money)
- Use **Alpha Vantage** for US fundamentals + **yfinance** for pricing

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
| **TwelveData** | ✓ | ✓ | Pro plans from $29/mo | 610-1597/min | Primary (all data, production) |
| **Alpha Vantage** | ✗ | ✓ | Free tier | 25/day | Light usage |
| **yfinance** | ✓ | ✓ | FREE | Unlimited | Pricing data (recommended) |

#### 1. TwelveData (Recommended Primary)
- **Type**: Financial + Pricing
- **Markets**: US, TASE, Global (60+ exchanges)
- **Key**: `TWELVEDATA_API_KEY`
- **Cost**: Pro 1597 plan - $XX/mo (1597 API credits/min, 1500 WebSocket credits, no daily limits)
- **Best for**: Primary all-in-one data source for production use
- **Performance**: Completes TASE125 fund build in ~2-3 minutes
- **Rate Limits**:
  - Pro 1597: 1597 credits/minute (recommended)
  - No daily limits
  - System includes automatic plan detection and credit tracking
- **Credits per stock**:
  - Financial data only: ~30 credits
  - Pricing data only: ~70 credits
  - Combined: ~100 credits
- **Recommendation**: Use TwelveData for financial data, yfinance for pricing to save ~70% credits
- **Signup**: https://twelvedata.com/

#### 2. Alpha Vantage
- **Type**: Financial + Pricing
- **Markets**: US stocks only
- **Key**: `ALPHAVANTAGE_API_KEY`
- **Free tier**: 25 requests/day (very limited)
- **Best for**: Light usage, testing

#### 3. yfinance (Yahoo Finance)
- **Type**: Pricing only (limited fundamentals)
- **Markets**: US, TASE, Global
- **Key**: None (free, no API key needed)
- **Best for**: All pricing data (highly recommended)
- **Note**: Unlimited requests, very reliable

### Recommended Configurations

#### Primary (Recommended - TwelveData + yfinance)
```bash
# Most cost-effective production setup
US_FINANCIAL_DATA_SOURCE=twelvedata
US_PRICING_DATA_SOURCE=yfinance          # Free! Saves ~70% credits
TASE_FINANCIAL_DATA_SOURCE=twelvedata
TASE_PRICING_DATA_SOURCE=yfinance        # Free! Saves ~70% credits
```

**Cost**: $XX/mo (TwelveData Pro 1597) + $0 (yfinance)
**Performance**: TASE125 build in ~2-3 minutes
**Credits used**: ~30 per stock (financial only)

#### All-in-One (TwelveData for Everything)
```bash
# Simplest configuration, higher credit usage
US_FINANCIAL_DATA_SOURCE=twelvedata
US_PRICING_DATA_SOURCE=twelvedata
TASE_FINANCIAL_DATA_SOURCE=twelvedata
TASE_PRICING_DATA_SOURCE=twelvedata
```

**Cost**: $XX/mo (TwelveData Pro 1597)
**Performance**: TASE125 build in ~4-5 minutes
**Credits used**: ~100 per stock (financial + pricing)

#### Alternative - Alpha Vantage + yfinance (US Only, Low Cost)
```bash
US_FINANCIAL_DATA_SOURCE=alphavantage
US_PRICING_DATA_SOURCE=yfinance          # Free!
TASE_FINANCIAL_DATA_SOURCE=twelvedata
TASE_PRICING_DATA_SOURCE=yfinance        # Free!
```

### Auto-Selection Fallback Chains

If you leave a source blank, the router auto-selects from these chains:

- **US Financial**: twelvedata → alphavantage
- **US Pricing**: yfinance → twelvedata → alphavantage
- **TASE Financial**: twelvedata
- **TASE Pricing**: yfinance → twelvedata

**Default**: TwelveData is the system default if no configuration is provided.

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

Example - switch from Alpha Vantage to TwelveData:
```bash
# In .env
US_FINANCIAL_DATA_SOURCE=twelvedata  # Changed from alphavantage
```

#### Problem: `ValueError: No financial data source available for SP500`

**Solution**: No API keys are configured or available.

1. Check which keys you have in `.env`
2. Configure at least one source for that market
3. Test the source: `python tests/test_all_sources.py`

Example fix:
```bash
# Add to .env
TWELVEDATA_API_KEY=your-key-here
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
- 5+ years of revenue history (required so the revenue-growth CAGR in scoring is real, not a placeholder 0.0)
- 4 out of 5 years with positive operating income
- Positive cash flow in majority of years
- Non-negative equity (negative/zero equity is rejected explicitly, because `debt_to_equity_ratio` returns `None` in that case and would otherwise pass the debt gate silently)
- Debt-to-equity ratio < 60%

Potential stocks have relaxed criteria:
- 3+ years of positive net income (most recent, consecutive)
- Complete growth data for 3 years (required for 2-year CAGR calculation)

**Eligibility is re-evaluated, not just granted.** `check_base_eligibility()` / `check_potential_eligibility()` reset their `is_eligible_*` flag to `False` at the top of each call before re-testing. This matters for the quarterly update, which re-checks `Stock` objects loaded from cache that were already flagged eligible: a holding whose refreshed LTM data now fails a criterion (e.g. a net loss, or debt/equity breaching 60%) correctly loses eligibility instead of being grandfathered in until the next full rebuild.

### Cache System

[config/settings.py](config/settings.py:91) creates cache directories:
- `cache/index_constituents/` - Index member lists (cached and reused between builds)
- `cache/stocks_data/` - Individual stock data (saved for debugging only, NOT loaded during full builds)

[build_fund.py](build_fund.py:185) creates:
- `logs/` - Data acquisition failure logs and scheduled automation logs

**Log files:**
- `logs/data_quality_*.json` - Data failures during API fetches (one per build)
- `logs/data_failures_*.json` - Summary of failed stocks per index/quarter
- `logs/scheduled_YYYY-MM-DD.log` - Output from automated scheduled runs (created by `run_fund.ps1`)

**Important**: During a full build (`python build_fund.py --index ...`), stock data is ALWAYS fetched fresh from APIs. Cache files are saved for debugging and manual analysis but are never loaded. The quarterly update (`--update` flag) is the exception: it intentionally loads cached `Stock` objects from `cache/stocks_data/` to avoid re-fetching the full index.

## Claude Code Skills

Two ad hoc, cache-only lookup tools live under `.claude/skills/` for inspecting a single
ticker without running (or waiting on) a build. Both read directly from
`cache/stocks_data/{TICKER}_US.json` / `_TA.json` — no API calls, no network cost — and
publish a self-contained HTML Artifact. They're invoked conversationally in Claude Code
("show me PLTR's chart", "is MTRX eligible for the fund") or run directly from the shell.

### `stock-financials-chart`

[`.claude/skills/stock-financials-chart/scripts/generate_chart.py`](.claude/skills/stock-financials-chart/scripts/generate_chart.py)
renders a grouped bar chart (zero baseline, hover tooltips, dark/light theme, "Show data
table" toggle) of one stock's Revenue, Net Income, Operating Income, and Operating Cash Flow
across every fiscal year in its cache file. Currency (`$`/USD vs `₪`/NIS) and unit scaling
(millions vs. billions) are picked automatically.

```bash
python3 .claude/skills/stock-financials-chart/scripts/generate_chart.py PLTR --output PLTR_chart.html
```

### `stock-snapshot`

[`.claude/skills/stock-snapshot/scripts/generate_snapshot.py`](.claude/skills/stock-snapshot/scripts/generate_snapshot.py)
composes a Fund Status card on top of the same chart (imported directly from
`stock-financials-chart`, not duplicated) showing:
- **Eligibility, recomputed live** — calls `Stock.check_base_eligibility()` /
  `check_potential_eligibility()` fresh against the cached fundamentals rather than trusting
  the cache's stored `is_eligible_for_*` flag, since that flag can be stale relative to the
  current eligibility rules (see "Eligibility is re-evaluated, not just granted" above). A
  per-criterion breakdown table shows why each axis passes or fails; a mismatch against the
  stored flag is surfaced as a note, not silently overwritten.
- **Score breakdown, as stored** — `base_score`/`potential_score` and their
  `*_scores_detail` sub-values (CAGR, stability R², percentile ranks, weighted contributions)
  from the last full build or quarterly update, using the live weight constants from
  `config/settings.py`. This is deliberately **not** recomputed live — the percentile ranks
  are only meaningful relative to the full candidate pool scored together in that run, which
  a single ticker's cache file can't reproduce on its own.

```bash
python3 .claude/skills/stock-snapshot/scripts/generate_snapshot.py PLTR --output PLTR_snapshot.html
```

Both scripts exit 1 with a clear message (never a stack trace) if the ticker has no cache
file, or if the file has no usable financial data — meaning the ticker was never fetched into
`cache/stocks_data/` by a prior full build, not a bug in the skill.

## Configuration

Create a `.env` file in the project root (see [.env.template](.env.template) for full template):

```bash
# ====================================================================
# Advanced Data Source Configuration (2x2 Matrix)
# ====================================================================

# US stocks (S&P 500) - Financial data
# Options: twelvedata, alphavantage
# Leave blank for auto-selection (defaults to twelvedata)
US_FINANCIAL_DATA_SOURCE=twelvedata

# US stocks (S&P 500) - Pricing data
# Options: yfinance, twelvedata, alphavantage
# Recommended: yfinance (free!)
US_PRICING_DATA_SOURCE=yfinance

# Israeli stocks (TA-125) - Financial data
# Options: twelvedata
# Leave blank for auto-selection (defaults to twelvedata)
TASE_FINANCIAL_DATA_SOURCE=twelvedata

# Israeli stocks (TA-125) - Pricing data
# Options: yfinance, twelvedata
# Recommended: yfinance (free!)
TASE_PRICING_DATA_SOURCE=yfinance

# ====================================================================
# API Keys
# ====================================================================

TWELVEDATA_API_KEY=your-key-here
ALPHAVANTAGE_API_KEY=your-key-here

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

# ====================================================================
# Google Drive Deployment (optional)
# ====================================================================
# Backend 1 (recommended, required on Linux): rclone remote + path.
# One-time authorisation: rclone config reconnect Home_Computer:
GOOGLE_DRIVE_RCLONE_REMOTE=Home_Computer:Fund_10

# Backend 2: local path where a Drive client exposes the folder.
# Must be ABSOLUTE and already exist. Windows-only in practice.
GOOGLE_DRIVE_DEPLOY_PATH=  # e.g. C:\Users\ranbe\My Drive\Fund_10

# If both are set, GOOGLE_DRIVE_RCLONE_REMOTE wins.
# If neither is set, deployment is silently skipped.
```

**Deploying without rebuilding:**

```bash
# Push existing docs for a quarter to Drive — no API credits, exit 1 on failure
python build_fund.py --index SP500 --quarter Q3 --year 2026 --deploy-only
```

Use this to backfill a quarter whose deploy failed, or to re-sync after fixing credentials. It skips `validate_settings()` since no data source is touched.

### Legacy Configuration (Backwards Compatible)

For simpler configuration, you can still use the old variables:

```bash
# These work but are less flexible than the 2x2 matrix above
FINANCIAL_DATA_SOURCE=twelvedata  # Used for both US and TASE (current default)
PRICING_DATA_SOURCE=yfinance       # Used for both US and TASE (recommended for cost savings)

# Even older - used for everything:
DATA_SOURCE=twelvedata  # Current system default
```

The system automatically falls back to these legacy settings if the 2x2 matrix is not configured. **Default value is `twelvedata`** if no configuration is provided.

## Key Design Patterns

- **Abstract Data Source**: Plugin architecture for multiple data providers
- **Pydantic Models**: Type-safe data validation throughout
- **Rich CLI**: Beautiful terminal UI with progress bars and panels
- **Singleton Settings**: Single `settings` instance exported from config module
- **Context Managers**: Resource cleanup patterns
