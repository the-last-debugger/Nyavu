# The institution list, and what priority the corpus says

## Why a list at all

A name can be judged on its shape, but it cannot be named. "This is the address Equity Bank
publishes" is a different claim, and it needs a stored list rather than an inference. This file
records where the list comes from, how it is built, and how far it can be trusted.

## How it is built

`tools/institutions.py` holds the table: name, registrable domain, category, and the institution's
own site as the source. It writes two artefacts:

- `data/institutions.json`, the record with categories and sources
- `app/static/institutions.js`, the same data for the page, loaded before `autopsy.js`

91 entries at present: banks, telecoms and mobile money, government bodies, universities, retailers,
media, utilities, and the global brands that dominate the corpus.

## What the corpus says about priority

789,654 phishing URLs were scanned for brand names appearing as host labels:

| name | URLs | share |
| --- | --- | --- |
| facebook | 6,290 | 0.80% |
| whatsapp | 3,940 | 0.50% |
| kra | 2,926 | 0.37% |
| apple | 2,898 | 0.37% |
| amazon | 2,836 | 0.36% |
| microsoft | 2,541 | 0.32% |
| paypal | 1,673 | 0.21% |
| google | 1,635 | 0.21% |
| instagram | 1,394 | 0.18% |
| netflix | 1,394 | 0.18% |

The lesson is uncomfortable for a Kenyan product: **global brands are borrowed far more often than
Kenyan ones in this corpus**. M-Pesa and Safaricom barely appear, which almost certainly reflects
the corpus being international rather than the absence of local campaigns. A Kenyan-sensitive corpus
would be needed to rank local institutions honestly; until then the list stays broad rather than
tuned to one market.

## What the list does, and does not, claim

- **claims**: this domain is the one the institution publishes
- **does not claim**: that a name is safe, that the site is up, or that the institution owns it today
- **does not fetch anything** when a link is checked

## Honest note on validation

DNS validation was attempted and abandoned as a filter: `kcb.co.ke` resolves in this environment
while `coopbank.co.ke` and `airtel.co.ke` do not, which is a resolver limitation rather than evidence
about those domains. The list is therefore sourced from published addresses, and the `resolves`
field in the JSON is deliberately `null` rather than a claim. A wrong entry would mislabel a domain;
it would not clear an impostor, because the check is an exact match against the registrable domain.

## Next

- grow to the full CBK, CUE, CA and IRA registers, each with the register page as the source
- a Kenyan corpus, so the ranking above reflects who is actually targeted here
