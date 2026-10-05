# Stealth Chromium roadmap

ChromVeil splits the problem the same way [ChromiumFish](https://github.com/arman-bd/chromiumfish) does:

| Layer | Owner in this stack | What “stealth” means |
|-------|---------------------|----------------------|
| **Browser engine** | Chromium fork + C++ patches | UA, Client Hints, WebGL/canvas, `navigator.webdriver`, no CDP leak artifacts |
| **Agent intelligence** | ChromVeil (`agent.py`, `llm.py`) | Perceive page → plan JSON actions → act via Playwright/CDP |

You cannot get **full** stealth from Playwright + injected JS alone; detectors look for tampering in the JS environment. Engine-level spoofing is the ChromiumFish approach.

## Where you are on Windows (today)

- **ChromiumFish PyPI** installs, but **prebuilt Windows binaries are not published yet** (`chromiumfish fetch` → 404).
- ChromVeil **falls back** to stock Playwright Chromium and prints a warning — fine for agent development, not for anti-bot production.

## Practical paths to “fully stealth”

### A. Build / run ChromiumFish on Linux (fastest to real stealth)

1. Clone [arman-bd/chromiumfish](https://github.com/arman-bd/chromiumfish).
2. On Ubuntu/WSL2: follow upstream docs — `apply.sh`, Chromium `depot_tools`, `out/Release` build (hours, ~100GB disk).
3. Point ChromVeil at the binary:
   ```powershell
   $env:CHROMVEIL_EXECUTABLE = "\\wsl$\Ubuntu\home\you\chromiumfish\out\Release\chrome"
   chromveil doctor
   ```

### B. Contribute Windows Release assets

- Same fork; add CI matrix `windows-latest`, publish `chrome-win.zip` to GitHub Releases.
- ChromVeil + ChromiumFish SDK then work without `CHROMVEIL_EXECUTABLE`.

### C. Your own patch set (CV differentiation)

1. Copy `patches/` layout from ChromiumFish.
2. Add one focused patch (e.g. WebRTC IP handling, timezone consistency with persona seed).
3. Document in a short `PATCHES.md` — recruiters love “touched Chromium C++”.

## Intelligence integration (already in ChromVeil)

- **`chromveil run`** — built-in perceive-act loop; any OpenAI-compatible endpoint (`CHROMVEIL_LLM_URL`, default Ollama).
- **`chromveil serve`** — exposes CDP so **Cursor, Hermes, browser-use, OpenClaw** drive the same browser persona.
- Next step: optional **`chromveil mcp`** (mirror ChromiumFish MCP) wrapping `run` + `serve` tools.

## Suggested resume narrative

> Built **ChromVeil**, a Playwright/CDP agent harness with persona-aware launcher integration for patched Chromium (ChromiumFish-compatible). Separates engine stealth (C++ fork) from agent loop (LLM tool JSON), with CDP serve for external agent frameworks.
