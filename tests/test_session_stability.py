from chromveil.intelligence.session_stability import (
    CHALLENGE_RE,
    HARD_BLOCK_RE,
    classify_page,
)


class _FakePage:
    def __init__(self, title: str, text: str):
        self._title = title
        self._text = text

    def title(self):
        return self._title

    def evaluate(self, _js):
        return self._text


def test_classify_hard_block():
    p = _FakePage("ERROR: The request could not be satisfied", "")
    assert classify_page(p) == "hard_block"


def test_classify_challenge():
    p = _FakePage("Attention Required! | Cloudflare", "Checking your browser")
    assert classify_page(p) == "challenge"


def test_classify_ok():
    p = _FakePage("Bet with bet365", "All Sports\nFootball")
    assert classify_page(p) == "ok"


def test_regex_overlap():
    assert HARD_BLOCK_RE.search("request could not be satisfied")
    assert CHALLENGE_RE.search("Attention Required")
