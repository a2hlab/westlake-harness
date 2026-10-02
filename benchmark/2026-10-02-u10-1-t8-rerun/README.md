# Logged T8 rerun + U10.1/U11i — promotion plan review

The first T8 used the native underlay and removed frozen APIs. The corrected original T8 used the effective `f3bcc9d7` stubs but had no saved bake stdout. A same-path logged rerun differed only in one `boot.art` field (three bytes); outer ACK(90) 11:51:56 selected the **entire logged rerun output** instead of substituting its log for the original. This candidate is paired to that actual execution. Original artifacts and both earlier rejected/unarmed candidates remain unchanged and superseded.

## Immutable candidate and execution provenance

Package: `$WORKSPACES/westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle`.

Native manifest `4db327033870b597248a7188ab7f007e1979dafbb330edc58a4f052b6a086e00`; unarmed bundle `1b089fb42756d252c3a6ccd7535e746251caa2864b873f692648f659a1194bd5`. Payload native bytes remain U10.1 policy `0718f01e`, host r3 `65cc3535`, compat `015aa3a6`; runtime JAR remains U11i `5ae3dd29`. T8 swaps stubs `2f365a75`, framework `2257b835` and all27 images (`boot.art ab88cf38`, `boot.oat 4ba08485`, `boot.vdex 23c1f5b0`). U10.1's six changed paths and T8's29 declared targets have no intersection.

Selected27 outputs are persisted in `$WORKSPACES/westlake-inputs/generations/t8-rebake-effective/image-rerun/`. Actual logs, original recipe, tool identity, input/output inventories and paired JSON are in its `receipt/`. `bake_eff-rerun.log` SHA `853ad83340feee86e76536def41c0148464f28e78d524a6513d22da924ebec03`; reference log `29b53a02a38c228bcce612eac1b09c4dd77cf3939483368481879356f3c0f7ca`. Both executions returned0 with27 nonempty outputs. The remote nine input hashes equal the receipt and final effective BCP hashes. Selected output inventories match the archived files; `paired-build-receipt.json` binds all9 inputs/all27 outputs to this log, the frozen baker `ae865ddd` and exact recipe/host-tool identity. No T7 provenance exception was reused.

Source/recipe: cc-wiki `feat/wikipedia-line@fd25c9814a`, `benchmark/2026-10-01-t8-bcp-cluster/build/build_t8_effective.sh`, and persistent `$LAB_HOME/t8-cc-wiki/bake_eff.sh`. Original `image/boot.art d5b43805` remains preserved and is explicitly superseded for promotion. The three-byte nondeterminism is outer-reviewed; this package uses the logged rerun, not the unlogged original.

## Final production gates — all green

`production-dry-run.json`: `device_io=false`, `gates_passed=true`, `build_receipt.status=verified`, `static_checks.status=PASS`. It remains `deployable=false` solely because `rollout_ready=false`: no promotion/window authorization yet. Exact raw reports persist outside git (`raw-audit-location.json`); portable git reports are readable evidence, not reusable execution tickets. Re-run production preflight after landing/arming before deployment.

