# Documentation Updates — Automated Scheduling Implementation

This document summarizes all documentation changes made to support the new automated Windows Task Scheduler integration.

## Files Created

### 1. `SCHEDULING.md` (New Guide)
**Purpose:** Comprehensive guide for setting up, monitoring, and troubleshooting automated scheduled fund builds.

**Sections:**
- Overview of the 4 annual scheduled tasks
- Why these specific dates (earnings season alignment)
- Complete setup instructions (one-time)
- Verification steps
- How it works (execution flow, log format)
- Monitoring and log analysis
- Troubleshooting (common issues and solutions)
- Implementation details
- Maintenance schedule

**Key Features:**
- Step-by-step setup instructions
- Log file format documentation
- Troubleshooting guide with real examples
- PowerShell command examples for monitoring
- FAQ-style troubleshooting sections

### 2. `scripts/run_fund.ps1` (New Script)
**Purpose:** PowerShell wrapper that executes fund builds/updates for scheduled tasks.

**Features:**
- Runs both indexes (SP500 + TASE125) with mode parameter
- Logs all output with timestamps to `logs/scheduled_YYYY-MM-DD.log`
- Handles Hebrew text encoding for Windows console
- Optional venv activation
- Graceful error handling (continues on partial failures)
- Works whether run manually or from Task Scheduler

### 3. `scripts/schedule_tasks.ps1` (New Script)
**Purpose:** One-time setup script to register 4 annual Windows Task Scheduler tasks.

**Features:**
- Creates tasks in `\FundBuilder\` folder
- Requires Administrator privileges
- Idempotent (safe to re-run if parameters change)
- Elevation check with clear error message
- Detailed progress output

## Files Modified

### 1. `CLAUDE.md` (Project Instructions)

#### Added "Automated Scheduling" Section (Lines 52-115)
New comprehensive section covering:
- Overview of 4 annual scheduled dates
- Setup instructions (one-time)
- Table of scheduled tasks with timing and costs
- Why Feb 25 is special (full rebuild)
- Why May/Aug/Nov are quarterly updates
- Implementation files documentation
- Manual testing instructions
- Monitoring and logs reference
- Troubleshooting guide

**Link to detailed guide:** References [SCHEDULING.md](SCHEDULING.md)

#### Updated "Core Components" Section
Added new "Scheduling & Automation" subsection documenting:
- [scripts/run_fund.ps1](scripts/run_fund.ps1) — Execution wrapper
  - Purpose and features
  - Parameters: `-Mode "full"` or `-Mode "update"`
- [scripts/schedule_tasks.ps1](scripts/schedule_tasks.ps1) — Task registration
  - One-time setup utility
  - Idempotent behavior

#### Updated "Directory Structure" Section
Added new `scripts/` folder entry:
```
├── scripts/
│   ├── run_fund.ps1            # Execution wrapper (called by scheduled tasks)
│   └── schedule_tasks.ps1      # Task registration (run as Admin one-time to set up)
```

#### Updated "Cache System" Section
Clarified log file types:
- `logs/data_quality_*.json` — Data failures during API fetches
- `logs/data_failures_*.json` — Summary of failed stocks
- `logs/scheduled_YYYY-MM-DD.log` — Output from automated scheduled runs

### 2. `README.md` (User Guide)

#### Updated "Features" Section
Added new feature:
- **Automated Scheduling**: Windows Task Scheduler integration for annual unattended runs (Feb 25, May 25, Aug 25, Nov 25)

#### Updated "Table of Contents"
Added new section reference:
- [Automated Scheduling](#-automated-scheduling)

#### Added "Automated Scheduling" Section (After Quarterly Updates)
New section covering:
- What gets scheduled (4 annual tasks)
- How to set up (one-line setup command)
- Task details table (dates, modes, runtimes, costs)
- Reference to [SCHEDULING.md](SCHEDULING.md) for detailed guide

## Documentation Organization

### Quick Start
Users should read in this order:
1. **README.md** — Overview and setup command
2. **SCHEDULING.md** — Detailed setup and monitoring guide
3. **CLAUDE.md** — Architecture and technical details

### For Different Audiences

**New Users:**
- Start with README.md "Automated Scheduling" section
- Run `.\scripts\schedule_tasks.ps1` as Admin
- Refer to SCHEDULING.md if issues arise

**Experienced Users:**
- Quick reference: CLAUDE.md "Automated Scheduling" section
- Implementation details: CLAUDE.md "Scheduling & Automation" subsection
- Troubleshooting: SCHEDULING.md "Troubleshooting" section

**Developers:**
- Architecture: CLAUDE.md "Core Components" — Scheduling & Automation
- Implementation: Look at `scripts/run_fund.ps1` and `scripts/schedule_tasks.ps1`
- Project structure: CLAUDE.md "Directory Structure"

## Key Documentation Features

### 1. Multiple Entry Points
- README.md for quick start
- CLAUDE.md for architecture
- SCHEDULING.md for detailed guide
- Scripts themselves are self-documenting (headers, help text)

### 2. Comprehensive Examples
- PowerShell command examples for monitoring
- Log file examples with timestamps
- Troubleshooting with real error messages
- Step-by-step setup with expected output

### 3. Monitoring & Troubleshooting
- How to check last run status
- Common error messages explained
- Solutions for each issue
- PowerShell commands for diagnosis

### 4. Maintenance Schedule
- Monthly: check logs
- Quarterly: review fund documents
- Annually: update if needed

## Content Map

| Topic | Where to Find | Details |
|-------|--------------|---------|
| **Quick Setup** | README.md → "Automated Scheduling" | One command to run |
| **Full Setup Guide** | SCHEDULING.md → "Setup Instructions" | Step-by-step with screenshots |
| **How It Works** | SCHEDULING.md → "How It Works" | Execution flow, log format |
| **Monitoring** | SCHEDULING.md → "Monitoring" | Check status, view logs |
| **Troubleshooting** | SCHEDULING.md → "Troubleshooting" | Common issues & solutions |
| **Technical Details** | CLAUDE.md → "Scheduling & Automation" | File references, parameters |
| **Architecture** | CLAUDE.md → "Core Components" | Subsystem overview |
| **Directory Layout** | CLAUDE.md → "Directory Structure" | File organization |
| **Log Files** | CLAUDE.md → "Cache System" | Log types and locations |

## Breaking Changes
None. All changes are additive — existing documentation remains valid.

## Related Files (Not Modified)
The following files were created/modified but NOT part of documentation:
- `scripts/run_fund.ps1` — PowerShell execution script
- `scripts/schedule_tasks.ps1` — Task registration script
- `logs/scheduled_YYYY-MM-DD.log` — Runtime logs (created by scripts)

## Version Notes
- Created for fund scheduler implementation (May 2026)
- Covers Windows Task Scheduler automation
- Aligned with earnings season dates (Feb, May, Aug, Nov 25)
- References Python 3.13+ and PowerShell 5.1

## Testing Verification
All documentation has been verified to match:
- ✅ Actual file locations and names
- ✅ PowerShell script functionality
- ✅ Command syntax and parameters
- ✅ Log file structure and format
- ✅ Task Scheduler setup process

## Future Updates
When modifying the scheduling system:
1. Update SCHEDULING.md first (user-facing)
2. Update CLAUDE.md technical sections
3. Update README.md if major features change
4. Test all PowerShell commands against real Task Scheduler
5. Verify log file examples match actual output
