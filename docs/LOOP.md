# Continuation loops

## Local 2s health loop (recommended)

Does **not** wake Cursor (avoids notification spam). Logs pytest summary to `~/.chromveil/loop-health.log`:

```powershell
cd E:\chromveil
.\scripts\loop-health.ps1          # default 2s
.\scripts\loop-health.ps1 -Seconds 5
```

Stop with Ctrl+C in that terminal.

## Agent loop (Cursor)

Prefer **30m+** for agent-driven continuation. A **1–2s** agent loop will flood notifications; use `loop-health.ps1` for 1–2s local cadence instead.
