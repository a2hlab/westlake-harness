# Restore v6: t10 capture path and t11 classifier, disabled 5cd derivative

Restore v5 still selected the old capture watchdog and feed classifier. This
revision imports the frozen composition's two programs and rebuilds their entry,
member and startup hashes. Eight control-target SHAs change. All 487 target
before/after records, host UID20011300, directory guards and all 463 runtime/stage
file bytes remain unchanged. No 61b preimages, startup authority or lock is used.

Source: t0 commit `c6c8f6145ae72da1331e5d461d4959532efeddd7`, tracked
`benchmark/2026-10-12-snapshot-path/classifier-composition/results.json`, blob SHA
`9e9ad35035916dca0339bb6f4daf5be117633c10ba6acb6280eee59f93312b14`.
That record pins the persistent generated `capture-feed-package`; the generated
package itself is not claimed to be tracked by that commit. Its composition SHA
is `5a591c13f94236cb8442616362427a5751b5484e89b6592700e8ce3adacab948`, and its
plan SHA is `9270f15cd5c25244aaf1f90ee3640bd39c9d136103f22201639deb290a42d832`.
Every listed source file was checked. Full provenance: `source-composition-audit.json`.

- Watchdog: `2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a`.
- Classifier: `0bf966d76e038379af1fa2542746572a2c76a9bf88e17a97869682debfc36eaf`.
- Prepared manifest: `f2d0ae4776be5d07f1145104908594eadce70c4b6aa93cbb21b302f187ddeaad`.
- Generated plan: `35276f1ef9f4e19996e5312db9e1a5cd111e76ededa559aae1895a764e8a07d2`.
- Executor, unchanged from v5: `496fa979f4af71b8c01c44a474aed4074b64544d5d1eb500709c649679831d0d`.

The only compiler addition is the independently pinned composition input and
`STARTUP_DECODER_SHA` refresh. It admits watchdog/classifier content, checks the
r3 helper/worker and other unchanged controls, then independently derives the
5cd entry, 13-member inventory and startup chain. Donor derived templates are not
copied. The three stage metadata evidence references move from t4 to the already
landed main-tree record with the same SHA, target and observed metadata. `invoke`
and `new_executor` are AST-identical to v5; the generated executor is byte-identical.
`delta.json` lists the exact eight changes. v3/v4/v5 freezes and all their declared
files were checked unchanged in `evidence/history-byte-equal.json`.

## Reproduce the sparse landing

Land exactly `landing-paths.txt` over the already landed v5 baseline (main commit
`34e9018091`). All 19 small control payload files are included, including the
ignored JPEG probe and classifier binary. Do not filter the explicit list using
`.gitignore`. The 463 runtime/stage files total 769,937,330 bytes and are excluded
from the landing. The package therefore requires a fresh local compile before
any prepared-package use. This is intentionally a review candidate, not a
self-contained executable or a signed seal.

The tests now compile the full real binding into a temporary directory themselves;
they do not depend on a producer's untracked package runtime. They need declared
local inputs under `$WORKSPACES`: main-tree measured preimages/metadata/archive,
`westlake-inputs` CAS, t0's pinned readiness/r3/composition sources, and the landed
v5 provider/binding/plan. `binding.5cd.composed.disabled.json` pins these inputs.
The old v5 package payload/runtime is never read. No network fallback exists.

From the checkout root:

```sh
export WORKSPACES="$(cd .. && pwd)"
python3 benchmark/2026-10-12-v1-seal-assembly/restore-v6/test_restore_v6.py
python3 benchmark/2026-10-12-v1-seal-assembly/restore-v6/replay_clean_landing.py \
  --workspaces "$WORKSPACES" --out "$TMPDIR/restore-v6-clean-review"
```

The replay output must not exist beforehand. `replay-inputs.json` pins the 31
small files required for the test copy, including three already landed v5 metadata
files. Replay denies private-t4 reads and subprocesses after copying; this is a
Python audit boundary, not an OS sandbox. Both local and clean-copy runs passed
8/8 checks: exact deterministic manifest, 486 manifest files/487 targets, all byte
pins, 13 boot hashes, source pins, strict UID, before/after/dirs, unchanged executor
and four negative pin cases. Full logs are in `evidence/`. No new transaction
matrix, production-lock simulation or full-tree lifecycle run is claimed.

To materialize a complete package locally, compile to a new output directory:

```sh
python3 benchmark/2026-10-12-v1-seal-assembly/restore-v6/toutiao_provider.py \
  --compile \
  --binding benchmark/2026-10-12-v1-seal-assembly/restore-v6/binding.5cd.composed.disabled.json \
  --out "$TMPDIR/restore-v6-full-review"
```

This must reproduce the manifest SHA above. The frozen deployment points to the
sparse sibling `package-composed-disabled`; no deployment or authorization is
created by these commands. `build_binding.py` documents the one-time binding
construction and refuses to overwrite its existing outputs.

Initial failed source lookup/compile logs are retained: Git initially rejected a
lookup of the untracked generated package, then an incomplete metadata-reference
relocation omitted its target selector. Both were corrected before the successful
compile. Initial clean-replay audit paths included relative cleanup events; the
final runner uses the clean directory as cwd and reports zero private read attempts.

## ARM receipt filename resolution

`arm-evidence-name-map.json` is a supplementary mapping proposal, not a rewrite.
Of 45 command references in the outer ARM summary, 29 need the image suffix
`.jpeg` or `.png` removed immediately before the receipt's final `.json`; 16
already match. All 45 resolve uniquely by command number with verified stdout,
stderr and serial, and no unknowns remain. Eight captured-image chains additionally
match source/input SHA, board SHA output, classify label/rc and cleanup checks.
Apply only the explicit old-to-actual pairs in the mapping when presenting a new
summary. Keep original summary, filenames, argv and raw evidence unchanged.

The mapped outer 5ea probe is the earlier 10/10 fixed-image classifier ABI evidence,
not v6 device execution or live recovery acceptance. Execution and startup remain
disabled, approval remains PENDING, and the user-derived equivalence decision is
still pending. No seal or authorization is manufactured. Zero board writes,
remote operations, push or 5cd execution occurred in this revision.
