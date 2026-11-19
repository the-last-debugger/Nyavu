# Backlog

Written on 17 November, rewritten on the evening of 18 November after the work below.
Live build: see the last commit.

## What the evening of 18 November settled

- **the verdict is a native dialog.** A fixed div is only above the page while its z-index
  wins inside its stacking context, and one transform on an ancestor buried it under its own
  backdrop. `showModal()` puts it in the browser's top layer, which cannot be covered.
  Verified with a transformed ancestor wrapped around the detector, which is the case that
  previously hid the card
- **assets carry a content hash.** Two deploys can no longer meet on one page. That mismatch
  is what produced a black screen with a blurred backdrop: a new script opening an overlay
  whose styles the old stylesheet did not contain
- **the page can tell it is stale** and says so, because a service worker answering a cold
  start from cache is how the mismatch reached a real browser
- **the backdrop is a scrim, not a blur.** Full-viewport `backdrop-filter` smears on some
  Windows compositors, and the smearing was reported twice as "blur everywhere"
- **the cursor types the notes.** Reading from the right, the caret arrives, then the note is
  written where it stopped
- **a verdict can be printed.** Nothing styled the page for paper before; the print rules
  produce a document with the verdict colours kept and a credit line
- **dialogs answer to Escape** and the verdict traps focus, which neither did before

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

---

## Detection depth: what was measured, and what it says

The question was whether detection can go beyond reading the name. To answer it without
guessing, two corpora were gathered and one rule was built and measured.

**Real phishing, 41,811 unique URLs** from OpenPhish and PhishTank, saved at
`ml/eval/phishing_feed_urls.txt`. Prevalence of the structural patterns in that set:

| pattern | appears in | share |
| --- | --- | --- |
| long base64-looking parameter | 2,197 | 5.25% |
| another address inside a parameter | 861 | 2.06% |
| more than four labels before the name | 218 | 0.52% |
| downloadable payload extension | 2 | 0.005% |

**Legitimate wrappers, 35 real shapes** at `ml/eval/benign_wrappers.txt`: Google, Outlook
SafeLinks, Facebook, LinkedIn, DoubleClick, Bing, DuckDuckGo, WhatsApp, GitHub releases,
MPESA statements, a Moodle deep link, an S3 object, a CDN path. These exist because a naive
rule would flag them, and flagging them would be worse than missing the phish.

**The rule.** Nested address or long encoded parameter, skipping known wrappers, then
lifting to medium only when the model already scored above 0.25. Result: **0 false
positives on the 35 wrappers**, and it moved **2 of 1,500** sampled phishing URLs, because
the model had already decided the rest.

**Conclusion.** The patterns are real and common, but as a conjunction they change almost
nothing, and alone they would put legitimate redirects at risk. So they are reported as
reasons and do not score. To overturn that, the missing corpus is legitimate redirects at
scale, not more ideas.

---

## Queued: the report, against Chapter One

A full comparison is written at `docs/REPORT_REVIEW.md`. The short version:

**Queue first: merge Chapter Five into Chapter Four.** That is the supervisor's instruction
and it is also a de-duplication, because 4.9 already reports the tests that 5.4 describes and
4.13 already carries the conclusions that 5.5 repeats.

**Then correct four contradictions**, each of which a marker would find before anything else:

| claim | what the artefact says |
| --- | --- |
| 5.5: "26,202 addresses" | 17,730 (14,157 train, 3,573 hold-out) |
| 5.5: "all four specific objectives" | there are three |
| 1.7: "does not implement browser or OS integration" | an extension and a native app exist |
| 5.6: extension listed as future work | already built |

**The one objective not yet met is III's second half**: "the clarity of the explanations it
presents to non-expert users". Accuracy is measured; clarity is not. 5.6 admits the feedback
was informal and 5.5 claims the objective was met anyway.

Two ways out, and the first is the better one:

1. run the test: eight to ten non-experts, five addresses across the three bands, three
   questions each (verdict, reason, action), and report comprehension as a proportion
2. if no participants can be found, say plainly that clarity was reviewed by design and
   informal feedback, not measured with representative users, and mark III partially met

Nothing in this queue needs a code change. It needs an afternoon, a printed form and people
who are not on the team.

---

## The emulator, and why the app still has no screenshots

An Android emulator was installed to close the last verification gap: the app has never been
seen running. It does not start in this environment, and the evidence is unambiguous.

- **WHPX path**: the emulator initialises, prints `Windows Hypervisor Platform accelerator is
  operational`, then exits with no error, no crash log and an empty exit code. Reproduced with
  hardware and software rendering. This is the signature of the sandbox blocking the named
  pipes QEMU needs, the same restriction that stopped ADB writing its log into the temp folder
  until the folder was redirected.
- **Software path** (`-accel off`): the process stays alive and ADB sees `emulator-5554`, but
  the device never leaves `offline`, and after twelve minutes the process has used 0.17
  seconds of CPU. It is not booting slowly; it is not executing.

What is installed and ready, for a terminal outside this session:

```
$env:ANDROID_EMULATOR_HOME="C:\dev\_tools\android\emu-home"
$env:ANDROID_AVD_HOME="C:\dev\_tools\android\avd"
C:\Users\tuyaa\AppData\Local\Android\Sdk\emulator\emulator.exe -avd nyavu
```

The AVD is a Pixel 5 profile on Android 11 with the light ATD image, and the screenshot
harness is at `C:\dev\_tools\android\run-apk.ps1`.

