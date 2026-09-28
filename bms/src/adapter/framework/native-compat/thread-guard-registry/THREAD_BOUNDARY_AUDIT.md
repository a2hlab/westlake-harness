# Current thread-boundary and guard-owner audit

Machine-readable evidence: `out/boundary-audit.json`.

## Main child

The current source places main-thread native compatibility preparation after
successful `applySELinux()` and before `zygotePostForkChild()` and
`zygotePostForkCommon()`. This is the correct source-order class of boundary:
SELinux specialization still runs single-threaded, while ART daemon restart and
guest execution have not begun.

That order is not yet a complete guard contract. The current prepare source
generates a private slot-5 value, while legacy `misc_compat.cpp` and
`bionic_tls_abi.c` own other global values. Same-generation binary equality is
NOT_PROVEN. It also clears the low byte, unlike the frozen Bionic full-width
`arc4random_buf`/kernel-`AT_RANDOM` fill.

Frozen AOSP clarifies the reset question: `android_reset_stack_guards()` is
called by the native zygote fork child branch. ART's
`ZygoteHooks.nativePostForkChild` does not call it. WestLake's external
appspawn route bypasses the native AOSP fork branch, so calling the ART hook
after MAIN publication does not by itself re-randomize the guard. The real
blocker is eliminating competing owners and publishing one canonical value.

A guard must never be changed from a stack-protected frame that will return;
frozen Bionic states this explicitly. Final binary proof must therefore include
the reset caller's stack-protector shape as well as source order.

## Guest pthread creation

The CardWords provider ledger rejects direct Musl `pthread_create` providers
for both `libunity.so` and `libil2cpp.so` with
`PTHREAD_OR_SEMAPHORE_OBJECT_CANNOT_CROSS_BIONIC_MUSL`.

The old `unity_pthread_box.c` globally defines pthread symbols. The old
`bionic_tls_abi.c` uses a constructor, direct TP write, Musl-global guard, and
fixed fallback. The generation verifier excludes these designs.

The missing owner is an APK-namespace-only typed bridge. It must preserve real
Musl thread creation, issue/cancel registry tickets on the creator, and copy the
same canonical process guard in the new-thread trampoline before any guest
start routine or guarded frame.

## JNI attach

Thirteen `AttachCurrentThread`/`AttachCurrentThreadAsDaemon` sites remain across
appspawn, android-runtime, activity, and window adapters. None has a centralized
registry owner. The architecture requires one adapter helper that verifies an
existing READY receipt or prepares a same-thread JNI_ATTACH ticket before
delegating unchanged to the JavaVM.

## Guest loader

`ANL_Dlopen()` correctly loads through the application namespace, but it has no
`WLTG_VerifyCurrentThreadReady()` gate. The gate must run immediately before
guest `dlopen_ns()` and its constructors, while host/OH loads remain outside it.
