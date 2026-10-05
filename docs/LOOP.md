# Continuation loops

## Local 5s health loop (recommended)

Does **not** wake Cursor every 5s (avoids notification spam). Logs pytest summary to `~/.chromveil/loop-health.log`:

```powershell
cd E:\chromveil
.\scripts\loop-health.ps1          # default 5s
.\scripts\loop-health.ps1 -Seconds 30
```

Stop with Ctrl+C in that terminal.

## Agent loop (Cursor)

Use a sane interval, e.g. `/loop 30m continue ChromVeil goal per NEXT_PHASE.md`. A **5s** agent loop is possible but will flood notifications; prefer `loop-health.ps1` for fast local cadence.
