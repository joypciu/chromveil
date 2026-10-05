import pytest

from chromveil.profile import ChromiumProfile
from chromveil.drivers import open_browser


@pytest.fixture(scope="module")
def browser_session():
    profile = ChromiumProfile.from_env()
    profile.headless = True
    try:
        session = open_browser(profile)
    except Exception as exc:
        pytest.skip(f"browser unavailable: {exc}")
    yield session
    session.close()
