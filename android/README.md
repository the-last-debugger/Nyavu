# Shusha Nyavu — Android agent

Filters known phishing and advertising domains at the DNS level and reads incoming
notifications for suspicious links.

## Status — read this first

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

**Notification access.** The user grants it in system settings — the app cannot read
notifications without it. The service receives each posted notification, looks for a
URL or for spam language, sends only the URL to Nyavu, and dismisses the notification
if the score exceeds 0.65.

**DNS filter.** A local VPN that routes nothing but the resolver address
(`10.111.222.1/32`) into the tunnel. Queries for blocked names are answered with
NXDOMAIN on the device; everything else is forwarded to an upstream resolver. Because
only the resolver route goes through the tunnel, the rest of the phone's traffic is
untouched — no data leaves the device and no remote VPN server exists.

## Known gaps

- TCP DNS, DNS-over-TLS and IPv6 are not handled; a resolver using them bypasses the filter.
- The blocklist is loaded once at start-up; regenerating it needs a service restart.
- No UI for the counters yet; `Counters` records them.
- `10.0.2.2` is the emulator's alias for the host machine — a physical phone needs the
  laptop's LAN address, set as `apiBase` in the `nyavu` preferences.

## Before the demonstration

Run it on a real phone with a real blocklist for a week first. A VPN that misroutes
traffic leaves the phone without internet, which is a worse demo than not showing it.
