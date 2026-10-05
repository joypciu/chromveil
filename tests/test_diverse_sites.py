"""Canary sportsbook navigation — betonline + bet365 pregame/live.

Set CHROMVEIL_CANARY_LIVE=1 (or CHROMVEIL_DIVERSE_E2E=1) to run on network.
These URLs are the default live regression targets for ChromVeil.
"""
import os

import pytest

from chromveil.e2e.canary_sites import CANARY_SPORTSBOOK_SITES
from chromveil.intelligence.navigation import goto_resilient

pytestmark = pytest.mark.skipif(
    os.environ.get("CHROMVEIL_CANARY_LIVE", "").lower() not in ("1", "true", "yes")
    and os.environ.get("CHROMVEIL_DIVERSE_E2E", "").lower() not in ("1", "true", "yes"),
    reason="set CHROMVEIL_CANARY_LIVE=1 for betonline + bet365 canary URLs",
)


@pytest.mark.parametrize(
    "site",
    CANARY_SPORTSBOOK_SITES,
    ids=[s.key for s in CANARY_SPORTSBOOK_SITES],
)
def test_canary_sportsbook_visit(site):
    result = goto_resilient(site.url, max_attempts=3)
    try:
        assert result.ok, f"navigation failed: {result.block_signals}"
        title = (result.title or "").lower()
        assert any(frag.lower() in title for frag in site.title_fragments), result.title
    finally:
        if result.session:
            result.session.close()