- rb PASS oat230/image108/concurrent-copying=false on the selected rerun files.
- Strict t4b switch checker PASS. `t4b-rerun-build.md` is an explicit SHA-bound **derived image-only binding** of archived frozen-baker flags to unchanged R155 libart/new OAT. It does not claim that R155 libart was rebuilt. Two initial CLI/input-readiness failures are retained in `evidence/`; only the completed `t4b.json` is the gate verdict.
- G1/G2 PASS on actual final images and effective U9 reference36. Seven unchanged BCP segments match; exactly stubs/framework are declared joint swaps. `String.hashCode` is36/36 instruction-identical.
- All three changed JARs pass effective `deployed_class_diff --frozen`. Exact two runtime drops only, paired5ae3/238f SHA + ACK11:34:15/8214ec53b4; no drop prefix is allowed. Frozen tagsoup/SSLSockets/NetworkInfo.State survive.
- Host/compat three physical open deltas are precisely approved by ACK11:57:27. Candidate/deployed/delta SHA, source interpretation and unchanged scanner observations are retained in `open-delta-review.json`, `outer-static-approval.json`, `approved-static-policy.json`. Compat rejects extension requests with ENOTSUP when its backend is missing; only no-extension inputs fall back to default dlopen. Host adds only two existing-namespace NOLOAD lookups, dlns_get and its marker.
- Final actual native bytes pass ABI/calls, consumer coverage102copies/86unique ELF +12 pinned app DSOs, readonly and exact reviewed strings. Raw strings exit1 remains recorded, not disguised as raw equality.
- N1=53 excepted/0 rejected; N2=103 excepted/0 rejected; all156 semantically identical to approved U10.1, no new findings. `registry-delta.json` is an additive delivery (do not overwrite master). Its cited prior report/evidence must land with it.
- Frozen registry:8 records,2 applicable artifact checks,0 violation. Final effective281members:253 byte-identical/28 changed; typed audits cover every changed artifact.

## Two-stage window proposals — outer ACK(90) 12:18:05

The earlier proposal incorrectly required a complete 166-key signoff within one
45-minute window. Observed throughput is only 20–27 keys per board window. The
new plans separate observation from promotion. Both phases remain review-only;
no arming, lock or device command is authorized by this revision.

`plan-diff.txt` shows the three original plans' changes. `plan-review.json` records
exact coverage: **166 unique keys**, Stage A assignments **56/55/55** and U9-lit
regression keys **37/38/40**. Toutiao is the first 5ea key and is removed from
61b original. Each board then runs lit-original, lit-cv2, unlit-original,
unlit-cv2; relative order within each group is preserved. Predictions-v5 is unchanged.

### Stage A: observe and always restore

`window/plan-{5ea,5cd,61b}.json` has phase A, a 45-minute ceiling and no new key
after minute35. Apply verifies same-board signed U9 before changing anything.
All27 images, two BCP JARs, runtime JAR and native changes remain one stopped-parent
transaction. Activation smoke checks318 identities/316 paths, both fingerprints,
real host owner_verified marker, ART/JVM each1 and bridge/runtime each2 by
load-base (the signed U9 multiplicity). Expected RUNTIME is `f3b604c94df4` on
5ea/5cd and `d6848fa2c989` on61b; BOOT is `e3806b65a079` on all boards.
These remain offline expectations, not live evidence.

`--finish-observation` **always** calls the existing signed-U9 rollback,
318 verification, recovery smoke and final verification. It ignores promotion
decisions and writes `observation-restored.json` only after the entire finish
succeeds. A finish failure retains the lock. OrganicMaps uses the existing
bounded cold_stop retry. No partial result may retain this candidate.

`promotion_dispatch.py` keeps the pre-lock infra sequence: offline admission,
then orb health, VM workspace bind SHA and exact HDC serial, then master
`board_run --detach`. It also refuses a stale plan/package SHA and disabled plans.
On approved apply, `window-input.json` snapshots the serial, phase, bundle/manifest
SHA, planned keys and expected fingerprints before any device mutation.

### Resume Stage A without rebuilding

Use the **canonical first-window plan** and all previous roots for that board:

```sh
python3 "$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/continue_observation.py" \
  "$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window/plan-5ea.json" \
  --prior-root "$PREVIOUS_WINDOW_ROOT" --output "$NEW_PLAN_DIRECTORY" --run-root "$NEW_WINDOW_ROOT"
```

Repeat `--prior-root` for every finished window; always use a fresh plan directory
and run root. The helper refuses SHA/serial/phase drift, incomplete U9 finish,
missing restoration receipts and batch fingerprints that differ from the
candidate. Only terminal per-key records in assigned shards are subtracted.
Started/interrupted/missing records remain pending; smoke controls never consume
assigned keys. Known install/app failures count as tested outcomes, **not lit**.
The new plan preserves original priority, contains only unmeasured keys and is
disabled pending outer approval. Any screenshot gap or inconclusive outer verdict
can be explicitly scheduled for a reviewed repeat; it cannot silently promote.
The helper makes no device call and never rebuilds/arms the package.

