# The examination, as considered work

A prototype, not shipped. `app/static/sim/examine.html` plus `examine.js`, reachable at
`/sim/examine?url=...`, unlinked from the product.

## What it is trying to do

Make the moment between pressing Examine and seeing a verdict read as *work being done on the
address*, rather than a spinner and then a card. The user's brief: it should feel like Nyavu is
reading, measuring, weighing and then writing the verdict, including the card itself.

## The rule that keeps it honest

**Pacing is designed. Content is not.** Every number, measurement, probability and reason on the
page is read out of the `/api/predict` response. Nothing is generated, invented or embellished to
look busier. The page says so at the bottom, and the "How this is done" panel lists the four real
stages: parse and reduce, measure seventeen things, score with a logistic model, turn the
strongest contributions into reasons.

That distinction is what separates this from a fake "thinking" animation. The system genuinely
computes each value shown; the choreography only decides when each real value appears. It is a
logistic regression reading measurements, not a deliberating agent, and the wording avoids
claiming otherwise.

## What the research said

From AI loading-state guidance ([ai-loading-ux](https://github.com/shipshitdev/library/blob/366150f6ff4abf908164df8b94a6a49d65f46295/bundles/frontend/skills/ai-loading-ux/SKILL.md))
and the Doherty threshold work:

- **Something to watch makes a wait feel shorter**, even when the wait is unchanged
- **Show the current step and what has finished**, not an opaque spinner
- **Reasoning is collapsed by default** and expandable, because more transparency is not the same
  as better experience
- **Signal completion clearly**
- **Under about 400 ms feels instant**, so anything slower needs to look like progress

The prototype applies all five: a phase line that names what is happening, real measurements
arriving one at a time, reasoning behind a closed panel, and an explicit Done state with the
elapsed time.

## The choreography

| phase | what appears | source |
| --- | --- | --- |
| reading | the address types itself, uneven cadence, extra pause at dots and hyphens, an occasional hesitation | the address the user gave |
| naming | the registered name is underlined inside the address | `host`, `domain` from the response |
| measuring | seventeen chips arrive in the extractor's own order, the ones that raised the score lit | `features` |
| weighing | the score climbs to the model's probability in four decelerating steps | `probability` |
| writing | band, headline, then each reason in turn | `verdict`, `risk`, `reasons` |

The request is sent **before** the typing starts and awaited only after it finishes, so the
animation runs *during* the network wait rather than after it. Measured end to end: **6.7
seconds**, against roughly seven for the current examination. The choreography does not add
latency; it fills latency that already exists.

## Measured behaviour

Run against the live service, captured at four moments:

- 17 measurement chips, 3 reasons, score 100, no console errors
- total 6.7 s, page fits 1,035 px at 760 px wide
- "How this is done" collapsed by default
- the figure is the model's, not the animation's: `safaricom.co.ke` produces 15, not 100

## Where it could mislead, and the guardrails

1. **"Thinking" is a metaphor.** The model computes; it does not deliberate. Wording must stay at
   "reading, measuring, weighing", which describe computation, and never "considering", "deciding
   after weighing the possibilities", or anything that implies judgement beyond the coefficients.
2. **Speed can imply more work than happened.** The status line therefore counts real work
   ("measuring 6 of 17"), not decorative steps.
3. **A slow connection must not look like deep thought.** If the response has not arrived when the
   measurements are exhausted, the phase line should say "waiting for the service" rather than
   looping fake progress.

## Decision needed

Ship it as the main examination, ship it behind a "watch Nyavu work" affordance, or keep it as a
prototype. It costs no extra latency and no extra storage, and it removes the spinner. The risk is
wording drift, which the three guardrails above are meant to contain.

## Data work this suggests

The measurement phase makes the feature set visible, which makes its poverty obvious: seventeen
values from the name alone. Two corpora are needed to broaden it, and the shape of both is now
clear:

- **phishing with paths**: already on disk, 789,054 URLs in `data/raw/phishing_database_active.txt`
- **legitimate with paths**: obtainable from the Common Crawl index. Probe confirmed it returns
  real deep URLs for a domain (`https://www.safaricom.co.ke/robots.txt` and so on) without
  crawling anything ourselves

With both classes carrying paths, path and query features stop being leakage and can be measured.
That is the next experiment, and it is now unblocked.
