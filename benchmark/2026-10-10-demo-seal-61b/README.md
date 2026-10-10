# 61b v1/v2 seal orchestration — offline revision

## Evidence first

The original workflow hardcoded WITH_BOAT=1, required two active overlays and Boat LAP, and required a v2 regression admission even for v1. Preview skipped binding validation, so a plausible preview did not prove v1 could execute.

This revision adds **--mode v1|v2, default v1**, with mode bound to the approved plan. **39 orchestration/UID-slot fixture tests pass** (`evidence/tests-v1-v2.txt`); the unchanged seal compiler's **18 tests pass**, including actual v1/v2 compiler and selfcheck cases (`evidence/compiler-tests-v1-v2.txt`). Syntax, Python compilation and both previews exit0 (`evidence/checks-v1-v2.txt`). No board, VM, SSH, lock or deployment was accessed. The template remains disabled with pending bindings; no live seal/UI success is claimed.

| Requirement | v1 (default) | v2 (explicit) |
|---|---|---|
| Installer | WITH_BOAT=0 | WITH_BOAT=1 |
| Active overlays | Toutiao Route B only | Toutiao Route B + admitted Boat |
| Boat compiler slot | Explicit absent, reason, no files | Active, reviewed admission and roles |
| Signed UI checks | Parent init, socket0660, HW/ZZ t20, Toutiao desktop click/refresh/article | Same + boat_five_touch_lap |
| Regression | Original U13 identity runner; all128 + healthy5cd signoff | Additionally pinned outer-reviewed overlay-aware identity admission |
| Output | seal_stage=v1, independently checked | seal_stage=v2, independently checked |

The compiler retains **two named slots** in v1: Boat is declared absent, never active. Omitting Toutiao is forbidden. The v2-only regression_admission reference is neither opened nor pinned in v1; its null template value does not block a fully bound v1 plan. Execution rejects a CLI mode differing from plan.mode, before any dispatch/output writes.

## Commands

```sh
bash scripts/lab/demo_seal_61b.sh
bash scripts/lab/demo_seal_61b.sh --mode v2 --dry-run
python3 -m unittest discover -s benchmark/2026-10-10-demo-seal-61b -p 'test_*.py' -v
```

Preview prints commands and per-step criteria only: no transport, lock or output-root creation. Future outer execution requires a fully reviewed plan, exact SHA authorization, fresh output root and approved window/lock handoff:

```sh
export WORKSPACES="$HOME/orca/workspaces"
bash scripts/lab/demo_seal_61b.sh --mode v1 --serial 61b --execute \
  --plan "$REVIEWED_V1_PLAN" --authorization "$OUTER_AUTHORIZATION_JSON" --out "$FRESH_OUTPUT"
```

For v2, change plan.mode, bind Boat admission/LAP and the v2 identity admission, reauthorize the changed plan SHA, and pass --mode v2. The v1 authorization cannot authorize v2.

## Fixed workflow

1. Fresh lock-conflict receipt, boot UUID, Enforcing and exact signed61b **319-path** inventory.
2. DISABLED, target boot, different ready boot UUID, persistent DISABLED.
3. Shell and init mountinfo: no mount at/below the **56 recover targets**, independent of source spelling. Empty/malformed output refuses. Repeat immediately before the guarded installer; pin source SHA and approved bare-boot support. ARCHIVE only on this bare no-bind boot.
4. Mode-specific installer, INSTALL_OK; concrete uid-dynamic Toutiao slot below, enabled receipt tied to bare boot; then U13 ENABLE.
5. Complete pre snapshot, fresh policy gate and physical simulator inputs. Simulator rc1 is advisory FAIL/UNKNOWN, not safety PASS; rc2/missing prediction stops.
6. Second target boot, changed ready UUID. No Mac replay, label repair, deployment, repave or provisioning during autonomous acceptance.
7. Enforcing/no INVALID; fresh outer-signed mode-specific screenshots. Independently verify one root AppSpawnX with PPID1, socket 660:0:6005:u:object_r:appspawn_socket:s0, and no invalid after taps. Toutiao uses **foreground desktop click**, never background aa start.
8. Complete post snapshot/diff; all128 without reinstall; exact membership/no missing captures, signed healthy5cd reference and fresh outer no-regression receipt in **both modes**.
9. Same boot complete live-readonly package/version/APK/hash inventory; unchanged build_seal.py consumes mode-specific overlays; compiled seal_stage must match.

