# Backlog

Written on 17 November, rewritten on the evening of 18 November after the work below.
Live build: see the last commit.

## Open

### 1. Real device pass
The only item nobody has done, and the only one I cannot do. The seven second examination,
the smooth scroll after a scan, the phone layout and the verdict card at true size. Every
check so far has been headless Edge with scripted input.

### 2. Phone sign-in only
Google is live: client created, both values in Render, the start endpoint redirects with the
right callback, and the panel offers it. Phone remains unavailable because no SMS provider
is configured, which costs roughly a shilling a message in Kenya. Until one is set the
method reports itself unavailable rather than offering a dead end. See docs/AUTH.md.

### 3. Measurement
There is no analytics. The honest next step is aggregate counts only, no URLs: how many
scans a day, how deep people get, where they stop. That needs a privacy stance that
matches the product's promise, which is why it has not been bolted on.

## Defects found in places nobody had looked

- watching for these is the habit that has paid off all day: the harness lies before the
  product does, and features nobody exercises are where the lies hide
- bulk scan works: CSV with a header, plain lines, an unparseable row that degrades to
  error rather than failing the run, and an empty file that returns a readable 422
- the Render helper script failed silently on its first run: a bulk PUT of the environment
  is rejected with an empty 400, so the values were stored locally and never reached the
  service. It writes one key at a time now, which is the route that works

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
