# U4: an offline rollout plan, not a deployment receipt

The earlier cluster handoff listed proposed repairs, not everything actually in
the candidate. This plan counts only N3/N3b and J4 changes already built. J5
`dbce2eee` arrived during preparation but lacks the exact class N3b requires;
five boot-class targets are outside U4. J3's reviewed baseline is **25
lit / 41 unlit**, not its process-survival count. No board command ran in this task.

`predictions.csv` / `predictions.json` cover all **66 keys**: **1 conditional
unlock candidate (noice), 20 checkpoint advances, 45 unchanged**. These are hypotheses;
predicted additional lights are **unknown**, including that unlock candidate.
NewPipe is already lit: passing PlayerService signing adds no light. fd-noice is
already lit; its background SSLSockets wall is not repaired by J4's media_router.
Immich's property-symbol improvement does not remove its earlier verifier wall.

## Fixed artifacts and prerequisites

| Component | Identity / action |
|---|---|
| U3 native | N2 package `51a78bde`, runtime `d932f2ba` |
| U3 Java | J2 `0715c964` underneath J3 `75c2068c`; final J3 SHA in probe receipt |
| U3 last fingerprint | `0b81cdbe0ed9`; last observed before USB disconnection, not current state |
| U4 native | Complete `westlake-generation-n3b-53bb18d1`, manifest `53bb18d1743a69bee9be98b4704afc5e684f57c002687fc2771678c2edd575d3`, runtime `7c9c6240c7bbaa529460d7acb8e12629e3c9f9151b390a071f1d10a0bd727042` |
| U4 Java | Delivered `vm-copies/j5-dbce2eee/oh-adapter-runtime.jar`, SHA `dbce2eeada1d40d34d7904936bc09860d6ad30009781444ecd73661ad7e7e223`; native contract **not closed** |
| Installer, ART, boot | Keep FZ-001 `6aadb8b4/7048c7c5`, R155 ART `59e1bb45`, existing image108/oat230; no #91/T7 boot artifacts in U4 |
| WebView | Real provider APK, metadata/signatures, native closure, child-visible paths, data ownership and compatible create entry remain integration prerequisites; see N3b JAVA-HANDOFF |
| Boards | A=5ea, B=5cd, C=61b; **D unassigned**. No Android-reference substitution |

N3b changes only one file **relative to N3**. Relative to U3/N2 it contains the
whole N3 host/ANL/ABI/private-library batch. Use complete same-platform `--upgrade`
from U3; **never just replace runtime from U3**. N3b's `rollout_ready=false` is
honest metadata, not a switch to flip. The deployer does not enforce that field:
the operator must check the cross-layer prerequisites before using it.

`inputs/` pins cx-bms's four shards and J3 evidence by SHA in `sources.json`.
The four key lists are unchanged (17/17/16/16). `cohort.json` fills two original
null identities (noice and x) from actual J3 records, with provenance in
`input-pins.json`; `shards.json` pins that derived manifest. Subway explicitly
changes to `ffd32287...` plus split `68920637...`: **an input variable**, not U4
runtime benefit. Seal/Toutiao sidecars use the input-recovery receipt; host input
success is not proof of device installation. Keep all split/sidecar identities.

Before scheduling: register/provision fourth OH board; obtain corrected J5 and
paired host tests; close WebView prerequisites or have outer explicitly narrow
the rollout and Tutanota prediction. Do not silently skip shard D or claim 66
observations from 50. Do not fabricate provider support from feature=true: native
prime/publish return values AND cache/public identities must succeed.
The 20:37 cx-bms audit (`inputs/webview-contract-gap.json`, source SHA recorded)
finds no definition of `adapter/core/WebViewUpdateServiceAdapter` in J5 or the
candidate boot JAR union, while N3b FindClass requires it. A similarly named
dynamic proxy does not satisfy this ABI. **Tutanota currently predicts unchanged**;
the earlier conditional-unlock forecast is superseded. Do not silently edit the
already delivered native package to compensate. cc-t3 owns the paired Java fix.

## Board-return sequence

