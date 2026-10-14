# Final API source/build correspondence views

The preview mapped moving review files and was correctly rejected. This publication instead consumes the sole frozen T4 mapping `6e65f6fdcd06efb7a8cc8630b2cdd9f0b9de49631d9f5f0b2894e20589d4458e` and recipes `59132e2e7291ae4c3adde3311ae68bd8d090aabd163e127c16d133c2703421b1`, now on MAIN4032695e02. Source-equivalent revision42c87ab42b is explicitly pinned. No drift alias was introduced for source-delivery metadata.

All315 original semantic records are unchanged. All304 source references resolve to exact MAIN/master files, and all120 non-null build-entry rows resolve to exact master blobs. The315 per-row correspondence receipt checks each of the seven additive fields against the frozen mapping and the four build fields against its shared recipe. Unknown commands, outputs, historical equivalence, stub grades and API versions remain as recorded. The later10 partial mappings belong to a separate follow-up; this publication does not invent them or claim complete315 source closure.

Python10/10, the Rust api_source_delivery selector, original atlas/CSV/Markdown checks and bilingual canonical payload checks passed. The isolated physical landing simulation checks410 links per language by SHA and1898 Markdown links. It is not an actual MAIN publication audit. ROOT should land exactly `final-landing-paths.txt`, preserving the directory `benchmark/2026-10-14-api-source-delivery/views` (no flattening). After that T0 runs the actual audit below and supplies an independent receipt. No build recipe was executed, no device accessed, no signed315/V2 input changed.

Two small publication changes accompany the views: verify.py selects the separately frozen final request and labels the stable mapping as bound; publication_check.py unlinks an existing simulated alias symlink before copying local bytes, so simulation cannot write through to MAIN. The original core freeze and all rejection evidence remain unchanged.

```sh
WORKSPACES=/path/to/workspaces PYTHONDONTWRITEBYTECODE=1 python3 benchmark/2026-10-14-api-source-delivery/verify.py
WORKSPACES=/path/to/workspaces cargo test --manifest-path tools/spec-checks/Cargo.toml --test api_source_delivery -- --nocapture
# Run only after MAIN views physically exist; receipt remains in T0.
WORKSPACES=/path/to/workspaces python3 benchmark/2026-10-14-api-source-delivery/publication_check.py actual --views "$WORKSPACES/westlake-harness/benchmark/2026-10-14-api-source-delivery/views" --receipt benchmark/2026-10-14-api-source-delivery/evidence/final-main-links.actual.json
```

The unchanged human-review contract remains pending_review, not machine acceptance. One recorded old DevEco compiler dependency is unavailable locally and stays an explicit dependency gap. Master source/build navigation never promotes a candidate worktree or absolute path to the user implementation entry. ROOT owns commit/push; T0 has not pushed.
