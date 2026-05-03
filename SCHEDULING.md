# Automated Fund Scheduling Guide

This guide explains how to set up automatic, unattended fund builds for all 4 quarterly earnings seasons.

## Overview

The Growth Fund Builder can run automatically on a precise annual schedule using **Windows Task Scheduler**. Once configured, the system will:

- **Feb 25 @ 7:00 AM**: Full rebuild of all 500+ stocks for both indexes, followed by LTM update
- **May 25 @ 7:00 AM**: Quick LTM update for both indexes
- **Aug 25 @ 7:00 AM**: Quick LTM update for both indexes  
- **Nov 25 @ 7:00 AM**: Quick LTM update for both indexes

All runs are logged with timestamps for monitoring and debugging.

## Why These Dates?

Earnings seasons end when ~95% of companies have reported:

| Season | Quarter | Reports | Ends | Best Update |
|--------|---------|---------|------|-------------|
| Q4/Annual | Oct-Dec | Jan-Feb | ~Feb 15-20 | **Feb 25** |
| Q1 | Jan-Mar | Apr-May | ~May 15-20 | **May 25** |
| Q2 | Apr-Jun | Jul-Aug | ~Aug 15-20 | **Aug 25** |
| Q3 | Jul-Sep | Oct-Nov | ~Nov 15-20 | **Nov 25** |

The Feb 25 full rebuild captures the complete annual reports. The three May/Aug/Nov updates use LTM (Last Twelve Months) calculations from cached stock data, which is much faster and cheaper.

## Setup Instructions

### Prerequisites

- Windows 10/11
- Administrator PowerShell access
- Valid `.env` file with API keys (same as manual builds)
- Latest Python dependencies: `pip install -r requirements.txt`

### Step 1: Register the Scheduled Tasks (One-time)

Open **PowerShell as Administrator**:

```powershell
# Right-click PowerShell and select "Run as administrator"
cd "d:\python\finance\קרן צמיחה 10"
.\scripts\schedule_tasks.ps1
```

You should see output like:

```
Created Task Scheduler folder: \FundBuilder\

Registering: FundBuild_Feb25 (Month=2, Mode=full)...
  Registered: \FundBuilder\FundBuild_Feb25
Registering: FundUpdate_May25 (Month=5, Mode=update)...
  Registered: \FundBuilder\FundUpdate_May25
Registering: FundUpdate_Aug25 (Month=8, Mode=update)...
  Registered: \FundBuilder\FundUpdate_Aug25
Registering: FundUpdate_Nov25 (Month=11, Mode=update)...
  Registered: \FundBuilder\FundUpdate_Nov25

All 4 tasks registered successfully.
Verify with: Get-ScheduledTask -TaskPath '\FundBuilder\' | Format-Table TaskName, State
```

### Step 2: Verify Installation

From any PowerShell prompt (Admin not required):

```powershell
# List all 4 tasks
Get-ScheduledTask -TaskPath "\FundBuilder\" | Format-Table TaskName, State, NextRunTime

# View details of a specific task
Get-ScheduledTask -TaskName "FundBuild_Feb25" -TaskPath "\FundBuilder\" | Format-List *

# Or use the GUI
taskschd.msc
# Navigate to: Task Scheduler Library > FundBuilder
```

### Step 3: Manual Testing (Recommended)

Before relying on automation, test the wrapper with a cheap quarterly update:

```powershell
cd "d:\python\finance\קרן צמיחה 10\scripts"

# Test with update mode (~5 minutes, ~30K API credits)
.\run_fund.ps1 -Mode update

# Monitor the log
tail -f ..\logs\scheduled_2026-05-04.log
```

Wait for completion. You should see:

```
[2026-05-04 01:20:27] OK: SP500 LTM update
[2026-05-04 01:20:27] OK: TASE125 LTM update
[2026-05-04 01:20:27] COMPLETED SUCCESSFULLY
```

## How It Works

### Scheduled Tasks

| Property | Value |
|----------|-------|
| **Trigger Type** | Monthly, day 25 |
| **Run Time** | 07:00 AM local time |
| **Run As** | Current user (`ranbe`) |
| **Privileges** | Limited (no admin needed) |
| **If Missed** | Run on next available logon (StartWhenAvailable) |
| **Max Runtime** | 3 hours |
| **Logs** | `logs/scheduled_YYYY-MM-DD.log` |

### Execution Flow

When a task triggers at 7:00 AM on the scheduled date:

1. Windows Task Scheduler launches `powershell.exe`
2. PowerShell runs `scripts/run_fund.ps1 -Mode <mode>`
3. Script sets up environment (UTF-8 encoding, venv, working directory)
4. For each index (SP500, TASE125):
   - Runs `python build_fund.py --index <INDEX> [--update]`
   - Pipes output to both console and log file
   - Tracks exit code from Python
5. Script logs completion status and exits
6. Task Scheduler records success/failure

### Log File Format

Each run creates/appends to a single daily log file: `logs/scheduled_YYYY-MM-DD.log`

Example structure:

```
======================================================================
[2026-05-04 01:04:51] Growth Fund Builder - Scheduled Run
[2026-05-04 01:04:51] Mode: update | User: ranbe | Host: BENH-LAPTOP
======================================================================
[2026-05-04 01:04:51] START: SP500 LTM update
[2026-05-04 01:04:51] CMD: python build_fund.py --index SP500 --update
[01:04:55] ┌──────────────────────────────────────┐
[01:04:55] │ עדכון רבעוני — Fund_10_SP500_Q2_2026 │
[01:04:55] └──────────────────────────────────────┘
...
[01:20:27] OK: SP500 LTM update
[01:20:27] START: TASE125 LTM update
...
[2026-05-04 01:20:27] COMPLETED SUCCESSFULLY
======================================================================
```

