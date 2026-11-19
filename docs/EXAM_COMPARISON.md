# Comparing the two examinations

Recorded from the same address, at the same viewport, starting at the moment the examination
begins. `docs/exam-comparison.gif` runs them side by side; `docs/exam-current.gif` and
`docs/exam-prototype.gif` are the individual runs.

## Measured

| | current | prototype |
| --- | --- | --- |
| recorded length | 8.2 s | 5.4 s |
| what the person sees while waiting | the dial counting, the address typing, the dissection notes filling in right to left, a skip control | one phase line, the address typing, then seventeen measurements arriving, then the score climbing |
| where the verdict lands | a dialog over the page, with the dial, the stamp and the reasons beneath | the same panel, with the reasons beneath |
| states shown at mid-point | rich: dial, partial dissection, phase line, skip | sparse: address typing and empty space |

## The judgement

**Visual craft: the current wins.** The dial, the stamp, the animated dissection and the
typography are more designed than the prototype's flat column. At the midpoint the current fills
its space and the prototype does not.

**Process transparency: the prototype wins.** It shows seventeen real measurements, a phase line
that counts real work, and a score that climbs to the model's own number. The current shows one
track of evidence, the dissection, and a dial.

**Ceiling: the merge is higher than either.** The prototype's weakness is that it replaced the
product's craft with a plain panel. The current's weakness is that it hides the work in a single
dissection. Put the measurement strip into the current's empty space and the current becomes
both crafted and transparent, without losing the dialog, the print rules or the skip control.

## The merge, concretely

1. Keep the current page, dialog, dissection, dial, stamp, print rules and skip control untouched
2. During the existing estimating phase, reveal the measurement chips under the address, in the
   extractor's own order, with the phase line counting "measuring 6 of 17"
3. Let the dial climb as it already does; the chips are the evidence the dial is summarising
4. When the response arrives, the dissection fills and the dialog opens as now
5. On a phone, show the five measurements that moved the score rather than all seventeen
6. Under prefers-reduced-motion, show the chips at once and keep the dialog as it is

The prototype stays reachable at `/sim/examine` either way, so the comparison can be repeated
after the merge.
