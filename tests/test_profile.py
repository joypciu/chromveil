from chromveil.profile import ChromiumProfile


def test_chromium_argv_persona_and_cdp():
    p = ChromiumProfile(persona_seed="x", cdp_port=9333)
    argv = p.chromium_argv()
    assert "--persona-seed=x" in argv
    assert "--remote-debugging-port=9333" in argv


def test_spec_kind():
    p = ChromiumProfile(persona_seed="test")
    spec = p.to_spec()
    assert spec["kind"] == "chromveil/browser-spec"
    assert "connect" in spec
    assert "playwright" in spec["connect"]
