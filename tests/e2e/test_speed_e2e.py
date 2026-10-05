import os

from chromveil.e2e.speed import bench_session


def test_speed_navigate_example(browser_session):
    max_nav = float(os.environ.get("CHROMVEIL_E2E_NAV_MS", "12000"))
    report = bench_session(browser_session, browser_session.driver)
    assert report.navigate_ms < max_nav
    assert report.snapshot_ms < 2000
