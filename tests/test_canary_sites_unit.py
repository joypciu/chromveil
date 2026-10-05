import json
from pathlib import Path

from chromveil.e2e.canary_sites import CANARY_SPORTSBOOK_SITES, default_canary_url


def test_canary_urls_match_config_json():
    cfg = json.loads(Path("config/canary_sites.json").read_text(encoding="utf-8"))
    by_key = {s["key"]: s["url"] for s in cfg["sites"]}
    for site in CANARY_SPORTSBOOK_SITES:
        assert by_key[site.key] == site.url


def test_canary_includes_betonline_and_bet365_routes():
    keys = {s.key for s in CANARY_SPORTSBOOK_SITES}
    assert keys == {"betonline_sportsbook", "bet365_pregame", "bet365_live"}
    assert "betonline.ag" in CANARY_SPORTSBOOK_SITES[0].url
    assert "#/HO/" in default_canary_url()
    assert "#/IP/" in next(s.url for s in CANARY_SPORTSBOOK_SITES if s.key == "bet365_live")
