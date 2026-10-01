# B1(+VMFALLBACK) t3 window FAIL — call-site + jvm source disassembled (846 vs B1): the VM pointer is NOT the bug

Outer-ring dispatch after the FAIL: *before any next window, offline-establish the SessionStageAdapter construction
call-site and the source of the `jvm_` passed in, by disassembling 846 vs B1 line-by-line; write it into
offline_precheck.evidence.* Done below. **Result: the passed VM is sourced identically in 846 and B1
(`AdapterBridge::getInstance().jvm_`) and is non-null; the InvalidDisplay is a foreign/wrong-copy VM handle
(the #80 double-load), not a null VM — so the VMFALLBACK fix could not and did not help.**

## This run (5cd, 2026-10-01T17:15, deployed B1+VMFALLBACK sha 53257ace, child 15793/15813)
Smoke FAIL. `[B1-VMFALLBACK].*recovered process VM` hits = **0** (hilog captured). HW+ZZ dead at t20, probe child
count 0. Child hilog, verbatim:
```
17:15:50.451 OH_WindowMgrClient: createSession: ... ohTokenAddr=0x7f34e18140
17:15:50.451 OH_SessionStageAdapter: SessionStageAdapter created
17:15:50.451 OH_SessionStageAdapter: Failed to get JNIEnv in constructor      <-- GetEnv(jvm_) gave no env
17:15:50.453 OH_SessionStageAdapter: [IPC] ENTER SessionStage.EnableRootBlast
17:15:50.453 OH_SessionStageAdapter: EnableRootBlast: missing JNIEnv or Android IWindow
17:15:50.453 OH_WindowMgrClient: createSession: failed to enable root BLAST ... refusing a null-BBQ ViewRoot
17:15:50.454 [stderr] android.view.WindowManager$InvalidDisplayException: Unable to add window ... the specified display can not be found
```
`[B1-VMFALLBACK]`=0 ⇒ `getJavaVM()` returned a **non-null** `jvm_` (the fallback branch, which only runs when
`jvm_==null`, never executed). So the VM pointer passed down was non-null, yet the ctor's
`ScopedJniAttachment(jvm_)` produced no `JNIEnv` — on thread 15813, which is **actively running a JNI native call**
(so it is attached to the real process VM and a valid env exists for it). The only way `GetEnv(jvm_)` yields nothing
on such a thread is if `jvm_` is a non-null VM handle the thread is **not attached to**.

## Call-site (source, vendored tree that was compiled)
- `window/jni/window_session_adapter.cpp:71` `JavaVM* jvm = AdapterBridge::getInstance().getJavaVM();`
  `:72` `createSession(jvm, androidWindow, ...)` — inside static `doCreateSession(JNIEnv* env, ...)`, which *has a
  live `env`* but does not use it to derive the VM. (Same in `nativeCreateSession_compat_impl:147`.)
- `window/jni/oh_window_manager_client.cpp:363` `OHOS::sptr<SessionStageAdapter> stage = new SessionStageAdapter(jvm, androidWindow);`
- `window/jni/session_stage_adapter.cpp:34` ctor `: jvm_(jvm)`, `ScopedJniAttachment(jvm_)` → null env → early return → `androidWindow_` stays null → EnableRootBlast false.

## 846 vs B1 disassembly of the jvm source (DevEco llvm-objdump)
**846** `(anonymous namespace)::doCreateSession` @ `0xf0938`:
```
f0a44:  bl   oh_adapter::AdapterBridge::getInstance()      ; x0 = &instance
f0a48:  ldr  x23, [x0]                                      ; x23 = *(instance+0) = instance.jvm_  (jvm_ is member 0)
f0a4c:  bl   oh_adapter::OHWindowManagerClient::getInstance()
...     ; x23 (jvm_) later passed as the JavaVM* arg to createSession -> SessionStageAdapter ctor
```
846 has **no `getJavaVM` symbol** — its inline `{ return jvm_; }` was compiled to the direct `ldr x23,[x0]` above.
**B1** calls the out-of-line `oh_adapter::AdapterBridge::getJavaVM() const` @ `0xd03c8`, which returns the same
`jvm_` (member 0) and, only when it is null, dlsym-recovers a process VM. Net: **both load
`AdapterBridge::getInstance().jvm_` (offset 0); B1 adds a null-only fallback that never triggered here.** The VM
source is byte-for-byte equivalent in intent; the divergence is not here.

## Conclusion (what the evidence proves)
1. The jvm handed to `SessionStageAdapter` is `AdapterBridge::getInstance().jvm_` in **both** 846 and B1 — not the
   live `env`, and not `JNI_GetCreatedJavaVMs`.
2. In this B1 run that `jvm_` was **non-null** (fallback hits 0) yet `GetEnv(jvm_)` gave no env on a JNI-call
   thread ⇒ `jvm_` is a **non-null but foreign/wrong-copy VM** — the #80 double-load (separate per-copy
   `AdapterBridge` singletons; `getInstance()` in the window copy returns a singleton whose `jvm_` was set to a VM
   this thread is not attached to). 846 lights in U8 because, in that deployment, the copy's `jvm_` is the real VM.
3. The VMFALLBACK fix targeted *null* `jvm_`; the actual failure is *foreign-non-null* `jvm_`. Different failure
   mode → no effect.

## Proposed next repair (NOT yet deployed — window stopped per outer ring)
At the call-site, derive the VM from the live `env` (always the process VM the current thread is attached to),
falling back to the stored singleton only if that fails:
```cpp
JavaVM* jvm = nullptr;
if (env->GetJavaVM(&jvm) != JNI_OK || jvm == nullptr)
    jvm = AdapterBridge::getInstance().getJavaVM();   // last resort
```
in `doCreateSession` and `nativeCreateSession_compat_impl`. This sidesteps the per-copy singleton entirely.
Equivalently/complementarily, dispatch ③'s N11b (collapse the double-load so `getInstance()` is process-unique)
makes `getInstance().jvm_` the real VM. Either must pass `abi_diff --old 846 --new … exit 0` offline before a
window. Evidence bundle: this file + the run hilog at
`$WORKSPACES/_cc-wiki-t3-rerun/win-b1vmfb-5cd-20261001T171427/smoke/group-0/.../helloworld/hilog.txt`.
