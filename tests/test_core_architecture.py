from chromveil import BrowserRuntime, build_launch_plan
from chromveil.core.builder import LaunchContext
from chromveil.core.engine import BrowserEngine
from chromveil.core.types import EngineTier
from chromveil.profile import ChromiumProfile


def test_launch_plan_immutable_and_deduped():
    p = ChromiumProfile(
        persona_seed="t",
        lean_gpu_args=False,
        persist_persona=False,
        extra_args=["--no-first-run"],
    )
    plan = build_launch_plan(p, LaunchContext(for_playwright=True))
    assert plan.persona_seed == "t"
    assert "--persona-seed=t" in plan.argv
    assert plan.engine_tier == EngineTier.FALLBACK.value


def test_browser_runtime_exposes_plan():
    p = ChromiumProfile(persist_persona=False, lean_gpu_args=False)
    rt = BrowserRuntime(p)
    plan = rt.launch_plan(for_playwright=True)
    assert isinstance(plan.argv, tuple)


def test_engine_tier_fallback_without_binary():
    p = ChromiumProfile(executable=None, persist_persona=False)
    eng = BrowserEngine.from_profile(p, download=False)
    assert eng.tier == EngineTier.FALLBACK
    assert eng.production_stealth_ready is False


def test_spec_version_includes_engine_tier():
    p = ChromiumProfile(persist_persona=False, lean_gpu_args=False)
    spec = p.to_spec()
    assert spec["version"] == 2
    assert "engine_tier" in spec