1. Outer explicitly restores a board window. Acquire each full-serial lock and
   confirm held. Read boot ID, active ledger, complete native/installer/JAR SHA,
   shell and daemon-root views, mount stack and live fingerprint before writing.
   An old receipt after power loss is not current state. No unrelated foundation
   restart, USB reset or boot-image work in this window.
2. Reestablish U3 if bindings were lost: original N2 native replay first (fresh
   boot uses normal deployment, not `--upgrade` against a nonexistent active
   generation), then cx-bms `replay_unified_state.sh` J2→J3. The latter checks
   native and installer; it does **not** restore missing native bindings. Verify
   the unified fingerprint. Fourth board needs the same firmware/provisioning.
3. Save each board's exact JAR layers and boot-bound ledger. Existing native
   deployment expects exposed r8b; prior instruction says keep J3. **Resolve
   that overlay procedure with outer before activation**, or use a reviewed
   deployer path preserving it. This offline plan grants no new permission to
   unmount J3. Never copy the hard-coded 61b receipt to another board. If approved,
   stop parent using begetctl only, expose the recorded layers transactionally,
   upgrade full N3b, then restore the approved lower layers and overlay J5 before
   spawning test children. Failure unwinds only owned layers, restores native,
   then reinstates exact J2/J3; read shell AND parent root back.
4. Run `check_frozen.py --package` with current registry and source receipts,
   offline deployment dry-run for each registered board, then the reviewed native
   activation. Verify package aliases/SHA, single ART, bridge `84695d62`, route
   libopenjdkjvm, runtime/ANL/host and prerequisites. J5 must resolve both N3b JNI
   methods from the resident runtime; no duplicate runtime loaded privately.
5. On one short-window board: HW/ZZ first; compare with fresh same-board U3
   controls. Then Tutanota/provider and one key per native cluster (LocalSend,
   SPD, Firefox, Libre, Mindustry), plus Auxio/NetGuard/Aegis/Fitness/Droid-ify
   protections. Do not treat a single known intermittent ZZ/Fitness flip as
   either a definite regression or an exemption: repeat same conditions three
   times and hand images/faults to outer. Deterministic new control failure stops
   rollout and restores U3. Missing provider prerequisites stop Tutanota claim.
6. After short-window acceptance, activate the **same** complete U4 identities on
   four boards. Compare entire fingerprint path→SHA maps (not merely counts or
   labels); JAR overlay identity, APK cohort, firmware, installer and boot image
   must match. Record board/boot as variables. Run four shards concurrently,
   starting 5 seconds apart, each within a 45-minute window. Batch enforces 16M
   hilog/private off, wake timeout, clock skew <=120s; failed preflight rejects.
7. Preserve original `facts.txt`, per-app `record.json`, t5/t20 images, all first
   fatal text plus earlier native relocation causes. Read images for lit verdicts.
   Audit four receipts for 66 unique keys, no omissions, pinned APKs, identical
   fingerprint maps; do not use the historical three-shard merger. Archive four
   facts files verbatim rather than inventing an aggregate TOTAL. Missing data is
   unknown; no-fatal/alive is not lit. Compare all 25 baseline protections, not
   just the five smoke keys. Complete/fail every shard explicitly.
8. Failed candidate: coordinated return to U3 on changed boards, verify native,
   frozen files and original JAR layers, then HW screenshot and final fingerprint.
   A disconnect/reboot/missing rollback readback is **rollback unverified**, not
   restored. Release the locks and report the actual state; never continue with
   a mixed unified generation as if it were signed U4.

## Command preparation (no device IO)

From this worktree:

```sh
python3 benchmark/2026-09-30-u4-plan/plan.py --write-predictions
python3 benchmark/2026-09-30-u4-plan/plan.py --commands
```

The second command currently exits 2 without explicit J5 and fourth serial. Even
with delivered dbce2eee it rejects the known cross-layer mismatch. After
outer registers the fourth OH board, bind only D's serial in a **new** copy of
`shards.json`, preserving keys and cohort SHA. Then render, do not execute, with:

```sh
python3 benchmark/2026-09-30-u4-plan/plan.py --commands \
  --shards "$BOUND_SHARDS" --j5 "$J5_JAR" --j5-sha256 "$J5_SHA" --run-id u4
```

