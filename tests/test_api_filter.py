from chromveil.intelligence.api_filter import is_api_candidate
from chromveil.intelligence.data_query import select_for_user


def test_other_resource_bet365_paths():
    url = "https://www.bet365.com/manifestapi/getmanifest?s=www-sports"
    assert is_api_candidate(url, "other", "application/octet-stream")
    assert is_api_candidate(
        "https://www.bet365.com/pullpodapi/gethomepagepods?lid=1",
        "xhr",
        "text/plain",
    )


def test_select_for_user_keywords():
    from chromveil.intelligence.network_capture import CapturedApi

    entries = [
        CapturedApi(
            url="https://api.example/v1/events",
            method="GET",
            status=200,
            resource_type="xhr",
            content_type="application/json",
            body={"events": [{"name": "A v B", "odds": "2.0"}]},
            size_bytes=50,
            relevance=3.0,
        ),
        CapturedApi(
            url="https://cdn.example/app.js",
            method="GET",
            status=200,
            resource_type="script",
            content_type="application/javascript",
            body="code",
            size_bytes=10,
            relevance=0.0,
        ),
    ]
    out = select_for_user(entries, want="odds,events")
    assert out["count"] >= 1
