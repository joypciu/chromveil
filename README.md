# ChromVeil

**Repository:** https://github.com/joypciu/chromveil

**Your own Chromium** — fully customizable (persona, binary, flags) and **driver-agnostic**:
Playwright, Patchright, Puppeteer, Selenium, or raw CDP all attach to the same browser.

Plus: ChromiumFish stealth patches, native in-browser agent, and fast MCP.

Stack:

| Layer | Project | Role |
|-------|---------|------|
| Engine | [ChromiumFish](https://github.com/arman-bd/chromiumfish) (`e:\chromiumfish`) | C++ fingerprint hardening + `Browser.agentRunTask` native agent |
| Fork tuning | `fork/patches/chromveil-agent-fast.patch` | Leaner prompts, snappier clicks (your patch layer) |
| Harness | ChromVeil | WSL bootstrap, MCP tools, `navigate(domcontentloaded)`, `snapshot_fast` |

**Custom fork not built yet?** Use [dev mode](docs/DEV_WITHOUT_CUSTOM_CHROME.md): Playwright/Patchright + launch tuning, or `scripts/fetch-chromiumfish.ps1` for the Windows prebuild. WSL build remains the path to *your* patched chrome + fork patches.

### E2E stealth + speed tests

```powershell
chromveil e2e                    # JSON report: probes + benchmarks
.\.venv\Scripts\python -m pytest tests -q
$env:CHROMVEIL_E2E_LIVE="1"      # optional live https tests
```

With patched Chromium in WSL: `CHROMVEIL_EXECUTABLE=... CHROMVEIL_EXPECT_PATCHED=1 chromveil e2e`

### Universal driver (Playwright / Patchright / anything)

```powershell
chromveil up --port 9222
chromveil spec -f config\chromveil.profile.example.json
chromveil open --driver patchright --headed
```

Profile JSON + `chromveil/browser-spec` = one identity for every library. See [docs/UNIVERSAL_DRIVER.md](docs/UNIVERSAL_DRIVER.md).

---

## 1. Install WSL + bootstrap (Windows, Admin PowerShell)

```powershell
cd E:\chromveil
.\scripts\Install-WslChromiumfish.ps1
```

Or manually: `wsl --install -d Ubuntu`, reboot, then in Ubuntu:

```bash
/mnt/e/chromveil/scripts/wsl/setup.sh
source ~/.chromveil/env
chromveil doctor --native
```

## 2. Cursor MCP

Copy `config/cursor-mcp.json.example` into Cursor MCP settings. It runs MCP **inside WSL** so the Linux ChromiumFish binary and native agent are available.

Tools exposed:

- `navigate` — `domcontentloaded` by default (faster than full load)
- `snapshot_fast` / `snapshot` — perceive page (48 vs 120 elements)
- `click` / `type_text` — **humanized** trusted input (fork CDP)
- `run_task` — **native C++ agent** (batched actions, fastest for multi-step flows)
- `browser_status` — persona + chrome path

## 3. Custom patches (stealth + speed)

After upstream `apply.sh`:

```bash
bash /mnt/e/chromveil/fork/apply-chromveil.sh
# rebuild chrome — see scripts/wsl/build-chromiumfish.sh
```

Add more patches under `fork/patches/`. See `fork/README.md`.

## 4. Full Chromium compile (optional, hours)

```bash
/mnt/e/chromveil/scripts/wsl/build-chromiumfish.sh
export CHROMVEIL_CHROME=/mnt/e/chromiumfish/src/out/Release/chrome
```

## Environment

| Variable | Purpose |
|----------|---------|
| `CHROMVEIL_PERSONA` | ChromiumFish persona seed |
| `CHROMVEIL_CHROME` | Patched `chrome` binary |
| `CHROMVEIL_NATIVE` | `0` to disable native agent |
| `OPENAI_API_*` | LLM for `run_task` (Ollama, OpenRouter, …) |

## Resume line

> ChromVeil — WSL toolchain and MCP server on ChromiumFish: engine-level stealth Chromium, native in-process agent (`agentRunTask`), custom latency patches, fast CDP perception tools for Cursor.

## License

MIT
