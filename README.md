# ChromVeil

Driver-agnostic automation harness for a **custom Chromium** stack: hardened browser binary, launch-time stealth tuning, and optional native in-browser agent tooling.

**Repository:** [github.com/joypciu/chromveil](https://github.com/joypciu/chromveil)

---

## Overview

ChromVeil separates concerns into four layers (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)):

| Layer | Responsibility |
|--------|----------------|
| **Engine** | Patched `chrome` (ChromiumFish or your build) |
| **Launch plan** | Persona, argv, env, stealth flags — one immutable contract per session |
| **Drivers** | Playwright, Patchright, subprocess CDP |
| **Intelligence** | MCP server, LLM tasks, native `agentRunTask` (when the fork is available) |

Every browser open uses **stealth by default**: automation tells stripped, lean pure-stealth Chromium flags, and Playwright `ignore_default_args`. Unless you opt in to persistence, each session gets a **rotating ephemeral identity** — new `persona-seed`, viewport, `lang`, and empty user-data under `~/.chromveil/sessions/` (removed on `close()`). Use `goto_resilient()` or `BrowserRuntime.open_and_visit()` to retry with a fresh identity when a site shows block signals.

---

## Quick start

### Install (Python)

```powershell
cd E:\chromveil
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
chromveil doctor
```

### Open a browser (stealth + ephemeral session)

```powershell
# Headed is the default (best User-Agent / fingerprint scores)
chromveil open --driver patchright

# Headless CI / servers
$env:CHROMVEIL_HEADLESS="1"
chromveil open --driver patchright
```

### Python API

```python
from chromveil import ChromiumProfile, BrowserRuntime

profile = ChromiumProfile.from_env()  # stealth on, ephemeral session
with BrowserRuntime(profile).open(driver="patchright") as session:
    page = session.new_page()
    page.goto("https://example.com")
```

### Health check

```powershell
chromveil e2e --headed          # stealth probes + timing JSON
python -m pytest tests -q
chromveil canary --headed                        # betonline + bet365 pregame/live
chromveil bench site --canary --headed -o reports
CHROMVEIL_CANARY_LIVE=1 pytest tests/test_diverse_sites.py -v
```

Local **5s health loop** (log only, no Cursor wake): `.\scripts\loop-health.ps1`

Until a patched binary is built, use **`CHROMVEIL_USE_SYSTEM_CHROME=1`** to drive installed Google Chrome with ChromVeil launch tuning. Roadmap: [docs/NEXT_PHASE.md](docs/NEXT_PHASE.md).

---

## Session identity

| Mode | Default | Behavior |
|------|---------|----------|
| **Ephemeral** | Yes (`persist_persona=false`) | New persona seed + temp profile dir per open; cleaned on close |
| **Persistent** | `CHROMVEIL_PERSIST_PROFILE=1` | Stable seed + `~/.chromveil/profiles/<hash>` |

| Variable | Purpose |
|----------|---------|
| `CHROMVEIL_PERSONA` | Pin persona seed (pair with `CHROMVEIL_ROTATE_SEED=0` to stop rotation) |
| `CHROMVEIL_FIXED_PERSONA` | `1` to keep constructor/env persona seed across opens |
| `CHROMVEIL_ROTATE_IDENTITY` | `0` to disable viewport/lang/seed rotation (default on) |
| `CHROMVEIL_PERSIST_PROFILE` | `1` to reuse profile storage across runs |
| `CHROMVEIL_HEADLESS` | `1` for headless (`new`); default is headed |
| `CHROMVEIL_STEALTH` / `CHROMVEIL_PURE_STEALTH` | Set `0` to disable launch stealth bundles |
| `CHROMVEIL_PURE_STEALTH_MODE` | `lean` (default), `full`, or `off` |
| `CHROMVEIL_EXECUTABLE` | Path to custom or ChromiumFish `chrome` |
| `CHROMVEIL_USE_SYSTEM_CHROME` | `1` force on / `0` force off installed Google Chrome |
| `CHROMVEIL_AUTO_SYSTEM_CHROME` | Windows default `1` — use system Chrome when no patched binary |
| `CHROMVEIL_DRIVER` | Default `patchright` when installed; or `playwright`, `subprocess`, `cdp` |

Long-running CDP attach:

```powershell
chromveil up --port 9222
chromveil spec -f config\chromveil.profile.example.json
```

---

## Custom Chromium engine

Production-grade fingerprint hardening lives in the **binary** (e.g. [ChromiumFish](https://github.com/arman-bd/chromiumfish)) plus optional patches under `fork/patches/`.

**Windows without a local build:** see [docs/DEV_WITHOUT_CUSTOM_CHROME.md](docs/DEV_WITHOUT_CUSTOM_CHROME.md) — Patchright + ChromVeil launch tuning until `CHROMVEIL_EXECUTABLE` is set.

**WSL build (recommended for patched chrome):**

```powershell
.\scripts\Install-WslChromiumfish.ps1
```

```bash
/mnt/e/chromveil/scripts/wsl/setup.sh
source ~/.chromveil/env
chromveil doctor --native
bash /mnt/e/chromveil/fork/apply-chromveil.sh
```

---

## Cursor MCP

Copy `config/cursor-mcp.json.example` into Cursor MCP settings (WSL entry recommended when the Linux binary is available).

Typical tools: `navigate`, `snapshot_fast`, `click`, `type_text`, `run_task`, `browser_status`.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Universal driver / browser spec](docs/UNIVERSAL_DRIVER.md)
- [E2E stealth tests](docs/E2E.md)
- [Pure stealth modes](docs/PURE_STEALTH.md)

---

## License

MIT