Hard failures stop later steps and retain raw stdout/stderr, return codes and hashes. Only read-only boot readiness retries. Recovery references are printed, never automatically dispatched: separately authorized fresh61b ticket replay or signed-bundle repave. The5cd ticket is provenance only, not reusable61b authorization.

## UID-dynamic Toutiao integration

The pinned concrete provider is **scripts/lab/demo_toutiao_slot.py --execute**, called from the exact plan/SHA/serial/current-boot context. It stages cc-wiki d837acf904 worker/owner/reconcile_uid.sh verbatim. prepare_payload.py removes the fixed UID20010053 precondition.

The six reconciled filename types are **run.sh, preseed_metasec48.sh, prepare_jit50.sh, start-parent.sh, watchdog.sh, request.bin**, including placement aliases. They are excluded from immutable.tsv; reconciliation/readback covers text UID, binary UID/GID offsets312/316 and runtime ownership. Archives, appspawn-x, screen-gate, worker, owner and reconciler stay SHA-pinned.

Order: Toutiao DISABLED → verified local payload (system files staged into data first) → reconcile → installed-host UID and all immutable members read back → same boot → rootfs transaction places worker/inactive cfg, then active cfg with permissions/labels → rm DISABLED → restore original read-only rootfs if remounted. Receipt includes **enabled:true, boot_id==bare_boot, uid_mode:installed-host-dynamic, reconcile_checked:true, immutable_preserved:true**. No application is launched; failed checks refuse ENABLE.

Local preparation does not enable the slot; pin the resulting placement.json in the plan:

```sh
python3 benchmark/2026-10-10-toutiao-boot-slot/prepare_payload.py \
  --inputs "$REVIEWED_TTBUNDLE_ARCHIVES" --out "$FRESH_PREPARED_PAYLOAD" \
  --payload-dir "$WORKSPACES/westlake-harness/benchmark/2026-10-10-toutiao-boot-slot/payload" \
  --uid-dynamic-dir "$WORKSPACES/westlake-harness/benchmark/2026-10-10-u13-autostart/boot-slot-uid-dynamic"
```

### Independent blocker: original helper mutates immutable controls

The **real d837 reconciler**, run offline with mocked installed UID20011206, returned0 and correctly patched both request fields, but broad find *.sh changed **reconcile_uid.sh, route-b-owner.sh and westlake-u13-toutiao-overlay.sh** under durable scripts. Raw output/source/after SHA evidence: `evidence/uid-immutable-original-negative.json`. Comments/OLD_UID literals were rewritten; next boot's immutable gate would refuse.

This revision does **not** exclude those controls or modify cc-wiki's approved source. Post-reconcile immutable readback refuses ENABLE. The source owner must restrict rewrites to reviewed business files, preserve controls, verify the real helper and bind new source hashes. Positive transport fixtures prove wiring/order, not that the original helper passes this gate. This independent blocker was reported at15:45:18, separately from the fixed v1 mode blocker.

## Binding handoff

Each pinned provider receives DEMO_SEAL_OUT/SERIAL/BOOT_ID/PLAN_SHA/STEP/PLAN, exits0 and writes <step>.json with exact serial/plan SHA. Output root must be fresh.

| Provider | Required output |
|---|---|
| lock_check | Fresh no_conflict:true, reviewed window/lock handoff |
| toutiao_slot | Verified dynamic reconciliation, immutable preserved, enabled, exact bare boot |
| reboot_inputs | This pre snapshot's physical underlay/closure/query/init-order inputs |
| acceptance | Current boot, outer signature/time, no_mac_repair:true, mode-specific checks, pinned human evidence |
| regression_review | Same envelope, exact comparison SHA, baseline5cd, all128/no regression/identity unchanged |
| seal_snapshot | Same boot complete live-readonly files/packages/APK hashes; board snapshot alone is insufficient |

Outer still binds the guarded **bare-boot-capable** installer, reconciler preservation repair, prepared slot, healthy5cd reference/comparator layout, physical simulator inputs, live UI/128 receipts, final inventory and authorization. Existing template references are not approval. **Only v2** additionally requires Boat and overlay-aware128 identity admission. No identity gate, registry, frozen artifact or board is modified.

Historical tests.txt/dry-run.txt/checks remain; current evidence is explicitly named tests-v1-v2.txt, compiler-tests-v1-v2.txt, checks-v1-v2.txt, dry-run-v1.txt and dry-run-v2.txt. Changes remain in this worktree for outer land; Git index metadata is not writable.
