# Naming the institution, without lying about it

The question: should Nyavu say "this belongs to Kabarak University" rather than "an ordinary
ending"? Yes, where we can, but not by looking anything up, and not as a claim of ownership.

## Three different claims

| claim | example | can we make it? |
| --- | --- | --- |
| the namespace is restricted | ".ac.ke is reserved for accredited Kenyan universities, so a phisher cannot buy one" | **yes**, it is a fact about the registry, no lookup needed |
| this is the address the institution publishes | "this is the address Kabarak University publishes" | **yes**, if it is on a list we keep and cite |
| this domain is owned by Kabarak today | "this belongs to Kabarak University" | **no**: it needs a WHOIS lookup, leaves a footprint, and .ke records are often thin or redacted |

The middle claim is the one with personality, and it is honest if we say where the list came from:
*"We know it from the list we keep, not by visiting the page when you ask."*

## What was built

- `SUFFIX_MEANING`: what each Kenyan ending is reserved for. `.ac.ke` accredited universities,
  `.go.ke` government, `.or.ke` non-profits, `.sc.ke` schools, `.ne.ke` networks, `.co.ke` open to
  any business. The last one matters: it says honestly that `.co.ke` proves nothing about ownership.
- `KNOWN_INSTITUTIONS`: a short list of institutions whose address we can name (Kabarak, Safaricom,
  KRA, Equity, KCB, Co-operative, Strathmore, University of Nairobi).
- the name note and the caption now name the institution, and say how we know.
- borrowed names are named in the other direction: a fake that puts `kabarak` inside its own domain
  gets *"Kabarak University's own name, borrowed as a label in a domain they do not own"* rather
  than "free to invent".

## Why not Google, or WHOIS

- **Google**: we would be fetching, and the promise is that nothing is fetched. It also cannot be
  done for every link in under a second.
- **WHOIS/RDAP**: possible, and a legitimate *opt-in* for a "check the owner" button, but it is a
  lookup at a registry, it fails behind privacy services, and `.ke` coverage is uneven. It would
  also change what Nyavu is: from judging a name to investigating a registration.

## The personality is the point

"An ordinary ending" is a database talking. The same fact, said properly: *".ac.ke is reserved for
universities accredited in Kenya, so a phisher cannot buy one."* That is the same evidence with a
voice, and it teaches the reader why the ending matters at all.

## Status

Branch `feat/institution-voice`, suite not yet run against it, not deployed. Screenshots:
`docs/voice-kabarak.png`, `docs/voice-spoof.png`.
