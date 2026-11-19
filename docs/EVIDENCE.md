# Evidence beyond the name

The gap was real: the model could only judge the shape of an address, so a plausible name passed.
This is what was added, what it can and cannot support, and what is still missing.

## What ships now

**A local snapshot of public phishing lists.** Nothing is fetched when a link is checked; the lists
are downloaded at build time and shipped with the project (`data/threat_snapshot.json.gz`, 3.4 MB
compressed).

| source | entries | what it gives |
| --- | --- | --- |
| PhishTank | 43,567 | exact URLs, plus the **target brand** for each |
| Phishing Army | 146,320 | host blocklist |
| Blocklist Project | 190,215 | host blocklist |
| OpenPhish | 300 | live URLs |

Together: **338,976 hosts**, 43,864 URLs, and **2,609 hosts mapped to the brand they imitate**.

A hit matches on exact URL or host, and is reported as:

> reported — On PhishTank and Phishing Army, snapshot 2026-11-19. It imitates Apple.

The date is not decoration. A domain can be re-registered after it is listed, so a hit is a reason
to stop rather than proof about the page answering today.

## How it changes the verdict

- a hit **escalates** the verdict to phishing and the dial to dangerous, because a report is
  stronger evidence than a shape
- a miss **never clears** anything: the absence of a report is not innocence, since the lists are
  partial and new campaigns are not on them yet
- the card says which of the two happened. When the report is what settles it, the sentence reads
  *"The name alone reads dangerous, which is how an address like this passes"* rather than claiming
  the name itself carried the marks

## The honest gaps

1. **Path and query features are still not in the model.** They are the biggest untapped signal:
   75.6% of phishing URLs carry a path, and 18.7% carry a login or verify keyword. They are absent
   only because the benign half of the corpus is bare domains. Fixing it needs 50,000 benign deep
   URLs from Common Crawl and a retrain, which is a data project rather than a UI change.
2. **The snapshot ages.** It is dated, and it is only as good as the last build. A refresh job is
   the next step, monthly at minimum.
3. **Feed coverage is uneven by country.** Kenyan campaigns are under-represented in these lists,
   which is the same bias the brand counts showed.
4. **No page inspection, by design.** The strongest evidence available, and the one that would break
   the promise.

## What this does not become

Nyavu still does not visit the link. A feed hit is knowledge we shipped, not a lookup we performed.
