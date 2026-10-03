# U16 assembly draft — disabled, incomplete, no bake

## Correction and pinned evidence

U15 candidate content is not a promoted transaction baseline. A changed stubs DEX
requires a complete 27-image FZ-005 pair; copying U15 boot images would create a
mixed-generation package. This directory therefore prepares **an incomplete ledger
and inputs**, not an executable generation bundle. All execution/rollout flags
remain false; final bundle/manifest/inputs hashes and candidate image hashes are null.
No compilation, remote probe, VM use, device operation or gate-registry edit occurred.

| Content profile | Exact bundle SHA256 | Installer in both system locations |
|---|---|---|
| common | `29c8a62cc78f5ba1eddea75fceb46e96baacba7e9b4d6fd046c9d8951ebe904f` | `2c9a5294` |
| 61b | `8a260cec9b4ab3505cf72fe445e34643f0f1441abe9367658f3240d2e45a6a8b` | `51e1b525` |

Complete base payload/BCP/paired receipts were checked through generation_bundle.
`preservation.json` pins their before/after bundle hashes; inherited native content
is identical across profiles, while each board-local installer stays unchanged.

## Arrived and pending

| Slot | Identity / state | Scope |
|---|---|---|
| t1 stubs | `85938130cbb016c568d0086a43f6dc865d638e63625c401e82f93987b1fa3c01` | WifiManager no-Wi-Fi member responses; donor deterministic recipe357808ce3f |
| t3 runtime JAR | `f6f5face66a90a16020877cddc5bb6e5bed28063dfabf02fa77064c00c50bb81` | AppSchedulerBridge launch ON_START sync; master8bbc7d9244, donorf2c2c90e67 |
| t4 M1 split runtime | pending, oc-t4 | One final runtime artifact; no intermediate native published |
| Flutter Impeller extension proc | pending, cc-t3 | Owner/paths depend on diagnosis; no guessed artifact |
| t2 adaptive icon raster | excluded from first batch | Installer and its frozen admission untouched |
| t5 WebView | dependency-blocked by A0 | No renderer/provider implementation or movement claim |

Actual JAR bytes were independently hashed and copied to persistent private
`.artifacts/inputs/` (nine BCP JARs plus one non-BCP runtime JAR). `input-inventory.json`
binds every private file; binary artifacts are deliberately absent from landing.
`source-snapshots.json` binds original/source snapshot hashes. Source snapshots
retain historical donor evidence rather than rewriting it to imply new results.

**Donor receipt mismatch:** the t1 `.jar.receipt.json` still says output `c53b7bd6`,
whereas the actual deterministic JAR and fresh class diff say `85938130`.
`donor-receipt-status.json` records this explicitly. That old merge receipt is not
current-artifact build proof; oc-t4/outer must supply the corrected deterministic
receipt before final provenance admission. It does not change the independently
verified nine planned input bytes or authorize any bake.

Fresh Mac `deployed_class_diff --frozen` versus exact effective U15 inputs, with
**no allow_add or allow_reshape**:
- stubs: rc1, 276→284 classes, 0 dropped/0 reshaped/8 added/frozen0. The eight exact
  descriptors are in `allow-add.pending.json`; outer approval is pending, not applied.
- runtime JAR: rc0, 224→224 classes, 0 dropped/0 reshaped/0 added/frozen0.

Conditional targets are fd-wifianalyzer's member-gap and fd-breezyweather's lifecycle
order only; observed first-fatal movement is **0**, not two newly lit apps.
The lifecycle change preserves deferred onResume; the four native-engine risk
keys fd-minetest/fd-mpv/fd-organicmaps/fd-stk and all reference-lit keys need later
board verification. Static class shape checks do not verify method-body behavior.

## FZ-005 rebake plan (not executed)

`plan.json` selects the ordered nine effective U15 BCP inputs: eight stay byte-identical,
only stubs94a9→8593 changes; framework9e55 stays. Runtime JAR20e7→f6f5 is **not BCP**.
`expected-images.{json,csv}` lists all 27 .art/.oat/.vdex targets. All are rebaked;
forecast changes are not measured output hashes or a claim that all 27 will differ.

Machine: hw248, hostname `ecs-9f6c`, Linux x86_64. Explicit `$HW248_HOME` must match
FZ-005 HOME identity `4e5277d9`; do not inherit an arbitrary SSH HOME or use a2hlab.
Frozen dex2oat64 SHA `ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b`;
frozen driver SHA `14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46`.
Their remote paths and full planned compiler arguments are in `planned-argv.json`.
The repository driver is not substituted for the separately pinned frozen driver.

`planned-bake.sh` and `dex2oat-tee.sh` copy the U15 bcp-v2 reviewed recipe with only
U16 labels/new persistent root substitutions. The default entry exits78 before
any machine probe. **Do not run it under this task.** After a separate outer approval,
the execution owner stages `.artifacts/inputs/jars9/` as `$HW248_HOME/u16-stubs-8593-runtime-f6f5-v1/jars9/`
and the public recipe/inputs as that root's `plan/`, then runs, in order:

```sh
U16_PLAN_EXECUTE=outer-approved-hw248-only HW248_HOME='<approved FZ-005 home>' bash plan/planned-bake.sh 1
U16_PLAN_EXECUTE=outer-approved-hw248-only HW248_HOME='<approved FZ-005 home>' bash plan/planned-bake.sh 2
```

Both compiler invocations use the same `work/` path. Distinct `run1/`, `run2/` and
`logs/*run{1,2}*` persist actual argv JSON, runtime tee logs, tool hashes, OS identity,
fresh hostlib inventories and compiler/tee/session/driver exit statuses. The driver
may exit6 for differences against U15 images; this is not compiler success unless
the compiler/tee statuses are0 and all27 nonempty files exist. Failed logs or partial
outputs cannot become a selected run. Never concatenate interrupted build logs.

`paired-receipt.template.json` contains both exact nine-input maps but null actual
argv/log/status/output identities and no selected run. Fill from fresh evidence,
compare all27, then select run1 only after review. Any boot.art nondeterminism needs
the **new8593 input/output pair** and actual object-chain evidence; old U15/T7d
exceptions are historical and do not transfer automatically.

## Finalization and BASE handoff

`transaction-base.template.json` reserves `--common-base/--common-base-sha256` and
`--61b-base/--61b-base-sha256` parameters for the future finalizer. They are null here:
only actual **promoted, armed, per-board U15** identity/signoff can bind them.
Do not copy the content bundle's older U14 static BASE into an executable U16 transaction.

After both native slots, approved eight adds, corrected donor receipt and full27 pair
arrive, compose one native version and one runtime JAR version. Replace exact target
and payload aliases together, rebuild metadata/input bindings/paired receipt and
per-board references, and run fresh open-site/strings/ABI/consumer/N1/N2/class/image/
frozen and Mac+VM production gates against the actual BASE. This task does none of
those future native or production gates and grants no execution approval.

## Offline verification

```sh
python3 benchmark/2026-10-03-u16-assembly-draft/prepare.py
python3 benchmark/2026-10-03-u16-assembly-draft/collect_static.py
python3 benchmark/2026-10-03-u16-assembly-draft/test_draft.py
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test --manifest-path tools/spec-checks/Cargo.toml --test u16_assembly_draft
```

Cold tests require landed JSON/source only, never private `.artifacts` or donor machines.
Raw logs and exit/hash receipts are in `evidence/`, `validation-runs.json` and `results.json`.
