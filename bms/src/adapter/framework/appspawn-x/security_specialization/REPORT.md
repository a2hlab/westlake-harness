# OH-owned security specialization handoff

Date: 2026-07-12

## Boundary

- Boundary: raw OH appspawn security-message preservation and the stock
  parent-pre-fork to child-execute invocation boundary.
- Android behavior: an Android app process may continue only after its complete
  security inputs have reached the system process factory and DAC, token,
  SELinux, namespace, and sandbox specialization have succeeded.
- OpenHarmony mapping: selected Route A retains the stock host, decoder,
  contexts, hook engine, fork, security stages, result pipe, and lifecycle;
  WestLake registers only the Android child processor through
  `RegChildLooper`. This root POD control plane is Route B fallback evidence.
- Fix layer: adapter-owned stock-host entry/plugin plus a typed C/POD boundary;
  no handwritten mount, namespace, procattr, SELinux, token, or DAC
  implementation.

## Evidence target

- What this proves: the fallback raw request can be retained without projection
  loss; additionally, Route A has exact stock module/child-looper seams,
  fail-closed stage-tail receipts, and target-compilable plugin/host/service
  objects as documented in `stock_child_plugin/REPORT.md`.
- What this does not prove: that the missing same-generation OH wrapper exists,
  that the stock sandbox ran on 5EAB5, or that Unity loaded or displayed a
  frame.

## Environment

- Host: Darwin arm64; local clang runs the C model and ASan/UBSan.
- Device: none used by this task. The separately frozen read-only identity
  evidence names 5EAB5, but runtime invocation is explicitly not proven.
- Tool path: project-local frozen OH clang 15, sysroot, readelf and objdump in
  `.work/product-tls-generation/frozen`, executed inside the image pinned by
  `.work/product-tls-generation/tool_runtime.lock` with network disabled.
- Artifact path: `adapter/framework/appspawn-x/security_specialization/out/target/`.
- App: generic `MSG_APP_SPAWN` security boundary; no package allowlist and no
  APK was launched.

## Status

- Label: `real_impl` for the fail-closed Route B control plane and Route A
  plugin/receipt/host-entry source; `build_pass` for their deterministic target
  objects; `stub`/disabled for Route A's missing runtime provider and final host
  link; `device_verified=false`.
- Why: both local verification suites pass. Product activation is blocked by
  the four real `WLAR_*` provider symbols, a security-free Android child entry,
  final stock-host link, and device proof—not by missing OH appspawn source.

## Proven

- Frozen OH wire ABI: message header 276 bytes, DAC payload 332 bytes, extended
  TLV header 40 bytes, maximum 128 TLVs, and 64 KiB message.
- Frozen OH ordering: server config preload; parent stage 20 from priority 0;
  fork; child stage 31 from priority 0; child failure blocks spawn success.
- `WlssSecurityRecordV1` preserves the original raw pointer/size/SHA, both v7
  flag words, owner, permission, internet, and arbitrary extension TLVs with
  their raw spans, names, types, and data lengths.
- Preparation rejects missing bundle/DAC/APL/token/owner/permission/internet,
  malformed DAC/ext/flags, zero token, empty APL, missing config/module engine,
  zero generations, and identity mismatch.
- `APP_FLAGS_NO_SANDBOX` and `APP_FLAGS_IGNORE_SANDBOX` are rejected before
  stock code can turn either path into success.
- Before both parent and child callbacks, raw bytes, full stock/config
  identities, and the parsed record shape are revalidated. Failure is terminal.
- Typed receipts require exact stage, start priority, generations, config
  preload, all parent hooks, shared mount, sandbox applied, no bypass, and
  stock result zero.
- Host: 29 tests pass; ASan/UBSan passes; 4/4 dangerous mutants are killed
  (NO_SANDBOX acceptance, missing DAC, missing token, ignored sandbox result).
- Target: two AArch64 builds are byte-identical. The DSO has no PT_TLS,
  constructor, DT_NEEDED, undefined symbol, direct syscall, security primitive,
  dynamic loader call, or fabricated opaque OH type. SHA-256 is
  `98a49fe25aa3927e5915b69e89dbdbb8653fee6b90d08458c7fcf8201f41c4a4`.

## Not proven

- No call site in existing `spawn_server` or `child_main` consumes this ABI.
- No stock config preload, parent shared mount/debug hook, child SELinux/DAC/
  token/namespace/sandbox operation, or child result pipe is device-proven.
