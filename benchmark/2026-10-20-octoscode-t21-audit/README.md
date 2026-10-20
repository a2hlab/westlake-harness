# T21 bounded read-only audit — child-11040 verification (2026-10-20, r2)

Round 1 was BLOCKED (inputs inaccessible; preserved as `blocked-r1.result.json` / `blocked-r1.README.md`). Outer then supplied byte-exact copies under `.octos/t21-audit-inputs/` (3 full stderr + 3 before/after receipts + `main-results.json` from MAIN HEAD `5d2ba3bd…` via git-show, per manifest). **7/7 manifest SHA-256 verified in this lane.** No permission changes; sibling MAIN / home / git untouched.

## Verification algorithm (this lane)

No original command-execution log exists for this lane's checks; the audit was a static parse of the supplied byte-exact stderr copy using this algorithm (implemented in Python, not a transcript of executed shell commands):

1. Hash each `.octos/t21-audit-inputs/` file and compare against `manifest.json` — 7/7 SHA-256 match.
2. Parse `11040-receipt.json`: `bytes=448572`, before/after dead-file SHA present, `source_dead=true`.
3. On `child-11040.stderr`: count lines starting with `[WL-R20-PAIR]` (10); split by `op=` and `rc=` → lock rc=0 ×5, unlock rc=0 ×5; extract per-line `request/handle/convert/map/unmap/flush/abort` fields; locate first `FATAL skia` and `Fatal signal 6` byte offsets (442461, 447480); count `frame-available` lines (5, count=1..5 monotonic).
4. Compare all derived values against `main-results.json` (see table).

## child-11040 independent facts vs MAIN `results.json`

| Fact | Independent | MAIN | Match |
|---|---|---|---|
| R20 lock rc=0 | 5 | 5 | ✅ |
| R20 unlock rc=0 | 5 | 5 | ✅ |
| frame-available lines (last count field) | 5 (count=5) | 5 | ✅ |
| first fatal byte offset | 442461 | 442461 | ✅ |
| second fatal byte offset | 447480 | 447480 | ✅ |

Per-pair-line fields (10 lines, `attempted/rc` = attempted a times with return code b): `request=1/0, handle=1/0, convert=1/0, map=1/0, abort=0/0` on all; `unmap`/`flush` are `0/0` on the 5 lock lines and `1/0` on the 5 unlock lines. First fatal line: `FATAL skia … AutoBackendTextureRelease.cpp Invalid GrBackendTexture. Width==1200, height==2132, protected==0`, followed by `Fatal signal 6 (SIGABRT)`. No literal "NativeImage" string occurs in this stderr; frame-available was counted on the `[WESTLAKE-SURFACETEXTURE]` lines. Receipt `11040-receipt.json` carries boot `5962c827…`, before/after dead-file SHA, `bytes=448572`, `source_dead=true`.

## Conclusion (within ceiling)

All independently computed child-11040 facts **match** MAIN `results.json`. Playback `NOT_PASSED`; no continuous displayed frames and no visual video pass — conclusion stays at: **video not visually passed; ad-path CPU5 pairs only**. Machine-readable detail: `result.json`.

Ledger: 0 device calls, 0 builds, 0 canonical/MAIN writes, 0 git commits, 0 permission changes. No unrelated directory scanning.
