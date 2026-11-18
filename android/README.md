# Shusha Nyavu. Android agent

Filters known phishing and advertising domains at the DNS level and reads incoming
notifications for suspicious links.

## Status, read this first

| Component | State |
|---|---|
| Project scaffolding, manifest, Gradle files | written, not compiled |
| `NotificationWatcher` (notification access) | written, not compiled |
| `NyavuVpnService` (DNS filter: UDP/53 only) | written, not compiled |
| `MainActivity` (two permission buttons) | written, not compiled |
| Blocklist generator and starter asset | written, generator not yet run at scale |

Nothing here has been built or run. It is a first cut so the work starts from a
compiling-shaped project rather than an empty folder. Expect to spend the first session
on Gradle and SDK versions.

## Build

The machine has the Android SDK but no Gradle wrapper. The fastest route is to copy
the wrapper from the OLPRS project, which already builds:

```powershell
Copy-Item C:\dev\OLPRS_V2_MOBILE\android\gradlew*        C:\dev\phishguard\android\
Copy-Item C:\dev\OLPRS_V2_MOBILE\android\gradle          C:\dev\phishguard\android\ -Recurse
cd C:\dev\phishguard\android
.\gradlew assembleDebug
```

The APK lands in `app\build\outputs\apk\debug\`. Sideload it; no store fee.

## How the two features work

**Notification access.** The user grants it in system settings, the app cannot read
notifications without it. The service receives each posted notification, looks for a
URL or for spam language, sends only the URL to Nyavu, and dismisses the notification
if the score exceeds 0.65.

**DNS filter.** A local VPN that routes nothing but the resolver address
(`10.111.222.1/32`) into the tunnel. Queries for blocked names are answered with
NXDOMAIN on the device; everything else is forwarded to an upstream resolver. Because
only the resolver route goes through the tunnel, the rest of the phone's traffic is
untouched, no data leaves the device and no remote VPN server exists.

## Known gaps

- TCP DNS, DNS-over-TLS and IPv6 are not handled; a resolver using them bypasses the filter.
- The blocklist is loaded once at start-up; regenerating it needs a service restart.
- No UI for the counters yet; `Counters` records them.
- `10.0.2.2` is the emulator's alias for the host machine, a physical phone needs the
  laptop's LAN address, set as `apiBase` in the `nyavu` preferences.

## Before the demonstration

Run it on a real phone with a real blocklist for a week first. A VPN that misroutes
traffic leaves the phone without internet, which is a worse demo than not showing it.

---

## 0.9.0, the first pass at matching the site

The app was still wearing the mint the website retired, and its verdict screen was four
lines of default Android text. This pass brings the two closer, without pretending the app
is a webview: it is a native screen, rebuilt with Android widgets.

What changed:

- **one palette**, in `NyavuTheme.kt`: sage for the accent, bone for anything you press, a
  serif for written matter, monospace for figures and addresses. A screen cannot drift back
  to the old mint because the colours are declared once
- **the verdict says what the site says**: "This one is worth avoiding", "Worth a second
  look", "This reads as ordinary", with the risk out of a hundred as a figure and a quiet bar
  rather than the old glowing dial
- **the reasons are rows**, numbered and explained, under the heading the verdict earned
- **the explanation folds** behind a plus, exactly as it does on the site
- **buttons are bone**, dark text on light, the way the site's primary action is written

What was removed, as asked:

- **the DNS filter**: its card, its tile, its VPN service declaration and its two foreground
  service permissions. The built APK now asks for INTERNET and nothing else. `Shusha.kt` still
  contains the service class, unused and unreferenced, so the decision is easy to reverse

What is not done yet:

- the address is shown as one string, not dissected into pieces with notes the way the site
  does it. That is the next piece of work, and it needs a layout that survives a narrow phone
- nothing here has been run on a device. It compiles, the APK installs nothing unusual, and
  the screen order is right, but only a hand on a phone can confirm how it feels


---

## Parity with the web app, 0.9.2

Written down plainly, because "ported" is doing a lot of work in a sentence.

**In the app now**

- the palette: sage, bone for actions, serif for written matter, mono for figures and addresses
- the verdict screen in the product's voice: the headline, the risk out of a hundred with a
  quiet bar, numbered reasons, and the explanation folded behind a plus
- the **address dissected** into scheme, name, ending and path, each with the note the site
  puts under it, and the reading line underneath. Client-side, no network call, same wording
- branding: the name Nyavu, a net drawn as the launcher icon, and nothing else

**Still only on the web**

- the **examination as an event**: the cursor that writes the address and then reads it from
  the right. The app shows the dissection complete, without the performance
- sample addresses, bulk screening, the history screen and optional accounts
- the model page with its comparison table, the printable verdict, and the router that makes
  the site three screens rather than two

So: the verdict is ported, the examination is shown but not performed, and the rest of the
product is absent. Anyone comparing the two side by side will see that immediately, and this
paragraph exists so the README does not pretend otherwise.


---

## 1.0.0: the four screens

The app is no longer a home screen with a link field. It is the product, with the same four
screens the site has and the same words:

| screen | what it does |
| --- | --- |
| Detector | paste or tap a sample, analyse, and the verdict arrives as a dialog over the screen: headline, the address dissected, the number, the reasons and the working folded behind a plus |
| Bulk | one address per line, up to two hundred, screened in one request against the same endpoint the site's file upload uses |
| History | the account's recent checks; a visitor without an account is told what the service says, that history needs a sign-in |
| Model | the three classifiers compared, with the deployed one marked, and the held-out numbers beneath |

The share sheet still works: share a link to Nyavu and the verdict appears.

Performance and comfort tweaks, kept minor: screens are built on demand and discarded when
another tab is chosen, network work is off the main thread, the bulk request sends one
multipart body rather than two hundred calls, and the cookie jar is one preference string so
a session survives between screens.

Known gaps, stated rather than hidden: the examination is shown as a finished dissection
rather than performed with a cursor, and sign-in opens the website rather than a native
Google flow.


---

## 1.1.0: the shared mark, and motion

**One icon.** `tools/make_icon.py` draws it once and writes every size: five Android
densities, the two manifest icons, the favicon and the Apple touch icon. A net rather than a
grid: warps and wefts that sag, stretched about a tenth vertically, with a knot at every
crossing and larger knots at the corners so the vertices read as bullets.

**Motion, which the app had none of:**

- the tab screens cross-fade and rise by ten pixels when you switch
- buttons dip under the finger
- the working line breathes while a check is in flight, instead of standing still
- the verdict opens at 97 per cent and settles, its risk bar fills over 720 ms, and the
  reasons rise in sequence rather than appearing all at once
- the examination types each piece of the address, then reads the notes from the ending back
