# U8 prospective work: current N10/J8 batch list

**Active delivery: [batch-v2/README.md](batch-v2/README.md)** and [batch-v2/results.json](batch-v2/results.json).

Outer ACK(95) 2026-10-01 08:21 superseded the narrow N8 + payload draft. This delivery is the donor-qualified **batch list first**, not the final 66-key prediction freeze: 22 accepted U7 clusters, 32 unlit keys, 23 rows after B1/B2 separation; requested N10 slots 18 keys, J8 9, deferred 5. Candidate count is not expected lights.

All earlier root skeleton and `draft-v1/` files are historical, superseded, excluded from `landing-paths.txt`. In particular draft CSV SHA `9540f9332f29281362a6be6ffacb3338a4132dccfceaa4d76d73b0bf3c1d3a36` is **not an active U8 freeze**. No new CSV, FREEZE or expected-run is created by this task.

The batch list records source paths, snapshot/last-change commits, hashes, conditional first-wall movement and evidence lines. It includes the 08:28:40 correction: current runtime is NOLOAD-only and both runtime/bridge have duplicate instances; the second loading point remains unknown. Do not apply an old-source fresh-dlopen fix as if same-source proven.

Replay: `python3 benchmark/2026-10-01-u8-prospective/batch-v2/test_batches.py -v`.
Landing scope: `landing-paths.txt`; shared documents: add only the exact lines in `documentation.json`. Gate receipts are `batch-v2/validation.json`. No old skeleton/draft, old staged U7 files, runtime binary or input data is included.
