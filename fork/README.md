# ChromVeil × ChromiumFish fork layer

Upstream stealth + native agent: [ChromiumFish `patches/`](../../chromiumfish/patches/) (persona, fingerprint, `ai-agent/agent-layer.patch`).

ChromVeil adds **latency-oriented** hunks without forking the whole monorepo:

| Patch | Intent |
|-------|--------|
| `chromveil-agent-fast.patch` | Smaller page context, shorter action history, faster humanized click glide |
| `chromveil-serialize-fast.patch` | Shorter APC labels → faster native agent perception |
| `chromveil-agent-step-wait.patch` | Faster agent re-observe delay (400ms → 220ms) |

## Apply order

1. Chromium checkout + `e:/chromiumfish/apply.sh` (all `patches/series` entries).
2. `bash fork/apply-chromveil.sh` (or from WSL: `/mnt/e/chromveil/fork/apply-chromveil.sh`).
3. `autoninja -C out/Release chrome`

Set `CHROMIUMFISH_ROOT` if your clone is not `/mnt/e/chromiumfish`.

## Your next custom patches

Add `fork/patches/my-feature.patch` and list it in `fork/patches/` (applied in lexical order). Keep **one upstream file per patch** (ChromiumFish rule) to reduce merge pain.
