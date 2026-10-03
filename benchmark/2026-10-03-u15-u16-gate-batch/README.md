# Signed U15/U16 gate batch (prepared, not applied)

## Corrected boundary

The17 and26 signed review rows are **not**17 and26 native-registry entries. Six U16 findings project into the final native table; four opens also have one exact Flutter ELF-delta allowance, three call-set deltas and eight readonly strings remain signature-referenced evidence. Exact class additions belong to bundle-local static policy, not an invented global gate. The outer explicitly approved this separation. No signed packet or authorized bundle is edited.

`change-plan.json` describes four sequential stages, each independently runnable and guarded:

| Stage | Exact change | Preconditions/postconditions |
|---|---|---|
| native-u15 |204 approved rebindings,198 exact +6 explicitly signed line shifts| native table2966→3170; preimage `a3b44942...`, postimage `4586770d...` |
| native-u16 |208 final bindings,202 strictly inherited +6 explicitly signed|3170→3378; preimage `4586770d...`, postimage `b3a717d7...` |
| image-u16 |1 new exact U16 boot.art exception| image table2→3; preimage `fe335ada...`, postimage `0b27c3fa...` |
| static-policy |Derived U15/U16 policy outputs, no in-place bundle change| targets must not exist; original policy and snapshot hashes must match; outputs `283ab631...` / `fdba6688...` |

The first two stages append412 rows, not partial-manifest duplicates. Old rows are preserved as JSON values. Full tables remain private generated artifacts, not giant tracked snapshots. Each tracked unified patch is byte-exact and hash-pinned; the application reconstructs its postimage from the recorded preimage plus the exact approved additions and checks the actual patch bytes. No fuzz application or SHA-prefix matching is used.

## Signatures and provenance

- U15: `benchmark/2026-10-03-u15-review/outer-approval-packet.json` (201ea897d1),204 native rows and13 class additions. The six finding changes are only reviewed `/line` fields;198 other rows retain every field.
- U16 first: `benchmark/2026-10-03-u16-review/outer-approval-packet.json` (23c158f54c),17 scopes.
- U16 second: `benchmark/2026-10-03-u16-review/outer-approval-packet-2.json` (931058bb81),26 decisions. Final208 findings consist of202 strict field matches to U15 and6 findings covered by the exact first→second signature transfer. Evidence line numbers and sequence indexes are **not dropped**.
- `scope-projection.json` explains where every signed object is consumed. No extra native admission, BCP swap waiver or new global static gate is added.

The new returned oatdump context has SHA256 `e358fa5747480aafdd424ab6ad26b22770dba1d904429e300acd1ee7f678f249`. Its original full-log line132722 identifies Class `sun.nio.ch.PendingFuture` at `0x700d51c8`; line132752 binds `CANCELLED` to `0x7003e360`. The small file and source-line mapping are in `evidence/`; run2's Class-header context is not locally present and is not invented. Previously signed packets remain untouched. The U16 image row binds all9 inputs and both new outputs, only `[0x3e3b8,0x3e3c0)` (3 differing bytes inside the8-byte field), with26 other images identical.

## Static policy is a later rebind input

`static-u15.patch` derives two exact JAR allowances: NSD8 in stubs94a9 versus87cf, trampoline5 in runtime20e7 versus0349. `static-u16.patch` derives the8 donor-compilation dependency classes in stubs8593 versus94a9 plus the single Flutter9b82→eb90 production delta `190c0607...`. Neither permits dropping or reshaping classes. Auxiliary class presence gives no Wi-Fi/radio/callback behaviour guarantee.

Stage4 writes only `benchmark/2026-10-03-u15-u16-gate-batch/.artifacts/applied-static/static-policy-{u15,u16}-approved.json` under the target repository. It verifies the original authorized policy bytes but never overwrites them or `bundle.json`. A later explicit bundle rebind must point at these policies and recompute identities/tickets; this changeset is not that rebind. The ANL/host paired condition remains unchanged.

## Application guards and rollback

Default entry is a read-only preview: no held calls, locks or target writes. `--outer-apply` is explicit; only the outer executes it after all three boards UNLOCK and this changeset's referenced proof/context files have landed byte-identically in master. Each stage requires all three `board_note.sh held` results to be **rc1 with empty stdout and stderr**, matching the real helper's unheld contract. rc0 with empty output is ambiguous and refused. Any nonempty holder, unexpected status, SHA/tool/signature/patch/evidence drift or existing derived output refuses.

After the first held check, the runner takes nonblocking **existing board lock-file maintenance mutexes** for all three serials, retaining them through writes, tests and any rollback. It neither creates holder records nor issues board LOCK/UNLOCK, device commands or deployments. This closes the race where a new window could start between a held check and a gate-table write. An unrecorded lock owner also causes refusal.

Every stage precomputes all its changes before the first write, rechecks SHA immediately before replacement, uses fsync plus same-directory atomic replacement and retains original bytes/modes in an independent attempt directory. It then runs, capturing original combined stdout/stderr and rc:

1. `python3 scripts/lab/check_frozen.py --git`
2. `python3 benchmark/2026-10-01-native-gate-landing/test_predeploy_hook.py` (deployment_native_gate known answers)
3. `python3 benchmark/2026-10-02-t8-executor-support/test_static_checks.py` (generation_static_checks known answers)

Any stage failure stops and rolls back all targets changed by that invocation. Rollback first verifies **every** current target is one of this invocation's original/postimage hashes and validates all backups before any restoration; external edits are never clobbered. Separate stages retain their own rollback receipts. A successful all-stage application can be rolled back with the printed attempt path. No commit or push is performed.

## Outer commands (run only at the unlocked gap)

Read-only preview:

```sh
WORKSPACES="$HOME/orca/workspaces" bash "$HOME/orca/workspaces/westlake-harness-bms/benchmark/2026-10-03-u15-u16-gate-batch/apply-all.sh"
```

Full application, native204→native208→image1→static outputs:

```sh
WORKSPACES="$HOME/orca/workspaces" bash "$HOME/orca/workspaces/westlake-harness-bms/benchmark/2026-10-03-u15-u16-gate-batch/apply-all.sh" --outer-apply
```

Independent stage: add `--stage native-u15`, `--stage native-u16`, `--stage image-u16` or `--stage static-policy`; prerequisites are exact, so native-u16 expects the already-applied native-u15 postimage. Explicit rollback: use the same command with `--outer-apply --rollback <printed-attempt-directory>`.

Fresh preparation validation stages the future native table in private artifacts, never in master: U15 N1/N2 rc0 (99/105 excepted),U16 rc0 (103/105), both approved static policies PASS. Real original-active-table selftests are fresh rc0/0/0 (frozen30 checks, Hook10 tests, Static7 tests). Those are **not** an actual post-write/production run; the outer application repeats the three tests after each stage. Default preview and fixture known answers never access boards. All package execution/rollout flags stay false.

## Delivery validation

`validation.json` and `evidence/validation/` retain fresh local exits and portable transcript copies; the original bytes and SHA256 remain in the persistent lane `.artifacts/validation/` directory. Python18, artifact-free cold Python18, the Rust forwarding selector, agent-spec lifecycle and macOS `/bin/bash` syntax validation all pass. Cold tests deliberately omit `.artifacts` and caches. `landing-paths.txt` contains no live gate files, signed packets, authorized bundles or unrelated worktree changes. Preflight is listing/size/user-path validation only; it copies nothing and does not commit.
