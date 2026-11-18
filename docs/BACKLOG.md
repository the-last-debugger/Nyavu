# Backlog

Written on 17 November, rewritten on the evening of 18 November after the work below.
Live build: see the last commit.

## Open

### 1. Real device pass
The only item nobody has done, and the only one I cannot do. The seven second examination,
the smooth scroll after a scan, the phone layout and the verdict card at true size. Every
check so far has been headless Edge with scripted input.

### 2. Sign-in keys
Google is free: create an OAuth client, set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.
SMS is not free: a Kenyan message is roughly one shilling on Africa's Talking and several
times that on Twilio. Until one is configured the phone method reports itself unavailable,
so the interface offers email only. See docs/AUTH.md.

### 3. Measurement
There is no analytics. The honest next step is aggregate counts only, no URLs: how many
scans a day, how deep people get, where they stop. That needs a privacy stance that
matches the product's promise, which is why it has not been bolted on.

## Done since the last rewrite

- styles.css: 6180 lines to 3448. The fishing theatre's rules are gone, the dead selectors
  are gone, and the verdict reveal is a keyframe animation that actually plays
- app.js: 1550 lines to 1174. Thirteen unreachable functions and three constant tables
  removed, brace matched, syntax checked after each
- fonts: Space Grotesk retired, four unused faces deleted, 45 KB of downloads saved
- imagery: contour plates, generated rather than photographed, now WebP at 65 KB instead
  of a 217 KB PNG
- the neon: replaced by sage, contrast measured at 7.95:1 rather than assumed
- public numbers: two figures at the door instead of four, the rest moved behind a sign-in
- copy: scoped claims, no absolutes, no fear framing
- score: the "15" was a reputation ceiling, not a probability, and the card says so
- input handling: bare words, private addresses, oversized input and credentials in the
  link are all handled and tested
- caching and 404: assets cached, the shell revalidates, a wrong address gets a page
- the harness: probes clear storage, unregister the service worker, declare motion, and
  the scratch files no longer shadow Python's standard library
