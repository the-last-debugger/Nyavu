# Nyavu, product review

Assessment of identity, language, information architecture and mobile direction.
Written after inspecting the running application, the Android project, the extension
and the live deployment. Implementation follows approval; nothing below has been built
except where explicitly marked.

---

## 0. What is actually true right now

Verified against the deployment, not assumed:

| Claim | Reality |
|---|---|
| Database persistence | **Postgres (Neon), pooled, Frankfurt.** `/api/health` reports `"db":"postgres"`. Data survives redeploys, tested by forcing one. |
| `render.yaml` says `/tmp/nyavu.db` | **Stale and misleading.** It describes the pre-Neon architecture. The env var is overridden at runtime and unused when `DATABASE_URL` is set. |
| Inference cost | 289 ms in production, 12.9 ms local, after the optimisation. |
| Test suite | 11/11 against production. |
| Android | Native Kotlin builds and installs; share target registered but **unverified on a device**; DNS filter **unverified**. |
| Expo client | Prototype only. Not wired to the share sheet or the DNS service. |

**P1, correct `render.yaml`.** A file in the repository describing the wrong
architecture will mislead whoever reads it next, including a marker.

---

## 1. Product voice

Nyavu is **a careful observer**, not a guard dog. It looks closely, says what it sees,
and is honest about what it cannot see. The voice follows from that.

**Principles**

1. **State the observation, then the judgement.** "Three indicators usually seen in
   impersonation" before "this looks like phishing".
2. **Never overclaim.** No "safe", no "verified", no "protected". The strongest
   positive is "no warning signs found".
3. **Name the uncertainty once, plainly.** "Our model is right about three times in
   four" is better than a hedge in every sentence.
4. **Calm under pressure.** No exclamation marks, no "DANGER", no red alerts flashing.
   The colour carries the urgency; the words stay level.
5. **Short sentences. Concrete nouns.** "The address hides a bank name inside a
   different domain" beats "suspicious lexical patterns detected".
6. **Second person, sparingly.** "You pasted" is fine; "your security posture" is not.

**Terminology, fixed**

| Use | Not |
|---|---|
| inspect / examine | scan (except as a noun for a record) |
| verdict | result / outcome |
| indicators / evidence | features, signals (internally) |
| likely phishing / suspicious / no warning signs | dangerous / safe / clean |
| model score | confidence, certainty, probability of harm |
| reference list | verified domains, official registry |

## 2. Copy: current vs proposed

| Where | Now | Proposed |
|---|---|---|
| H1 | Check a link before you click it. | *(keep, it is good)* |
| Lede | Paste any URL. Nyavu scores it against a curated corpus and tells you *why* it looks dangerous. | Paste a link. Nyavu examines the address itself, never the page, and tells you what it noticed. |
| Button | Analyse | **Inspect link** |
| Scanning | Analysing… | **Taking a closer look…** |
| Scanning hint | *(none)* | Examining the address and domain indicators… |
| Verdict, high | This link looks like phishing | **Something doesn't look right** |
| Verdict, low | No phishing pattern detected | **No warning signs found** |
| Confidence | Confidence 100% | **Model score 99.98 · an estimate, not a guarantee** |
| Suggest | Did you mean X? The genuine Y site is much closer to this name. | **You may have meant X**, that address is in our reference list for Y. We cannot verify official sites; open it only if you trust the address you typed. |
| Reasons heading | Why | **Why Nyavu raised a concern** |
| Features heading | Computed features | **What the model measured** *(collapsed by default)* |
| History empty | No scans yet. | **Nothing inspected yet.** Links you check will appear here. |
| Bulk | Bulk URL screening | **Inspect a list of links** |
| Error | Error | **That link could not be read** + what to try |
| Sign in CTA | Sign in | **Keep a history** |

## 3. Information hierarchy of a result

Three layers, and only the first is guaranteed screen space:

**Primary, always visible, above the fold after a scan**
verdict in words · risk band · the needle · one sentence of advice.

**Supporting, visible, scannable**
why (up to five indicators) · the suggested destination, if any · host and model score.

**Advanced, collapsed behind a disclosure**
the seventeen measured values · evidence tokens with weights · inference time.

Today the advanced layer is rendered inline, which pushes the advice below the fold and
lets the needle animate off-screen. That is the single biggest usability defect.

## 4. The needle problem

**P0.** The result section sits below the scanner. On a 900 px viewport with the hero
present, a scan produces a verdict roughly 400 to 700 px below the fold: the needle sweeps
and settles where nobody can see it, and the user is left with the impression that
nothing happened.

**Proposed fix**

1. After a successful render, if the result's top edge is below the viewport, smooth-scroll
   so it lands just under the sticky header (offset = header height + 16 px).
2. Anchor on the verdict card, not the page top: the user keeps the Context of what they typed.
3. If the result is already visible, do not move the page at all. Never scroll when the user
   has deliberately scrolled elsewhere.
4. Honour `prefers-reduced-motion`: instant jump, and skip the needle sweep entirely
   (show the final value).
5. On mobile, the dial scales to 160 px and sits above the verdict text; the advice line
   becomes the second element, not the sixth.

