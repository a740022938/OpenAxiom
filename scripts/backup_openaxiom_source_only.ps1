<#
.SYNOPSIS
  OpenAxiom source-only backup script.  By default runs in dry-run mode.
.DESCRIPTION
  Backups up the OpenAxiom UI Lab project source code, excluding .venv,
  __pycache__, .pytest_cache, *.pyc, and other build artifacts.
  Supports -DryRun (default) and -Execute modes.
.PARAMETER Version
  Version string for the backup folder name (e.g., "v0.4.6-rc1").
.PARAMETER Execute
  If specified, actually creates the backup.  Default is dry-run only.
.PARAMETER OutputDir
  Target backup root directory.  Default: E:\_AXIOM_BACKUPS
.EXAMPLE
  .\scripts\backup_openaxiom_source_only.ps1 -Version "v0.4.6-rc1" -DryRun
  .\scripts\backup_openaxiom_source_only.ps1 -Version "v0.4.6-rc1" -Execute
#>
param(
    [Parameter(Mandatory)]
    [string]$Version,
    [switch]$Execute,
    [string]$OutputDir = "E:\_AXIOM_BACKUPS"
)

$src = "E:\Axiom_UI_Lab\Axiom"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "OpenAxiom_source_only_${Version}_${ts}"
$dst = Join-Path $OutputDir $backupName

$excludeDirs = @(
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "build",
    "dist",
    ".git",
    ".idea",
    ".vscode"
)
$excludeFiles = @("*.pyc", "*.pyo", "*.cache", "*.egg-info", "*.so")

Write-Host "======================================"
Write-Host " OpenAxiom Source-Only Backup"
Write-Host "======================================"
Write-Host "Source : $src"
Write-Host "Target : $dst"
Write-Host "Version: $Version"
Write-Host "Mode   : $(if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' })"
Write-Host ""
Write-Host "Excluded directories: $($excludeDirs -join ', ')"
Write-Host "Excluded files     : $($excludeFiles -join ', ')"
Write-Host ""

if (-not (Test-Path $src)) {
    Write-Host "ERROR: Source not found: $src"
    exit 1
}

# Build robocopy exclude-dir switches — single /XD with all dirs
$xd = @("/XD")
foreach ($d in $excludeDirs) { $xd += $d }
# Build robocopy exclude-file switches
$xf = @("/XF")
foreach ($f in $excludeFiles) { $xf += $f }

# Count what would be copied
Write-Host "Estimating file count and size..."
$allFiles = Get-ChildItem $src -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
    $file = $_.FullName
    $keep = $true
    foreach ($d in $excludeDirs) {
        if ($file -match [regex]::Escape("\$d\") -or $file -match [regex]::Escape("/$d/")) { $keep = $false; break }
    }
    if ($keep) {
        foreach ($f in $excludeFiles) {
            if ($_.Name -like $f) { $keep = $false; break }
        }
    }
    $keep
}
$fileCount = ($allFiles | Measure-Object).Count
$totalSize = ($allFiles | Measure-Object Length -Sum).Sum
Write-Host "Files to copy: $fileCount"
Write-Host "Total size   : $(if ($totalSize -gt 1GB) { '{0:N2} GB' -f ($totalSize/1GB) } elseif ($totalSize -gt 1MB) { '{0:N2} MB' -f ($totalSize/1MB) } else { '{0:N0} KB' -f ($totalSize/1KB) })"
Write-Host ""

if (-not $Execute) {
    Write-Host "DRY-RUN complete.  Pass -Execute to create the backup."
    Write-Host "Example: .\scripts\backup_openaxiom_source_only.ps1 -Version '$Version' -Execute"
    exit 0
}

# Create target
New-Item -ItemType Directory -Path $dst -Force | Out-Null

# Robocopy for recursive exclusion
$robocopyArgs = @($src, $dst, "/MIR", "/NP") + $xd + $xf + @("/R:2", "/W:2")
Write-Host "Running robocopy..."
robocopy @robocopyArgs

# Verify
$copied = (Get-ChildItem $dst -Recurse -File -ErrorAction SilentlyContinue).Count
$copiedSize = (Get-ChildItem $dst -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
$hasVenv = (Test-Path (Join-Path $dst ".venv")) -or (Get-ChildItem $dst -Recurse -Directory -Filter ".venv" -ErrorAction SilentlyContinue | Select-Object -First 1)

Write-Host ""
Write-Host "======================================"
Write-Host " Backup Summary"
Write-Host "======================================"
Write-Host "Target   : $dst"
Write-Host "Copied   : $copied files"
Write-Host "Size     : $(if ($copiedSize -gt 1GB) { '{0:N2} GB' -f ($copiedSize/1GB) } elseif ($copiedSize -gt 1MB) { '{0:N2} MB' -f ($copiedSize/1MB) } else { '{0:N0} KB' -f ($copiedSize/1KB) })"
Write-Host ".venv excluded: $(if (-not $hasVenv) { 'YES' } else { 'WARNING: .venv found!' })"
Write-Host "Status   : $(if ($?) { 'SUCCESS' } else { 'ERROR' })"
