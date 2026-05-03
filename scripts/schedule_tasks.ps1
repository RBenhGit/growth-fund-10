<#
.SYNOPSIS
    Registers 4 annual Windows Scheduled Tasks for Growth Fund Builder.
    Must be run from an elevated (Administrator) PowerShell prompt.
.NOTES
    Safe to re-run — existing tasks are replaced cleanly.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Elevation check ───────────────────────────────────────────────────────────
$identity  = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator. Right-click PowerShell and choose 'Run as administrator'."
    exit 1
}

# ── Configuration ─────────────────────────────────────────────────────────────
# Script is run from the project root (via admin PowerShell)
# Compute paths by checking current location
$CurrentDir  = Get-Location
if ((Split-Path -Leaf $CurrentDir) -eq "scripts") {
    $ProjectDir = Split-Path -Parent $CurrentDir
} else {
    $ProjectDir = $CurrentDir
}
$ScriptPath  = Join-Path $ProjectDir "scripts\run_fund.ps1"
$WorkDir     = $ProjectDir
$TaskFolder  = "\FundBuilder\"
$RunAt       = "07:00"       # 07:00 AM local time

# Task definitions: Name → Mode, Month number
$tasks = @(
    @{ Name = "FundBuild_Feb25";  Mode = "full";   Month = 2  }
    @{ Name = "FundUpdate_May25"; Mode = "update"; Month = 5  }
    @{ Name = "FundUpdate_Aug25"; Mode = "update"; Month = 8  }
    @{ Name = "FundUpdate_Nov25"; Mode = "update"; Month = 11 }
)

# ── Task Scheduler folder ─────────────────────────────────────────────────────
$scheduler = New-Object -ComObject Schedule.Service
$scheduler.Connect()
$rootFolder = $scheduler.GetFolder("\")
try {
    $rootFolder.GetFolder("FundBuilder") | Out-Null
} catch {
    $rootFolder.CreateFolder("FundBuilder") | Out-Null
    Write-Host "Created Task Scheduler folder: \FundBuilder\"
}

# ── Register each task ────────────────────────────────────────────────────────
foreach ($t in $tasks) {
    $taskName = $t.Name
    $mode     = $t.Mode
    $month    = $t.Month

    Write-Host "`nRegistering: $taskName (Month=$month, Mode=$mode)..."

    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $taskName -TaskPath $TaskFolder `
        -Confirm:$false -ErrorAction SilentlyContinue

    # Build trigger: monthly on day 25 of the specified month at 07:00
    $trigger = New-ScheduledTaskTrigger `
        -Monthly `
        -DaysOfMonth 25 `
        -MonthsOfYear $month `
        -At $RunAt

    # Build action: call Windows PowerShell with ExecutionPolicy bypass
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`" -Mode $mode" `
        -WorkingDirectory $WorkDir

    # Principal: run as current user, limited privileges
    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    # Settings: allow run on battery, wake to run, stop if runs > 3 hours
    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -DontStopIfGoingOnBatteries `
        -WakeToRun

    Register-ScheduledTask `
        -TaskName  $taskName `
        -TaskPath  $TaskFolder `
        -Trigger   $trigger `
        -Action    $action `
        -Principal $principal `
        -Settings  $settings `
        -Description "Growth Fund Builder: $mode run on day 25 of month $month at $RunAt" `
        -Force | Out-Null

    Write-Host "  Registered: $TaskFolder$taskName"
}

Write-Host "`nAll 4 tasks registered successfully."
Write-Host "Verify with: Get-ScheduledTask -TaskPath '\FundBuilder\' | Format-Table TaskName, State"
