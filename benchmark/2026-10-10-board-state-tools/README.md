# Read-only board snapshots and integrity-aware comparison

## Evidence first

This replaces the handed-off cc-t3 prototype, not the board state. The prototype
did not canonicalize the complete Android label tree, capped mount target reads
at 80, collapsed processes sharing one executable in its diff, and converted
missing raw evidence into an empty set. Those behaviors can hide precisely the
post-reboot differences the investigation needs.

The new tools use an injected transport and are tested entirely on Mac fixtures.
No HDC, VM, SSH, board lock or write was attempted. The known answer has **56
deployment targets and 85 mounted targets**, and retains the 85th target. Every
command's stdout/stderr/exit and hashes are retained. A changed boot, failed
mandatory read, unknown label or changed cfg content makes the capture
incomplete. Missing/drifted/symlink raw evidence is **incomparable**, never an
empty/equal set. Multiple PIDs sharing one exe remain separate observations.

## One-command capture

```sh
python3 scripts/lab/board_state_snapshot.py "$SERIAL" \
  --hdc "$HDC" --plan "$NATIVE_PACKAGE/package.json" \
  --out "$NEW_SNAPSHOT_DIR" --label pre-reboot
```

Run the same command to a new directory after reboot. Only full whitelisted OH
serials are accepted by the real transport. `HDC` or `--hdc` selects an existing
executable/forwarding wrapper; there is no implicit OrbStack dispatch. This
lane cannot connect to the server; actual collection belongs to an accessible
lane. Existing output directories are not reused or overwritten.

`--out` names **one capture**, not a multi-board container. Each board and round
must use its own directory, for example
`--out "$CAPTURE_ROOT/$SERIAL/$(date +%Y%m%dT%H%M%S)-$$-pre"`. For a second board,
change `$SERIAL` and choose another fresh directory. Reusing any existing `raw/`
refuses before reads/writes; the earlier evidence is never overwritten.

Output: `snapshot.json` plus `raw/<item>.txt` and
`raw/<item>.stderr.txt`. Each `items` row holds command, return code and both
SHA256 values. `readonly=true` describes the command set, not app lighting.
Return 0 means full requested collection/coverage with a stable boot; 1 means
the snapshot exists with partial coverage or failed reads; 2 is a setup refusal.
`capture_status` distinguishes `COMPLETE`, `PARTIAL_COVERAGE`, and
`INCOMPLETE_READS`. `collection_complete` reports read/boot integrity independently
from `coverage.deployment_targets_complete`; `complete` remains their conjunction.

The input plan is the full native package's `mounts`/`files`, a `recover_layers`
object, or explicit targets/kinds accepted by the shared audit parser. No
changed-files-only transaction journal is accepted as complete coverage.
Without a plan the general reads are still archived. A successful capture is
`PARTIAL_COVERAGE`, with a `coverage_warnings` entry, not a read failure. Its
observed fields remain comparable after raw SHA checks, but `complete=false`
cannot satisfy a full-deployment or reboot-simulator input gate. The target count is not forced to 56 for other
generations; the current deployment's 56-layer plan must be passed explicitly.

## Collected data

The inventory in `knowledge/gates/board-state-collection.json` cites RUNBOOK
`63668b4db9` and is hashed into each snapshot:

- Boot ID before/after, uptime and SELinux enforce mode.
- Canonical recursive labels for Android, host, child, registry, seccomp and
  every plan target; labels for every captured system/app mount target.
- Full `/proc/mounts` and init mountinfo, all `param ls` output and exact
  config-policy parameter queries.
- System/vendor/chipset init cfg names, file SHAs and raw contents. Content
  reads must match the preceding SHA inventory, otherwise the read race is
  surfaced instead of silently using mixed state.
- Default or explicitly enumerated config-policy layer probes, seccomp library
  hashes and appspawn sandbox JSON hashes; discovered `/system/etc/sandbox/*.json`
  files have an additional SHA-bound raw label read, even without a plan.
- Every appspawn/appspawn-x/foundation PID's exe, domain, mountinfo and
  **environment key names only**; environment values are never output.

Absent optional config-policy parameters and layer probes are diagnostic
records, not proof of absence/readability. Their original exit codes/stderr
remain available (`diagnostic=true`). Mandatory collection failures are not
suppressed. A missing partition init root is incomplete. No reported
`COMPLETE` proves a seccomp allow rule or successful app launch.

Real full parameter/raw outputs may contain private system information; keep
them at a persistent local evidence location rather than blindly committing
them to the public repository. This delivery includes only synthetic fixtures.

## Static comparison

```sh
python3 scripts/lab/board_state_diff.py "$BEFORE_DIR" "$AFTER_DIR" \
  --json "$NEW_DIFF_JSON"
```

The JSON compares mode/boot/uptime/layer roots, labels, parameters, file SHAs,
init configurations, all process records, mount rows/target sets and exact raw
records. Return 0 means the inputs are comparable, **not that they match**;
return 1 preserves an incomparable report; return 2 is a load/format refusal.
`seccomp_relevant_observations` only indexes relevant changes and always sets
`causal_proof=false`. It includes sandbox JSON labels, all `const.cust.*` changes,
and `system_data_label_counts` for `data_local_tmp`/`data_file`. Counts are only
over captured canonical `/system` paths, not a whole-tree census; paths and
captured scope are retained. `coverage_complete=false`/`observed-fields-only`
make missing-plan comparisons explicit. Only the exact prior missing-plan
warning is downgraded in legacy captures; any other read error, boot drift,
missing raw file or raw SHA mismatch still makes them incomparable.
Differences in enforce mode are not authorization to
change SELinux settings. Labels equal to the factory are not evidence of an
allow rule in the sandboxed child's domain.

Old prototype snapshots without raw hashes are deliberately incomparable. Do
not manufacture hashes as if those earlier captures had verified completeness;
keep them as diagnostic evidence and collect a fresh snapshot with this tool.

## Reboot simulator handoff

These snapshots retain the observed mounted view. They cannot reveal an inode
hidden by a bind mount or invent `DT_NEEDED` resolution. The pending simulator
therefore also requires a pinned underlying physical/source inventory and
native closure evidence. Missing underlay or domain queries remain unknown.
Cfg contents and per-process namespace mountinfo are now retained for that
normalization step; no snapshot is silently promoted into a reboot prediction.

## Reproduction

```sh
python3 scripts/lab/test_board_state.py -v
cargo test --manifest-path tools/spec-checks/Cargo.toml \
  --test board_state -- --nocapture
```

`results.json` and `evidence/` contain the fresh mock-only test/lifecycle/user
path outcomes and the operator handoff. No live recovery or 128-app regression
is claimed.

The first-board correction and its sourced, limited 61b/5cd regression replay
are recorded separately in `first-board-fix/`; the original receipts above
remain historical rather than being overwritten with the new test counts.
