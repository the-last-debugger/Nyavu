# Backlog

Written at the end of the 17 November session. Live build: `d4c7379`.

## 1. Real-device pass

The one thing no probe can do. The scene at true phone size, the smooth-scroll hand-off
after a scan, and whether the thirty-second runway feels right in the hand rather than in
a screenshot.

## 2. Search visibility — Google and Bing

The pages carry titles, descriptions and `application/ld+json`, but nothing tells a
crawler what exists or that it may index it.

- `robots.txt` allowing everything, with the sitemap referenced
- `sitemap.xml` generated from the real routes: `/`, `/learn/is-this-link-safe`,
  `/learn/how-phishing-works`, `/about`, and the three app views if they deserve their own
  URLs rather than hash fragments
- canonical URLs on every page, so `?u=` deep links do not compete with `/`
- `og:` and `twitter:` tags with a real preview image, since a shared link is how most
  people will first see this
- verification: `GOOGLE_SITE_VERIFICATION` and `BING_SITE_VERIFICATION` as meta tags,
  fed from env so the keys are not committed
- IndexNow for Bing, which accepts a key file and a ping rather than needing a console
- check that the hash-router views (`#model`, `#history`) either get real paths or are
  excluded, because they cannot be indexed as fragments

## 3. Suggestions while typing a link

Typing a URL by hand is the slowest way into the product. A suggestion list would meet
people halfway.

- `GET /api/suggest?q=` returning completions ranked by what people actually scan
- three sources, in order: hosts this deployment has seen, known-good Kenyan domains
  from the brand list (safaricom.co.ke, kra.go.ke, kabarak.ac.ke), and plain domain
  completion for whatever is typed
- keyboard navigation: arrows to move, Enter to accept, Escape to dismiss
- never invent a host that does not exist, and never suggest a domain that scored
  phishing — suggesting a phishing link as a convenience would be a bug, not a feature

## 4. Stale fonts

The service worker still caches `space-grotesk-500.woff2` and `jetbrains-mono-500.woff2`.
After the type change to a serif display face they are barely used. Drop the unused
weights and the matching `@font-face` rules.

## 5. `styles.css` tidy-up

About five thousand lines, most of them appended overrides from successive passes. It
works, and it is the least readable file in the project. Fold the overrides into the
original rules, delete what nothing matches, and keep one section per concern.

## 6. Sign-in credentials

Google and phone sign-in are built and tested but invisible until configured. See
`docs/AUTH.md`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and either Africa's Talking
or Twilio.
