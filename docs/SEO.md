# Search

## What is already in place

| signal | state |
|---|---|
| robots.txt | allows everything except `/api/`, names the sitemap |
| sitemap.xml | generated from the routes that exist, so it cannot list a page that 404s |
| canonical | every page declares its own URL |
| titles and descriptions | unique per page |
| structured data | WebApplication on the home page; Article and BreadcrumbList on both guides; AboutPage on About |
| IndexNow key | served at `/{KEY}.txt`, so Bing can verify the site |
| hash routes | deliberately absent from the sitemap: `#model` is a fragment, not a page |

Run `python tools/indexnow.py` after a deploy to announce the pages to Bing, Yandex, Seznam and Naver.

## What only the owner can do

Search engines need to be *told* about a new site before they crawl it on their own schedule.

1. **Google Search Console** - add `nyavu.onrender.com`, verify with the HTML tag. Set the environment
   variable `GOOGLE_SITE_VERIFICATION` to the token; the home page splices it in from the environment.
   Then submit `sitemap.xml`.
2. **Bing Webmaster Tools** - the same, with `BING_SITE_VERIFICATION` and `msvalidate.01`.
3. **A custom domain.** `nyavu.onrender.com` is a subdomain of a shared host: its reputation is shared
   with every other Render app, and a surprising number of them are spam. A real domain is the single
   strongest thing that can be done for ranking.
4. **Links.** A site nobody links to is a site nobody crawls. The project page, the repository, the
   university writeup and any forum answer that mentions the tool all count.

## The honest expectation

A new site on a shared subdomain, with no inbound links, is typically discovered in days to weeks and ranks
for its own name only after it has been linked from somewhere. Submitting the sitemap shortens discovery;
it does not create authority. Cold starts on a free instance also make crawling less reliable, since a
crawler that times out may wait longer before it tries again.
