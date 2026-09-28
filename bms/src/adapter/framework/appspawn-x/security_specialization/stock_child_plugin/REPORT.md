# Route A stock-host/plugin handoff

## Boundary

- Boundary: OH appspawn process/security factory below, Android ART child entry
  above.
- Android behavior: preload ART in the process factory, coordinate zygote fork,
  then enter ActivityThread only after system-owned specialization succeeds.
- OpenHarmony mapping: stock `StartSpawnService`, decoder, contexts, stage 20,
  fork, stages 30/31, sandbox/common modules, response pipe, and process records;
  `RegChildLooper` is the sole Android-specific execution seam.
- Fix layer: adapter-owned stock-host main, stock module plugin, typed C/POD
  request/receipt, and one fail-closed parent-hook result check.

## Evidence target

- What this proves: Route A is a final-linked, deterministic target generation
  with exact stock/provider exports, an unambiguous module path, stage receipts,
  fail-closed bypass handling, receipt-bound MAIN admission, and a strict
  recursive real-provider closure without broad ART stubs.
- What this does not prove: admission of every later Android pthread/JNI thread,
  product deployment, device execution, Unity load, or first frame.

## Environment

- Host: Darwin arm64, clang host model, ASan/UBSan, Python stock-source gate.
- Device: no device operation in this task; `device_verified=false`.
- Tool path: project-local frozen OH clang 15/sysroot and image pinned by
  `.work/product-tls-generation/tool_runtime.lock`, network disabled.
- Artifact path: ABI fixture under `out/target/`; final host/provider generation
  under `out/route-a-generation/`.
- App: generic Android `MSG_APP_SPAWN`; no title/package allowlist.

## Status

- Label: `real_impl` for receipt/plugin/provider/post-specialization child path;
  `build_pending` for the new strict host-table/phase-aware AArch64 generation;
  the prior `build_pass` was invalidated by this ABI change. Product activation
  remains disabled and `device_verified=false`.
- Why: all six `WLAR_*` symbols, identity-bound host tables, MAIN WLTG
  admission, and the final adapter symbol closure are real, but pthread/JNI
  admission is not yet proven.

## Proven

- Full OH appspawn source closure is project-local: 430 files, tree SHA-256
  `1a113881bb525ea29b29ed6ffaea3948b8f64cea0a88ab978458894c503448d4`.
- Frozen stock source order is decoder/context -> stage20 -> fork -> stage31
  STOP_WHEN_ERROR -> reply -> child processor.
- Stock module export ABI contains the five imports the plugin uses:
  `AddServerStageHook`, `AddAppSpawnHook`, `GetAppSpawnMsgInfo`,
  `CheckAppSpawnMsgFlag`, and `RegChildLooper`.
- Explicit `MODULE_DEFAULT` installation avoids loading the competing ACE child
  processor while leaving `MODULE_COMMON` stock security modules intact.
- The plugin registers ART pre-fork/post-fork hooks, a pre-sandbox bypass guard,
  a stage-31 tail marker, and the final Android child looper. It contains no
  mount, namespace, procattr, token, UID/GID, or SELinux operation.
- The typed runtime preload receipt must be ready, generation-bound, SHA-bound,
  and declare `security_operations_mask=0` before child-looper registration.
- Ten stage-receipt tests pass. The host-services registry adds concurrent
  token, reentry, replay, callback-error and ABA controls; the loader-phase
  state machine and local SHA-256 implementation also pass ASan/UBSan. Four
  stage mutants are killed: missing parent tail, NO_SANDBOX acceptance,
  missing bypass guard, and missing child tail/replay.
- The parent fail-closed patch applies exactly and its candidate
  `appspawn_service.c` compiles to deterministic AArch64 object SHA-256
  `a63192557b72707cbad083393c877d8df8bf06c5c5291bc697516e922f1f63eb`.
- The previous plugin/host hashes are invalidated by the strict typed-table
  change. Current identities must come only from the next passing
  `out/route-a-generation/verification.json`; no pre-table hash is reusable.
