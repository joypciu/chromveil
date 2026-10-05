from chromveil.intelligence.api_filter import is_api_candidate, is_noise_url
from chromveil.intelligence.data_query import select_for_user
from chromveil.intelligence.network_capture import CapturedApi


def test_noise_urls_filtered():
    assert is_noise_url("https://www.google-analytics.com/collect?v=1")
    assert is_noise_url("https://cdn.site.com/app.js")
    assert not is_noise_url("https://api.example.com/v1/events")


def test_api_candidate_xhr_json():
    assert is_api_candidate("https://x.com/api/odds", "xhr", "application/json")
    assert not is_api_candidate("https://x.com/static/logo.png", "image", "image/png")


def test_select_for_user_keywords():
    entries = [
        CapturedApi(
            url="https://api.test/sportsbook/odds",
            method="GET",
            status=200,
            resource_type="xhr",
            content_type="application/json",
            body={"events": [{"name": "match", "odds": 1.9}]},
            size_bytes=100,
            relevance=3.0,
        ),
        CapturedApi(
            url="https://api.test/telemetry",
            method="POST",
            status=200,
            resource_type="xhr",
            content_type="application/json",
            body={"ping": 1},
            size_bytes=10,
            relevance=1.0,
        ),
    ]
    out = select_for_user(entries, want="odds,events")
    assert out["count"] == 1
    assert "odds" in out["apis"][0]["url"]
