from chromveil.e2e.probes import evaluate_checks, score_checks, run_probes_on_page
from chromveil.profile import ChromiumProfile, is_patched_build


def test_stealth_probe_local(browser_session):
    profile = ChromiumProfile.from_env()
    exe = profile.resolve_executable(download=False)
    patched = is_patched_build(exe)
    page = browser_session.new_page()
    try:
        report = run_probes_on_page(
            page,
            patched=patched,
            driver=browser_session.driver,
            executable=exe,
        )
    finally:
        page.close()

    assert report.checks["no_cdc_globals"]
    assert report.checks["languages_non_empty"]
    assert report.score >= 0.75
    if patched:
        assert report.checks["webdriver_false"]


def test_evaluate_checks_unit():
    probes = {
        "cdcKeys": [],
        "webdriver": False,
        "webdriverAttr": None,
        "languages": ["en"],
        "outerWidth": 1920,
        "innerWidth": 1280,
        "userAgent": "Mozilla/5.0 Chrome/120.0",
        "pluginsLength": 2,
    }
    checks = evaluate_checks(probes, strict=True)
    assert score_checks(checks) == 1.0
