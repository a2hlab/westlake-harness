# First 20 function assessments (task56 corrected baseline)

Provider compares sealed R155 80c9aee0 against NEW 8d109259. All task52 NEW hashes still differ; old hashes now match. The earlier 977fb347 provider judgments are superseded. Restore means R155 parity, not proven crash causality. See RESTORE-PLAN.md.

## 1. host: `WlResolveHostStdio` — restore

Resolves host stdio through dlsym(-1, ...) and terminates with _exit(127) on lookup failure. Entire broker is absent in R155; new failure path and dependency on lookup scope. Remove as one stdio-interposition unit when reproducing R155.

Evidence: `evidence/host/new/disassembly.txt:16373`; [evidence/host/functions/ea23f80c08521c25.diff](evidence/host/functions/ea23f80c08521c25.diff).

## 2. host: `vfprintf` — restore

New globally exported wrapper calls pthread_once, recognizes __sF slots at strides 152/304, remaps FILE pointers and indirectly calls the resolved libc function. R155 imports this symbol. This changes binding and FILE ownership behavior, not a harmless rename.

Evidence: `evidence/host/new/disassembly.txt:16326`; [evidence/host/functions/2047ed1ad4f4f2b2.diff](evidence/host/functions/2047ed1ad4f4f2b2.diff).

## 3. host: `fflush` — restore

New wrapper remaps Bionic stream slots, handles NULL, and branches through g_host_fflush. R155 uses an imported PLT entry. Restore together with __sF and the other five wrappers, not just this export.

Evidence: `evidence/host/new/disassembly.txt:16626`; [evidence/host/functions/994ad13f9341d810.diff](evidence/host/functions/994ad13f9341d810.diff).

## 4. host: `fwrite` — restore

New wrapper rewrites the stream argument before indirect dispatch. R155 has no such definition. ABI-visible behavior differs even if many non-Bionic calls still pass through.

Evidence: `evidence/host/new/disassembly.txt:16506`; [evidence/host/functions/37abd85243d6f655.diff](evidence/host/functions/37abd85243d6f655.diff).

## 5. host: `fprintf` — restore

New variadic adapter invokes the local vfprintf broker. Changes symbol resolution and logging path for dependencies; remove with broker for an exact R155 host control.

Evidence: `evidence/host/new/disassembly.txt:16443`; [evidence/host/functions/1be4491e83fe9767.diff](evidence/host/functions/1be4491e83fe9767.diff).

## 6. host: `InstallPluginHostServices` — restore

NEW requires lookup of WLSCPL_InheritAndroidRuntimeV1, records parent PID and callback identity, and introduces additional rejection branches. R155 never requires that symbol. Restore host/child contract as a coherent pair; retaining a candidate child while deleting required services is not parity.

Evidence: `evidence/host/r155/disassembly.txt:449`, `evidence/host/new/disassembly.txt:449`; [evidence/host/functions/db22d3adbf8515e5.diff](evidence/host/functions/db22d3adbf8515e5.diff).

## 7. child: `LoadSealedProviderAfterHooks` — restore

Manifest version comparison changes 1 to 2, extra production identity callback checks appear, and the load path grows from 208 to 588 instructions. Boot-bound identity, receipt and A06/A02 admission are runtime gating changes. Revert the whole loader/provider protocol only as a generation-consistent control.

Evidence: `evidence/child/r155/disassembly.txt:3405`, `evidence/child/new/disassembly.txt:8265`; [evidence/child/functions/7293af0ca174140d.diff](evidence/child/functions/7293af0ca174140d.diff).

## 8. child: `WLSCPL_OpenPreparedNamespace` — restore

R155 validates absolute canonical /system/android/lib64/ path and flags then uses dlopen. NEW tests nonempty input and prepared state then calls dlopen_ns in g_sealed_namespace. Search scope, admission conditions and load grouping change.

Evidence: `evidence/child/r155/disassembly.txt:144`, `evidence/child/new/disassembly.txt:144`; [evidence/child/functions/a7972c88802d846c.diff](evidence/child/functions/a7972c88802d846c.diff).

## 9. child: `WLSCPL_InheritAndroidRuntimeV1` — restore

NEW calls dlns_inherit, then dlopen_ns(flags 258) and caches the Android runtime handle; absent in R155. This affects namespace visibility and load lifetime. Restore with the host installer and namespace callbacks, not by deleting a symbol alone.

Evidence: `evidence/child/new/disassembly.txt:168`; [evidence/child/functions/916349540820e557.diff](evidence/child/functions/916349540820e557.diff).

## 10. child: `InvokeProviderA06ThenA02` — restore

New staged receipt-generation and provider prerequisite/handoff path replaces InvokeProviderChildEntryWithResolver. Calls, transition validation, deadlines/identity inputs and failure returns are new runtime behavior.

Evidence: `evidence/child/new/disassembly.txt:9480`; [evidence/child/functions/8af5553d9b67cab4.diff](evidence/child/functions/8af5553d9b67cab4.diff).

## 11. runtime-provider: `WLAR_EnterAndroidAfterStockSpecialization` — restore

