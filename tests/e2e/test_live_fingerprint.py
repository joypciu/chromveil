"""Optional live site checks (network). Run: CHROMVEIL_E2E_LIVE=1 pytest tests/e2e/test_live_fingerprint.py"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CHROMVEIL_E2E_LIVE", "").lower() not in ("1", "true", "yes"),
    reason="set CHROMVEIL_E2E_LIVE=1 for live fingerprint sites",
)


def test_example_com_loads(browser_session):
    page = browser_session.new_page()
    try:
        page.goto("https://example.com", wait_until="domcontentloaded", timeout=60_000)
        assert "Example" in page.title()
    finally:
        page.close()
