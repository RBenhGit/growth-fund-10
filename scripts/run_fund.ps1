<#
.SYNOPSIS
    Growth Fund Builder - Scheduled execution wrapper
.PARAMETER Mode
    "full"   - Full rebuild (all 500+ stocks) followed by LTM update
    "update" - Quarterly LTM update only (~50 stocks)
.EXAMPLE
    .\run_fund.ps1 -Mode full
    .\run_fund.ps1 -Mode update
#>
param(
    [Parameter(Mandatory)]
    [ValidateSet("full", "update")]
    [string]$Mode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# ── Paths ────────────────────────────────────────────────────────────────────
# When run from Task Scheduler, $PWD will be set to the project directory
# When run manually from scripts/, go up one level to project root
$ProjectDir = Get-Location
if ((Split-Path -Leaf $ProjectDir) -eq "scripts") {
    $ProjectDir = Split-Path -Parent $ProjectDir
}
$LogDir      = Join-Path $ProjectDir "logs"
$LogFile     = Join-Path $LogDir ("scheduled_" + (Get-Date -Format "yyyy-MM-dd") + ".log")

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding utf8
}

function Invoke-Fund {
    param([string[]]$Arguments, [string]$Description)
    Write-Log "START: $Description"
    Write-Log "CMD: python build_fund.py $($Arguments -join ' ')"

    # Run Python and capture STDOUT only (not STDERR mixed in)
    # STDERR from Python will appear on console in real-time but won't break exit code detection
    & python build_fund.py @Arguments | ForEach-Object {
        $logLine = "[$(Get-Date -Format 'HH:mm:ss')] $_"
        Write-Host $logLine
        Add-Content -Path $LogFile -Value $logLine -Encoding utf8
    }

    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Log "FAILED: $Description (exit code $exitCode)"
        return $false
    }
    Write-Log "OK: $Description"
    return $true
}

# ── Setup ─────────────────────────────────────────────────────────────────────
Set-Location $ProjectDir

# Ensure logs directory exists (it should, but be safe)
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# UTF-8 environment for Hebrew output
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8       = "1"

# Optional venv activation
foreach ($venvPath in @("venv\Scripts\Activate.ps1", ".venv\Scripts\Activate.ps1")) {
    $full = Join-Path $ProjectDir $venvPath
    if (Test-Path $full) {
        Write-Log "Activating venv: $full"
        . $full
        break
    }
}

# ── Run header ────────────────────────────────────────────────────────────────
$separator = "=" * 70
Add-Content -Path $LogFile -Value $separator -Encoding utf8
Write-Log "Growth Fund Builder - Scheduled Run"
Write-Log "Mode: $Mode | User: $env:USERNAME | Host: $env:COMPUTERNAME"
Add-Content -Path $LogFile -Value $separator -Encoding utf8

# ── Execute ───────────────────────────────────────────────────────────────────
$anyFailure = $false

if ($Mode -eq "full") {
    # Feb 25: Full rebuild then LTM update for each index
    if (-not (Invoke-Fund -Arguments @("--index", "SP500") `
                          -Description "SP500 full build")) {
        $anyFailure = $true
    }
    if (-not (Invoke-Fund -Arguments @("--index", "TASE125") `
                          -Description "TASE125 full build")) {
        $anyFailure = $true
    }
    # Follow-up LTM updates regardless of build outcome (catch late reporters)
    if (-not (Invoke-Fund -Arguments @("--index", "SP500", "--update") `
                          -Description "SP500 LTM update")) {
        $anyFailure = $true
    }
    if (-not (Invoke-Fund -Arguments @("--index", "TASE125", "--update") `
                          -Description "TASE125 LTM update")) {
        $anyFailure = $true
    }
}
elseif ($Mode -eq "update") {
    # May/Aug/Nov: LTM updates only
    if (-not (Invoke-Fund -Arguments @("--index", "SP500", "--update") `
                          -Description "SP500 LTM update")) {
        $anyFailure = $true
    }
    if (-not (Invoke-Fund -Arguments @("--index", "TASE125", "--update") `
                          -Description "TASE125 LTM update")) {
        $anyFailure = $true
    }
}

# ── Footer ────────────────────────────────────────────────────────────────────
if ($anyFailure) {
    Write-Log "COMPLETED WITH ERRORS"
    Add-Content -Path $LogFile -Value $separator -Encoding utf8
    exit 1
}
else {
    Write-Log "COMPLETED SUCCESSFULLY"
    Add-Content -Path $LogFile -Value $separator -Encoding utf8
    exit 0
}