R155 drives constructor/VM/JNI/main sequence directly. NEW validates a previously prepared request and A02 bundle, compares persisted identity/receipt data, then commits A02 handoff. Same exported name now has different preconditions and sequencing.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:5890`, `evidence/runtime-provider/new/disassembly.txt:7545`; [evidence/runtime-provider/functions/3228fee5dd0320f9.diff](evidence/runtime-provider/functions/3228fee5dd0320f9.diff).

## 12. runtime-provider: `WLAR_PrepareA02PrerequisiteBundleV2` — restore

New public entry validates V2 manifest/load result, process identity and prerequisite transitions before preparation. It is part of the new A06/A02 protocol; not an ABI-neutral helper.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8310`; [evidence/runtime-provider/functions/9772286fc273ebf2.diff](evidence/runtime-provider/functions/9772286fc273ebf2.diff).

## 13. runtime-provider: `_ZN9appspawnx16AppSpawnXRuntime7startVmEb` — restore

Both artifacts already implement startVm(bool) and non-zygote mode. NEW adds the abort VM option and Java System.loadLibrary(javacore), and moves registerNativeMethods/cacheJavaReferences out to preload. Restore R155 ordering and dependencies as a unit; retain startVm(false) for the specialized child. R155 calls are at disassembly lines 1261/1264/1267.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:232`, `evidence/runtime-provider/new/disassembly.txt:232`; [evidence/runtime-provider/functions/5377bb33fa19d9f6.diff](evidence/runtime-provider/functions/5377bb33fa19d9f6.diff).

## 14. runtime-provider: `_ZN9appspawnx9ChildMain27runAfterStockSpecializationERKNS_8SpawnMsgEPNS_16AppSpawnXRuntimeE` — harmless-constant-relocation

Correct R155 80c9aee0 already has the Typeface nativeWarmUpCache no-op, omits zygote post-fork calls and defers adapter initialization. Only one unresolved rodata displacement differs; both resolve to nativeWarmUpCache (provider-focused-evidence.json). Withdraw the earlier behavioral rollback recommendation.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:4078`, `evidence/runtime-provider/new/disassembly.txt:4344`; [evidence/runtime-provider/functions/f8463b3e55a8975d.diff](evidence/runtime-provider/functions/f8463b3e55a8975d.diff).

## 15. runtime-provider: `_ZN9appspawnx16AppSpawnXRuntime7preloadEv` — restore

NEW moves registerNativeMethods and cacheJavaReferences from startVm into preload, preceded by VerifyLoadedAdapterBridge. Restore the R155 phase boundary together with startVm; retain exact adapter-bridge verification. Typeface behavior already exists in R155 and needs no restoration.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:2620`, `evidence/runtime-provider/new/disassembly.txt:2835`; [evidence/runtime-provider/functions/6d5a1aaa444cdd18.diff](evidence/runtime-provider/functions/6d5a1aaa444cdd18.diff).

## 16. runtime-provider: `_ZN12_GLOBAL__N_121ConstructChildRuntimeEPv` — restore

Removed R155 callback contains setenv calls, stack-limit setup and runtime construction. Deleted environment literals include ICU/TZDATA/I18N/DEX2OAT settings. NEW Constructors callback must be assessed with its callers; three-file evidence does not prove equivalent setup occurs elsewhere.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:6918`; [evidence/runtime-provider/functions/393b8f6894fd9fae.diff](evidence/runtime-provider/functions/393b8f6894fd9fae.diff).

## 17. child: `westlake_child_hook_table_v1_prepare_candidate` — restore

Candidate preparation now participates in callback-owner lifetime management and a new prepare_candidate_with_callbacks entry. Receipt publication/revocation semantics changed. Keep the R155 lifecycle unless the new owner protocol is intentionally adopted and tested as a complete set.

Evidence: `evidence/child/r155/disassembly.txt:1105`, `evidence/child/new/disassembly.txt:6177`; [evidence/child/functions/4048961ccf1ee582.diff](evidence/child/functions/4048961ccf1ee582.diff).

## 18. host: `WLEI_VerifyFileHex` — retain-hardening

Verification delegates to a verified-open helper and closes the verified descriptor instead of the old separate checks. Do not blindly remove identity verification to emulate R155. Inspect OpenVerifiedFileHex and VerifyBuildId deltas; failed candidate identity may be a generation mismatch, not a defect in verification. Functional equivalence is not yet proven.

Evidence: `evidence/host/r155/disassembly.txt:15148`, `evidence/host/new/disassembly.txt:15512`; [evidence/host/functions/9d3ec6012099fd07.diff](evidence/host/functions/9d3ec6012099fd07.diff).

## 19. runtime-provider: `_GLOBAL__sub_I_westlake_android_runtime_provider.cpp` — restore-with-protocol

New constructor zeroes/initializes global Context and registers its destructor through __cxa_atexit. It is not an empty compiler stub. It supports the new protocol; remove only if reverting that stateful protocol, not as an isolated constructor deletion.

Evidence: `evidence/runtime-provider/new/disassembly.txt:9307`; [evidence/runtime-provider/functions/b781eb8d00eb13f1.diff](evidence/runtime-provider/functions/b781eb8d00eb13f1.diff).

## 20. host: `AppSpawnClearEnv` — harmless

The resolved diff only changes w6 source-line literals passed to HiLogPrint (1437→1442, 1433→1438). Calls, control flow and cleanup operations are unchanged after address resolution. Keep; no behavioral restoration needed beyond diagnostic text.

Evidence: `evidence/host/r155/disassembly.txt:6527`, `evidence/host/new/disassembly.txt:6567`; [evidence/host/functions/64dd717e78a1b172.diff](evidence/host/functions/64dd717e78a1b172.diff).
