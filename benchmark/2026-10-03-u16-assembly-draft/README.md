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
| t4 M1 split runtime | `1d42dbfb473f87e8a31e7403c7f67c3544b8a5cea109e73e71250596ecb31942`, arrived/staged | Replace only root runtime94c31177; disabled native-only staging, not a bundle |
| Flutter Impeller extension proc + EGL names | `eb90a6409c9caaba058d2463cad9c193d344527051455d8aca8421e6b7011b4f`, arrived/staged | A3 on b1c9/U15 9b82, all three ATrace retained; donora53534971f, accepted outer13:34 |
| t2 adaptive icon raster | excluded from first batch | Installer and its frozen admission untouched |
| t5 WebView | dependency-blocked by A0 | No renderer/provider implementation or movement claim |

Actual JAR bytes were independently hashed and copied to persistent private
`.artifacts/inputs/` (nine BCP JARs plus one non-BCP runtime JAR). `input-inventory.json`
binds every private file; binary artifacts are deliberately absent from landing.
`source-snapshots.json` binds original/source snapshot hashes. Source snapshots
retain historical donor evidence rather than rewriting it to imply new results.

**Receipt correction:** master `receipt-u16t1.json` now pins85938130 and its
classes.dex b3b24a0c, both independently matched to the actual JAR. The historical
c53b7bd6 mismatch remains in `inputs/history-v1/`; it is not current build proof.
`donor-receipt-status.json` binds the corrected receipt SHA126b9381. No bake is authorized.

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

## Historical runtime-only native static review — not admission

Explicit U15 runtime94c31177 is the content comparison baseline. WHOIS uses that
exact generation; its historical process-map observations do not prove U15 is on
the boards. `native-slot-binding.json` binds the disabled `.artifacts/native-t4-v1/native`
manifest eaa70761 and gate inputs7129ce1d. Every other payload, both libandroid domains,
live target and namespace manifest is preserved. The actual split shim and M1 TU,
accepted objects003a4edb/3e2b4323 and donor A′ proofs are hashed in
`native-source-snapshots.json`. No donor build was repeated here.

Fresh Mac outputs are preserved verbatim privately and path-portably in `evidence/`:

| Command | Raw exit | Result |
|---|---:|---|
| WHOIS explicit U15 runtime | 0 | Exact94c3 comparison identity |
| open_site_scan U15 / t4 | 0 / 0 | 197 / 197 sites; namespace edges0 / 0; unchanged DEFAULT-NS197 and UNRESOLVED1, no MULTI-NS |
| readelf NEEDED U15 / t4 | 0 / 0 | Same dependency list |
| readelf dynsym U15 / t4 | 0 / 0 | Exact inventories retained |
| deployed_strings_diff t4 vs U15 | 0 | 0 removed / 0 added strings |
| ABI --calls +219 consumers | 0 | 0 removed / 1 added export; drift0 / consumer breaks0 / **call differences3** |
| N1 U15 / t4, current active table | 1 / 1 | REJECT99 / REJECT99; errors[] |
| N2 U15 / t4, current active table | 1 / 1 | REJECT105 / REJECT105; errors[] |

These N1/N2 outputs are **not PASS**. Strip binding identities only, preserving
profile/function/namespace/library/target/evidence/kind/reason:202 findings are equal,
two N1 source lines differ. No registry signature, rebind or exception apply occurred.
`native-gate-runs.json` pins identical before/after active-registry hashes.

### Three raw call-set differences requiring outer review

These are the exact ABI report rows, not a calls0 claim. The split TU moves the
M1 implementation behind one external entry; caller optimization can inline the
short local wrapper. Source evidence explains the routing but does not replace
outer acceptance of the emitted call differences.

1. `android::(anonymous namespace)::BBQ_nativeUpdate(_JNIEnv*, _jclass*, long, long, long, long, int)`:
   added `_ZN7android34m1_native_window_from_other_copiesEPFPviEi`;
   removed `_ZN7android12_GLOBAL__N_123oh_wm_get_native_windowEi`.
   Source `inputs/native-source/u13-m1-compat-shim.cpp:513` and `:523` still calls
   the local wrapper; its fallback at `:454` calls the new TU entry.
2. `android::(anonymous namespace)::sc_to_oh_native_window(long)`:
   added `_ZN7android12_GLOBAL__N_119resolve_oh_wm_funcsEv` and
   `_ZN7android34m1_native_window_from_other_copiesEPFPviEi`;
   removed `_ZN7android12_GLOBAL__N_123oh_wm_get_native_windowEi`.
   Source `inputs/native-source/u13-m1-compat-shim.cpp:183`, wrapper `:451`.
