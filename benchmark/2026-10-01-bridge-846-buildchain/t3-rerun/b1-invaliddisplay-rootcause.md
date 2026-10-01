# B1 (and 7cf8ebcc) InvalidDisplayException root cause: SessionStageAdapter ctor can't get a JNIEnv

**The t3 blank is NOT the 5 ABI signatures (B1 proved that: abi_diff exit 0, behavior unchanged). It is a
JavaVM/JNI-attachment runtime regression that only manifests in the REBUILT bridge — which is why both 7cf8ebcc
and B1 fail where the original 846 binary works.** Found offline by aligning the HelloWorld window/display hilog of
a U8+846 success run against the B1 fail run (outer-ring dispatch).

## The first divergence (846 success vs B1 fail), with hilog
Both runs query the display fine (`getDisplayInfo(0) -> 1200x1920`). They diverge inside `createSession`:
```
846 (OK, 61b U8 smoke):  OH_WindowMgrClient: createSession: bound Android top-level content to OH MainSession parentId=187  -> CreateAndConnectSpecificSession OK -> window lit
B1 (FAIL, 5ea):          OH_WindowMgrClient: createSession: failed to enable root BLAST for Android top-level content; refusing a null-BBQ ViewRoot
                         -> android.view.WindowManager$InvalidDisplayException: … the specified display can not be found -> System.exit(1)
```

## The causal chain (source-pinned)
1. `OHWindowManagerClient::createSession` (oh_window_manager_client.cpp:495): `if
   (!stage->EnableRootBlastForTopLevelContent()) { LOGE("…failed to enable root BLAST…refusing a null-BBQ
   ViewRoot"); … }`.
2. `SessionStageAdapter::EnableRootBlastForTopLevelContent` (session_stage_adapter.cpp:147):
   `if (!env || !androidWindow_) { ALOGE("EnableRootBlast: missing JNIEnv or Android IWindow"); return false; }`
   — B1 hilog: `OH_SessionStageAdapter: EnableRootBlast: missing JNIEnv or Android IWindow`.
3. **Why `androidWindow_` is null** — the SessionStageAdapter constructor (session_stage_adapter.cpp:34-47):
   ```cpp
   SessionStageAdapter::SessionStageAdapter(JavaVM* jvm, jobject androidWindow) : jvm_(jvm) {
     ScopedJniAttachment attachment(jvm_, "OH_SessionStageAdapter");
     JNIEnv* env = attachment.env();
     if (!env) { ALOGE("Failed to get JNIEnv in constructor"); return; }   // <-- B1 hits THIS
     androidWindow_ = env->NewGlobalRef(androidWindow);                    // <-- never runs -> androidWindow_ stays null
     …
   }
   ```
   B1 hilog: `OH_SessionStageAdapter: Failed to get JNIEnv in constructor`. So `ScopedJniAttachment(jvm_)` yields a
   **null env** → the ctor returns early → `androidWindow_` is never set.
4. `ViewRootImpl.setView` (Java) then can't add the window (the session was refused) → `InvalidDisplayException`
   → uncaught → `OpenjdkJvm System.exit(1)` → the app process exits → desktop/blank. Both HW and ZZ, identical.

846 (OK) reaches `EnableRootBlast: mUseBLASTAdapter` (the success tail) → true → window created → lit.

## Root: JavaVM not usable by the rebuilt bridge's SessionStageAdapter ctor
`ScopedJniAttachment(jvm_).env()` returns null in the rebuild ⇒ `jvm_` is null/unusable (or the thread can't attach
to it) **in the rebuilt bridge**. This is the same family as the #97 ath0-rpn/Typeface finding (route-A not making
the JavaVM available to an adapter; `SessionStageAdapter::getJNIEnv` was itself one of the 846-"absent" exports).

**Key: this is invisible to `abi_diff`.** abi_diff compares native EXPORT signatures; it (correctly) passed B1 at
exit 0. But the failure is a *runtime* JNI-attachment/VM-availability behavior that differs between the **rebuilt**
bridge and the **original 846 binary** even though they share this source. That is exactly why both 7cf8ebcc and
B1 — two independent rebuilds — fail here, while the deployed 846 binary succeeds. The abi_diff gate was necessary
but not sufficient; the behavior gate (the board window's `expect.refute`) caught it in one window.

## Next (offline hypotheses to test — do NOT need a board window to start)
Why does `ScopedJniAttachment(jvm_)` get a null env in the rebuild but not in 846?
1. **VM-global not shared across the #80 double-loaded bridge.** oc-t4 showed the route-A bridge loads twice (one
   copy in the runtime-CL namespace, one in the default namespace) — separate process-global singletons. If the
   JavaVM is stored in a bridge global set in copy A (via the JNI_OnLoad / setJavaVM path) but `createSession` →
   `SessionStageAdapter` runs against copy B's unset VM global, `jvm_` is null. Check: in the B1 child maps, is
   liboh_adapter_bridge.so loaded twice, and is the SessionStageAdapter ctor's jvm_ sourced from a per-copy global?
   (This ties the t3 blank to the N11 double-load fix.)
2. **Thread not attached + jvm_ null vs valid.** Confirm whether `jvm_` is null (VM never propagated to this call)
   or non-null-but-unattached (ScopedJniAttachment's AttachCurrentThread failing). Instrument/trace the VM pointer
   value through `createSession(JavaVM* jvm, …)` → the SessionStageAdapter ctor.
3. Compare how the deployed 846 binary sources the VM for this path (disassemble 846's SessionStageAdapter ctor /
   the createSession VM argument) vs the rebuild.

## Status
- First divergence + source pinpoint: **done** (SessionStageAdapter ctor null-JNIEnv → androidWindow_ null →
  EnableRootBlast false → createSession null-BBQ refusal → InvalidDisplayException).
- Verdict: the t3 blank is a rebuilt-bridge JavaVM/JNI-attachment regression, NOT the 5 ABI signatures (B1 with
  abi_diff exit 0 still fails identically). Leading hypothesis: the #80 double-load leaves the VM-global unset in
  the copy the SessionStageAdapter ctor uses → ties the fix to N11.
- Offline; board restored to U8 (B1 window rolled back + unlocked 16:21:20).
