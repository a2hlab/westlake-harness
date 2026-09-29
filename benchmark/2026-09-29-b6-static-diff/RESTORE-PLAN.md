# Task 56: restore one coherent R155 protocol generation

The previous provider baseline was wrong: **977fb347 is superseded**. The sealed R155 provider is **80c9aee0f39b860b1ce8d72af106e4fde49c0dbf41ef1b426c1e3103086d9b2f**, matching the old child's embedded manifest. NEW remains **8d1092590c2ca550d45ffdf686c874b2e9fde9029b9f9b2d0e415d66cd07b1d5**. Host and child findings and evidence are unchanged, verified by `host-child-preserved.json:1`. Full six paths/hashes: `results.json:1`; identity/manifest reconciliation: `provider-baseline-caveat.json:1`, `reference-identity.json:1`.

**Apply G1–G4 together to one build before cx-t0's next device run.** “Must restore” below means needed for the R155 protocol parity control; it is not proof that a difference caused the failure. R2: binary identities and instruction/metadata observations **verified**; source restoration design **partially** (static reasoning); device success/root cause **unverified**. This task neither edits deployment source nor operates a device. Outer loop owns commit.

Source notation (all read-only, snapshot in `source-targets.json:1`):

- `S = ~/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/appspawn-x`
- `P = S/security_specialization/stock_child_plugin`
- `G = ~/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-28-bms-route-deploy/latest-source-generation`
- Evidence paths below are relative to this report directory. Source lines describe the current preparation snapshot, **not a claim that it built task50's pinned binary**. cx-t0 may already have restored some items; preserve those edits and verify the resulting ELF.

## G1 — host ↔ child ↔ provider service table and publication order

**R155 contract and evidence**

1. `WlascHostRuntimeServicesV1` is 128 bytes. The provider requires all callbacks, including `open_sealed_exact` at **+104**, `create_configured_namespaces` at **+112**, and `open_namespace` at **+120**, nonnull. Correct old and NEW `WLAR_HostServicesInstall` have **93 identical normalized instructions**. R155 loads +112 at `evidence/runtime-provider/r155/disassembly.txt:7501`, rejects null, then loads +120 and rejects null; complete routine starts at `:7435`, NEW at `evidence/runtime-provider/new/disassembly.txt:9344`. **Do not zero these fields or invert the predicates.**
2. R155 outer installer first calls `WLAR_HostServicesInstall`, then `WLNL_InstallSealedOpenV1(services->open_sealed_exact)`, and only after success release-publishes READY. Failure publishes FAILED. R155 call at `evidence/runtime-provider/r155/disassembly.txt:5879`; full routine `:5850`. NEW publishes after the first call and delays sealed-open installation until `Constructors`, `evidence/runtime-provider/new/disassembly.txt:8161`. This is **a moved call**, not a globally deleted import/call.
3. R155 `WLAR_HostServicesGetNamespaceCallbacks` returns **two** callbacks (create/open namespace); NEW adds sealed-open as the first of **three** outputs. Registry slots are +144/+152 versus +136/+144/+152; they are not the public service-table offsets. Evidence: `evidence/runtime-provider/r155/disassembly.txt:7952`, `evidence/runtime-provider/new/disassembly.txt:9854`, `evidence/runtime-provider/functions/ade19426b5548e16.diff:1`.
4. NEW host additionally requires child `WLSCPL_InheritAndroidRuntimeV1` and parent-PID/inheritance checks; R155 host does not. Evidence: both `evidence/host/{r155,new}/disassembly.txt:449`, `evidence/host/functions/db22d3adbf8515e5.diff:1`.

**Source edits as a group**

