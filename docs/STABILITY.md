# Browser stability & staying unblocked

Sites do not see “Chrome” — they score **sessions**. ChromVeil optimizes for a **consistent, returning browser** with fewer automation tells.

## What sites actually check

| Signal | Why it matters |
|--------|----------------|
| **IP / ASN reputation** | Datacenter & VPN ranges get harder WAF rules (FanDuel CloudFront, etc.). |
| **TLS + HTTP/2 fingerprint** | Must match a real Chrome build (system Chrome helps). |
| **Cookie & storage age** | Fresh empty profiles look like bots; returning `user-data` looks human. |
| **Fingerprint consistency** | Same viewport, lang, timezone across visits — not random every 10s. |
| **Headless tells** | `HeadlessChrome` UA, `navigator.webdriver`, zero plugins, tiny `outerWidth`. |
| **Behavior** | Instant navigation, no scroll, 0ms between pages. |
| **Challenge completion** | Cloudflare “Attention Required” must be waited out, not classified as final failure. |

ChromVeil cannot fix bad IP alone — use residential egress when books hard-block.

## What ChromVeil does

1. **Sticky session** (`CHROMVEIL_STICKY_SESSION=1`, default on)  
   Per-host profile under `~/.chromveil/sticky/<hash>` — cookies and local state survive runs.

2. **Challenge wait** (`wait_for_challenge_clear`)  
   Collect/visit wait up to ~40s for CF interstitials before marking failure.

3. **Block classes**  
   - `challenge` → wait/retry  
   - `soft_error` → brief retry (e.g. BetOnline “Internal Error”)  
   - `hard_block` → rotate only if not sticky (geo, CloudFront 403)

4. **Headless**  
   - `--headless=new` + headless stealth args  
   - `CHROMVEIL_HEADLESS_SYSTEM_CHROME=1` (default): use installed Google Chrome when headless  
   - **Patchright** driver (default when installed) for `navigator.webdriver`  
   - `stealth_init.js` on every context (webdriver, chrome stub, outer window size)

5. **Identity rotation** (`CHROMVEIL_ROTATE_IDENTITY`)  
   Off while sticky — viewport/lang no longer change every open for the same book.

## Recommended env (headless sportsbooks)

```powershell
$env:CHROMVEIL_HEADLESS='1'
$env:CHROMVEIL_DRIVER='patchright'
$env:CHROMVEIL_STICKY_SESSION='1'
$env:CHROMVEIL_ROTATE_IDENTITY='0'
$env:CHROMVEIL_HEADLESS_SYSTEM_CHROME='1'
$env:CHROMVEIL_LIGHT='1'

chromveil collect "https://www.bet365.com/#/HO/" --all --settle-ms 12000 -o out.json --compact
```

Run **twice** on the same host — second visit often passes WAF because `_cf` / session cookies exist.

## Staying on a site “as long as you want”

- Use **`chromveil open`** or MCP with **sticky** profile (same host).  
- Do **not** call `clone_fresh_session()` between actions on one book.  
- Prefer **headed** for first login/geo clearance, then headless with same sticky dir.  
- Set `CHROMVEIL_PERSIST_PROFILE=1` + `CHROMVEIL_PERSONA=mybook` for a named long-lived profile.

## When you are still blocked

- **FanDuel / some US books**: IP-level — need US residential or manual browser export cookies.  
- **bet365 Cloudflare headless**: retry with sticky + system Chrome; use headed once to seed profile.  
- **Patched ChromiumFish** (when built): best probe scores for strict anti-bot.
