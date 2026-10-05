import os

import pytest

from chromveil.intelligence.navigation import detect_block_signals, goto_resilient


def test_detect_block_empty_on_blank():
    pytest.importorskip("patchright")
    from chromveil import ChromiumProfile
    from chromveil.core.runtime import BrowserRuntime

    prof = ChromiumProfile(headless=True, persist_persona=False, lean_gpu_args=False)
    session = BrowserRuntime(prof).open(driver="patchright")
    try:
        page = session.new_page()
        page.goto("about:blank", wait_until="commit", timeout=30_000)
        assert detect_block_signals(page) == []
    finally:
        session.close()


@pytest.mark.skipif(
    os.environ.get("CHROMVEIL_E2E_LIVE", "").lower() not in ("1", "true", "yes"),
    reason="set CHROMVEIL_E2E_LIVE=1",
)
def test_goto_resilient_example_com():
    result = goto_resilient("https://example.com", max_attempts=2)
    try:
        assert result.ok
        assert result.title
        assert "Example" in (result.title or "")
    finally:
        if result.session:
            result.session.close()
