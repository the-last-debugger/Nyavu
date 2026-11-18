# Looking the name up: what we would change, and what protects us

## Why the promise existed

"Nothing is fetched" was not a marketing line. It was the only claim the product could
make without a footnote:

- a checker that fetches a page tells that page it was checked. The operator learns an IP,
  a time, and sometimes a user agent. For someone checking a link they are frightened of,
  "we told them you were looking" is a real harm, small but real
- it kept the product small: no rendering, no sandbox, no crawling infrastructure, no
  bandwidth to a hostile host, and no legal question about fetching other people's pages
- it was checkable. A reader could verify it against the About page and the absence of any
  outbound request in the network tab

## Why it is worth revisiting

The model reads the name and nothing else, so it cannot see four things that matter:

1. whether the name resolves at all, which separates abandoned phishing from live attacks
2. when the certificate was issued, which is the strongest single signal on cheap endings
3. whether the page redirects somewhere else entirely
4. whether the page asks for a password and posts it to a different domain

Points 1 and 2 need no page fetch. A DNS lookup and a TLS handshake give both. That keeps
the promise partly intact: the site's web server may see a connection, but it is never
asked for a page, nothing is rendered, and no HTML is parsed.

## What protects us, and the user

Fetching or even connecting from our server is the standard shape for a scanner, and the
guards matter more than the feature:

| risk | guard |
| --- | --- |
| SSRF to internal services | resolve first, refuse private, loopback, link-local, multicast and metadata ranges, before any connection |
| DNS rebinding | connect to the resolved IP literal, never re-resolve between check and connect |
| slow or hostile hosts | 2s resolution, 3s connection, hard total budget; per-request, not per-scan |
| being used as a proxy | only DNS and TLS, never HTTP bodies. No redirects followed |
| rate abuse | existing per-IP limits apply; the probe is cached per host |
| leaking the user | the connection comes from the server, so the target sees Nyavu's address, not theirs |
| cost | one DNS query and one TLS handshake per unique host, cached for an hour |

## What changes in the product

- the hero note, the About page and the learn pages stop saying "nothing is fetched" and
  say what actually happens: the name is looked up and its certificate inspected from our
  server, so the site sees us and never the visitor
- the reasons gain up to three new lines, in the same plain voice
- the score changes only after measurement. The plan is to measure on the phishing feed at
  `ml/eval/phishing_feed_urls.txt` and on the thirty-five legitimate wrappers at
  `ml/eval/benign_wrappers.txt`, and ship no adjustment that cannot show its effect

## What we would not do

- fetch page bodies, run scripts, or screenshot. The gain is smaller than the risk, and the
  bandwidth to a hostile host is not worth it
- follow redirects. A redirect chain is a fingerprint that can be used against the checker
- send the visitor's address anywhere

## Order of work

1. `app/network.py`: resolve, classify the address, TLS handshake, certificate age. Guards
   above, results cached, total budget under four seconds
2. reasons only, no score change, behind `NYAVU_PROBE=1`
3. measure: hit rate and direction on the feed and on the benign set
4. if the signals separate the classes, wire the score; if not, keep the reasons and say so
5. copy updated in the same commit that turns the flag on, never before
