"""Launch patched chrome via ChromVeil profile + Patchright driver."""
from chromveil import ChromiumProfile, open as veil_open

profile = ChromiumProfile.from_env()
profile.persona_seed = "demo-1"
profile.headless = False

with veil_open(profile, driver="patchright") as session:
    page = session.new_page()
    page.goto("https://example.com")
    print(session.driver, page.title())
