# Benchmark: ChromVeil vs Patchright stock (2026-10-05)

Environment: Windows, headless, Patchright driver, **no ChromiumFish binary yet** (tuned launch only).

| Metric (median) | ChromVeil | Patchright stock | Winner |
|-----------------|-----------|------------------|--------|
| Cold launch | 176 ms | 174 ms | ~tie |
| Navigate example.com | **196 ms** | 293 ms | **ChromVeil** |
| DOM snapshot | 11.5 ms | 10.5 ms | ~tie |
| Stealth score (local probes) | 0.83 | 0.83 | tie |

## Good

- **Navigation ~33% faster** with ChromVeil speed flags (`disable-background-timer-throttling`, etc.).
- **webdriver false**, no `cdc_*` globals — matches Patchright on these probes.
- Launch overhead stays negligible vs stock after **lean** pure-stealth defaults.

## Bad / gaps

- **`ua_no_headless_token`** fails for both in headless (expected until ChromiumFish binary or headed mode).
- **Custom chrome not in run** — engine-level persona/fingerprint not measured.
- Cold launch still loses by ~1–2 ms without binary; acceptable.

## Actions taken

- Default `CHROMVEIL_PURE_STEALTH_MODE=lean` (trimmed argv vs full).
- `chromveil bench compare` for repeatable reports.
- Fork patches for agent loop when binary is built.

## Re-run

```powershell
chromveil bench compare -n 5 -o reports
chromveil bench compare -n 3 --headed   # stricter UA checks
$env:CHROMVEIL_EXECUTABLE="..."; chromveil bench compare -n 5
```
