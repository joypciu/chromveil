"""Smoke: collect pipeline pieces (no network)."""
from chromveil.intelligence.display import format_collect_display


def test_display_includes_api_section():
    text = format_collect_display(
        ok=True,
        url="https://x.com",
        final_url="https://x.com/",
        title="T",
        block_signals=[],
        capture={
            "noise_filtered_total": 1,
            "count": 1,
            "apis": [{"url": "https://api.x/v1", "method": "GET", "status": 200, "data": {"a": 1}}],
        },
    )
    assert "## APIs" in text
    assert "api.x" in text
