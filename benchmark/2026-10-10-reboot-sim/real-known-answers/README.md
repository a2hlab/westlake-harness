# Real observed preload/map known answers

## Evidence first

**A mounted-view label check is not complete reboot safety.** The earlier
no-plan snapshots only listed route directory mountpoints and two patched
members; they could not identify the 23 historical bad library basenames.
The new rule is to obtain a recursive declared scope, verify every referenced
raw stdout/stderr SHA, and keep cross-board object inference explicit.

| Case | Pinned source | Raw receipts | Observed file checks | Result |
|---|---|---:|---:|---|
| 5cd healthy v2 | recursive snapshot `2e55b3587d2808a1` | 259 | 58 (sandbox + 57 route paths) | scope PASS |
| 5ea healthy v2, before apps | cx-t0 snapshot `5cbd3e56e7ed23b4` | 256 | 30 (sandbox + 29 route paths) | scope PASS |
| 61b pre-fix | original manual `61b.txt` `2eb80d83f1ca36ed`, basename list `94696c8f81a99ee4` | two pinned source texts | 24 (sandbox + 23 library basenames) | recipe FAIL |

Full references and SHA are in `inputs.json`. `prediction.json` and
`prediction.tsv` are generated twice with identical bytes. They retain raw
file, line, text and SHA for every positive label, plus the signed policy proof
for appspawn file read/open/getattr (sandbox) or read/open/map (route libraries).
Policy bytes are `7d23015f...`; the signed 32-proof report and single recipe are
both pinned. The report's recipe identity uses the producer's actual
`json.dumps(recipe, sort_keys=True)` formula, not the shell generator's compact
JSON formula. These different hashes are not interchangeable.

The 61b pre-fix sandbox path is explicit in the original text. Its library
list contains **basenames**, not canonical per-file paths. Historical mountinfo
names both route roots; healthy captures supply their member paths. We report
`canonical_candidates`, not pretend to have captured each old inode's path.
22 basenames have two candidates; one has one. The wall count remains **23
basenames + one config = 24**, never 46 libraries or 57 bad paths. The repaired
61b snapshot `f5cf9fc0` is not rewritten into the negative fixture.

FAIL here means a mismatch with the deployed single label recipe. Missing DATA
rows in the positive policy report are **not** proof of a SELinux denial.
`policy_denial_proven=false` on every historical negative row. Neither report
claims root-cause proof for a specific duplicate mapping or a new live reboot.

## Reproduce the real known answers (offline)

```sh
export WORKSPACES="$HOME/orca/workspaces"
HERE="$WORKSPACES/westlake-harness-bms/benchmark/2026-10-10-reboot-sim/real-known-answers"
python3 "$HERE/audit_scope.py" --inputs "$HERE/inputs.json" --out "$FRESH_SCOPE_OUTPUT"
```

Exit 0 means the **known-answer comparison** matched: healthy cases scope PASS,
historical case 24 mismatches. It does not mean the historical board was safe.
Every generated report explicitly has `safe_to_reboot=false`,
`execution_enabled=false`, `board_access=false`, `advisory_only=true`.
Missing/drifted evidence exits 2 before creating an output directory; missing
required basenames or positive proofs cannot PASS.

## Before the final 61b seal reboot

The collecting/outer lane first takes a fresh snapshot. Use the real 56-layer
plan where available, **or** the supplied six-target `capture-scope-plan.json`
only for this narrower label inventory. That plan deliberately recurses the
route root and sandbox JSON directory. It is not a deployment/recovery plan;
`deployment_targets_complete=true` means all its six declared scopes were read,
not that the 56-layer transaction was checked. Per-serial timestamped output
directories prevent collisions. The delegatable `capture-readonly.sh` supports
only healthy spare serials; the final 61b collection command is explicit:

```sh
python3 "$WORKSPACES/westlake-harness/scripts/lab/board_state_snapshot.py" \
  61b0657200000000000000000324012c --plan "$HERE/capture-scope-plan.json" \
  --label pre-v1-seal --out "$FRESH_61B_SNAPSHOT_DIR"
shasum -a 256 "$FRESH_61B_SNAPSHOT_DIR/snapshot.json"
python3 "$HERE/audit_scope.py" --inputs "$HERE/inputs.json" \
  --observed-snapshot "$FRESH_61B_SNAPSHOT_DIR/snapshot.json" \
  --snapshot-sha256 "$ACTUAL_61B_SNAPSHOT_SHA256" --out "$FRESH_61B_SCOPE_PREDICTION"
```

The second command audits **that new observed state**, not the historical
negative case. Its exit 0 still means scope PASS only. Full reboot inference is
the separate `scripts/lab/reboot_sim.py --inputs "$PINNED_INPUTS_JSON" --out
"$FRESH_FULL_REBOOT_PREDICTION"` eight-input interface. Independent hidden
underlay, persistent sources, namespace-resolved DT_NEEDED closure, directory
traversal and exact negative queries remain outside this scope. Do not substitute
mounted labels for them or reuse the old captures as fresh pre-seal receipts.

The outer executed the 5cd capture at 13:47. cx-bms only read files, generated
reports and ran local tests; no HDC/board/VM/SSH commands were executed by this
lane. No lock, relabel, deployment or reboot authorization is issued.

## Tests

The existing Rust `demo_baseline_reboot_sim` selector runs the original 20
simulator tests and the new scope tests. Tests cover missing/raw-drifted input,
missing route coverage/proofs, label-only negatives, real recorded answers,
ambiguous duplicate route identities, scoped pre-seal CLI and no safe flag.
Original logs are under `evidence/`; the large original capture trees stay at
the SHA-bound persistent paths in `inputs.json`.
