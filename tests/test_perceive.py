from chromveil.perceive import PageView


def test_page_view_prompt():
    v = PageView(
        url="https://example.com",
        title="Example",
        text_excerpt="Hello",
        elements=[{"ref": "e0", "tag": "a", "label": "More", "visible": True, "href": ""}],
    )
    block = v.to_prompt_block()
    assert "example.com" in block
    assert "[e0]" in block
