from chromveil.native import wsl_mcp_hint


def test_wsl_hint_mentions_mcp():
    assert "run-mcp" in wsl_mcp_hint()
