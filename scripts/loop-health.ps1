# Local 5s health loop (does not wake Cursor — logs only).
# Usage: .\scripts\loop-health.ps1 [-Seconds 5]
param([int]$Seconds = 5)
$root = Split-Path $PSScriptRoot -Parent
$log = Join-Path $env:USERPROFILE ".chromveil\loop-health.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$py = Join-Path $root ".venv\Scripts\python.exe"
while ($true) {
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $env:CHROMVEIL_AUTO_FETCH = "0"
    $pytest = & $py -m pytest $root\tests -q 2>&1 | Select-Object -Last 1
    Add-Content -Path $log -Value "$ts $pytest"
    Start-Sleep -Seconds $Seconds
}
