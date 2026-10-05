# Developing before custom Chromium is ready

ChromVeil is designed in layers. **Only the bottom layer** (patched `chrome`) is blocked on your WSL build. Everything above it already works.

## Tiers (`chromveil doctor`)

| Tier | What you have | Production stealth |
|------|----------------|-------------------|
| `driver-fallback` | Playwright/Patchright + ChromVeil flags | Partial (launch tuning only) |
| `chromiumfish-binary` | `chromiumfish fetch` prebuild | Strong (engine patches) |
| `patched` | Your `out/Release/chrome` + ChromVeil fork patches | Strongest + fastest agent |

## What works today (no custom build)

```powershell
pip install -e ".[dev,drivers,native]"
python -m playwright install chromium
chromveil doctor
chromveil e2e
chromveil open --driver patchright --headed
```

## Upgrade path

1. **Windows:** `python -m chromiumfish fetch` → sets tier to `chromiumfish-binary`
2. **WSL:** `scripts/wsl/setup.sh` + optional `build-chromiumfish.sh`
3. **Fork:** `fork/apply-chromveil.sh` → rebuild → `CHROMVEIL_EXECUTABLE=...`

## Env

- `CHROMVEIL_DEV=1` (default) — apply stealth/speed launch defaults
- `CHROMVEIL_DEV=0` — raw profile only