- Keep `P/include/westlake_android_child_plugin.h:162` and `P/src/host_runtime_services.c:196` at the existing V1 size/nonnull contract. Never weaken generation/SHA, table-size or callback checks.
- In `P/src/westlake_android_runtime_provider.cpp:714`, restore installer-time `WLNL_InstallSealedOpenV1` after successful registry install and before READY. Propagate its failure to FAILED; preserve atomic single-install admission. Remove the later constructor registration when applying G2/G3, so there is one owner and one phase.
- Restore the two-output namespace getter declaration/implementation/callers together (`P/include/host_runtime_services.h:70`, `P/src/host_runtime_services.c:437`). The inspected current implementation already has two outputs; keep that restoration. Constructor still needs create/open callbacks for its runtime gate; this is distinct from registering sealed-open.
- **Current concrete integration gap:** `P/src/westlake_android_child_plugin.c:794` zeroes `child_services`, fills through `get_pthread_bridge_ops`, and calls the installer at `:815`, leaving all three final callbacks zero. Assign `child_services.open_sealed_exact = WLSCPL_OpenPreparedNamespace`, and copy `create_configured_namespaces` / `open_namespace` from `g_stock_host_services` before invoking the provider. The old store to +104 loads GOT slot 0xb338, whose RELATIVE relocation resolves to 0x31f0 (`WLSCPL_OpenPreparedNamespace`); see `evidence/child/r155/relocations.txt:31` and `evidence/child/r155/disassembly.txt:3627`. Follow the old `LoadSealedProviderAfterHooks` assignments, not arbitrary nonnull stubs (`evidence/child/r155/disassembly.txt:3405`).
- Keep host `InstallPluginHostServices` and child inheritance export consistent (`P/src/westlake_stock_host_main.c:328`): remove the candidate-only inheritance requirement and associated cache/publication path as G2 is restored. The current host snapshot already omits that requirement. Keep stock security and parent/child stage-tail verification.

**Offline exit check:** three trailing service callbacks bound to actual matching implementations; size 128 and mandatory nonnull checks retained; exactly one sealed-open install in provider installer before READY; getter/callers use the same two-output signature; host has no dependency on the removed inheritance export.

## G2 — child namespace, sealed identity and A06/A02 sequence

**R155 contract and evidence**

1. R155 `WLSCPL_OpenPreparedNamespace` checks prepared state, absolute canonical path, the exact `/system/android/lib64/` prefix and a nonempty suffix; `(flags & 258) == 2` requires NOW and excludes GLOBAL. It then calls **dlopen**, not dlopen_ns. Evidence: `evidence/child/r155/disassembly.txt:144`; comparison `evidence/child/functions/a7972c88802d846c.diff:1`. Restore the whole admission rule, not just the call name.
2. Candidate `WLSCPL_InheritAndroidRuntimeV1` adds dlns_inherit, dlopen_ns(flags 258) and a cached runtime handle. Restore with G1's host requirement. Evidence: its per-function record in `evidence/child/functions.json:1` and TOP20 row 9.
3. R155 sealed manifest V1 uses artifact stride **376** and array slot **32**; candidate V2 uses **400** and **64**, plus boot/process identity and stage receipts. The caller changes from `InvokeProviderChildEntryWithResolver` (resolve install/entry → install services → direct entry) to `InvokeProviderA06ThenA02`. Evidence: `evidence/child/r155/disassembly.txt:3782`, `evidence/child/functions/e42a067cfbdce593.diff:1`, `evidence/child/functions/7293af0ca174140d.diff:1`, and `VisitClosure` record in `ALL-FUNCTIONS.md`.
4. R155 provider's exported direct entry validates the V1 request, stock receipt, generation, installed services and child admission, then runs constructor → VM → JNI → main using the R155 sequence/ledger. Candidate requires persisted V2 preparation, identity/receipt state and A02 commit. Evidence: `evidence/runtime-provider/r155/disassembly.txt:5890`, `evidence/runtime-provider/new/disassembly.txt:7545`, `evidence/runtime-provider/functions/3228fee5dd0320f9.diff:1`.

**Source edits as a group**

- Restore V1 manifest producer/header/loader/consumer consistently, including generated artifact records, graph traversal, result structures and resolver. Primary targets: `P/src/sealed_child_provider_loader.c:291`, `:644`; `P/src/westlake_android_child_plugin.c:617`, `:738`, `:772`; associated loader headers and generated manifest in the build recipe. Do not hand-edit numeric offsets into V2 structs.
- `P/src/sealed_child_provider_loader.c:319` currently already calls dlopen, but still lacks R155 canonical/prefix/flags checks. Restore them and the matching V1 prepared-namespace lifecycle; remove candidate-only inheritance/cached preload behavior with G1.
- `P/src/westlake_android_child_plugin.c:76` already restores the direct V1 resolver; retain it and complete the G1 callback table. Remove its dependence on V2 acquire/prepare/commit and owner receipt publication as one call-chain change, not by forcing a failed gate to return success.
- **Current concrete integration gap:** `P/src/westlake_android_runtime_provider.cpp:725` direct entry unconditionally returns `WLGR_V2_ERROR_MISSING_PREREQUISITE`, while the child already calls it directly. Replace the stub with the R155 validated direct sequence, its ledger/operations, audit capture/commit and error propagation. Restore corresponding old callbacks and Context lifetime; retire V2 prerequisite entry/global Context constructor/destructor when they become unused. A direct success return is not a restoration.
- Restore hook-table candidate/publication/owner lifetime consistently with the V1 route. P0 rejector renames whose complete bodies match are harmless; do not confuse the renames with actual new revoke/drain/identity gates. Keep uid/gid, stock specialization ownership, stage tails, bypass guard, receipt and verified-artifact checks required by the restored route.
- Regenerate generation IDs, provider hash/build ID, manifest, expected bridge identity and dependency closure from the **new coherent build**. Do not paste 80c9aee0 or R155 generation constants into changed binaries. Descriptor-based verified-open and support for 16/20-byte build IDs may remain as explicitly retained verification changes; never remove hash checks to admit a mismatched build.

