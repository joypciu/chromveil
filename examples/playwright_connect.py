"""Use ChromVeil CDP with stock Playwright (any OS once chrome is up)."""
import os

from playwright.sync_api import sync_playwright

cdp = os.environ["CHROMVEIL_CDP_URL"]  # from: chromveil up --port 9222

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(cdp)
    page = browser.contexts[0].pages[0] if browser.contexts else browser.new_page()
    page.goto("https://example.com")
    print(page.title())
