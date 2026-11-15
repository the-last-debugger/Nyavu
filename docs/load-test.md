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

**Prediction is ~540 ms because of pandas.** The service builds a one-row DataFrame per
request before handing it to the pipeline. On a full core that costs ~66 ms; on the free
tier it costs several hundred. This is the single largest avoidable cost in the request
path, and it is a small change — construct the feature vector directly and call the
pipeline on a numpy array.

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
2. **pandas per request** — removable; expect a 5–10× improvement in server time.
3. **Single worker, 0.1 CPU** — solved by paying, not by tuning. Only worth doing if
   real traffic appears.
4. **Model import at boot** (~20 s) — affects cold starts after the instance sleeps.

## What to do next, and what not to do

**Do**: remove pandas from the request path, then re-measure. That is an afternoon's work
and the largest gain available at zero cost.

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
