"""Launch-time stealth + speed tuning (driver + Chromium flags)."""
from __future__ import annotations

# Strip automation tells Playwright/Patchright inject by default.
PLAYWRIGHT_IGNORE_DEFAULT_ARGS: tuple[str, ...] = (
    "--enable-automation",
    "--disable-extensions",
    "--disable-component-extensions-with-background-pages",
)

# Baseline stealth flags (stock Chrome + patched builds).
STEALTH_CHROMIUM_ARGS: tuple[str, ...] = (
    "--disable-blink-features=AutomationControlled",
    "--exclude-switches=enable-automation",
    "--disable-infobars",
    "--disable-features=AutomationControlled",
)

# Lean pure stealth (default) — benchmark: ~same cold launch as Patchright, faster navigation.
PURE_STEALTH_LEAN_ARGS: tuple[str, ...] = (
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-default-apps",
)

# Full pure stealth — more isolation, slightly slower startup.
PURE_STEALTH_FULL_ARGS: tuple[str, ...] = PURE_STEALTH_LEAN_ARGS + (
    "--disable-sync",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-features=TranslateUI",
    "--metrics-recording-only",
)

PURE_STEALTH_CHROMIUM_ARGS: tuple[str, ...] = PURE_STEALTH_LEAN_ARGS

# Throughput: keep renderers hot during automation.
SPEED_CHROMIUM_ARGS: tuple[str, ...] = (
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--disable-hang-monitor",
)

# Headless: align window size with viewport probes; avoid looking like a tiny automation window.
HEADLESS_STEALTH_ARGS: tuple[str, ...] = (
    "--hide-scrollbars",
    "--mute-audio",
)