Until then, the app's verification stops at: it compiles, `aapt` confirms the label, icon and
permissions, and the interface is reviewed by reading it. Everything about how it feels is
still a judgement only a running device can make.

---

## The app: a worklist before more code

Two attempts at the Android app failed the same way: they reproduced the web layout on a
phone instead of redesigning for the platform. Expo's migration guide is blunt about it —
*"if it still feels like a website, you ported instead of redesigned."* The Kotlin app was
rigid because every screen assembled itself from literals in view constructors, and the first
React Native pass reskinned the same cards and a text caret drawn as a `|` character.

`docs/MIGRATION.md` now holds the worklist: twelve surfaces bucketed as nativize-now,
nativize-later, port-as-is or drop, with the reasoning for each and what "done" means.

The decision that orders everything: **the examination is the product**, so it is built first
and built for the phone — full-bleed, one character per measured position, a real caret that
springs between them, haptics as each piece lands, then the notes read from the ending
backwards, then a native sheet for the verdict.

Three things are deliberately not carried over: the model page (a comparison table is a web
page), the printable verdict (a phone shares instead), and CSV header handling.

---

## For the presentation: what to say about the app

The Android application is **out of scope**. The supervisor confirmed it is not required now
that the installed web application covers the mobile case. Two builds exist:
a Kotlin app published at `dist/Nyavu-1.3.4-debug.apk`, and a React Native port with the
examination, verdict sheet and shell that has never run on a device. Neither should be claimed
as delivered.

What *is* delivered on a phone is the progressive web application: installable from the live
site, styled for the phone, with the examination and the verdict at full size.

The status report for review is `docs/REPORT_STATUS.md`: objectives, measurements, what is
delivered, and the four things that are not.

---

## The model, measured (19 November)

`docs/MODEL_IMPROVEMENTS.md` now holds the full analysis and the agenda. The four numbers that
change how this project should be discussed:

1. **The percentage is honest.** ECE 0.028, Brier 0.1674. When the interface says 80, about 80
   of 100 such addresses are phishing. This claim is stronger than the accuracy headline.
2. **Domain-level recall is 0.690, not 0.705.** Rows repeat domains; the row figure flatters.
3. **What decay costs is precision, not recall.** On 1,774 fresh rows drawn from a large
   phishing dump and Tranco ranks 100k-1M: recall holds at 0.703 against 0.705 on the 2025
   hold-out, while false alarms rise from 0.198 to 0.268 and AUC falls from 0.829 to 0.792. An
   earlier figure of 0.570 came from 86 live-feed domains and is sampling noise; both runs are
   kept in the repository so the correction is visible.
4. **The reputation ceiling has a 17.4 per cent blind spot.** Fifteen of 86 phishing domains in
   today's feed sit inside the top-100k allowlist, where the cap reports them at 15 or less.

What was tried and did not work, so nobody repeats it: a bigger brand list (no gain), character
shape features (+0.36 points in-domain, zero on today's data), a benign-likeness feature
(worse), gradient boosting without n-grams (much worse). What is blocked: path and redirect
features, because the corpus contains no paths at all.

The ordering that follows: retrain on a schedule with a frozen baseline, curate the negative
class so the false-positive rate measures the model rather than Tranco, then acquire a benign
corpus with paths. The privacy decision on measurement is also the retraining decision, since
continuous improvement needs recent outcomes and the service stores none by design.

### Retraining is hygiene, not improvement

Measured: training on 2,000 additional fresh rows moved fresh-set F1 from 0.7199 to 0.7196 and
AUC from 0.792 to 0.805, while dropping the old corpus cost four points on the old hold-out. The
information in a domain name is the binding constraint, not the age of the corpus.

`/api/stats/daily` now carries `mean_probability` and `flagged_share` per day, computed from
columns the scans table already had, so drift is visible as a series rather than a debate.
Retraining stays on the calendar, with the frozen baseline kept for comparison.

### The host has a memory budget, and it is now measured

Free tier: 512 MB and a tenth of a CPU. Loading the model and scoring twenty addresses costs
169.8 MB with pandas installed and 143.7 MB without, so pandas left the runtime requirements
(it was only ever used to build a one-row frame) and moved to `requirements-train.txt`. The
scores are identical to the last bit on 306 addresses. That rules out loading a transformer or
a second model into the same process on this tier.

### Shipped since: no-account history, drift series, leaner service

Three changes made on the assumption that most visitors will never sign in, and that the host
is small.

1. **Device-only history.** Every successful scan is also kept in the visitor's own browser,
   capped at twenty-five, and shown when the account has nothing to show. Nothing is posted and
   nothing is keyed to a person. A Forget control removes the list from storage as well as from
   the view. Verified in production: two scans, two rows, survives a reload, Forget empties
   both.
2. **Drift is a series now.** `/api/stats/daily` returns mean probability and the share flagged
   per day, from columns the scans table already had. No schema change. A rising series is the
   earliest visible failure, and it costs nothing to look at.
3. **pandas left the runtime.** It was imported only to build a one-row frame. Calling the two
   fitted transformers directly removed it: 169.8 MB to 143.7 MB of peak working set, identical
   scores on 306 addresses. Test suite is 17 of 17, including the new drift case.

**Known mismatch, for the record.** The submitted report's Figure 9 shows the signed-out history
as an empty prompt. That is still what a first-time visitor sees, but a returning visitor now
sees rows, so the figure and the sentence above it are no longer the whole truth. If the report
is ever resubmitted, both need updating.
