# The four fixes, and the honest answer on signals

Branch `feat/loading-and-dial`. Nothing deployed.

## 1 and 4. Where the detailed breakdown went

It was not a bug, but it became a loss. The one-line examination shows **one note at a time**, which
is right while it runs and wrong as a record: the complete reading existed only in the print
stylesheet. And the settled card showed a features grid of non-zero values only, so most of the
seventeen measurements disappeared once the verdict landed.

Both now live in **"How that was worked out"**:

- **The name, piece by piece**: every piece, its role and its note, in reading order.
- **What was measured**: all seventeen, zeros included, with the ones that moved the score marked.

Zeros are shown deliberately. "A known brand appears: 0" is evidence; hiding it makes the list look
like a fault count rather than a set of measurements.

## 3. The fold appeared before it was needed

`details.score-more` was visible while the answer was still being computed, offering to explain
something that did not exist yet. It is now `display: none` under `.result.pending` and appears with
the verdict. Verified: `display: none` at 3 s, present at the verdict.

## 2. Is the name really all we have?

No, and the measurements say the biggest remaining signal is the **rest of the address**. From the
789,054 phishing URLs on disk:

| what | count | share |
| --- | --- | --- |
| has a path | 596,184 | **75.6%** |
| path contains login/verify/secure/account/update/mpesa/safaricom | 147,187 | 18.7% |
| has a query string | 146,027 | 18.5% |
| punycode host | 889 | 0.1% |
| raw IP host | 9,128 | 1.2% |

The address after the name is present in three quarters of real phishing and invisible to the
current model, because the benign half of the corpus was harvested as bare domains. **That is a data
problem, not a permission problem.** Common Crawl returns real deep URLs for a domain without us
crawling anything (probe confirmed: `https://www.safaricom.co.ke/robots.txt` and similar). With
50,000 legitimate deep URLs, path and query features stop being leakage and can be measured.

What else exists, and what each costs:

| signal | value | cost |
| --- | --- | --- |
| path and query keywords | high, 75.6% presence in phishing | needs benign deep URLs |
| punycode / homoglyph / mixed script | already partly used; rare (0.1%) | free, already offline |
| brand list beyond the current 40 | measured: no gain, slightly worse F1 | free, already tried |
| offline reputation snapshot from public feeds | catches known phish immediately | staleness; also a different claim from "judged unseen" |
| DNS and certificate age | strong on fresh domains | a third-party lookup, so a footprint, even if not at the site |
| page content | the strongest of all | breaks the promise outright |
| message context, if the sender is known | high | needs an integration we do not have |

So the hands are not tied; the largest lever is simply not yet loaded. The ethical line stays where
it is: nothing is fetched, nothing is stored about the person. Path features respect that line
completely, which is why they are next.

## 5. Deployment

Nothing is merged or deployed. `main` is untouched. The gif to review is `docs/full-flow.gif`.
