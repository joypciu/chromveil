# One ChromVeil browser, any library

ChromVeil is **not** tied to Playwright. It owns:

1. **Which** `chrome` binary runs (ChromiumFish / your patched build)
2. **How** it is configured (`persona_seed`, GPU-less flags, proxy, timezone)
3. **Where** it listens (`cdp_url`)

Automation libraries only **attach**.

## Pattern A — CDP hub (recommended)

```bash
chromveil up --port 9222
# prints cdp_url + CHROMVEIL_CDP_URL
```

| Library | Connect |
|---------|---------|
| Playwright | `chromium.connect_over_cdp(cdp_url)` |
| Patchright | same API |
| Puppeteer | `puppeteer.connect({ browserURL: cdp_url })` |
| Selenium 4 | `options.debugger_address = "127.0.0.1:9222"` |

See `examples/playwright_connect.py`, `examples/puppeteer_connect.mjs`.

## Pattern B — Launch via driver

```python
from chromveil import ChromiumProfile, open

profile = ChromiumProfile.from_file("config/chromveil.profile.example.json")
with open(profile, driver="patchright") as s:
    page = s.new_page()
```

`driver=auto` prefers **Patchright** when installed, else Playwright.

## Pattern C — Raw subprocess

```python
from chromveil import ChromiumProfile, spawn_cdp

profile = ChromiumProfile.from_env()
profile.cdp_port = 9222
sess = spawn_cdp(profile)
# use sess.cdp_url with anything that speaks CDP
```

## Machine-readable spec

```bash
chromveil spec -f config/chromveil.profile.example.json
```

Emits `chromveil/browser-spec` JSON: `executable`, `argv`, `cdp_url`, connect hints.

## Customize the binary

Engine patches live in ChromiumFish + your `fork/patches/`. ChromVeil does not
replace that — it **standardizes** how every driver talks to the same build.