**Offline exit check:** one V1 producer/consumer schema end-to-end; no direct-entry stub; install→entry runs the full sequence with errors propagated; no mandatory dependency on V2 A06/A02 state or removed inheritance export; full regenerated identities match all emitted artifacts. Keeping a V2 manifest while switching only the entry is not the requested R155 control.

## G3 — VM mode, environment, JNI order and provider dependencies

**R155 contract and evidence**

1. **Preserve non-zygote mode.** R155 already has `startVm(bool)`, and `CreateChildVm` passes **false** (`mov w1,wzr`). Evidence: `evidence/runtime-provider/r155/disassembly.txt:7332`, `evidence/runtime-provider/functions/453251049f79cde1.diff:1`. Do not restore unconditional `-Xzygote` or postFork hooks.
2. R155 startVm calls `LoadVerifiedAdapterBridge`, `registerNativeMethods`, `cacheJavaReferences` in that order at `evidence/runtime-provider/r155/disassembly.txt:1261`, `:1264`, `:1267`. NEW retains the first in startVm but moves the latter two to preload behind `VerifyLoadedAdapterBridge`. NEW also adds Java `System.loadLibrary("javacore")` and an abort VM option/helper. Evidence: old/new startVm at `:232`, preload at old `:2620` / NEW `:2835`; `provider-focused-evidence.json:1`.
3. R155 constructor sets BOOTCLASSPATH, DEX2OATBOOTCLASSPATH, ANDROID_ROOT=/system/android, ANDROID_DATA=/data, ANDROID_BOOT_IMAGE=/system/android/framework/boot.art, ANDROID_I18N_ROOT=/system/android, ANDROID_TZDATA_ROOT=/system/android and ICU_DATA=/system/android/etc/icu. It reads RLIMIT_STACK and sets **both soft/hard to 16 MiB**. The pair is loaded from virtual address **0x5da0**, exact bytes recorded in `provider-focused-evidence.json:1`. Evidence: `evidence/runtime-provider/r155/disassembly.txt:6918`, constant load `:6927`, resolved strings/calls in `evidence/runtime-provider/functions/393b8f6894fd9fae.diff:1`. Candidate uses a reduced environment and RLIMIT_CORE=infinity; that is not equivalent stack setup.
4. Correct old ChildMain already installs the Typeface nativeWarmUpCache no-op and defers adapter initialization to Java. Its only residual instruction diff resolves to the **same nativeWarmUpCache string**; preserve this behavior. Evidence: `evidence/runtime-provider/functions/f8463b3e55a8975d.diff:1`, `provider-focused-evidence.json:1`.
5. Correct old provider NEEDED includes **libopenjdkjvm.so** after libart.so. NEW removes it and adds libwestlake_art_abort_bridge.so before libart.so plus libbase.so after libart.so. R155 full order is `libapp_native_loader.so, libwestlake_thread_guard_registry.so, libhilog.so, libnativehelper.so, liblog.so, libbionic_compat.so, libart.so, libopenjdkjvm.so, libnativeloader.so, libc++.so, libc.so`. Evidence: `evidence/runtime-provider/r155/dynamic.txt:3`, `evidence/runtime-provider/new/dynamic.txt:3`.

**Source edits as a group**

