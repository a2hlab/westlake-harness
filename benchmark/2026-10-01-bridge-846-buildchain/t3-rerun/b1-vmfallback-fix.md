# B1(+VMFALLBACK): recover the process JavaVM when the double-loaded bridge copy's `jvm_` is null

**The t3 `InvalidDisplayException` was never the 5 ABI signatures.** The prior B1 (sha `a1f57197…`) was
already 846-faithful (`abi_diff` exit 0, drift 0, consumer-breaks 0) and *still* failed the on-board t3 window
identically to 7cf8ebcc. Disassembly + hilog alignment pinned the real cause to a **null `JavaVM` passed into the
`SessionStageAdapter` constructor**, and this change fixes it at the source where the bridge fetches the VM.

## What was wrong (root, source-pinned)
`OHWindowManagerClient::createSession` → `SessionStageAdapter(jvm, androidWindow)` ctor →
`ScopedJniAttachment(jvm_)` returns a null `JNIEnv` when `jvm_` is null →
ctor returns early → `androidWindow_` stays null → `EnableRootBlastForTopLevelContent()` returns false →
`createSession` refuses the null-BBQ ViewRoot → Java `ViewRootImpl.setView` →
`WindowManager$InvalidDisplayException` → `System.exit(1)` → blank. (Full chain: `b1-invaliddisplay-rootcause.md`.)

The VM that reaches that ctor comes from `AdapterBridge::getInstance().getJavaVM()`
(`window_session_adapter.cpp:71/147`). Under the #80 **double-load** (oc-t4: the route-A bridge is mapped twice —
one copy in the runtime-CL musl namespace, one in the default namespace — with *separate* process-global
`AdapterBridge` singletons), `JNI_OnLoad`/`setJavaVM` only populates `jvm_` in the copy OH ran `JNI_OnLoad`
against. The copy whose ctor runs `createSession` can have `jvm_ == nullptr`.

Disassembly of the deployed **846** binary's `SessionStageAdapter` ctor shows it uses the **passed** `jvm_`
(member at +0x80) + `GetEnv` + attach-on-`EDETACHED`, with **zero** references to `JNI_GetCreatedJavaVMs`. So 846
uses the same ctor mechanism — the divergence is purely that in the *rebuilt* copy running `createSession`, the
passed VM is null, while the deployed 846 (which double-loads too, yet lights) has a usable VM on that path.

## The fix (one accessor, process-level fallback + one activation log)
`AdapterBridge::getJavaVM()` changed from an inline `{ return jvm_; }` to an out-of-line definition that, when
`jvm_` is null, recovers the one process VM via `dlsym(RTLD_DEFAULT, "JNI_GetCreatedJavaVMs")` and caches it
(`jvm_` made `mutable`). `JNI_GetCreatedJavaVMs` is in the sysroot `jni.h` but **not** in the bridge's import
table, so it must be resolved by `dlsym` (the bridge already links `-ldl` / includes `<dlfcn.h>`).

- `adapter/framework/core/jni/adapter_bridge.cpp`: out-of-line `getJavaVM()` + `[B1-VMFALLBACK]` log.
- `adapter/framework/core/jni/adapter_bridge.h` **and** `adapter/sources/oh61-v7-b2133b5b/framework/core/jni/adapter_bridge.h`:
  inline getter → out-of-line declaration; `jvm_` → `mutable`. **Both** copies had to change: an inline getter in
  the header the caller compiles against bakes the old body into the caller; moving it out-of-line only takes
  effect once every header the callers see agrees it is out-of-line.

Activation log (grep `[B1-VMFALLBACK]` in child hilog):
`getJavaVM: jvm_ null in this bridge copy -> JNI_GetCreatedJavaVMs recovered process VM %p (nVMs=%d)`.
Absence of the line + a set `jvm_` means the fallback was not needed on that path; the error variants cover
"no VM" and "dlsym failed".

## Build-config correction found along the way
The clean rebuild surfaced that `run-compile.sh` had `OH61_WINDOW_SOURCE_ROOT` pointing at the **in-tree**
`adapter/framework/window/jni`, whose `oh_window_manager_client.h` `SessionEntry` was a stale half-revert
(missing `sessionProperty` / `ohTokenAddr` that the `.cpp` uses → 5 compile errors). The **vendored**
`adapter/sources/oh61-v7-b2133b5b/framework/window/jni` tree is the self-consistent 846-reverted one (same TU
set, the recipe default, and what `run-link.sh` already uses). Repointed `run-compile.sh` at the vendored tree so
both phases agree. **Rule: a self-inconsistent `.cpp`/`.h` pair cannot have produced a valid strict-linked `.so`;
when two source roots disagree, the one that compiles + links is ground truth, not the one a stale env var names.**

## Evidence / numbers
- Build: 58/58 TUs compiled, 0 fails; strict link (`-z defs --no-undefined --no-allow-shlib-undefined`) OK → 2.6M
  AArch64 ELF64.
- Symbols (DevEco Darwin `llvm-nm`): `adapter_bridge.o` and the `.so` both define
  `T oh_adapter::AdapterBridge::getJavaVM() const`; `window_session_adapter.o` holds a matching `U` reference →
  the window path **calls** the fallback-equipped symbol (not the old inlined `return jvm_`).
- Binary strings: the 3 `[B1-VMFALLBACK]` messages + `JNI_GetCreatedJavaVMs` present.
- **Offline gate — PASS**: `abi_diff.py --old <846> --new <B1+VMFALLBACK> --consumer <liboh_android_runtime.so 9e14bf20…>`
  → `exports: old 2357, new 2662; removed 8, added 313; signature drift 0; consumer breaks 0` → **exit 0**.
  `removed 8` = the same genuinely-absent set (SessionStageAdapter/WindowCallbackAdapter `getJNIEnv`+`detachIfNeeded`,
  2 template instantiations, `oh_anw_notify_presented`, `oh_anw_wrap_for_activity`). JSON:
  `b1-abi-diff-846-vs-B1-vmfallback.json`.
- **New B1(+VMFALLBACK) sha256**: `53257ace843983e609afed59dacb4be2048106db011cfcb8a94b7f541e8ca151`
  (prior B1 `a1f571978d320b13266b9d83a03e48d6ff4fc6e1e44a16b0ecb90b856a45605b`).
- Artifact: `$WORKSPACES/_cc-wiki-t3-bridge/liboh_adapter_bridge.so.b1-846sig-vmfallback`.

## Status / next
Offline gate green. Board window not opened (awaiting outer-ring 5ea slot). Plan `t3-b1-board-run-plan.json` +
smoke `t3-smoke-b1-5ea.json` updated to the new artifact/sha and the corrected (null-`jvm_`) hypothesis.
Per dispatch ③, B1(+VMFALLBACK) can also be stacked on N11b if that lands.