3. `android::(anonymous namespace)::oh_wm_get_native_window(int)`:
   added `_ZN7android34m1_native_window_from_other_copiesEPFPviEi`;
   removed `HiLogPrint` and `dl_iterate_phdr`.
   New TU `inputs/native-source/u16-m1-copy.cpp:84` retains the actual iterator
   calls at `:88`/`:90` and logging; wrapper at shim`:454` forwards its resolved
   file-static function pointer. Their disappearance from the wrapper call set
   is not removal from the whole runtime.

### Two raw NOLOAD source-line shifts requiring outer review

Both remain N1 `unknown`, dispositionREJECT, namespace`default`, reason
`fresh namespace or literal target not established`; profile`u13-m1-compat-shim.cpp`.
`native-review.pending.json` contains complete before/after finding rows and source hashes.

| Function / library | Old → new evidence line | Exact evidence text |
|---|---|---|
| resolve_oh_wm_funcs / liboh_adapter_bridge.so | 415 → 421 | `s_bridgeHandle = dlopen("liboh_adapter_bridge.so", RTLD_NOW \u007c RTLD_NOLOAD);` |
| eglCreateWindowSurface / libEGL.so | 1408 → 1334 | `void* h = android::dlopen("libEGL.so", RTLD_NOW \u007c RTLD_NOLOAD);` |

The old full source is `inputs/native-source/u15-m1-compat-shim.cpp`; the new full
source is `inputs/native-source/u13-m1-compat-shim.cpp`. All nonbinding fields,
including exact text, are equal after replacing only these two line numbers.
This is a review request, not an unsigned auto-approval.

### Withdrawn Flutter donor

15e9885a2086ab854e4489fdaf3a39d74aa94c7155e9b7184d4ac2e3c281a85a was built
against U14fff9, not the U15 content member9b824502. Fresh diagnostic ABI--calls
against9b82 reports12→10 exports:removed `ATrace_beginSection`, `ATrace_endSection`,
`ATrace_isEnabled`; added `eglGetProcAddress`; drift0/calls0. CLIrc0 does not gate
export removal, and the diagnostic supplied no consumers. It is not the219-consumer check.
Outer12:48 withdrew15e988; it was never selected, copied into native staging or deployed.
`flutter-withdrawal.json` and `evidence/flutter-withdrawn-abi.*` retain the original
diagnostic and pinned identities. The donor subsequently replaced that release path;
the diagnostic's own old/new SHA binds the withdrawn bytes, not the current path.
Correctedb1c9 arrived and was selected only after outer12:58, as detailed next.

## Historical single native snapshot: runtime1d42 + Flutterb1c9

The **only selected native batch** is `.artifacts/native-pair-v2/native`, copied
from the historical t4 staging, with exactly one further payload change:
`westlake_flutter/libandroid.so`9b82→b1c9. `westlake_native/libandroid.so` stays
byte-identical. Native manifestSHA
`998248b862f947b8b29da4344deced29e9d46d1ba20c41aecb3142953bed61c0`, inputsSHA
`d310e29ad53402b61ad267d9758dbf8380b83a0b90d3bde007effa283ab84029`.
These are **partial native metadata**, not final bundle identities. No images/JARs
were mixed into an executable bundle; transaction BASE remains a future parameter.

`flutter-source-snapshots.json` binds the corrected donor's source/map/recipe,
two live tee logs, x2 receipt,34/34 instruction-equivalence report including ATrace,
and payload inventory. The new interposer has its own namespace scan profile,
while all old native domains/profile sources are preserved and identities rebound.
The old historical t4 evidence and withdrawal diagnostic remain available.
The interposer source's old header still mentionsfff9; it is preserved verbatim,
not used as build identity. Corrected recipe's ndk_trace extra/android_v3.map,
actual ELF hashes and34-function proof establish the9b82 base.

