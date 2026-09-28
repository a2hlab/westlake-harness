# WestLake Bionic process-guard thread registry

This standalone adapter module controls the lifecycle and publishes the
AArch64 Bionic stack-guard slot used by Android guest code on real
OpenHarmony Musl threads. It is intentionally absent from the product build
graph until every guest thread boundary is proven.

## Boundary

- Frozen AOSP contract: one non-zero OS-CSPRNG guard is generated for each
  child process epoch, installed in the main thread, and copied unchanged into
  every later Bionic pthread. AOSP's own test requires exactly one guard value
  across all threads and equality with Bionic's global `__stack_chk_guard`.
- OpenHarmony mapping: Musl remains the only pthread/TCB owner. The appspawn-x
  MAIN ELF owns the reviewed TLS reservation; a caller-owned TLS relocation
  resolves that reservation for the current thread.
- Adapter owner: `framework/native-compat/thread-guard-registry`.
- Explicit exclusions: no APK, Unity, ART, BCP, Musl, SELinux, global pthread,
  signal, loader, constructor, direct-TP, fixed/zero fallback, or Musl-global
  guard modification.

## Lifecycle contract

1. `WLTG_AfterForkChildReset()` clears inherited parent state at the earliest
   single-threaded child boundary.
2. `WLTG_ProcessArm()` verifies one generation/process/policy binding and
   obtains exactly one canonical process guard from the OS-CSPRNG callback.
3. The adapter issues one typed lifecycle ticket at a known boundary: MAIN
   post-specialization, namespace pthread creation, or adapter JNI attach.
4. `WLTG_PrepareCurrentThread()` consumes the ticket, validates the current
   MAIN-ELF reservation, copies the canonical process guard into slot 5 through
   the module's hidden write/readback backend, stages a receipt, and only then
   release-publishes READY.
5. `WLTG_VerifyCurrentThreadReady()` is the future guest-loader/attach gate.
6. `WLTG_RetireCurrentThread()` clears the registry receipt only after guest
   frames and destructors have left. It never zeros the dying thread's slot.

The registry is both the control plane (binding, tickets, states, receipts,
revoke) and the narrow data-plane publisher (`WLTG_StoreGuardAndReadback`). The
MAIN ELF remains the address owner; the registry never reads the thread pointer.

The registry never calls `pthread_create`. A future APK-namespace-only typed
bridge must call real Musl `pthread_create`, consume the ticket in its new-thread
trampoline before the guest start routine, and prove its final destructor/exit
boundary. The legacy global `unity_pthread_box.c` path remains forbidden.

## Reproduce

From the project root:

```sh
adapter/framework/native-compat/thread-guard-registry/tests/run_all.sh
```

This runs the frozen-AOSP semantic gate, 14 host groups, 24 concurrent real
pthread publications, 20 stress iterations, ASan, UBSan, TSan, six host
mutants, the product-boundary audit, two deterministic AArch64 builds, and
three target structural mutants. Outputs stay below this module's `out/`.

A pass means `real_impl` for the standalone mechanism and `build_pass` for its
target shape. It does not mean product activation, device verification, Unity
load, or first frame.
