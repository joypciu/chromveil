from chromveil.intelligence.ws_insights import parse_pipe_fields, summarize_websocket_frames


def test_parse_pipe_fields():
    raw = "\x14__time\x01F|IN;TI=20261005105400402;UF=55;|"
    fields = parse_pipe_fields(raw)
    assert fields and fields[0].get("TI") == "20261005105400402"


def test_summarize_websocket_frames():
    frames = [
        {
            "url": "wss://premws.example/zap/",
            "direction": "received",
            "payload": "F|IN;TI=1;UF=55;|",
            "size_bytes": 20,
        }
    ]
    s = summarize_websocket_frames(frames)
    assert s["frame_count"] == 1
    assert s["pipe_samples"]
