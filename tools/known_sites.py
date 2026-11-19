import gzip, io, json, sys
sys.stdout.reconfigure(encoding="utf-8")

allow = []
with io.open("ml/artifacts/allowlist.txt", encoding="utf-8") as handle:
    for line in handle:
        line = line.strip().lower()
        if line:
            allow.append(line)
print("allowlist entries:", len(allow))

with gzip.open("data/threat_snapshot.json.gz", "rb") as handle:
    snapshot = json.load(handle)
listed = set(snapshot["hosts"])
print("threat hosts:", len(listed))

institutions = {row["domain"].lower() for row in
                json.load(io.open("data/institutions.json", encoding="utf-8"))["entries"]}

# the top slice of the most visited sites, minus anything a public list has reported
TOP = 1200
picked = {}
for rank, domain in enumerate(allow[:TOP], start=1):
    if domain in institutions or domain in listed:
        continue
    labels = domain.split(".")
    if any(".".join(labels[index:]) in listed for index in range(1, len(labels) - 1)):
        continue
    picked[domain] = {
        "rank": rank,
        "evidence": [
            f"Among the {TOP:,} most visited sites worldwide (rank {rank})",
            "Not on any of the phishing lists we ship",
        ],
    }
print("known sites kept:", len(picked), "| dropped as listed:", TOP - len(picked))

io.open("data/known_sites.json", "w", encoding="utf-8", newline="\n").write(json.dumps(picked, indent=0))
print("wrote data/known_sites.json")
