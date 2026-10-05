from chromveil.core.identity_rotate import apply_rotating_identity
from chromveil.profile import ChromiumProfile


def test_ephemeral_rotates_seed_and_viewport():
    a = ChromiumProfile(persist_persona=False, lean_gpu_args=False)
    apply_rotating_identity(a)
    b = ChromiumProfile(persist_persona=False, lean_gpu_args=False)
    apply_rotating_identity(b)
    assert a.persona_seed != b.persona_seed
    assert any(arg.startswith("--lang=") for arg in a.extra_args)


def test_persistent_skips_rotation():
    p = ChromiumProfile(persona_seed="x", persist_persona=True, lean_gpu_args=False)
    apply_rotating_identity(p)
    assert p.persona_seed == "x"
    assert not any(arg.startswith("--lang=") for arg in p.extra_args)
