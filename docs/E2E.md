# ChromVeil E2E testing

## What runs

| Suite | Command | Checks |
|-------|---------|--------|
| Unit | `pytest tests -q` | Profile args, probe scoring |
| Stealth E2E | `tests/e2e/test_stealth_e2e.py` | `navigator.webdriver`, no `cdc_*` globals, viewport |
| Speed E2E | `tests/e2e/test_speed_e2e.py` | example.com navigation + DOM snapshot latency |
| Live (optional) | `CHROMVEIL_E2E_LIVE=1 pytest tests/e2e/test_live_fingerprint.py` | Network smoke |

CLI aggregator:

```bash
chromveil e2e -o report.json
```

## Tunables

| Env | Default | Meaning |
|-----|---------|---------|
| `CHROMVEIL_STEALTH` | `1` | Stealth Chromium + Playwright ignore args |
| `CHROMVEIL_SPEED` | `1` | Disable background throttling flags |
| `CHROMVEIL_E2E_NAV_MS` | `8000` | Max navigation time |
| `CHROMVEIL_E2E_SCORE_MIN` | `0.75` | Min stealth score (0–1) |
| `CHROMVEIL_EXPECT_PATCHED` | `0` | Require `webdriver===false` strictly |

## Patched build (WSL)

After `chromiumfish fetch` or `out/Release/chrome`:

```bash
export CHROMVEIL_EXECUTABLE=/path/to/chrome
export CHROMVEIL_EXPECT_PATCHED=1
chromveil e2e
```

Apply fork speed patches before compile:

```bash
bash /mnt/e/chromveil/fork/apply-chromveil.sh
```

## Launch tuning (Python layer)

See `chromveil/stealth.py` — applied via `ChromiumProfile.stealth_tuning` and `speed_tuning`.

Engine tuning — `fork/patches/chromveil-agent-fast.patch`, `chromveil-serialize-fast.patch`.
