# Shusha Nyavu, browser extension

Warns before a phishing page loads. Every top-level navigation has its host scored by
the Nyavu API; a flagged host raises a banner, or is blocked if you choose that mode.

## Load it

1. Start the API: `uvicorn app.main:app --port 8000` from the project root.
2. Edge: `edge://extensions` → Developer mode → **Load unpacked** → select this folder.
   Chrome: `chrome://extensions` → Developer mode → **Load unpacked**.
3. Open the toolbar popup → **Settings** → confirm the API address → **Test connection**.
4. Visit `http://mpesa.co.ke.verify-account.top/`, a red banner should appear.

## What it sends

Only the host name of a page you are already navigating to. No page content, no
cookies, no history. Verdicts are cached per host for six hours so a site is scored
once rather than on every request.

## Files

| File | Purpose |
|---|---|
| `background.js` | Navigation listener, API call, cache, banner injection, block mode |
| `popup.html/.js` | Current tab verdict, session counters, trust-this-site |
| `options.html/.js` | API address, warn-or-block mode, trusted hosts |
| `warning.html` | Interstitial shown in block mode |

## Before the demonstration

- Set **block** mode only if you have tested it; warn mode cannot break a page.
- Trust `google.com` and the university portal first, so a false positive cannot
  interrupt the demo.
- The counters reset when the extension is reloaded.
