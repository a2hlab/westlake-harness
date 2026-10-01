# B1 end-to-end revert spec — re-emit the 5 drifted functions (+ internal callers) at 846 signatures

Goal (outer ring, 2026-10-01): produce a bridge artifact whose 5 drifted functions carry **846's signatures AND
846's behavior**, so `abi_diff --old <846> --new <artifact>` exits 0 and the on-board t3 `InvalidDisplayException`
is gone. Technique: **demote each evolved parameter to an internal default and revert the internal callers** — keep
the current implementation but drop the later-rev parameters from the exported signature and from the call sites,
so both the mangled export and the call ABI match 846. (This is B1: the drift is purely N2 being a later revision
than 846; there is no separate 846 source snapshot — B1/flattened history.)

All line numbers are against `bms/src/adapter/framework/...` at the snapshot read 2026-10-01; the builder must
confirm each function still carries the evolved signature in the chosen build snapshot (see the HEAD-vs-7cf8ebcc
note under #4/#5).

## 1. `OHWindowManagerClient::createSession` — drop the 5th int `androidFlags`  **(the t3 fix)**
- File: `window/jni/oh_window_manager_client.cpp:357` (impl), `window/jni/oh_window_manager_client.h:114` (decl).
- NEW (846-absent param in **bold**):
  `createSession(JavaVM*, jobject, bundleName&, abilityName&, moduleName&, windowName&, int androidWindowType,
  int displayId, int requestedWidth, int requestedHeight, **int androidFlags**, uint64_t ohTokenAddr)`
  — mangled `…iiiiim`.
- 846: `(…, int androidWindowType, int displayId, int requestedWidth, int requestedHeight, uint64_t ohTokenAddr)`
  — mangled `…iiiim`. **846 already had `displayId` (2nd int); the added int is `androidFlags` (the last int,
  appended before the `uint64` handle).**
- Revert: remove the `androidFlags` parameter. In the body, delete the `androidFlags`-derived logic and restore the
  846 `SceneSessionManager.CreateAndConnectSpecificSession(...)` call shape (the 846 path did not pass/derive from
  `androidFlags`). If a flags value is still needed internally, default it to `0`.
- Caller: the `adapter.activity.WindowSessionProxy` JNI binding / whatever native method invokes `createSession`
  (grep `createSession(` call sites in `window/jni/` and `surface/jni/`) — stop passing `androidFlags`.
- Why this is the t3 fix: t3 showed every app dying at `addView` with `InvalidDisplayException: the specified
  display can not be found`. `consumer_breaks=0` ⇒ the caller is the bridge's own (internal) binding passing the
  new 5-int form, so it is **not** an arg-shift; it is the new `androidFlags`-aware session-creation path producing
  a session the deployed OH SceneSessionManager treats as an invalid display. Reverting to the 846 call shape
  removes that path.

## 2/3. `OHInputBridge::injectKeyEvent` / `injectTouchEvent` — drop `ohEventId` (long) + `std::function<void()>`
- File: `window/jni/oh_input_bridge.cpp:298` (injectTouchEvent; injectKeyEvent nearby), `.h:102/137` (decls),
  caller `window/jni/oh_input_manager_bridge.cpp`.
- NEW: `injectTouchEvent(int sessionId, int action, float, float, long downTime, long eventTime,
  **long ohEventId, std::function<void()>**)`; `injectKeyEvent(..., long downTime, long eventTime,
  **long ohEventId, std::function<void()>**)`.
- 846: `(…, long downTime, long eventTime)` — no `ohEventId`, no callback.
- Revert: remove `ohEventId` + the `std::function<void()>` completion callback. In the body, delete the
  `completionRouter_` (EventCompletionRouter) usage — `openSession`/`closeSession`, the `INPUT_MSG_TYPE_FINISHED`
  gated-completion contract (the FinishedTokenLedger/EventCompletionRouter subsystem is a 2026-07-28+ addition that
  is **0 functions in 846**). Revert to 846 fire-and-forget injection (inject the event, return, no FINISHED gate).
- Caller: `oh_input_manager_bridge.cpp` (the dispatcher that forwards events to `injectKeyEvent`/`injectTouchEvent`)
  — stop computing/passing `ohEventId` and the callback.

## 4. `ConfigureComponentResolverRuntimeV1` — drop the trailing `ComponentStateReaderV1*`
- File: `package-manager/component_resolver/include/component_resolver_runtime_v1.h:77`,
  `src/component_resolver_runtime_v1.cpp`.
- NEW: `(Catalog*, Guard*, CallerResolveContextProviderV1*, FaultInjector*, string*, **ComponentStateReaderV1***)`.
- 846: `(Catalog*, Guard*, CallerResolveContextProviderV1*, FaultInjector*, string*)`.
- Revert: remove the `ComponentStateReaderV1*` parameter; in the body, drop its wiring into the service (pass
  nothing / construct the service without a state reader). Caller(s) of `ConfigureComponentResolverRuntimeV1`
  stop passing it.

## 5. `ComponentResolverServiceV1::ctor` — drop the trailing `ComponentStateReaderV1*`
- File: `package-manager/component_resolver/include/component_resolver_v1.h:203`,
  `src/component_resolver_runtime_v1.cpp`.
- NEW: `(ComponentCatalogProviderV1*, PackageGuardReaderV1*, ResolveFaultInjectorV1*, **ComponentStateReaderV1***)`.
- 846: `(ComponentCatalogProviderV1*, PackageGuardReaderV1*, ResolveFaultInjectorV1*)`.
- Revert: remove the `ComponentStateReaderV1*` param + the `stateReader_` member and all `stateReader_->…` uses
  (guard-off = 846 behavior).
- **HEAD note:** the read-2026-10-01 HEAD of `component_resolver_v1.h:203` already shows the **3-arg** (846) ctor,
  and the 7cf8ebcc *binary* has the 4-arg. So HEAD ≠ 7cf8ebcc's source for this TU. The builder must build from a
  snapshot and apply the revert only to the functions that still carry the evolved signature **in that snapshot**;
  verify with `abi_diff` against the freshly-built artifact, not against HEAD assumptions (EVO-0053).

## Build + gate order
1. **Build** (needs the part-D environment): DevEco clang is local
   (`/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/clang++`), but the **board
   6.1.0.31 link inputs are NOT local** — they were rsynced from hw248 for part D and are gone now
   (`hw248:/opt/build-runs/m1-full-generation-20260824-r43-icu76/meta/immutable-base/system/lib64`, 41 `-l` libs).
   So a deployable `.so` needs those re-fetched. Compile-only is local; link is not. Recipe +
   receipts: `partD-repro/compile_oh_adapter_bridge_arm64.partD.sh` + `run-link.sh` + `rebuild-receipt-partD.json`.
2. **Offline gate**: `abi_diff.py --old <846> --new <B1 artifact> --consumer <runtime>` → **exit 0** (drift 0,
   consumer breaks 0). If non-zero, a function still carries an evolved signature — fix and rebuild.
3. **On-board** (only after gate 2): the `t3-b1-board-run-plan.json` window on 5ea (single variable: bridge
   846→B1), `offline_precheck` citing the exit-0 abi_diff output + the prior t3 `InvalidDisplayException` line;
   pass = HW/ZZ + View/Compose/lit shards show no `InvalidDisplayException`/`System.exit(1)` and no U8 regression.

## Status / handoff
- Spec complete and source-grounded (5 functions, exact params to drop, callers to update).
- **Build blocker**: the deployable rebuild needs the hw248 6.1.0.31 link inputs re-provisioned (compile is local,
  link is not). Options: (a) re-rsync the link inputs from hw248 and build here, or (b) hand the end-to-end rebuild
  to cx-t0 / a build-host lane using this spec. Either way, `abi_diff` exit 0 is the gate before the 5ea window.
