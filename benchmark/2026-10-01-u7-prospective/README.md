# U7 prediction bundle

**Final accepted composition and freeze:** [v1/README.md](v1/README.md), U6 + T7d with U5 native unchanged, CSV `fa92c5b964fed2976ba66d82fb703672241435a294c8d9286a7c9192ebab9007`. The combined U7 run consumes `v1/expected-run.json` and `v1/apps-u7.json`. All text and artifacts below describe the **historical pre-result skeleton**, not the current candidate or readiness state. Its N6 plan and pending U6 handoff are superseded by v1 and the completed U6 scoring bundle respectively.

## Historical offline skeleton

The wrong shortcut would be to copy U6 predictions into a measured baseline,
or to count a source stub / native export as an executed repair. This package
instead keeps **66 draft rows, zero U7 final predictions, zero actual U6 scores**.
U6 remains frozen at CSV SHA256
`b9a414ed0b70134e2b9dbd54be91dd843e130c5d3020acf905577e17ef419746`.
No device command was used. No `PREDICTIONS.csv` or `FREEZE.json` is produced.

## Evidence and planned changes

- `repair-catalog.json`: six T7d class edits / seven methods, exact descriptors,
  stub semantics, limitations, positive execution requirements and source lines.
  Original spec `d32b314b7` is superseded for actual edit scope by `f4a059ef0`.
  `MediaServiceManager` is **dropped**, not a promised Noice repair.
  ColorMatrix is already in this board's stubs jar; do not assume stock AOSP
  ownership. The actual patch implements saturation as a no-op, not matrix math.
  SSLSockets permits fallback, not guaranteed TLS; requestNetwork may hang
  waiting for a callback. LibreTube and Feeder have no claimed T7d repair.
- N6 is candidate `westlake-generation-n6-b70b3d00`, manifest `423ea1ff...`;
  full hashes are in the catalog. Relative to U5 it includes N5's two ANL aliases
  **and** the Flutter-private ABI replacement. It is not a one-file U6 delta.
  Six Flutter keys are candidates, not six unlocked apps. Earlier JNI ID or
  provider VerifyError walls may prevent reaching the EGL wrapper.
- N5 LocalSend's captured raster stack enters Mali/platform EGL and fails in
  `ANativeWindow_getFormat`; the nearby missing-path warning is not a GL root
  cause. Require target-process unwrap, surface result and swap evidence.
  Compare duplicate mappings against same-board U5, not an absolute one-inode
  rule. N6's 184 temporary exceptions do not authorize a future U7 deployment.
- `evidence/source-priors.json` stores numbered, SHA-checked source snapshots;
  these are **component source priors**, not T7d/N6 device outcomes. The captured
  T7d document retains its historical build-blocker prose; outer ACK(80)
  03:23:32 supersedes that recipe with the existing local dockbuild instructions.

## Draft and intake

`SKELETON.{json,md}` enumerate all 66 keys. U6 projected first walls are labeled
reference-only; measured walls, U7 input identity, first-wall/checkpoint/t20
predictions are null. Seal/Toutiao retain the frozen U6 input warning as a
reference, but **U7 does not assume either repaired or still broken**: collect
fresh resolve receipts and physical APK/sidecar hashes at final composition.
Outer ACK(95) 03:29:21 permits VM quarantine first and defers Mac cleanup until
U6 finishes. oc-t4 reports VM resolve success at 03:32:21 (Seal 6 / Toutiao 137
sidecars); Mac remains unchanged. This is not yet a pinned U7 input receipt.
Do not mutate either input root from this lane.

`intake.json` has 6 U6 scoring requirements and 10 U7 prediction requirements.
All start missing. `--readiness` exits 2 with the missing list; even a filled
checklist only means ready for evidence review, never freeze authorization.
This is not a substitute for G1/G2/G3, N1/N2 or reviewer validation.

```sh
python3 benchmark/2026-10-01-u7-prospective/skeleton.py --check
python3 benchmark/2026-10-01-u7-prospective/skeleton.py --readiness
python3 benchmark/2026-10-01-u7-prospective/test_skeleton.py
```

Wait for T7d and N6 board evidence, bind the final runtime/boot/input manifests,
review all 66 final predictions and their criteria, then use a new version and
register its CSV SHA **before the combined U7 run**. Component pretests must be
labeled training/prior evidence; they cannot score their own forecasts.

## U6 scoring handoff (pending, not executed)

After cc-t3 supplies the complete run and outer signs the images:

1. Verify unchanged U6 freeze, per-board 119 runtime / 36 boot identities and
   each key's APK, package, sidecars, resolve outcome and scheduled first attempt.
   A changed input or candidate is non-comparable, not a forecast miss. Preserve
   original first-attempt failures even if a retry succeeds.
2. Bind raw records, target PIDs, original hilog line numbers, first causal fatal
   review, image SHA and outer signature. Missing evidence stays unknown. Host
   inventory rejection has no target PID; report its pre-launch wall explicitly
   and document ambiguity rather than inventing a PID or relaxing criteria.
3. Use the unchanged U6 `score_reviewed` helper. Publish **three separate axes**:
   first wall, repaired-operation checkpoints, and t20. For each report numerator,
   eligible denominator, unknown/non-comparable and not-applicable counts out of
   66. Do not merge first-wall accuracy with screenshot success rate. Preserve the
   frozen helper's outcome names; list observed unpredicted walls separately with
   evidence rather than retrospectively turning an unknown forecast into a hit.
4. Checkpoints require positive execution beyond each operation; contradictory,
   masked or partial evidence stays unknown. `alive` and absent error strings
   are not sufficient. t20 uses outer-reviewed own content, not launcher/blank;
   retain explicit flaky treatment and separate component runs from combined U6.

The tests replay only **synthetic** observations through the frozen helper.
They do not constitute U6 scoring or visual approval.

## Landing

Take only `landing-paths.txt` plus this task's single root README/DIGEST line.
Do not copy the stale worktree's exception registries or previous-task dirt.
Validation receipts are under `validation/`; `results.json` states which work
is verified and which still waits on external evidence.

Git staging initially accepted 12 new files, then staging the isolated shared-doc
lines failed with `index.lock: Operation not permitted` (exit 128). No commit was
made. The index may contain that earlier partial snapshot; take final worktree
bytes from the landing list, plus the U7 README/DIGEST line only.