- The ELF gate requires an inert plugin, BIND_NOW, no PT_TLS, direct syscall,
  security primitive, RPATH, or TEXTREL, plus an exact provider `DT_NEEDED`.
- `WLAR_GetRuntimeIdentity`, `WLAR_ServerPreload`,
  `WLAR_InstallHostRuntimeServices`, `WLAR_ZygotePreFork`,
  `WLAR_ZygotePostForkParent`, and
  `WLAR_EnterAndroidAfterStockSpecialization` are implemented in one provider
  DSO with exact SONAME, Build-ID, six-symbol export map, and a nonzero frozen
  generation identity.
- The provider compiles the existing `AppSpawnXRuntime` plus the new
  `child_main_after_stock.cpp`; legacy `child_main.cpp` and all of its token,
  DAC, sandbox, UID/GID mutation, and SELinux code are absent from the provider.
- The strict generation must build each artifact twice byte-identically. Its
  final host/provider/plugin identities are emitted only after the complete
  typed-gate build passes; older identities are not deployment candidates.
- Binary call-edge evidence proves server preload reaches real ART start/preload,
  parent hooks reach the real zygote methods, and the receipt-bound child entry
  reaches only the post-stock Android path. The final host exports every stock
  symbol used by the plugin and the main-owned compatibility preparation API.
- `ROUTE_A_INPUTS.json` binds the 430-file OH closure plus every direct adapter
  source, auxiliary header, link library, and pinned tool-generation manifest.
- The certified v12 ART provider base is frozen locally: two 23-DSO builds are
  byte-identical (manifest SHA-256
  `3177745fafb7b4cc9f49c1c535a11de0c79bbec51b4a7cee6f42ee2386425752`),
  with independent audit SHA-256
  `597d1b367c8ab399e2edb9d564e92ea550d57fffdf2198a2122bc791c5fad13f`.
  Route A freezes the base, replaces the old compat, app loader, and host-fake
  Palette with in-generation safe/real builds, and loads the 22-member
  recursive initial closure. Twenty base DSOs remain byte-identical.
  `libart_runtime_stubs.so` is absent; the real
  `libartpalette-system.so` is packaged but not initially loaded.
- The provider validates the stock receipt and already-applied uid/gid, binds
  them to the generation SHA in `WlncProcessIdentityV1`, and calls the
  main-owned WLTG preparation exactly once before request translation or any
  Android child entry. `child_main_after_stock.cpp` owns no second prepare.
- The final host links with `-z defs --no-allow-shlib-undefined`; its direct
  NEEDED edges bind the same-generation provider and freestanding registry,
  while the provider binds the same-generation safe compatibility DSO.
- The same-generation app native loader installs a one-shot typed gate after
  MAIN admission. Each guest `ANL_Dlopen` and `ANL_Dlclose` verifies the current
  thread is WLTG READY before entering `dlopen_ns` or running unload
  destructors; missing, duplicate, reentrant, or non-READY gates fail closed.

## Not proven

- `AppSpawnXRuntime::startVm()` has two dynamic roots outside the frozen ART
  provider set: `liboh_android_runtime.so` and `liboh_adapter_bridge.so`.
  No deploy-eligible same-generation ARM64 pair exists in the current output:
  the current runtime is ARM32, while the historical ARM64 bridge lacks the
  required SONAME/Build-ID/no-RUNPATH closure. The old Route-A certificate did
  not include these roots and is therefore invalidated for product preload.
- Namespace-pthread creation and JNI attach have not yet proven that WLTG's
  canonical per-process Bionic guard is copied
  to slot 5 of every admitted Android thread. CardWords has no Bionic-global
  guard import; Musl's `__stack_chk_guard` is outside this contract and is not
  read or written.
- No stock module load, config preload, fork receipt, process attach, APK load,
  render present, or visible frame is device-proven.

## Failed

- Route B is rejected as the immediate path because Route A exposes the real
  child-processor seam and preserves all stock owners with far less duplicated
  code.
- The earlier ABI-only plugin was deliberately load-ineligible without the six
  provider symbols. The final generation closes those symbols; no weak symbol,
  dlsym fallback, or fake success was introduced.
