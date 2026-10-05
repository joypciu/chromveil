# Intelligent API collect

Open any URL with ChromVeil stealth, record **XHR/fetch** responses, drop analytics/ads/static noise, and return JSON the user asked for.

## CLI

```powershell
chromveil collect "https://www.betonline.ag/sportsbook" --headed --want odds,events,markets -o report.json

chromveil collect "https://www.bet365.com/#/HO/" --want sports,fixture --url-pattern "bet365|sportsbook"

chromveil collect "https://www.betonline.ag/sportsbook" --headed `
  --ask "What betting markets and odds APIs loaded?"
```

Natural language `--ask` uses your LLM (`CHROMVEIL_LLM_URL` / Ollama) to pick keywords and write a short **Answer** section. Set `CHROMVEIL_COLLECT_LLM=0` for heuristic-only mode.

WebSocket frames are captured when the site uses them (filtered like HTTP noise).
MCP tool: `collect_apis(url, want="", ask="")`.
```

| Flag | Purpose |
|------|---------|
| `--want` | Comma keywords — match API URLs or JSON keys/values |
| `--url-pattern` | Regex on captured API URLs |
| `--settle-ms` | Wait after load for SPA traffic (default 6000) |
| `--headed` | Headed browser (recommended) |

## Python

```python
from chromveil import collect_from_url

result = collect_from_url(
    "https://example.com",
    want="users,profile",
)
print(result.capture["apis"])
```

## What gets filtered out

Telemetry hosts (GA, GTM, Segment, Sentry, ad networks), beacons/pixels, and static assets (`.js`, `.png`, fonts). See `chromveil/intelligence/api_filter.py`.

## Limits

- Captures browser network only (not WebSocket binary unless extended).
- Large bodies truncated at 512KB per response.
- Sites with certificate pinning or isolated workers may hide some calls.