## 5. Web: cohesion findings

**Works, keep:** dark identity, type system, orbital hero, needle, evidence cards,
reason list, responsive rules, honesty section on the landing page.

**Undermines the product:**

| Issue | Impact | Priority |
|---|---|---|
| Result below the fold | The product's best moment is invisible | **P0** |
| Advanced values inline | Verdict competes with 17 numbers | **P0** |
| "Confidence 100%" | Reads as certainty | **P0** |
| "The genuine safaricom site" | Implies verification we do not perform | **P0** |
| Nav labels ("Bulk scan", "Model") | Feature names, not user intentions | P1 |
| One page carries landing, tool, education | Crawlable but not navigable | P1 |
| No empty/error/loading copy beyond defaults | Generic where trust is built | P1 |
| Cards carry no data texture | Reads as statements, not instruments | P1 |

## 6. Armour.mobi, not inspected

**I have not reviewed it, and will not pretend otherwise.** No APK was attached to this
project, the Play Store cannot be inspected from this machine, and I have no device to
install it on. Anything I wrote about it would be invention.

**To proceed**, any one of these is enough: a screenshot set of its main screens, its
.apk file placed in the repository, or a short description of the three or four screens
you find most effective.

What I can say from your own description, "animated, moving parts, fun", is that the
quality you are reacting to is **liveness**: the sense that the product is doing
something continuous rather than waiting for input. That is achievable in Nyavu without
copying anyone's interface, and it is where I would aim the Android work.

## 7. Web vs Android today

| | Web | Android |
|---|---|---|
| Verdict | Full result, needle, evidence | Basic text screen, no needle |
| History | Table, private per account | Not implemented |
| Protection controls | None | DNS filter + VPN service |
| Share sheet | n/a | Registered, unverified |
| Identity | Distinct, polished | Default Material, branded tonight |
| Navigation | Four tabs, hash routes | Single screen |

The Android app has the capability the web does not, it can act at the moment a link
arrives, and none of the presentation. That inversion is the opportunity.

## 8. Which Android implementation is maintained

**Recommendation: native Kotlin. Retire the Expo prototype.**

- Kotlin already has the share target, the DNS service, the foreground-service handling
  and a published release. The Expo client has none of these and cannot have them without
  a native module.
- Two clients double every future change and split the identity.
- **Action:** move `expo-app/` to `archive/` and note in the README that Kotlin is the
  shipped client. *(P1, a decision, not a build.)*

## 9. Android information architecture

Five screens, one thumb-reachable primary action.

1. **Home**, shield state, one large "Inspect a link" action, last three inspections,
   protection status as a single honest line ("DNS filter off · manual inspection only").
2. **Result**, needle and verdict, three reasons, one action ("Open anyway" is never
   offered), disclosure for the measured values.
3. **Activity**, the account's inspections, newest first, verdict dot and time.
4. **Protection**, DNS filter switch with a plain statement of what it does and does not
   cover; QR inspection; trusted domains.
5. **About**, what Nyavu is, the 75.4%, the limits, privacy, version.

Navigation: bottom bar with four items (Home, Activity, Protection, About). Result is a
screen, not a tab.

## 10. Extension

Keep it to one job: a warning that interrupts at the right moment.

- Badge on the toolbar: neutral by default, amber for suspicious, red for likely phishing.
- One card, three lines: what was found, why, what to do.
- Never auto-block a tab silently. Offer "Leave this page" and "Continue, I understand".
- State the limit once: "Nyavu read the address, not the page."

## 11. Content placement

| Information | Web | Android | Extension |
|---|---|---|---|
| Verdict | Full | Full | One line |
| Needle | Full | Full, 160 px | None |
| Reasons | Up to 5, expanded | Top 3, expand for all | One |
| Measured values | Collapsed | Collapsed | Never |
| Model card | Full page | About screen | Never |
| History | Full table | Activity tab | Popup, last 5 |
| Education | Three pages | About | Never |
| Protection controls | Describe only | Primary | Settings link |
| Privacy | Detailed page | About | One line |

## 12. Roadmap

**P0, correctness and usability (do first, small, testable)**
1. Result scroll-into-view with header offset, reduced-motion aware.
2. Collapse advanced values behind a disclosure.
3. Relabel model score honestly; remove "confidence".
4. Rewrite the suggestion copy so it never implies verification.
5. Fix `render.yaml` to describe Postgres.

**P1, the experience**
6. Copy pass across all surfaces using the voice above.
7. Empty, loading and error states written properly.
8. Cards with data texture: sparkline in the stats strip, weight bars on evidence.
9. Shared-element transition from scanner to result.
10. Android: five-screen IA, needle in results, animated home.
11. Retire the Expo prototype from the active tree.

**P2, refinement**
12. Cursor-following light on cards; skeleton shimmer while scanning.
13. Extension warning card redesign.
14. Per-page navigation on the website (`/check`, `/learn`, `/about` in the header).

**Explicitly not doing:** new features, accounts for their own sake, third-party
analytics, dashboards of invented statistics, or any claim of protection Nyavu does not
provide.
