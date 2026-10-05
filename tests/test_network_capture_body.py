import json

from chromveil.intelligence.network_capture import NetworkCapture


class _FakeResponse:
    def __init__(self, raw: bytes, content_type: str = ""):
        self._raw = raw
        self.headers = {"content-type": content_type}

    def body(self):
        return self._raw


def test_read_body_pipe_text_with_empty_content_type():
    nc = NetworkCapture(page=None)
    pipe = b"F|MA;N2=A v B;OD=2/1;|"
    body = nc._read_body(_FakeResponse(pipe, ""), "")
    assert isinstance(body, str)
    assert "F|MA" in body


def test_read_body_json():
    nc = NetworkCapture(page=None)
    raw = json.dumps({"a": 1}).encode()
    body = nc._read_body(_FakeResponse(raw, "application/json"), "application/json")
    assert body == {"a": 1}
