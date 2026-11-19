# Web to native: the worklist

Written before any further porting, because the last two attempts failed for the same
reason: I reskinned web layouts instead of redesigning screens for the platform. Expo's own
migration guide puts it plainly — *"if it still feels like a website, you ported instead of
redesigned."*

This file is the durable list. Each item is checked off only when it runs, not when it
compiles.

## What exists on the web

Four views, two modals, one dialog, three static pages, nine endpoints:

| surface | route | what it does |
| --- | --- | --- |
| Detector | `#detector` | input, samples, the examination, the verdict |
| Bulk | `#bulk` | CSV upload, results table |
| History | `#history` | the account's recent checks |
| Model | `#model` | classifier comparison, metrics |
| Verdict | `verdictDialog` | the card: dissection, number, reasons, fold |
| QR | `qrModal` | camera scan of a QR code |
| Auth | `authModal` | Google sign-in |
| About | `/about` | what the product is, and its limits |
| Learn | `/learn/*` | two pages on reading an address |

Endpoints: `predict`, `scan/bulk`, `history`, `model`, `auth/me`, `auth/logout`, `stats`,
`stats/daily`, `app/version`.

## The decision that shapes everything

**The examination is the product.** Everything else is scaffolding around it. So the first
screen nativized is the one a person opens the app for, and it is rebuilt for the phone
rather than restyled from the web.

## Buckets

Rules used: *nativize-now* if the screen is hot or needs gestures, keyboard, camera or
lists; *port-as-is* if it is presentational and rarely visited; *later* if it needs data or
permissions the shell does not have yet; *drop* if a phone is the wrong place for it.

| # | screen | bucket | why |
| --- | --- | --- | --- |
| 1 | Detector: the examination | **nativize-now**, bespoke | the product's signature; needs a real caret, haptics, timing |
| 2 | Verdict | **nativize-now** | arrives over the exam; should be a native sheet with detents, draggable |
| 3 | Shell: tabs, safe areas, back | **nativize-now** | the frame is what makes everything else feel like an app |
| 4 | App identity: icon, splash, theme | **nativize-now** | adaptive icon, splash, system bars; cheap and very visible |
| 5 | QR scanner | **later** | camera permission, `expo-camera`; the web has it, phones deserve it |
| 6 | History | **later** | needs the session cookie and an accounts story |
| 7 | Bulk | **later** | needs a file picker and a results list that behaves like a native list |
| 8 | Auth | **blocked** | native Google needs an Android OAuth client with the app's SHA-1 |
| 9 | About | **port-as-is** | presentational; open in an in-app browser for now |
| 10 | Learn pages | **port-as-is** | same; content, not interaction |
| 11 | Model page | **drop** | a comparison table is a web page, not a phone screen. Link to the site |
| 12 | Sample addresses | **nativize-now**, trivial | three chips, one tap, no typing |

## Phase 1 — the shell and the exam (the shippable core)

| item | done when |
| --- | --- |
| Safe areas | content never sits under the status bar or the gesture bar |
| Back handling | back closes the verdict sheet before it leaves the screen |
| Press feedback | Android ripple, iOS opacity, 48 dp minimum targets |
| Haptics | a light tick per piece landing, a firmer one at the verdict |
| Exam surface | full-bleed, address at 22–24 pt mono, one character per `<Text>` so each has a measured x |
| Real caret | an animated bar that springs to each character's measured position, not a `\|` glyph |
| Reading phase | notes arrive from the ending backwards, 320 ms apart, sliding 8 pt and fading |
| Verdict sheet | native sheet, draggable to dismiss, number large, reasons beneath |
| Identity | adaptive icon from the shield, splash on the product background, dark system bars |

**Verification.** Layout and content against the web original via the exported web build;
motion and haptics only on a device. Both are listed honestly, because the second one is
still blocked.

## Phase 2 — what a phone adds

| item | why it is worth doing natively |
| --- | --- |
| QR scanning | the web needs a camera permission prompt too, but a phone is where scanning belongs |
| Share target | another app shares a link, Nyavu answers with the verdict; the web cannot do this |
| History | the phone is where you check the same link twice |

## Phase 3 — the accounts story

Native Google sign-in is blocked on an Android OAuth client. Until then, sign-in opens the
site, and the app says so rather than pretending. If the client is created, the swap is
`expo-auth-session` and a deep-link redirect.

## What is deliberately not carried over

- **the model page**, as above
- **the printable verdict**, which exists because a web page prints; a phone shares instead
- **the CSV header handling**, which is a desktop convenience; the app takes pasted lines

## The rule for each pass

For every screen: run the web original and the native build side by side, and compare
**content and behaviour**, never pixels. A nativized screen should look *more* native than
the web, not identical. If it looks like the web page with rounded corners, it is not done.
