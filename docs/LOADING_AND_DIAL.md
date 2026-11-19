# Loading states and the dial's arrival

Prototype on `feat/loading-and-dial`, not deployed. Two problems, two different bodies of
research, and an honest note about where deliberate delay is and is not acceptable.

## What the research says

**Response-time limits** ([Nielsen, 1993/2014](https://www.nngroup.com/articles/response-times-3-important-limits/)):

- **0.1 s**: feels instantaneous. No indicator needed.
- **1 s**: the user's flow is uninterrupted, but they notice the delay. Below this, an indicator
  is often worse than none, because it draws attention to a wait they would not otherwise feel.
- **10 s**: the limit for holding attention. Past this, a percent-done indicator and a way to
  interrupt are expected.

The page's own fetches take tens of milliseconds on a good connection and one to three seconds on
a poor one. So the correct answer is **not** a spinner on every route: it is a signal that appears
only when work is actually slow, and content-shaped placeholders where the shape is known.

**The labour illusion** ([Buell & Norton, Management Science](https://pubsonline.informs.org/doi/10.1287/mnsc.1110.1376))
finds that showing the work behind a result increases perceived value, which is the same reason the
examination helps. It is also the reason to be careful: adding delay that does not correspond to
work is manipulation, and it is visible as such when the delay and the result are unrelated.

**Skeleton screens** are preferred over spinners for content whose layout is already known,
because the eye is shown where the answer will arrive instead of a generic symbol of waiting.

## What was built

### The dial

The complaint was exact: the readout said **clear** before anything had been measured, and the
faded bands competed with the needle once it settled. Three changes:

1. **The dial is hidden until 900 ms before the needle moves**, then fades up over 0.95 s from
   `opacity 0` through a wrapper element. It arrives when it is about to be used.
2. **The readout is hidden until the sweep starts**, so the dial never appears to have answered.
3. **The bands fade to 0.05 once the reading settles**, so the bright arc and needle are the only
   thing that glows.

A stylesheet detail worth recording: older rules force the gauge's opacity and a 2.4 s transition
duration, so anything set on the dial itself was overruled and it stayed fully visible while the
script believed it was fading. The fade now lives on a wrapper, `.gauge-fade`, which no old rule
targets.

### Loading

| element | why |
| --- | --- |
| **transit bar** at the top | appears only while a fetch is in flight or a view is changing; covers the transition, the swap and the new view's data |
| **skeleton counters** | the two figures arrive as a shimmer in the shape of the number, not a spinner |
| **skeleton sparkline** | same reasoning: the shape is known |
| **arrival ease-in** | on first visit only, `main` eases from 0.62 to 1 over 0.45 s. It must never look blank: the shell and the skeleton are visible from the first frame |

The arrival fade is the only concession to "a page should load". It covers work that genuinely
happens on the first visit (fonts, shell, counters), runs once per session, and is measured in
hundreds of milliseconds rather than seconds.

## Measured

- transit bar visible about 1 s of a 9 s throttled load, and on a tab change within 120 ms
- skeletons visible about 3.3 s of that load, then cleared
- dial wrapper opacity 0 at 6.0 s, 1 at 8.6 s, readout armed at the sweep
- suite 17 of 17, no console errors

## Options not taken

- **A spinner on every route**: contradicts the 1 s rule and adds noise to fast paths.
- **A boot splash for a fixed second**: the labour illusion with none of the labour. It would test
  well for "feels like an app" and badly for honesty.
- **Percent-done on the examination**: the operation is 11 s but its internal progress is not
  linear or knowable, and the evidence beats a progress bar for the same purpose.

## Decision needed

Whether to merge. If yes, the file to watch is `app/static/app.js` around `render` and
`sweepNeedle`; the wrapper is the part that makes the fade work.
