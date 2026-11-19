# Restoring the examination

The system as it stood before the choreography prototype is tagged and branched:

- tag `pre-exam-choreography`
- branch `stable/pre-exam-choreography`

## To put the old examination back on the live site

```
git checkout stable/pre-exam-choreography
git push origin HEAD:main
```

Render redeploys `main` on push, and the shell is served with a new asset hash, so the change
arrives without anyone clearing a cache.

## To try the prototype without committing to it

```
git checkout main
```

The prototype lives at `/sim/examine?url=...` and is not linked from the product, so `main` can
carry both while the decision is open.

## What the tag contains

The typed examination with its notes read right to left, the verdict dialog with the dissection,
print rules, QR scanning, bulk screening and the rest of the product. Everything except the
measurement-by-measurement choreography.