- `P/src/westlake_android_runtime_provider.cpp:693` currently uses `startVm()` (default true via `S/src/appspawnx_runtime.cpp:94`). Change the specialized-child operation to **startVm(false)** when rebuilding the G2 sequence.
- In `S/src/appspawnx_runtime.cpp:98`, restore startVm's verified bridge → native registration → cache order, remove candidate Java javacore bootstrap (`:287`) and added abort option/helper together with their link dependencies. Remove duplicated registration/cache from preload (`:530`). Keep identity verification before using the bridge; do not leave JNI initialized twice.
- Restore the full constructor environment and 16 MiB RLIMIT_STACK behavior before runtime construction/VM start (`P/src/westlake_android_runtime_provider.cpp:672`). Use the matching generated R155-route boot/dex2oat classpaths, not a guessed shortened list. A log/stat diagnostic may stay or be omitted without changing the required setup; a failed required operation must propagate.
- Restore provider link input/order and remove now-unused abort/base direct dependency as part of this VM change. `G/task52/recipes/build-retained-generation-inner.sh:276` currently links abort bridge/art/base and omits openjdkjvm. Update the actual active recipe and generated dependency closure together; verify emitted DT_NEEDED because --as-needed can discard an intended library.
- Preserve Typeface no-op, deferred adapter initialization, non-zygote start and absence of postFork calls. The earlier 977fb347-based advice to revert them is withdrawn. Preserve BTI landing-pad generation where R155 had it (`__emutls_unregister_key`); do not claim a BTI fault without runtime evidence.

**Offline exit check:** startVm(false) in child sequence; one JNI registration/cache phase; no candidate-only javacore bootstrap/abort option; old environment and stack limit; exact intended provider dependency order; no new global V2 Context initializer after G2 retirement.

## G4 — host stdio exports and host link order

**R155 contract and evidence**

R155 host imports fflush/vfprintf; NEW exports `__sF@@LIBC` plus fflush, fprintf, fputc, fputs, fwrite, vfprintf. The wrappers remap FILE pointers and resolve real functions via dlsym/pthread_once; lookup failure adds `_exit(127)`. Restore the complete broker and binding change. Evidence: `evidence/host/versioned-symbols-diff.json:1`, TOP20 rows 1–5, `evidence/host/functions.json:1` (WlResolveHostStdio and six wrappers). R155 host NEEDED puts libhilog.so after libsec_shared.z.so (eighth); NEW puts it first, other dependencies preserve relative order: `evidence/host/r155/dynamic.txt:3`, `evidence/host/new/dynamic.txt:3`.

**Source edits as a group**

- Apply cx-t0's prepared `G/task52/preparation/host-stdio-parity.patch:1` after checking the active recipe: remove broker source/object compile and link inputs (`G/task52/recipes/build-retained-generation-inner.sh:426`, `:478`), and remove the seven broker exports from the host export/version map. Restore callsites to libc imports, including AppSpawnDump; no local wrapper fallback.
- Do **not** delete the separate `S/bionic_compat/src/unity_libc_stubs.c:202` __sF implementation merely because it has the same symbol name. The restore target is host interposition, and R155 still depends on libbionic_compat.
- Preserve #52's already prepared/restored host libhilog order; check emitted order after all final linking. Maintain declared --no-as-needed/group semantics where needed to retain the intended old dependencies.

**Offline exit check:** no seven broker definitions in host .dynsym; fflush/vfprintf bind as imports; no broker resolver/pthread_once/_exit path; old host ordered NEEDED. This is a namespace-wide binding change, so testing a single wrapper in isolation is insufficient.

## Handoff and exclusions

cx-t0 should implement all four groups in one source revision, rebuild all affected artifacts/dependencies and regenerated manifests, then repeat hash/ELF inventory checks against this pinned baseline. Only after the assembled source/binary contract is consistent should cx-t0 conduct its separately authorized device test. Capture actual mapped provider identity as well as final screenshots; static parity is not an on-screen result.

The exhaustive disposition ledger remains `ALL-FUNCTIONS.md:1` / `function-assessments.json:1`: host **54**, child **104**, corrected provider **65** differing defined-function records. Added/removed protocol helpers are covered by their owning groups; PLT stubs and relocations follow the same owners and should never be patched independently. Keep harmless address/constant-pool moves, diagnostic line changes and body-identical rejector renames. Keep useful diagnostics, verified-open improvements and receive-bound arithmetic as explicitly retained differences; they are not evidence of complete bitwise/semantic parity. Any remaining difference after the build must have an explicit owner/disposition before calling it the R155 protocol control.
