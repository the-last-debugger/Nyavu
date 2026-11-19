import collections, io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")

institutions = json.load(io.open("data/institutions.json", encoding="utf-8"))["entries"]
allow = set()
try:
    allow = {line.strip().lower() for line in io.open("data/allowlist.txt", encoding="utf-8") if line.strip()}
except OSError:
    for candidate in ("ml/artifacts/allowlist.txt", "artifacts/allowlist.txt", "data/processed/allowlist.txt"):
        try:
            allow = {line.strip().lower() for line in io.open(candidate, encoding="utf-8") if line.strip()}
            break
        except OSError:
            continue

pages = collections.Counter()
try:
    for line in io.open("data/processed/benign_deep.jsonl", encoding="utf-8"):
        row = json.loads(line)
        pages[row["host"].lower()] += 1
except OSError:
    pass

RESTRICTED = {"ac.ke": "reserved for accredited universities", "go.ke": "reserved for government bodies",
              "or.ke": "reserved for non-profits", "sc.ke": "reserved for schools"}

# Provenance a reader can check, by category: the second line for institutions that publish
# no sitemap and sit outside the top 100,000.
REGISTER = {
    "bank": "licensed by the Central Bank of Kenya",
    "telecom": "licensed by the Communications Authority of Kenya",
    "mobile money": "operated under Safaricom's licence",
    "government": "published under the government .go.ke namespace",
    "university": "accredited by the Commission for University Education",
    "utility": "a regulated Kenyan utility",
    "media": "a Kenyan media house",
    "retail": "a Kenyan retailer",
    "airline": "a licensed Kenyan carrier",
    "nGO": "a registered Kenyan organisation",
    "global": "the company's own published domain",
}

records = {}
for row in institutions:
    domain = row["domain"].lower()
    evidence = ["On the institution list we keep, built from published addresses"]
    if domain in allow:
        evidence.append("Among the 100,000 most visited sites (Tranco)")
    count = pages.get(domain, 0)
    if count:
        evidence.append(f"Publishes {count} pages in its sitemap")
    suffix = ".".join(domain.split(".")[-2:])
    if suffix in RESTRICTED:
        evidence.append(f".{suffix} is {RESTRICTED[suffix]}")
    register = REGISTER.get((row.get("category") or "").lower())
    if register:
        evidence.append(register[0].upper() + register[1:])
    records[domain] = {"name": row["name"], "category": row.get("category"),
                       "pages": count, "ranked": domain in allow, "evidence": evidence}

io.open("data/legitimacy.json", "w", encoding="utf-8", newline="\n").write(json.dumps(records, indent=1))
print("records:", len(records), "| with sitemap pages:", sum(1 for r in records.values() if r["pages"]),
      "| ranked:", sum(1 for r in records.values() if r["ranked"]))
sample = next(iter(records.items()))
print("sample:", sample[0], sample[1]["evidence"])
