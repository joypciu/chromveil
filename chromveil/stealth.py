"""Launch-time stealth + speed tuning (driver + Chromium flags)."""
from __future__ import annotations

# Strip automation tells Playwright/Patchright inject by default.
PLAYWRIGHT_IGNORE_DEFAULT_ARGS: tuple[str, ...] = (
    "--enable-automation",
    "--disable-extensions",
)

# Extra Chromium flags (stock Chrome + patched builds). Patched ChromiumFish already
# fixes navigator.webdriver in C++; these still help when attaching via CDP.
STEALTH_CHROMIUM_ARGS: tuple[str, ...] = (
    "--disable-blink-features=AutomationControlled",
    "--exclude-switches=enable-automation",
    "--disable-infobars",
)

# Safe throughput tweaks for automation (disable throttling of background tabs).
SPEED_CHROMIUM_ARGS: tuple[str, ...] = (
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
)
