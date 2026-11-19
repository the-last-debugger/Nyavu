# Why the green felt weak and the red felt pink

Measured, not guessed. Both colours were describing themselves wrongly.

| token | value | hue | saturation | contrast on the card |
| --- | --- | --- | --- | --- |
| safe (old) | `#7FA98F` | 142.9 | **19.6%** | 7.70:1 |
| accent | `#8FA98F` | 120.0 | **13.1%** | 7.95:1 |
| danger (old) | `#ff4d6d` | **349.2** | 100% | 6.31:1 |
| warn (old) | `#ffb020` | 38.7 | 100% | 11.08:1 |

- **The green was a grey-green.** Hue 120 is a true green, but 13% saturation means 87% of the colour
  is grey. At 13 pixels wide on a near-black card, grey reads as absence. That is the whole
  explanation: the dial was being told "safe" in the one colour that refuses to be seen.
- **The red was not red.** Hue 349 sits 11 degrees past red, towards magenta. Pink is red with its
  blue raised; `#ff4d6d` is 255 red with 109 blue, which is rose, not alarm. The warning amber was
  the only honest signal in the palette.

## The fix: a signal palette

The interface tokens stay as they are, because the app's calm voice is not the problem. A second set
carries the verdict, and only the verdict uses it:

| signal | value | hue | saturation | contrast |
| --- | --- | --- | --- | --- |
| safe | `#57C08A` | 149.1 | **45.5%** | 8.99:1 |
| warn | `#E6B450` | 40.0 | 75.0% | 10.63:1 |
| danger | `#EF4444` | **0.0** | 83.3% | 5.18:1 |

Danger now sits at hue 0 exactly: red with no magenta in it. Safe moves from 13% to 45% saturation,
and gets *better* contrast at the same time.

## The bands

They were drawn on the arc itself, where the track, the readout pill and the needle all sit on top
of them. They are now on a thin ring outside the arc, at 0.62 opacity while the dial is at rest and
0.3 once the reading has landed. Faded is the intent; invisible was the bug.

## Files

- `docs/palette-compare.png`: the three verdict states, old palette above, new below
- `docs/palette-bands.png`: the dial at rest, old beside new

## Status

Branch `feat/signal-colours`, not deployed. The earlier work (accumulating notes, the fold report,
the dial arrival, the loading states) is live at `v=207531d42c`.
