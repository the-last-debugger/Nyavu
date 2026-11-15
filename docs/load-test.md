# Load test — first pass

Run against the public deployment on Render's free instance (0.1 CPU, 512 MB), from
Nairobi, on 16 November 2026. Purpose: find the first bottleneck, not to prove scale.

## Results

| Test | Concurrency | Requests | OK | p50 | p95 | max |
|---|---|---|---|---|---|---|
| `GET /api/health` | 20 | 120 | 120/120 | 339 ms | 700 ms | 792 ms |
| `POST /api/predict` | 1 | 25 | 25/25 | 540 ms | 716 ms | 1078 ms |

No errors, no 5xx, no dropped connections.

## What the numbers mean

**~340 ms is the floor, and it is geography plus cold CPU.** A round trip from Nairobi
to Frankfurt is 120–160 ms before the server does anything. The free instance has a
fraction of a shared core, so anything CPU-bound multiplies.

**Prediction was ~540 ms because the request path was doing avoidable work.** It built the
feature frame column by column, transformed it twice — once to score, once to explain — and
then densified and fully sorted a 50,000-column matrix to find five n-grams.

All three were fixed on 16 November. The transform now runs once and is reused; the
contribution step reads only the sparse entries and considers only the n-gram columns.
Measured locally: **94.3 ms → 12.9 ms per URL**, with verdicts, probabilities, reasons and
suggestions unchanged across the 20 reference URLs in `docs/baseline_full.json`.

The gain was smaller in production than locally — **~570 ms → ~289 ms** — because the free
instance's CPU is the binding constraint, not the code. The remaining cost is mostly the
network round trip plus a throttled core; neither is fixed by editing Python.

**The rate limit is the first hard ceiling, by design.** 30 predictions per minute per IP
means a single client cannot exceed that regardless of capacity. From one IP, this test
hit the wall before the server did.

## Realistic thresholds

| Metric | Target | Current |
|---|---|---|
| p95 on `/api/health` | < 800 ms | 700 ms ✓ |
| p95 on `/api/predict` | < 1000 ms | 716 ms ✓ |
| Error rate | < 1% | 0% ✓ |
| Sustained predictions | 30/min/IP (policy) | reached |

For an audience of a few visitors a day, this is comfortably adequate.

## First bottlenecks, in order

1. **Rate limit** — intentional; protects a free instance from a single abusive client.
2. **Single worker on a throttled CPU** — now the dominant cost. Solved by paying, not by
   tuning; only worth doing if real traffic appears.
3. **Model import at boot** (~20 s) — affects cold starts after the instance sleeps.
4. ~~pandas per request~~ — fixed; 7× faster locally.

## What to do next, and what not to do

**Do**: re-run this test after any change to the request path, and keep the reference
outputs in `docs/baseline_full.json` so a regression shows up as a diff rather than a
complaint.

**Do not**: add GPUs, autoscaling, load balancers or a second instance. At two visitors a
day none of these would change a single user-visible number, and each adds cost and
failure modes. Revisit only if measured traffic approaches the thresholds above.

## Reproducing

The measurements use only the standard library, so no tooling needs installing:

```python
# health throughput
with ThreadPoolExecutor(max_workers=20) as ex:
    list(ex.map(lambda _: get("/api/health"), range(120)))

# prediction latency, sequential and inside the 30/min budget
for _ in range(25):
    post("/api/predict", {"url": "http://mpesa.co.ke.verify-account.top/"})
```