| Fresh combined run | Raw exit | Result |
|---|---:|---|
| WHOIS runtime / Flutter, explicit U15 content | 0 / 0 | Runtime94c3, selected Flutter counterpart9b82 (not another libandroid alias) |
| runtime open U15 / U16 | 0 / 0 | 197 / 197, no open/namespace delta |
| runtime NEEDED U15 / U16 | 0 / 0 | Same23 dependencies |
| runtime dynsym U15 / U16 | 0 / 0 | 787 / 788 exports, only M1 TU entry added |
| runtime strings | 0 | 0 drop / 0 add |
| runtime ABI --calls +219 consumers | 0 | 0 removed / 1 added / drift0 / consumer breaks0 / callset3 |
| Flutter open U15 / U16 | 0 / 0 | 7 / 11, four added NOLOAD sites, namespace API/literal delta empty |
| Flutter NEEDED U15 / U16 | 0 / 0 | Same runtime/surface/libc++/libc dependencies |
| Flutter dynsym U15 / U16 | 0 / 0 | 12 / 13 exports, all3 ATrace retained |
| Flutter strings | **1** | 0 drop / 8 add, no allow list applied |
| Flutter ABI --calls +219 consumers | 0 | REMOVED empty / +eglGetProcAddress / drift0 / consumer breaks0 / callset0 |
| combined N1, U15 / U16 pair | **1 / 1** | REJECT99 / REJECT103, errors[] |
| combined N2, U15 / U16 pair | **1 / 1** | REJECT105 / REJECT105, errors[] |

`native-pair-gates.json` preserves every command/exit/raw and portable-log SHA.
Strict comparison gives202 nonbinding-equal findings + the same two shifted
runtime NOLOAD lines + four new Flutter N1 NOLOAD findings. The active table is
unchanged before/after; nothing is signed or applied by this lane.
`native-pair-review.pending.json` binds all pending rows to the pair's current hashes,
including complete issue IDs. Outer may review them individually:

| New N1 | Source in `inputs/flutter-source/src/flutter_egl_getprocaddress.cpp` | Exact evidence |
|---|---:|---|
| gl_log / runtime | 29 | `void* rt = dlopen("liboh_android_runtime.so", RTLD_NOW \u007c RTLD_NOLOAD);` |
| ensure_driver / GLES2 | 48 | `if (!g_gles2) g_gles2 = dlopen("libGLESv2.so", RTLD_NOLOAD \u007c RTLD_NOW);` |
| ensure_driver / GLES3 | 49 | `if (!g_gles3) g_gles3 = dlopen("libGLESv3.so", RTLD_NOLOAD \u007c RTLD_NOW);` |
| eglGetProcAddress / EGL | 78 | `void* egl = dlopen("libEGL.so", RTLD_NOLOAD \u007c RTLD_NOW);` |

Raw open sites added: `gl_log@0x4c04` runtime, `eglGetProcAddress@0x490c` GLES2,
`@0x492c` GLES3 and `@0x48c4` path`unknown:adr x0, #-11794`.
All four showflags`0x6=NOW|NOLOAD` and caller-default. The last target is **unresolved
in the tool**, although source78 says libEGL; raw output is not silently corrected.
The seven inherited sites include **two existing NOW fresh-open fallbacks**, not
eleven NOLOAD-only calls. DEFAULT-NS7→11; no MULTI-NS or namespace-edge change.
Production open deltaSHA`bbf0ed5de0568e25e3523517ca65e6798b489b1b4f4fa15cd11aa23c681711d4`
is unsigned, not an allowance. All original/fresh site text is in the evidence logs.

The exact eight strings pending review (no removals) are:
`FLUTTER-GLSTUB` (source33, once-per-name residual logging), `eglGetProcAddress`
(79, real provider lookup), `glClearDepth`/`glDepthRange` (89/88, double→float shims),
`glClearDepthf`/`glDepthRangef` (56/51, backend lookup),
`libGLESv2.so`/`libGLESv3.so` (48/49, resident driver lookup).
Logged residual no-op procedures are not a proof of real rendering or new lit apps;
board observed first-fatal movement remains0. No approval is inferred from CLIrc0.
Outer13:07 subsequently requested an A‴ Libre EGL-name routing extension from
cc-wiki. That successor has not arrived in this report and has no selected SHA;
thisb1c9 batch is a disabled review snapshot, **not a frozen final U16 version**.
When the new donor arrives, replace only the Flutter slot and rerun these gates.

## Current single native version: runtime1d42 + FlutterA3 eb90

Outer13:34 replaces only the Flutter slot with A3, the four EGL-name branches in
`eglGetProcAddress`. The immutable b1c9 staging remains intact; its metadata is
archived in `inputs/history-pair-b1c9/`. The selected disabled staging is now
`.artifacts/native-pair-a3/native`; all296 payloads were SHA-checked and only root
runtime1d42 plus Fluttereb90 differ from U15. The westlake_native libandroid owner
ee2fb82c, original domains, JAR inputs, installer identities and unbaked image
plan do not change. Source, map, frozen recipe, two build tee logs and original
SHA256SUMS are pinned in `flutter-source-snapshots.json` / `inputs/flutter-source-a3/`.
No donor rebuild or remote command was performed here.

