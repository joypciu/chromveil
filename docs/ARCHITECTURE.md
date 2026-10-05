# ChromVeil architecture

Custom Chrome is three layers. **Only layer 1** is the patched `chrome` binary; layers 2–4 stay in Python and stay driver-agnostic.

```
┌─────────────────────────────────────────────────────────────────┐
│ 4. Intelligence (optional)                                      │
│    agent.py · llm.py · mcp_server.py · native agentRunTask      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│ 3. Driver adapters                                              │
│    drivers/registry.py — Playwright · Patchright · subprocess CDP │
└───────────────────────────────┬─────────────────────────────────┘
                                │ consumes LaunchPlan
┌───────────────────────────────▼─────────────────────────────────┐
│ 2. Launch composition (Python)                                  │
│    core/builder.py → LaunchPlan (argv, env, ignore_default_args)│
│    profile.py — user-facing ChromiumProfile                       │
│    stealth.py — flag bundles                                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │ executable path
┌───────────────────────────────▼─────────────────────────────────┐
│ 1. Engine (binary + fork)                                       │
│    core/engine.py — BrowserEngine + EngineTier                    │
│    resolve.py / binfetch.py — locate ChromiumFish / custom build│
│    fork/patches/*.patch — C++ deltas on ChromiumFish              │
└─────────────────────────────────────────────────────────────────┘
```

## Core types

| Type | Role |
|------|------|
| `ChromiumProfile` | Declarative identity: persona, stealth/speed toggles, driver preference |
| `BrowserEngine` | Resolved binary + `EngineTier` (`fallback` … `patched`) |
| `LaunchPlan` | **Immutable** contract passed to drivers (no flag logic in drivers) |
| `BrowserRuntime` | Façade: `runtime.open(driver=...)` |
| `VeilSession` | Live browser handle + `close()` |

## Data flow

1. `ChromiumProfile.from_env()` / JSON file  
2. `materialize()` → `core/persona.py` (stealth defaults + ephemeral or persistent user-data)  
3. `build_launch_plan(profile, LaunchContext)`  
4. `get_adapter(driver).open(profile, plan)` — Playwright uses `launch_persistent_context` when a profile dir is set  
5. Optional: MCP / agent on CDP or native `agentRunTask`

## Session defaults

- **Stealth:** `stealth_tuning`, `pure_stealth`, and `speed_tuning` default to on.  
- **Ephemeral:** `persist_persona=false` — new minimal persona seed and `~/.chromveil/sessions/run-*` per open; directory removed on `VeilSession.close()`.  
- **Persistent:** set `CHROMVEIL_PERSIST_PROFILE=1` or `persist_persona: true` in JSON for `~/.chromveil/profiles/<hash>`.

## Extension points

- **New driver:** implement `DriverAdapter` in `drivers/registry.py`  
- **New stealth flags:** edit `stealth.py`, not drivers  
- **New engine:** set `CHROMVEIL_EXECUTABLE` or extend `resolve.py`  
- **Fork tuning:** add patch under `fork/patches/`, apply with `fork/apply-chromveil.sh`

## Public API (preferred)

```python
from chromveil import ChromiumProfile, BrowserRuntime

profile = ChromiumProfile.from_env()
runtime = BrowserRuntime(profile)
plan = runtime.launch_plan(for_playwright=True)
session = runtime.open(driver="patchright")
```

Legacy: `chromveil.open()`, `chromveil.launch()` unchanged.
