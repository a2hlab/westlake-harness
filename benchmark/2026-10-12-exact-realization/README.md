# Exact parameter realization (offline candidate)

The old exact fingerprint rejects an ordinary host window-ID change. A backup
also has a different measured host UID. This candidate preserves complete SHA
checks and the frozen v6 transaction, with an explicit parameter-proof entry.
It does not sign a seal or perform a device operation during compilation.

The user approved exact parameter realization in main `121f4ecce`; the restore
wrapper boundary was added in `52747bbcb`. `user_approval` is pinned in the
request. Earlier composed-runbook's pending decision is historical; it is not
silently rewritten. Actual recovery and separate admission belong to the outer
operator. No device, VM or remote command was run by this implementation.

## Inputs already assembled

`source-fingerprint.json` contains 806 unique files: 319 baseline, 24 controls,
460 runtime and 3 stage objects. Every local byte source was rehashed.
`evidence/input-build.json` records 782 measured and 24 reviewed-template files.
The source is a composite historical candidate, **not a same-boot live seal**;
its `boot_id` is null, and individual source epochs remain declared.
`run.sh`, `prepare_jit50.sh` and `preseed_metasec48.sh` use the captured current
61b CAS from `restore-live-scripts/index.json`, not the archive's historical UID.

`request.5cd.placement.json` pins the actual read-only placement observation:
`a7d9ae13a29e84aeb13a00c6afab7e3b089f43ef0a33c8f8c72be05e50d42fab`,
boot `43bc3915-04bd-42ca-895e-26e8292911fa`, UID=GID 20011300, window_id=null.
`build_inputs.py` reproducibly assembles these two JSON inputs from the declared
main archives/CAS and composition inputs. It does not collect device data.

Set `WORKSPACES` to the directory containing `westlake-harness`, its worktrees,
and `westlake-inputs`. Run from the landed repository root:

```sh
EXACT=benchmark/2026-10-12-exact-realization
python3 "$EXACT/exact_realization.py" compile \
  --request "$EXACT/request.5cd.placement.json" --out /tmp/exact-5cd-placement
python3 "$EXACT/exact_realization.py" verify \
  --realization /tmp/exact-5cd-placement/realization.json
bash scripts/lab/demo_restore.sh \
  --realization /tmp/exact-5cd-placement/realization.json \
  --out /tmp/exact-5cd-restoration-preview
```

All outputs must be fresh paths. Compilation and preview use local files only.
The placement package reproduces the frozen v6 manifest exactly, including 487
transaction targets and the original executor. Existing target before-images,
metadata, directories, prerequisites and rollback semantics are unchanged.
Preview produces a separately reviewable enabled plan and prospective startup
fields, marked NOT_AUTHORIZED. It creates no authorization or board write.
Candidate placement does not require an active host or a WMS window.

## Source fingerprint and real seal

See `source-fingerprint.example.json` and `request.example.json` for schemas.
Each fingerprint file has `target`, full `sha256`, `groups`, pinned `source`,
and provenance (`measured` or `reviewed-template`, pinned evidence).
The declaration is validated against actual unique rows, not merely a number.

For a real seal request use `source_identity={kind:"seal",path,sha256}` and
`source_seal={path,sha256}` for the **same original immutable seal**. The original
four-group seal structure and non-file identity requirements are retained.
Extra U13 cfg/script/selinux-mode/table files are carried into the proof and
checked by full SHA; no list of 806 or 487 silently drops them.

If the seal's captured run.sh differs from the reviewed upstream run.sh, provide:

- `source_files[absolute_run_target]={path,sha256}` with captured source bytes;
- `source_parameter_evidence={path,sha256}` with independent running observations
  from the seal's `provenance.capture_boot_id` (or consistent `boot_id`).

The validator checks raw WMS PID/WID, proc UID/GID/birth/cmdline, HAP SHA and boot
bookends, then proves that the **single** `export WL_PARENT_ID` numeric span
produces exactly the captured whole-file SHA. Other bytes, duplicate assignments,
wrong boot, file-derived window claims, missing evidence and transport errors
reject. Source owner remains the proven 61b UID/GID 20011206. Normal WID changes
are not treated as arbitrary SHA exclusions.

To attach the later real seal without editing the candidate proof:

```sh
python3 "$EXACT/appendix.py" \
  --realization /tmp/exact-5cd-placement/realization.json \
  --sealed-request /path/to/real-seal-request.json --out /tmp/exact-seal-appendix
```

The appendix binds both proof and seal SHA, recompiles the same target bytes,
and adds every extra static seal target. Its status is
UNSIGNED_REQUIRES_OUTER_SIGNOFF; `signed_by` is null. The operator's later signed
record must pin this appendix. This is evidence generation, never self-signing.

