from chromveil.profile import ChromiumProfile


def test_stealth_args_in_argv():
    p = ChromiumProfile(
        stealth_tuning=True,
        pure_stealth=True,
        speed_tuning=True,
        lean_gpu_args=False,
        persist_persona=False,
    )
    argv = p.chromium_argv(include_cdp=False)
    assert "--disable-blink-features=AutomationControlled" in argv
    assert "--no-first-run" in argv
    assert "--exclude-switches=enable-automation" in argv
    ignore = p.playwright_ignore_default_args()
    assert "--enable-automation" in ignore