- The selected Route A final executable is not linked and its four Android
  runtime-provider symbols are not implemented. The frozen stock host—not a
  new wrapper—will own `AppSpawnMsgNode`, `AppSpawningCtx`, `AppSpawnMgr`, the
  decoder, hook engine, and child hook runner.
- No APK, Unity native initialization, Surface/EGL, present, or visible frame is
  proven by this control-plane fixture.

## Failed

- Direct binding to installed `/system/lib64/libappspawn_module_engine.so`
  failed the ABI closure check: it resolves to `libappspawn_stub_empty.so`, has
  only two exports, and provides no hook engine or decoder.
- Direct invocation of the real sandbox DSO's exported
  `SetAppSandboxProperty(AppSpawnMgr *, AppSpawningCtx *)` failed architecture
  review: its arguments are opaque generation-private owners, its constructor
  expects hook-engine symbols from the owning executable, and calling only the
  child function omits config preload and parent hooks.
- Route B as the immediate implementation path failed architecture comparison:
  the complete frozen source proves Route A can preserve the stock owner and
  use `RegChildLooper`, avoiding a duplicated socket/decoder/fork engine.

## Next evidence

- Command: implement the four `WLAR_*` symbols and the security-free
  post-specialization Android child entry, final-link the frozen stock host,
  rerun both verification suites, then perform a true-cold device spawn.
- Expected output: no unresolved provider edge; plugin and stock common/sandbox
  modules load; ART preFork succeeds before fork; bypass guard and stage-31
  tail succeed; the stock result pipe reports success; Android child entry is
  reached exactly once.
- If it fails: leave `product_activation=false`. Do not use the empty stub,
  fabricate OH structs, call only `SetAppSandboxProperty`, handwrite mounts,
  touch procattr, enable NO_SANDBOX, ignore errors, or return a fake receipt.

## Shim/stub/bypass inventory

- Item: `WlssStockOps` callback fixture and typed receipts.
- Owner: common appspawn-x security boundary; request-local future OH wrapper.
- Why it exists: it makes the correct OH ownership and ordering executable
  while the matching production wrapper inputs are missing.
- Removal condition: callbacks become real only when the exact OH GN wrapper
  owns and executes the complete stock engine; the POD boundary remains.
- Test coverage: 29 host groups, ASan/UBSan, four semantic mutants, target ELF
  and deterministic-build gates.
- App-specific or common: common; no CardWords, Unity, or package policy.

- Item: `WLSS_STOCK_BINDING_EMPTY_STUB`.
- Owner: negative identity model only.
- Why it exists: explicitly identifies and rejects the device's installed empty
  module-engine alias instead of confusing filename presence with capability.
- Removal condition: never accepted; a full exact binding uses
  `WLSS_STOCK_BINDING_OH_GN_NORMAL_V7` plus verified identities.
- Test coverage: empty-module-engine rejection and stock identity failure.
- App-specific or common: common negative fixture.

- Item: product activation.
- Owner: future generation producer, currently disabled.
- Why it exists: no activation code was added; this line records the absence of
  a bypass or fake-success route.
- Removal condition: exact wrapper and true-cold device receipt satisfy every
  item under Next evidence.
- Test coverage: target verifier reports `product_activation=false`; DSO has no
  loader dependency or environment/package switch.
- App-specific or common: common.

## Memory/skill/CI/review updates

- Memory: stock `AppSpawnChild` already owns the complete security pipeline and
  `RegChildLooper` is the correct Android seam. Raw OH TLV preservation remains
  the fallback discipline; an empty stub identity is not a callable engine.
- Skill: WestLake boundary-first, four-gate, bring-up discipline, and HanBing
  design checks were applied; no device trial replaced missing source proof.
- CI: run both `security_specialization/run_all.sh` and
  `security_specialization/stock_child_plugin/run_all.sh`; forbid packaging
  while any `WLAR_*` import or final-link evidence is absent.
- Review checklist: reject direct procattr/mount/namespace code, guessed OH
  layouts, dlopen/dlsym of the sandbox export, missing raw TLVs, one-word flags,
  either bypass flag, nonzero-result suppression, or identity-free receipts.

## HanBing five-question design check

- Q1 ART/class linker/vtable changed: no.
- Q2 BCP/ActivityThread changed: no.
- Q3 fix is at the adapter boundary: yes; the adapter only preserves and gates,
  while exact OH code remains the security-operation owner.
- Q4 coherent rebake: an OH GN wrapper built from one exact generation is
  required; mixing the device sandbox with guessed local engine code is banned.
- Q5 truly-cold device proof: not proven and not claimed.