## Window derivation and both selfcheck paths

`observations.py` defines `exact-parameter-observation/v1`; raw stdout and the
observation JSON are independently SHA-pinned. `commands()` only describes the
allowlisted read commands. Placement has no PID/WID. Running requires unique
visible `imehost0`, a matching process identity, current boot and installed HAP.

After the target icon starts the host, the outer collector supplies real running
observations. Derive a local run.sh with just the current WID (no device write):

```sh
python3 "$EXACT/exact_realization.py" window \
  --realization /tmp/exact-5cd-placement/realization.json \
  --observation /path/to/current-running.json --observation-sha256 FULL_SHA \
  --boot-id CURRENT_BOOT_UUID --out /tmp/exact-current-window
```

The outer operator owns any actual placement of that exact file. No WID is read
back from run.sh to prove itself. The receipt includes offset, old/new bytes,
input SHA, current boot, independent observations and full output SHA.

For **61b same-board** selfcheck, use the same request schema with `phase=running`,
61b UID/GID/serial/control_root and independently observed current window_id.
Provide pinned bytes for all source files (candidate `row.source`, or real-seal
`request.source_files[target]`). Same-board compilation retains every original
path/SHA, except the unique WID span, and has no restoration authority. It never
requires 5cd placement evidence. Its package contains only run.sh and a manifest.

For either 61b or 5cd, the explicit read-only selfcheck is:

```sh
bash scripts/lab/demo_selfcheck.sh --realization /path/to/realization.json \
  --serial FULL_SERIAL --boot-id CURRENT_BOOT_UUID \
  --observed /path/to/readback.json --out /tmp/exact-selfcheck.json
```

Recorded input produces OFFLINE_MATCH only. For the outer's actual read-only
capture, replace `--observed` with explicit `--hdc /path/to/local/hdc`; raw
readbacks are persisted beside the receipt. Actual reads may produce PASS, but
this is file/identity verification, not screenshot/UI acceptance. With a real
seal, system parameters, package version/APK SHA and inventories remain checked.
A candidate reports candidate-file-fingerprint-only coverage, never full seal.

## Actual restore admission (outer only)

The wrapper's old arguments still invoke the original t5 restore.py unchanged.
New `--realization` selects the explicit adapter. For execution it requires
`--execute --prepared PREVIEW_DIRECTORY`, separately pinned `--admission` and
`--authorization`, and `--lock-tool` with their respective `--*-sha256` values.
`--out` is a fresh original transaction directory for apply. Use
`--transaction-action rollback --out ORIGINAL_TRANSACTION_DIRECTORY` for retryable
rollback, with a fresh current-boot admission and original transaction binding.

The admission schema is `exact-realization-admission/v1`. Required fields:
`admitted=true`, `signed_by="outer(claude)"` (unchanged spare rehearsal role),
`generator_sha256` (restore.py), `realization_sha256`, `source_identity_sha256`,
`source_seal_sha256` (explicit null for a candidate), `prepared_manifest_sha256`,
`plan_sha256`, `executor_sha256`, `serial`, current `boot_id`, `expires_epoch`,
`action` (apply/rollback), `holder`, `lock_tool={path,sha256}` and the **complete**
`target_sha256` map from the preview. No such admission is supplied here.

The original executor authorization separately retains `approved_by=outer(codex)`,
plan/serial/boot/origin_boot_id/expiry and exact actions
`["place-only","one-reboot","rollback-safe"]`; the adapter additionally requires
its `derived_manifest_sha256` and holder. The unchanged executor validates real
preimages, tools and metadata; the real held-lock check precedes its subprocess.
Apply/rollback propagate the real executor rc. Unknown/nonempty cleanup remains
its explicit failure/retry receipt, never a fabricated ROLLED_BACK success.
Synthetic source/parameter evidence cannot authorize execution.

The v6 target-preimage guard and disabled-startup recipe already differ from
61b's enabled control configuration. They are explicitly recorded as inherited
v6 recipe spans and revalidated against the immutable v6 manifest, **not** added
to the new parameter whitelist. No old seal/provider/executor gate is changed.

## Reproduction and landing

`landing-paths.txt` is the exact small delivery. Runtime binaries are excluded.
Every test/compile reconstructs declared inputs from pinned main/CAS sources;
there is no dependency on an unlanded t4 package. `replay_clean_landing.py` copies
only the declared source/test inputs into a temporary clean layout and runs the
narrow tests with WORKSPACES explicitly supplied. Missing inputs reject rather
than fetching or guessing. See `results.json`, `freeze.json`, and persisted logs
for actual counts/exit statuses; synthetic tests are not board evidence.
