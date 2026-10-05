from chromveil.intelligence.auto_capture import should_auto_capture


def test_sportsbook_urls_auto_capture():
    assert should_auto_capture("https://www.betonline.ag/sportsbook")
    assert should_auto_capture("https://www.bet365.com/#/IP/")


def test_about_blank_skipped():
    assert not should_auto_capture("about:blank")
