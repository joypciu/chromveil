from chromveil.intelligence.pipe_extract import extract_pipe_text, is_pipe_payload
from chromveil.intelligence.structured_extract import build_extracted
from chromveil.intelligence.network_capture import CapturedApi


SAMPLE = (
    "F|PS;IT=#HO#;|MA;N2=France v Belgium;MN=Goals in First 10 Minutes;"
    "NA=Over;OD=3/1;CC=UEFA-NAT-LGE-A;|MA;N2=Italy v Türkiye;MN=Goals in First 10 Minutes;"
    "NA=Over;OD=11/4;CC=UEFA-NAT-LGE-A;|"
)


def test_is_pipe_payload():
    assert is_pipe_payload(SAMPLE)
    assert not is_pipe_payload("(()=>{window.foo=1})")


def test_extract_pipe_text():
    rows = extract_pipe_text(SAMPLE, source="/pullpodapi/gethomepagepods")
    assert len(rows) >= 2
    assert any(r["event"] == "France v Belgium" and r["odds"] == "3/1" for r in rows)


def test_build_extracted_from_entries():
    entries = [
        CapturedApi(
            url="https://www.bet365.com/pullpodapi/gethomepagepods",
            method="GET",
            status=200,
            resource_type="xhr",
            content_type="text/plain",
            body=SAMPLE,
            size_bytes=len(SAMPLE),
        )
    ]
    ex = build_extracted(entries, [], None)
    assert ex["selection_count"] >= 2
    assert "France v Belgium" in ex["events"]