## Monitoring

### Check Last Run Status

```powershell
# View recent log
Get-Item "d:\python\finance\קרן צמיחה 10\logs\scheduled_*.log" | Sort-Object LastWriteTime | Select-Object -Last 1 | Tee-Object -Variable lastLog
Get-Content $lastLog.FullName -Tail 50

# Check task's last result (0 = success, non-zero = failure)
(Get-ScheduledTask -TaskName "FundUpdate_May25" -TaskPath "\FundBuilder\").LastTaskResult

# View when it last ran
(Get-ScheduledTask -TaskName "FundUpdate_May25" -TaskPath "\FundBuilder\").LastRunTime
```

### Search for Completion Status

```powershell
# Find all successful runs
Select-String "COMPLETED SUCCESSFULLY" logs\scheduled*.log

# Find all failed runs
Select-String "COMPLETED WITH ERRORS" logs\scheduled*.log

# Count runs by month
(Get-ChildItem logs\scheduled_*.log).Name | Group-Object {$_.Split('_')[1].Substring(5, 2)}
```

## Troubleshooting

### Task Didn't Run on Scheduled Date

**Symptom:** Feb 25 comes and goes, no log file created

**Causes:**
- Computer was powered off or in sleep mode
- User was not logged in
- Scheduled Tasks service is disabled

**Solutions:**
- Ensure computer is on and logged in at 7:00 AM on the 25th
- If you need runs to happen while logged out, upgrade to `LogonType = S4U` (requires storing password in Task Scheduler)
- Enable Windows Task Scheduler service: `Services.msc` → Task Scheduler → Right-click → Start
- Check Windows Event Viewer for Task Scheduler errors: Event Viewer → Windows Logs → System → Filter "Task Scheduler"

### Task Ran But Failed

**Symptom:** Log file exists, but ends with `COMPLETED WITH ERRORS`

**Solutions:**
1. **Check the log file** for the actual error message:
   ```powershell
   Get-Content "d:\python\finance\קרן צמיחה 10\logs\scheduled_*.log" | Select-String "FAILED\|Error\|error" -Context 3
   ```

2. **Common errors:**
   - `[Errno 2] No such file or directory: build_fund.py` → Working directory is wrong
   - `DataSourceAuthenticationError` → API key in `.env` is invalid or expired
   - `DataSourceRateLimitError` → API rate limit hit (retry next hour)
   - Network timeout → Temporary internet issue (will retry on next date)

3. **Re-run manually** to verify it works:
   ```powershell
   cd "d:\python\finance\קרן צמיחה 10\scripts"
   .\run_fund.ps1 -Mode update
   ```

### API Credits Used Up Before End of Month

**Symptom:** Task runs successfully on Feb 25, but subsequent manual builds fail with rate limit errors

**Solutions:**
- Check TwelveData dashboard for credit usage
- Prioritize: Feb 25 full build (highest priority) > quarterly updates (lower priority)
- If budget is tight, consider skipping the follow-up update on Feb 25 (edit `schedule_tasks.ps1` to only run full build)

### Want to Modify Run Time or Dates

**Edit the task parameters:**

1. Edit `scripts/schedule_tasks.ps1`:
   - Line 25: `$RunAt = "07:00"` → Change to your preferred time
   - Line 29-32: Modify `@{ Name = ..., Month = N }` entries

2. Re-run as Administrator:
   ```powershell
   .\scripts\schedule_tasks.ps1
   ```

3. Old tasks will be replaced with new schedule

## Implementation Details

### Files Involved

**`scripts/run_fund.ps1`** (118 lines)
- Main execution wrapper
- Handles logging, environment setup, error tracking
- Called by all 4 scheduled tasks
- Parameters: `-Mode "full"` or `-Mode "update"`

**`scripts/schedule_tasks.ps1`** (75 lines)
- One-time task registration
- Creates 4 annual tasks in `\FundBuilder\` folder
- Idempotent — safe to re-run

**`logs/scheduled_YYYY-MM-DD.log`** (created per day)
- Timestamped output from all runs on that date
- Both stdout and stderr captured
- UTF-8 encoded for Hebrew character support

### Key Design Decisions

1. **Working directory detection:** Script detects project root from current location, works whether run manually or from Task Scheduler

2. **Error handling:** If SP500 build fails, TASE125 still runs (partial success is better than complete failure)

3. **Log rotation:** One file per date, appended if script runs multiple times same day

4. **No silent failures:** Task Scheduler sees non-zero exit code if ANY component fails

5. **Hebrew encoding:** UTF-8 environment variables set before Python runs, handles Rich UI text properly

## Support & Questions

For issues or questions:
1. Check the relevant log file in `logs/`
2. Review this guide's Troubleshooting section
3. Refer to CLAUDE.md for general architecture and commands
4. Test manually: `.\scripts\run_fund.ps1 -Mode update`

## Maintenance

### Monthly
- Check log files for any errors
- Verify next scheduled date will happen

### Quarterly (after each run)
- Review generated fund documents in `Fund_Docs/`
- Check CHANGELOG.md for composition changes

### Annually
- Review API usage and costs
- Adjust schedule or budget if needed
- Update `.env` if API keys change
- Re-run `schedule_tasks.ps1` if any parameters changed
