# Pure stealth + performance

## Python launch (`CHROMVEIL_PURE_STEALTH=1`, default on)

- Strips Playwright/Patchright `--enable-automation`
- Chromium: `AutomationControlled`, no infobars, no first-run/sync/background update noise
- Persona-stable profile dir: `~/.chromveil/profiles/<hash>/` when `CHROMVEIL_PERSIST_PROFILE=1`

## Engine patches (after WSL build)

Apply all `fork/patches/*.patch` then rebuild:

```bash
bash /mnt/e/chromveil/fork/apply-chromveil.sh
autoninja -C out/Release chrome
```

| Patch | Effect |
|-------|--------|
| `chromveil-agent-fast` | Leaner LLM context, faster clicks |
| `chromveil-serialize-fast` | Faster page serialization |
| `chromveil-agent-step-wait` | Snappier agent loop |

## Verify

```bash
chromveil fetch
chromveil e2e
```

Strict checks (`plugins_present`, `ua_no_headless_token`) apply when a custom/chromiumfish binary is detected.
