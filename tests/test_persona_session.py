from chromveil.core.persona import prepare_session_identity
from chromveil.profile import ChromiumProfile


def test_ephemeral_session_fresh_seed_and_dir():
    a = ChromiumProfile(lean_gpu_args=False, persist_persona=False)
    prepare_session_identity(a)
    b = ChromiumProfile(lean_gpu_args=False, persist_persona=False)
    prepare_session_identity(b)
    assert a.persona_seed and b.persona_seed
    assert a.persona_seed != b.persona_seed
    assert a.user_data_dir and b.user_data_dir
    assert a.user_data_dir != b.user_data_dir
    assert "sessions" in a.user_data_dir.replace("\\", "/")


def test_persistent_session_stable_dir():
    p = ChromiumProfile(persona_seed="stable-1", persist_persona=True, lean_gpu_args=False)
    prepare_session_identity(p)
    again = ChromiumProfile(persona_seed="stable-1", persist_persona=True, lean_gpu_args=False)
    prepare_session_identity(again)
    assert p.user_data_dir == again.user_data_dir
    assert "profiles" in p.user_data_dir.replace("\\", "/")


def test_explicit_persona_seed_preserved_when_fixed(monkeypatch):
    monkeypatch.setenv("CHROMVEIL_FIXED_PERSONA", "1")
    p = ChromiumProfile(persona_seed="my-brand", persist_persona=False, lean_gpu_args=False)
    prepare_session_identity(p)
    assert p.persona_seed == "my-brand"


def test_ephemeral_rotates_seed_each_materialize():
    p = ChromiumProfile(persist_persona=False, lean_gpu_args=False)
    prepare_session_identity(p)
    first = p.persona_seed
    p.user_data_dir = None
    prepare_session_identity(p)
    assert p.persona_seed != first