Fresh Mac reports are prefixed `u16-a3-`, rather than borrowing the b1c9 reports.
ABI calls/219 consumers: Flutter removed0/added1/calls0/breaks0; runtime
removed0/added1/calls3/breaks0. Both NEEDED lists are unchanged. Runtime opens
197→197; Flutter7→11, four additional resident-only opens, no removed open,
DEFAULT-NS7→11, no MULTI-NS or namespace-edge delta. Unlike the historical b1c9
ADR diagnostic, A3's actual scanner resolves `libEGL.so` at0x4ad8. Its other new
sites are GLES2@0x4984, GLES3@0x49a4 and runtime@0x4cf0, all NOW|NOLOAD.
The production Flutter open delta is now
`190c06078c04cc6e5ada7f5d2b195c07e2a60b708f897223de5b5dfa8e659b93`,
still unsigned. Raw strings remain0 dropped/8 added, exit1. Native N1/N2 retain
103/105 rejected bindings;202 exactly equal nonbinding rows, two runtime source
line shifts and four new Flutter NOLOAD findings at38/57/58/96 require outer
review. No exception or allowance is applied.

### Fresh fix-observer matrix

`increments.csv` has **8 arrived changes (four targets × common/61b)**: root
runtime, Flutter libandroid, stubs JAR and runtime JAR. Each SHA is checked
against its actual per-board U15 content baseline and selected source bytes.
The27 images have no candidate bytes yet: they remain in `expected-images.csv`,
not rows with invented identities. This is not full-bundle observer coverage.

Exact keys SHA is
`6f42bf0a5265da6709c63698adb5f97c7bffd1e18e9fa70c37dae64c00239d38`.
Actual `check_fix_observers` v3 yields **8 artifacts,0 without an observer**,
exit0, with no smoke supplements. Master's worktree has no copy of that script;
the read-only oc-t4 copy is verified byte-identical to commit
`770ef6e9e4fa0aa2a240c38578957a9fca12924d`, SHA
`01f0b55a3d0ec6b4aa0a7fa9614a63123617f1c9ca8f5d337314a97ccbc5a22e`.
The exact keys bytes and tool snapshot are landed in `inputs/observers/`.
`fix-observer-receipt.json` binds argv, raw/matrix/CSV SHA and scope; no tool or
keys edit is made. A negative replay removes all Flutter mover sources and
correctly reports two GAP rows, exit1. Fresh Mac21/Rust4/cold21 and contract
results are recorded separately in `validation-runs.json`; no VM is used.

```sh
python3 benchmark/2026-10-03-u16-assembly-draft/observer_matrix.py
```

The four Flutter movers remain localsend, fd-kitchenowl, fd-fluffychat and
fd-libre. The latter now observes raster-thread proc-address routing through
the ANW-unwrapping hooks. These are future observations, not proven lit counts.

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

After approval of the native pending rows, eight JAR adds and full27 image pair
arrive, compose one native version and one runtime JAR version. Replace exact target
and payload aliases together, rebuild metadata/input bindings/paired receipt and
per-board references, and run fresh open-site/strings/ABI/consumer/N1/N2/class/image/
frozen and Mac+VM production gates against the actual BASE. Runtime-only static
gates above do not substitute for those future full-bundle production gates.

## Offline verification

```sh
python3 benchmark/2026-10-03-u16-assembly-draft/prepare.py
python3 benchmark/2026-10-03-u16-assembly-draft/collect_static.py
python3 benchmark/2026-10-03-u16-assembly-draft/native_static.py
python3 benchmark/2026-10-03-u16-assembly-draft/collect_review.py
python3 benchmark/2026-10-03-u16-assembly-draft/native_pair_static.py
python3 benchmark/2026-10-03-u16-assembly-draft/collect_pair_review.py
python3 benchmark/2026-10-03-u16-assembly-draft/test_draft.py
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test --manifest-path tools/spec-checks/Cargo.toml --test u16_assembly_draft
```

Cold tests require landed JSON/source only, never private `.artifacts` or donor machines.
Raw logs and exit/hash receipts are in `evidence/`, `validation-runs.json` and `results.json`.
`native_stage.py` and `native_pair.py` create immutable staging once, not reusable
production replay entry points. Do not run the bake under this task.
