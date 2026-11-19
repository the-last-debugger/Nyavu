# Benign deep URLs: the first harvest, and the bias it carries

Path and query features are the largest signal still missing from the model. This is the first
attempt at the data they need, and it is recorded with its flaw because the flaw changes the
conclusion.

## What was tried

1. **Common Crawl index** (`CC-MAIN-2026-43`). Queries for `safaricom.co.ke`, `kabarak.ac.ke` and
   `equitybank.co.ke` returned two rows, no rows, and a gateway timeout. Kenyan institutional
   coverage in the index is thin and the endpoint is unreliable under load.
2. **Sitemaps** (`tools/harvest_benign.py`). For each of the 91 institution domains: try
   `/sitemap.xml`, `/sitemap_index.xml`, then the sitemaps listed in `robots.txt`, following one
   level of sitemap index. Ten workers, nine second timeout.

## What it produced

- **40 of 91 domains** yielded URLs
- **5,395 deep URLs**, written to `data/processed/benign_deep.jsonl`
- largest sources: booking.com 637, sc.com 223, microsoft.com 214, binance.com 210, betika.com 202

## What the measurement says

| corpus | n | has a path | path keyword | depth 2+ | has a query |
| --- | --- | --- | --- | --- | --- |
| benign (sitemaps) | 5,395 | 99.7% | **6.8%** | 41.3% | **1.0%** |
| phishing | 789,652 | 75.5% | **19.8%** | 30.2% | **18.5%** |

Two readings, one of which is a trap:

- **path keywords look genuinely discriminative**: 6.8% benign against 19.8% phishing. A URL path
  that says "verify" or "account" is about three times more common in the phishing corpus.
- **the query-string figure is an artefact and must not be used.** Sitemaps list canonical URLs and
  routinely strip parameters, so 1.0% measures sitemap convention, not the web. Training on it
  would teach the model that `?` means phishing, which would then flag every Google result.

## What this means for the model

The keyword result justifies continuing; the query artefact is the warning. The next corpus needs:

- benign URLs **with parameters**, which sitemaps will not give;
- benign **login and account paths**, since sitemaps mostly list marketing and catalogue pages, and
  a real bank's `/login` is exactly what a phisher imitates;
- enough volume to train: a few hundred thousand, against the 5,395 here.

Realistic sources: a Common Crawl WARC sample filtered to the top 10,000 domains, or a crawl of
`robots.txt`-permitted paths on the institution list, respecting `robots.txt`.

## Status

Data collection only. No model change, nothing deployed. The 91-domain list and 5,395 URLs are
committed as the seed; the retrain waits on a corpus that contains queries and login flows.
