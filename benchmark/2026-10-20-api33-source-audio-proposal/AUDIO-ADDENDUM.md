# T18 clip-audio / window-close / archive evidence addendum (2026-10-20)

Standalone addendum to the task2 API33 source proposal (accepted, commit `a7cc1b1e…` — outer-supplied). The four task2 files are **not modified**. This package only proposes one **append-only observation row** on canonical API33; no canonical write, no rendering, no device calls, no builds, no git (outer exact-commits).

## Proposed canonical change (exactly one)

Append row 34 `OBS-20261020-T18-5CD-CLIP-AUDIO-RESTORED-HOST-ONLY` to `benchmark/2026-10-19-api-progress-update/observations.json` (preimage SHA bound in `audio-evidence-addendum.json`). The existing 33 row objects stay byte/serialization-identical and in order — proven by in-memory simulation in `audio-evidence-validation.json` (deep-copy, append, re-hash all 34 rows; old 33 match preimage hashes; T18 candidate row 32 and T17 row 31 unchanged; new row schema keys identical to existing rows; `frozen=false`).

## What the new row records (from public receipts only)

- **Audio**: `PASS_USER_CONFIRMED_CLIP_AUDIO` — explicit user audible observation in candidate window boot `6b99680b-…` (receipt `final/receipts/human-audio-observation.json`, reported_at 1792462242.818399). This is human observation, **not** instrumented capture or getter-return proof.
- **Close/rollback**: window `CLOSED_RUNTIME_RESTORED_UI_NOT_RECOVERED`, fresh boot `9e75bd0f-…`, runtime hashes restored, unlocked, 1483.28s elapsed; **restored UI is HOST_ONLY** — baseline `MediaPlayer.native_init` raised `UnsatisfiedLinkError`; not full UI recovery, not a random-crash fix.
- **Video**: `NOT_PASSED_STILL_COVER` (ANW CPU draw −19). No video upgrade.
- **Archives**: production / source-closure / window remote archives are **VERIFIED only via the cited outer-success verification receipts** (the `packet-final/archive-receipt.json` itself remains `LOCAL_VERIFIED_REMOTE_PENDING`). This is **not** remote git publication and **not** a whole-source fresh rebuild.

## Explicit non-changes

- Existing candidate row `OBS-20261020-T18-AUDIOTRACK-SIZE-CANDIDATE` (status/method/apps/deployment/…) untouched; task2's old-candidate increments are **not** applied (task2 remains accepted proposal history). Its four real source/build refs are carried on this new actual row instead.
- Historical 315 classifications untouched; first 31 rows byte-equivalent; historical candidate not rewritten as current deployment.

## Files

`AUDIO-ADDENDUM.md` (this), `audio-evidence-addendum.json` (proposal, append_observation with full new row), `audio-evidence-validation.json` (243/243 input SHA + append simulation proof), `audio-landing-paths.txt`.

Writes ledger: 0 device calls, 0 builds, 0 canonical writes, 0 git commits.