Output gives quoted Mac→VM commands using **master** bms_batch, fixed cohort,
`--reinstall --hilog 20 --shots 5,20 --focus-check` and full serial in every run
ID. Rendering validates local identities only; it neither deploys U4 nor grants
a board window. Log the 66 predictions with PROGRESS before the first launch.
Deployment recipe, once the above gates and overlay procedure are approved:

```sh
python3 scripts/lab/check_frozen.py --package "$N3B_PACKAGE"
bash scripts/lab/deploy_generation.sh "$SERIAL" "$N3B_PACKAGE" --dry-run
bash scripts/lab/deploy_generation.sh "$SERIAL" "$N3B_PACKAGE" --upgrade
# Failure on same boot / owned transaction, after respecting JAR overlay order:
bash scripts/lab/deploy_generation.sh "$SERIAL" "$N3B_PACKAGE" --upgrade --rollback
```

## Failure bisection order

Run `scripts/lab/compare_runs.py A B --keys affected` on every comparison and
quote `variables:` verbatim. A package is **not** automatically one variable:
this tool groups installer pairs only, so N3's many changed paths remain many
variables. Hold board, boot, APK/splits, clean-install mode, network and inputs
constant. Repeat three times first when identical-state outcomes flip.

| Stage | Paired states / decision |
|---|---|
| Control failure | Restore U3; reproduce U3 control with same clean mode. Failure there is not attributable to U4 |
| First split | U3; N3b+J3 (native half); N2+J5 (Java half), then full pair. J5 half may need its documented native-unavailable behavior; if unsafe/unavailable, use J4+N2 and record that J5/N3b interaction remains unresolved, not a valid substitute proof |
| Java half | J3 vs J4 at same native isolates the two J4 fixes as a group; J4 vs J5 at N3b isolates WebView integration. Further split J4 signature vs media_router in temporary derived JARs only after scheduling; keep frozen classes unchanged |
| Native half | N3 vs N3b at same JAR isolates runtime publication addition (one path). N2 vs N3 still multi-path |
| N3 groups | Split runtime EGL registration vs loader/ABI group, after constructing compatible packages with complete dependency closures. Keep host+ANL+private-library publication together first. Then bisect ABI stdio/property vs facades/OpenSLES, retaining required suppliers in both halves. Do not combine mismatched protocol pieces and diagnose their startup failure as app regression |
| Only full pair fails | Native×JAR/provider interaction; preserve both passing half receipts and failing pair, then split call timing/cache identity vs provider native closure. No single-component attribution |
| Input change | Re-run same APK/sidecars under old/new runtime; Subway's changed APK cannot establish native improvement against historical J3 |

The intermediate split packages are a **future construction plan**, not existing
signed artifacts. Run frozen/strict link/closure/dry-run gates for each. No split
may weaken frozen behavior; outer must register any permitted frozen revision.
At most one diagnosis window per board; return to the currently signed unified
state before release. See [PROBES.md](PROBES.md) for the two prepared experiments.

## Verification and limits

12 new tests passed (66-key/protection accounting, unresolved-input refusal,
quoted master command rendering, actual JVM forwarding/exception identity, A/B
DEX delta, and FakeBoard rollback including ambiguous mount and competing layer).
82 known-answer tests ran, 3 skipped, no failures. Current frozen registry checks:
3 checked, zero violations (provider aliases and asset-fd source); installer is
unchanged and still requires live preflight. Eight new scripts passed user-path
gate. Lifecycle: predictions **pass**, commands **pass**, experiments
**pendingreview**. Probe JAR SHA readback and local-only readiness succeeded.

R2: offline build, source/DEX identities, JVM and FakeBoard behavior verified;
real ART controller delivery, theme intervention and all UI effects unverified.
No board lock, HDC or device command was issued. This task has no facts.txt or
screenshots; screenshot/alive counts **unknown**, not a planned count. Uploaded
probe payloads are not U4, and the full rollout remains blocked by the listed
inputs/permissions. Source files/recipes are tracked; JARs remain outside git.
