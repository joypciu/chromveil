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
)

# Extra hygiene for "pure" mode — fewer background services & first-run UI.
PURE_STEALTH_CHROMIUM_ARGS: tuple[str, ...] = (
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-features=TranslateUI",
    "--metrics-recording-only",
)

# Throughput: keep renderers hot during automation.
SPEED_CHROMIUM_ARGS: tuple[str, ...] = (
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--disable-hang-monitor",
)
