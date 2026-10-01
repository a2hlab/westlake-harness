# deployed 846 (84695d62) vs B1 (a1f57197): doCreateSession → SessionStageAdapter ctor → GetEnv, disassembled

Outer-ring control refuted the "foreign-copy VM" story: the deployed 846 **also** double-loads and **also**
contains the `Failed to get JNIEnv` string, yet hits it **0× in 209 U8 lines**. So the double-load is not the
discriminator. This compares the exact path in both binaries (DevEco `llvm-objdump`/`llvm-nm`, aarch64).
**Finding: the VM source, member offsets, GetEnv version and vtable slot are identical; the divergence is the
`SessionStageAdapter` *constructor body* — 846 does a plain inline `GetEnv` attach, B1 routes through the
WLTG-ticket-gated `westlake::jni::ScopedJniAttachment`, which yields no env on the createSession thread.**
This is a body/behavior change, invisible to signature-diff **and** to a layout-diff.

## 1. jvm source + member offset — IDENTICAL
Both load the VM from `AdapterBridge::getInstance()` member **offset 0**:
```
846  doCreateSession@0xf0938:        f0a44 bl getInstance ; f0a48 ldr x23,[x0]        ; x23 = instance.jvm_ (+0)
B1   nativeCreateSession_impl@0x10e1d8: 10e2c0 bl getInstance ; 10e2c4 ldr x22,[x0]   ; x22 = instance.jvm_ (+0)
```
`getInstance()` is a `T` export in both; its singleton (`...getInstance()::instance`) is a single `b` symbol in
each. No layout drift in the AdapterBridge read: the member offset is 0 on both sides.

## 2. GetEnv version + vtable slot — IDENTICAL
- 846 (inlined in the ctor): `e69e4 ldr x8,[x8,#48]` (vtable slot 0x30 = GetEnv) ; `e69e8 mov w2,#6` + `e69f0 movk w2,#1,lsl#16` → version **0x00010006** (JNI_VERSION_1_6) ; `e69f4 blr x8` ; `e69f8 cmn w0,#2` (JNI_EDETACHED).
- B1 (inside `ScopedJniAttachment` ctor @0x1c4774): `1c47f8 movk w2,#1,lsl#16` → version **0x00010006** ; `1c47fc blr x8` (GetEnv) ; `1c4804 cbnz w0` ; `1c4850 cmn w0,#2`.
Same version, same slot, same EDETACHED check.

## 3. The divergence — SessionStageAdapter constructor BODY
**846 ctor @0xe6900** — bl/blr targets across the whole body: `__android_log_print` ×4, `IRemoteStub<ISessionStage>::IRemoteStub`, and indirect `blr x8` (the VM-vtable GetEnv/attach + NewGlobalRef). **No `bl ScopedJniAttachment`, no `WLTG_*` call anywhere.** 846 attaches with a *plain inline* `GetEnv(jvm_, &env, 0x10006)` on the current thread (which, for the synchronous JNI createSession upcall, is already attached → returns JNI_OK → env valid).

**B1 ctor @0x1050d0** — `10519c ldr x1,[x19,#128]` (this->jvm_, same +128 as 846) → `1051a8 mov x0,sp` (stack ScopedJniAttachment) → `1051b0 bl westlake::jni::ScopedJniAttachment::ScopedJniAttachment(JavaVM*, const char*, AttachMode)` → `1051b4 ldr x22,[sp,#8]` (scoped.env_) → `1051b8 cbz x22,fail`. The attach now lives in `ScopedJniAttachment`, whose body (@0x1c4774) is **WLTG-ticket-gated**:
```
1c47fc blr x8                      ; GetEnv(vm,&env,0x10006)
1c4804 cbnz w0 -> 0xdc             ; if !JNI_OK
1c480c cbz  x8 -> 0xdc             ; or env null
1c4828 bl WLTG_VerifyCurrentThreadReady   ; success path still gated on a WLTG ticket
1c4850 cmn w0,#2                   ; EDETACHED?
1c4874 bl WLTG_VerifyCurrentThreadReady
1c48bc bl WLTG_IssueThreadTicket   ; attach path issues a WLTG thread ticket
```
Both binaries *define* the whole WLTG machinery (`ScopedJniAttachment`, `AttachJvm`, `WLTG_VerifyCurrentThreadReady`,
`WLTG_IssueThreadTicket`, receipts) — 846 at 0x18c6xx, B1 at 0x1c47xx. The difference is **who calls it**: in 846
the SessionStageAdapter ctor does **not** (plain GetEnv); in B1 it **does** (WLTG-gated). On the createSession
thread the WLTG gate does not yield a usable env (hilog: `SessionStageAdapter created` → `Failed to get JNIEnv in
constructor`, with **no** WLTG success line and `[B1-VMFALLBACK]`=0), so `androidWindow_` stays null →
`EnableRootBlast: missing JNIEnv` → null-BBQ ViewRoot → `InvalidDisplayException` → `System.exit(1)`.

## Answer to the outer-ring questions
- **jvm source / getInstance / member offset**: identical (`getInstance().jvm_`, offset 0) in 846 and B1.
- **AdapterBridge & cross-library layout**: no drift observed on this path (jvm_ @0, SessionStageAdapter jvm_ @128
  in both; WLTG types defined in both).
- **GetEnv version**: identical (0x00010006, vtable slot 0x30).
- **Root**: the b68/B1 `SessionStageAdapter` **ctor body** was rewired to attach via the WLTG-ticket-gated
  `westlake::jni::ScopedJniAttachment`; the deployed 846 ctor uses a plain `GetEnv`. The WLTG gate fails to produce
  an env on the synchronous JNI createSession thread. **Not** a null VM, **not** a foreign-copy VM, **not** the 5
  ABI signatures, **not** a member-layout drift.

## On `abi_diff --layout`
A `--layout` check would **not** catch this: the AdapterBridge/SessionStageAdapter layouts are identical and the
exported ctor signature (`SessionStageAdapter(_JavaVM*, _jobject*)`) is unchanged. The regression is purely in the
constructor's *call graph/body* (plain GetEnv vs WLTG-gated ScopedJniAttachment), which signature- and
layout-diffing cannot see. The only cheap guard is the on-board behavior gate (which did flag it in one window). A
static approximation would be a *symbol-reference diff* per exported function (e.g. "B1's `SessionStageAdapter` ctor
references `WLTG_*`/`ScopedJniAttachment` that the 846 ctor does not") — proposed as a separate check, not `--layout`.

## Proposed fix (offline, no window until abi_diff exit 0)
Make B1's `SessionStageAdapter` ctor attach like 846 on the JNI-call thread: use a plain
`jvm_->GetEnv(&env, JNI_VERSION_1_6)` (the createSession upcall thread is already attached) and only fall back to a
real attach when `JNI_EDETACHED`, **without** the WLTG ticket gate on this synchronous path — i.e. do not route the
SessionStageAdapter ctor through `westlake::jni::ScopedJniAttachment`. (WLTG gating is appropriate for OH *callback*
threads, e.g. WindowCallbackAdapter, not for the inline JNI createSession thread.) Alternatively make the WLTG gate
accept an already-attached JNI thread (issue/verify a ticket for it). Either must pass
`abi_diff --old 846 --new … exit 0` offline before any board window.

Evidence: this file; run hilog `b1-vmfallback-WINDOW-FAIL-hilog.txt`; disasm reproduced with
`llvm-objdump -d` on `vm-copies/bridge-84695d62/liboh_adapter_bridge.so` and
`_cc-wiki-t3-bridge/liboh_adapter_bridge.so.b1-846sig`.
