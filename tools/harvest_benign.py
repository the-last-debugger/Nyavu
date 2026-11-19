import concurrent.futures, gzip, io, json, os, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

institutions = json.load(io.open("data/institutions.json", encoding="utf-8"))["entries"]
domains = sorted({row["domain"].lower() for row in institutions})
print("institution domains:", len(domains))

def fetch(url, timeout=9):
    request = urllib.request.Request(url, headers={"User-Agent": "Nyavu/1.0 (academic project; sitemap survey)"})
    raw = urllib.request.urlopen(request, timeout=timeout).read(2_000_000)
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "ignore")

def locs(text, domain, limit):
    out = []
    for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text):
        loc = loc.replace("&amp;", "&")
        if domain in loc and loc.startswith("http"):
            out.append(loc)
        if len(out) >= limit:
            break
    return out

def harvest(domain):
    urls = []
    for candidate in (f"https://{domain}/sitemap.xml", f"https://www.{domain}/sitemap.xml",
                      f"https://{domain}/robots.txt"):
        try:
            text = fetch(candidate)
        except Exception:
            continue
        if candidate.endswith("robots.txt"):
            for line in text.splitlines():
                if line.lower().startswith("sitemap:"):
                    nested = line.split(":", 1)[1].strip()
                    try:
                        urls.extend(locs(fetch(nested), domain, 200 - len(urls)))
                    except Exception:
                        pass
        else:
            urls.extend(locs(text, domain, 200 - len(urls)))
        urls = list(dict.fromkeys(urls))
        if len(urls) >= 100:
            break
    return domain, urls

results = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    for domain, urls in pool.map(harvest, domains):
        if urls:
            results[domain] = urls

total = sum(len(v) for v in results.values())
print(f"domains with deep urls: {len(results)} of {len(domains)} | urls: {total:,}")
for domain, urls in sorted(results.items(), key=lambda kv: -len(kv[1]))[:10]:
    print(f"  {domain:24} {len(urls):4}")

with io.open("data/processed/benign_deep.jsonl", "w", encoding="utf-8", newline="\n") as out:
    for domain, urls in results.items():
        for url in urls:
            out.write(json.dumps({"host": domain, "url": url}) + "\n")
print("wrote data/processed/benign_deep.jsonl")
