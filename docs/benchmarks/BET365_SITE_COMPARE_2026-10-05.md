# bet365 stack comparison (headed, Windows)

**Command:** `CHROMVEIL_AUTO_FETCH=0 chromveil bench site --url https://www.bet365.com/ --headed`

**Report:** `reports/site-https_www.bet365.com_-20261005-092227.json`

**Environment:** No `CHROMVEIL_EXECUTABLE` (custom/patched engine not installed). System Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`.

## Variants tested

| # | Stack | Executable | Navigate (ms) | Stealth score | `navigator.webdriver` |
|---|--------|------------|---------------|---------------|------------------------|
| 1 | Playwright stock | Bundled Chromium | 763 | **0.83** | **true** (leaked) |
| 2 | Patchright stock | Bundled Chromium | 773 | 1.00 | false |
| 3 | Patchright + manual Chrome | Google Chrome stable | 640 | 1.00 | false |
| 4 | ChromVeil + Playwright | Bundled + stealth argv | 671 | 1.00 | false |
| 5 | ChromVeil + Patchright | Bundled + stealth argv | **548** | 1.00 | false |

All five reached the bet365 title page (`Bet with bet365 – …`) at `https://www.bet365.com/` with no HTTP errors. `body_chars` was 0 for all (heavy client-side app; DOM text not in `body.innerText` at probe time).

## Takeaways

1. **Playwright alone is the weak link** on bet365 for automation signals: stock launch left `navigator.webdriver === true` (score 5/6). Patchright stock fixed that without extra flags.
2. **ChromVeil launch tuning on Playwright** brings Playwright to parity (1.0 score, `webdriver` false) via stealth argv + `ignore_default_args` — same class as Patchright.
3. **Patchright + system Chrome** is slightly faster than stock Patchright bundled build (~640 ms vs ~773 ms navigate) with identical probe scores.
4. **ChromVeil + Patchright** was fastest in this run (~548 ms) while keeping a 1.0 probe score — tuned flags + Patchright’s driver stack.
5. **True custom Chromium** (ChromiumFish / patched `CHROMVEIL_EXECUTABLE`) was **not** in this run; engine-level fingerprint hardening is untested here. Set `CHROMVEIL_EXECUTABLE` and re-run to compare binary vs launch-only tuning.

## Re-run

```powershell
cd E:\chromveil
$env:CHROMVEIL_AUTO_FETCH='0'
chromveil bench site --url "https://www.bet365.com/" --headed -o reports

# With patched binary when available:
$env:CHROMVEIL_EXECUTABLE="C:\path\to\chrome.exe"
chromveil bench site --url "https://www.bet365.com/" --headed
```
