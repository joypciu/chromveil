#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Install WSL (Ubuntu) and bootstrap ChromiumFish + ChromVeil MCP inside Linux.

  Stealth ChromiumFish binaries are Linux/macOS today. MCP + native agent should
  run inside WSL; Cursor on Windows connects via wsl.exe (see config/cursor-mcp.json.example).
#>
$ErrorActionPreference = "Stop"

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "Installing WSL..."
    wsl --install -d Ubuntu
    Write-Host "Reboot if prompted, then re-run this script."
    exit 0
}

$distro = $env:CHROMVEIL_WSL_DISTRO
if (-not $distro) { $distro = "Ubuntu" }

Write-Host "Bootstrapping ChromVeil in WSL ($distro)..."
wsl -d $distro -e bash -lc "chmod +x /mnt/e/chromveil/scripts/wsl/*.sh && /mnt/e/chromveil/scripts/wsl/setup.sh"

Write-Host @"

Done (if setup.sh succeeded).

1. Edit config/cursor-mcp.json.example -> Cursor MCP settings
2. In WSL: source ~/.chromveil/venv/bin/activate && chromveil doctor --native
3. Optional full build: /mnt/e/chromveil/scripts/wsl/build-chromiumfish.sh

"@
