# ChromVeil — recommended next phase

Based on architecture work, E2E probes, and the bet365 stack comparison (see `docs/benchmarks/BET365_SITE_COMPARE_2026-10-05.md`).

## Phase 1 — Engine binary (highest impact)

**Goal:** Run with a real patched `chrome`, not launch-tuning only.

1. **WSL path (recommended):** `.\scripts\Install-WslChromiumfish.ps1` → `scripts/wsl/setup.sh` → build → `export CHROMVEIL_EXECUTABLE=...`
2. **Windows prebuild:** Fix or mirror ChromiumFish release asset; `chromveil fetch` when HTTP 200.
3. **Optional interim:** `CHROMVEIL_USE_SYSTEM_CHROME=1` uses installed Google Chrome with ChromVeil argv (tier `custom`, not ChromiumFish patches).

**Verify:** `chromveil doctor`, `CHROMVEIL_EXPECT_PATCHED=1 chromveil e2e`, `chromveil bench site --headed`.

## Phase 2 — Fork integration

1. Apply `fork/patches/*.patch` on ChromiumFish source.
2. Rebuild and point `CHROMVEIL_EXECUTABLE` at `out/Release/chrome`.
3. Benchmark native `agentRunTask` + MCP in WSL.

## Phase 3 — Production hardening

1. **Driver default:** Patchright (already default when installed); avoid raw Playwright stock launch.
2. **Headed vs headless policy:** Headed for max probe score; `CHROMVEIL_E2E_HEADLESS` for CI.
3. **Site matrix:** Extend `chromveil bench site` to your target URLs; store reports under `reports/`.
4. **Proxy/geo:** Separate profile fields + docs if you need jurisdiction-correct access (out of scope for engine code).

## Phase 4 — Product surface

1. Publish MCP config for Cursor (WSL + native agent).
2. CI: `pytest`, `chromveil e2e` (headless), optional weekly `bench site` on a canary URL.
3. Versioned browser-spec (`to_spec` v2) for external automation teams.

## Success criteria for “custom chrome done”

- `chromveil doctor` tier ≠ `driver-fallback`
- `chromveil bench site` ChromVeil variants use `CHROMVEIL_EXECUTABLE` with `engine_tier` patched/chromiumfish
- Stealth score ≥ 0.75 headless and 1.0 headed on your canary sites
- Native agent available in WSL MCP path
