from chromveil.intelligence.api_filter import is_obfuscated_chunk_url, should_read_response_body
from chromveil.intelligence.collect_tuning import (
    capture_limits,
    resolve_all_data,
    resolve_capture_websockets,
)


def test_obfuscated_chunk_skipped():
    url = "https://www.bet365.com/lWS48EACROdodngxRUOe3VtaEPyoStdAGa8CP"
    assert is_obfuscated_chunk_url(url, "fetch")
    assert not should_read_response_body(url, "fetch", "application/octet-stream")


def test_pullpod_still_read():
    url = "https://www.bet365.com/pullpodapi/gethomepagepods?lid=1"
    assert should_read_response_body(url, "xhr", "text/plain")


def test_smart_defaults():
    assert resolve_all_data(all_flag=False, no_all_flag=False, want=None, ask=None) is False
    assert resolve_all_data(all_flag=True, no_all_flag=False, want=None, ask=None) is True
    assert capture_limits(False)["max_ws_frames"] == 0
    assert resolve_capture_websockets("https://www.bet365.com/", all_data=False, explicit=None) is False
