# What the number should say

Dr Komen's question is the right one, and there are two different confusions tangled in it. Only
one of them is about the model.

## Confusion one: the number means two things

For `safaricom.co.ke` the screen said **15**. That is not the model's estimate. The model said
**22**; the reputation prior held it at 15 because the domain is in the Tranco top 100,000. So
the same figure is sometimes a probability and sometimes a policy ceiling, and nothing on screen
said which. A reader reasonably concludes "fifteen things are wrong with this site".

That is a design error, not a model error, and it is worth fixing before the report is rewritten.

## Confusion two: people do not read percentages the way we expect

Two pieces of evidence, from different fields:

- SAP's design guidance for explainable AI recommends **confidence categories rather than
  percentages**, and gives the reason: *"People interpret confidence percentages differently,
  depending on their character and mood and the current situation. Some users might reject
  predictions with a relatively high confidence rating (like 84%). Others will go with a proposal
  despite a much lower confidence rating (like 64%)."* ([SAP Fiori, Explainable AI](https://www.sap.com/design-system/fiori-design-web/v1-96/foundations/ai-and-joule-design/guidelines/explainable-ai))
- In risk communication, **natural frequencies beat percentages**: "about 1 in 5" is understood
  more accurately than "22%", particularly by people with lower numeracy
  ([study of verbal descriptors, percentages and natural frequencies](https://pubmed.ncbi.nlm.nih.gov/18992183/)).

The same guidance says explanations should be progressive: an indicator first, the reasoning on
demand, the detail for auditors. We already have that shape, with one fault: the indicator is a
number.

## What not to do

**Hard 0 and 100 is the one option to reject.** It would claim certainty the system does not have.
The model is wrong about one address in four on a domain-disjoint hold-out, and the false-positive
rate is 19.8 per cent. A tool that prints `0` for a site it has never seen is making a promise it
cannot keep, and `100` would be equally indefensible. It would also erase the middle band, which
is the honest and useful part: "this looks odd, check before you click".

There is a second cost. A marker will ask how the figure was produced. "It is a probability with
a measured calibration error of 0.028" is a strong answer. "We clamp it to 0 or 100" is not.

## What to do instead: verdict first, number underneath

| layer | what the reader sees | what it is |
| --- | --- | --- |
| indicator | **Likely legitimate** pill, a headline, one sentence | the decision, in words |
| reasoning | the dissection and the reasons, as now | why |
| detail, behind a fold | "about 1 in 5", the band legend, the model estimate | the measurement |

Three changes from today:

1. **The pill and the sentence lead.** The headline already exists; the number stops competing
   with it.
2. **The number moves under "How that was worked out"**, and is expressed as a frequency first
   ("about 1 in 5"), with the percentage beside it for anyone who wants it.
3. **A capped verdict never shows a bare percentage.** For an allowlisted domain the card says
   "an established domain, held clear by reputation", and the details show the model's own
   estimate separately. That removes the two-meanings-under-one-number fault entirely.

None of this hides anything. Every fact on the current card survives, in the order a
non-specialist reads: verdict, reason, evidence.

## The "standard measurement" answer for Dr Komen

Worth putting in the report, on the model page, and in the defence:

> The standard measurement is the model's estimated probability that the address is phishing,
> reported from 0 to 100. On a domain-disjoint hold-out of 3,573 addresses the probability is
> calibrated, with an expected calibration error of 0.028 and a Brier score of 0.167, so a stated
> 80 is observed about 80 times in 100. Bands are drawn at 35 and 65. A domain in the Tranco top
> 100,000 is held at 15 by a reputation prior, because name-level evidence is not enough to flag a
> site that is demonstrably used; when that applies, the card says so and reports the model's own
> estimate separately.

That single paragraph answers both of his questions: what the number is, and why Safaricom is not
zero.

## Cost, honestly

| work | size |
| --- | --- |
| card restructure: pill and sentence first, number folded | small, one component, no API change |
| frequency wording and band legend | a few strings |
| capped case: badge plus separate model estimate | already in the API as `model_probability` and `capped_by_reputation` |
| print layout | the printed card keeps the number, since paper has no fold |
| report | one paragraph in 4.5 and one on the model page, in next week's rewrite |
| tests | the suite checks verdicts and the cap flag, not the wording; one string may need updating |

The binary option is not cheaper. It is a smaller code change and a much larger defence burden,
because it makes a claim the system cannot support.

## Recommendation

Option 3, the verdict-first card. It answers Dr Komen without a new measurement system, removes
the two-meanings fault, keeps the calibrated number for anyone who wants it, and requires no
model change and no new paperwork beyond one paragraph.

`docs/score-options.png` shows the three side by side, rendered from
`/sim/score-options.html`.
