# The dissection: what is wrong, and four ways out

The block below the dial is the largest thing on the card and the least legible. This note records
what is wrong with it, four options, and a recommendation.

## What is wrong today

1. **The label explains the method, not the finding.** "reading from the right" tells a person a
   technique. It does not tell them what was found.
2. **Notes live under their piece, in whatever width remains.** On a wide screen the row shows six
   pieces with narrow note columns; on a phone each piece becomes its own row and the address
   stops looking like an address at all.
3. **The rules under the notes read like form fields.** Three or four underlines in a row invite
   the eye to treat them as inputs.
4. **The cursor implies a scan, but the reason for the scan is asserted in the caption** rather
   than shown. "Read it from the right" is a caption, not a demonstration.
5. **It competes with the verdict.** The dissection is the tallest element, so the thing a person
   came for is below the thing they did not ask for.

## Four options

| | shape | strength | cost |
| --- | --- | --- | --- |
| **1** | today, condensed | keeps the address as one line on a wide screen | narrow note columns, phone breaks the line |
| **2** | ladder, one row per piece | never wraps, phone is free, the active row can travel upward | stops looking like an address |
| **3** | one line, one note panel | notes get a full line, address stays whole, works at every width | one note visible at a time |
| **4** | two readings, side by side | teaches the lesson in a single comparison | doubles the content, cannot show every piece |

`docs/dissection-options.png` renders all four, from `/sim/dissection-options.html`.

## Recommendation: option 3, with the label fixed

The address stays whole and the note appears once, in a panel that changes as the read sweeps
right to left. That solves the two structural faults at once: notes never get squeezed, and the
address never breaks into columns.

Three details worth fixing at the same time:

- **the label becomes a question with an answer**, not a method name: "the registered name is
  verify-account.top", or "reading outward from the ending", followed by the panel text.
- **the underline disappears** from the notes; the highlight belongs to the address, not to the
  text below it.
- **the caption stops duplicating the panel.** One of the two should carry the lesson.

Option 2 is the safer one if the phone matters more than the desktop, but it trades away the
thing that makes the block feel like an address. Option 4 is worth stealing as a *caption* rather
than as a layout: "the eye stops at mpesa; the name is verify-account.top" is one sentence that
does most of the teaching, and it can sit under option 3.

## What it would take

| work | size |
| --- | --- |
| markup: one line of segments, one note panel, no per-piece notes | a rewrite of `autopsyMarkup`, contained |
| animation: move the highlight and swap the panel, right to left | reuse the existing beat clock; the current cursor work is replaced, not added to |
| phone: identical, because there are no columns to collapse | nothing extra |
| report: the figure changes, which is fine since the report is being rewritten next week | one figure and a paragraph |
| risk | moderate: the block is used by the print path and the clean/risky captions |

The ladder is the cheaper change if we want to be conservative: it is mostly CSS, and the notes
already exist.