- Unpatched OH v7 parent stage 20 ignores hook failures. It is ineligible for
  ART pre-fork coordination; the exact six-line fail-closed source delta is
  required before final link.
- Treating MAIN admission as all-thread completion failed architecture review:
  external appspawn bypasses the AOSP native-fork child path, while later
  pthread/JNI/loader boundaries still require typed WLTG admission. Product
  activation remains false.

## Next evidence

- Command: first build and manifest the same-generation ARM64 adapter runtime
  and bridge with exact SHA/Build-ID, strict links, and complete closure; then
  integrate namespace-pthread/JNI WLTG admission and rerun
  `stock_child_plugin/run_all.sh`, then install the exact same-generation
  host/provider/plugin/registry/compat set and perform a true-cold spawn on 5EAB5.
- Expected output: binary proof of one generation-bound Bionic guard copied to
  main/created/attached-thread slot 5; provider/plugin load succeeds; runtime preload
  declares zero security operations; stage20 preFork and stage31 tail succeed;
  Android child entry is reached exactly once.
- If it fails: keep product activation false. Do not call legacy
  `ChildMain::run`, handwrite security, load ACE as a competing child owner,
  weaken BIND_NOW, ignore preFork failure, fabricate a receipt, or accept
  different guards across admitted threads.

## Shim/stub/bypass inventory

- Item: product-disabled later-thread admission edge.
- Owner: adapter native-compat thread-guard registry, called from the
  receipt-bound Route A child entry.
- Why it exists: receipt-bound MAIN publication and the loader gate are present,
  but namespace pthread and JNI attach gates are not yet closed.
- Removal condition: binary/mutation tests and true-cold device evidence prove
  the same generation-bound nonzero guard across MAIN/new/attached threads.
- Test coverage: final verifier records
  `wltg_canonical_bionic_process_guard_equals_all_admitted_slot5=false` and
  rejects activation.
- App-specific or common: common.

- Item: `WlascStageLedgerV1` COW call-order ledger.
- Owner: OH-owned WestLake plugin.
- Why it exists: bind parent tail, fork inheritance, bypass guard, child tail,
  and one-shot child entry without claiming a fabricated sandbox result.
- Removal condition: remains as the typed boundary; product activation only
  replaces missing provider symbols.
- Test coverage: ten tests, sanitizers, four semantic mutants, replay rejection.
- App-specific or common: common.

- Item: OH prefork cache, trace emission, and DFX dump catcher.
- Owner: stock host optional/diagnostic features.
- Why it exists: these three unused features are the only deliberate stubs in
  the final-link candidate; they are not on the normal Unity spawn path.
- Removal condition: add their exact frozen providers if product policy requires
  them; never substitute a process/security/lifecycle stub.
- Test coverage: `ROUTE_A_INPUTS.json` records the three-feature inventory.
- App-specific or common: common.

## Memory/skill/CI/review updates

- Memory: stock `AppSpawnChild` already owns the complete security sequence;
  `RegChildLooper` is the correct Android boundary. Parent stage20 must honor
  ART preFork failure before fork.
- Skill: HanBing no-drift, boundary-first, AonB black-box, frozen provenance,
  and explicit stub inventory guided the A-over-B decision.
- CI: `stock_child_plugin/run_all.sh` now builds the ABI fixture and final
  generation; forbid packaging while the guard semantic flag is false or any
  adapter symbol edge is unresolved.
- Review checklist: reject duplicate socket/decoder/fork/security owners,
  MODULE_APPSPAWN/ACE child competition, current security-repeating ChildMain,
  weak provider symbols, NO_SANDBOX/IGNORE_SANDBOX, and unhandled preFork error.

## HanBing five-question design check

- Q1 ART/class-linker/vtable changed: no.
- Q2 BCP/ActivityThread changed: no.
- Q3 boundary ownership: pass; stock OH owns process/security, adapter owns ART
  preload and final child entry.
- Q4 coherent build: required; one frozen OH source tree and one provider
  generation must produce the final host/plugin pair.
- Q5 truly-cold device proof: not proven and not claimed.
