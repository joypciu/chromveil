from chromveil.browser import launch


def test_launch_new_page_with_persistent_context():
    """Regression: ephemeral profiles use launch_persistent_context (browser may be None)."""
    sess = launch(headless=True, driver="patchright")
    try:
        page = sess.new_page()
        page.goto("about:blank", wait_until="commit", timeout=30_000)
        assert page.url.startswith("about:")
    finally:
        sess.close()
