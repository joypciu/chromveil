from chromveil.profile import ChromiumProfile


def test_stealth_args_in_argv():
    p = ChromiumProfile(stealth_tuning=True, speed_tuning=True, lean_gpu_args=False)
    argv = p.chromium_argv(include_cdp=False)
    assert "--disable-blink-features=AutomationControlled" in argv
    assert "--exclude-switches=enable-automation" in argv
    assert p.playwright_ignore_default_args() == ["--enable-automation", "--disable-extensions"]
