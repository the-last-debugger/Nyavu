# The mark

One drawing, one source file, everywhere it is needed.

`tools/make_logo.py` draws the net and writes every size the product uses. Nothing is
hand-exported, so the web and the app cannot drift apart the way they did when the app was
still mint and the site was sage.

## What it is

A throwing net seen from the side: strands leave an apex at the top, bow outward and land on
a base line in knots, and two wefts cross them, sagging a little so they read as rope rather
than as rules. It is not a spiderweb, which is radial and unknotted, and it is not a grid,
which says nothing about catching anything.

The wordmark is not part of the drawing. "Nyavu" is set in the product's serif beside it, so
the mark can stand alone as an icon and the name can change weight with the layout.

## Where it is used

| place | file | how |
| --- | --- | --- |
| Browser tab | `app/static/favicon-32.png` | 32 px, generated |
| Installed web app | `app/static/icon-192.png`, `icon-512.png` | manifest, `any` and `maskable` |
| iOS home screen | `app/static/apple-touch-icon.png` | 180 px |
| Social preview | `og:image` points at `icon-512.png` | 512 px |
| Header, every page | `app/static/logo-mark.svg`, inlined | takes `currentColor`, 30 px |
| About page, above the title | same SVG, `.logo-plate` | 68 px |
| Android launcher | `android/app/src/main/res/mipmap-*/ic_launcher.png` | five densities, on the dark tile |
| Android header | `android/app/src/main/res/drawable-nodpi/logo_mark.png` | 192 px, transparent, 34 dp |
| Android welcome screen | same drawable | 96 dp |
| Documentation preview | `docs/logo-preview.png` | 512 px, transparent |

## Rules

- The mark is bone (`#E9E6DE`) or sage (`#8FA98F`) on the product's background. On a light
  surface it would need a dark copy, which does not exist yet; nothing in the product prints
  it on white except the print stylesheet, which omits it.
- The launcher icon carries the dark rounded tile; the in-app header does not. A tiled mark in
  a header reads as a button.
- Change the geometry only in `tools/make_logo.py`, then re-run it. Editing an exported PNG is
  how the two products drifted the first time.

## Regenerating

```
python tools/make_logo.py
```

That rewrites all eleven files above from the same geometry.