After outer approves Stage A, the existing prepare approve route will arm the
bundle/composition consistently and bind plans to its final armed SHA. Every
subsequent A/B window uses that same SHA and identical payload bytes; this
revision preserves the currently unarmed `1b089fb42756` bundle unchanged.

### Stage B: separate short promotion only after complete signoff

`window/plan-promotion-{5ea,5cd,61b}.json` are **separately disabled drafts**,
30 minutes maximum (minute20 cutoff reserves finish time). Each applies the
same package, runs smoke/318/dual fingerprints and a fresh Toutiao t20 retest.
Stage A's shared `window/outer-stage-a.json` must have `phase=A`, `signed_by=
outer(claude)`, exact bundle/manifest SHA, all166 reviewed keys, zero regression
among the115 U9-lit keys, signed HW/ZZ/Toutiao and `promotion_authorized=true`.
Missing/incomplete/wrong-SHA evidence refuses before infra/LOCK and again before apply.

Retention additionally requires a **fresh same-board** `outer-promotion.json`
inside that B window root: phase B, exact serial/window_root/bundle/manifest,
`toutiao_t20=lit`, `controls_t20_lit=[helloworld,zigzag]`, no confirmed regression,
plus fresh smoke PASS and final318/fingerprints. No current-window signed review,
smoke/identity failure or regression means unconditional U9 finish. This phase
is not authorized until outer explicitly approves it after A completes.

## Tests and scope

19 plan/hook/continuation safety tests pass; 82 harness tests pass (3 skipped).
Tests cover forced Stage A rollback even with a promotion decision, failed-finish
receipt suppression, exact166 priority/ownership, interrupted-key continuation,
SHA/fingerprint/cleanup refusal and fresh Stage B screenshot/identity admission.
The earlier15 static tool tests and accepted artifact/image gates remain unchanged.
An initial root-test invocation with system Python lacked dependencies; the
prescribed env-mac.sh interpreter rerun passed all82.

At the plan-revision checkpoint, no payload change, bundle re-arm, board command, lock, apply or promotion had occurred. The later window attempt is recorded below.
R2: plan safety and offline coverage verified; A/B board behavior unverified.

## Stage A window1 attempt — rejected before candidate writes

The exact renewed host delta14e37320 was applied through prepare's atomic policy,
bundle and composition transaction. The armed bundle is now190afedd3ddb (payload
bytes unchanged). Mac production dry-run passes all gates and is deployable.
The three detached runners acquired their locks at12:49:47, verified U9, then
VM preflight refused missing dexdump. All apply receipts have device_io=false;
no candidate transaction was created. Automatic finish passed recovery smoke
and final318 on all boards; locks were released. Candidate measured keys=0;
all166 assigned keys remain unmeasured. This is no candidate behavior verdict.

The VM tools directory initially had only ssh/scp. Versioned Mac SDK/NDK wrappers
now provide dexdump/llvm-nm/llvm-objdump/llvm-readelf, using the same approved Mac
tool bytes and shared .vm-tmp (created before Python may fall back to /tmp).
Wrapper tests cover selection, quoting, invoked tool name and missing-tool refusal.
A real VM rerun then found a separate landing omission: master has zero candidate
exception rows while the lane has156 approved rows. N1/N2 findings match Mac's
approved issue-id sets exactly (53/103; zero new findings). The already-delivered
registry-delta.json must be appended to master by outer; the gate remains closed.
No exception was fabricated, no rejection suppressed and no new runner started.

window1-environment-report holds raw recovery facts, control t20 contact sheets,
final fingerprints/diff/absent and measured/unmeasured lists. Recovery pictures
are explicitly U9, never presented as candidate screenshots. Full failed logs,
apply receipts and recovery directories remain at window/boards/u101-t8-A1-20261002T124934/;
raw VM gate logs are also persisted in the inputs generation audit directory.
After the additive registry landing, rerun real VM production gates before a
fresh same-package window1 retry. No rebuild and no additional keys are needed.
