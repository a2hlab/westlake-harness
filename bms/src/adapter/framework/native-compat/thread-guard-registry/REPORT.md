# Bionic process-guard thread registry handoff

## Boundary

- Boundary: Bionic/Musl thread ABI at the appspawn-x child, APK native loader,
  namespace pthread, and adapter JNI-attach boundaries.
- Android behavior: one non-zero OS-CSPRNG guard is created for a child
  process epoch; the main thread and every later pthread receive that identical
  value in Bionic TLS slot 5. Bionic's global guard must equal the TLS value.
- OpenHarmony mapping: Musl remains the real pthread/TCB owner. The appspawn-x
  MAIN ELF owns reservation addresses. This adapter registry owns the Bionic
  process-guard lifecycle and the validated slot write/readback publisher.
- Fix layer: project-local native adapter module
  `adapter/framework/native-compat/thread-guard-registry`.

## Evidence target

- What this proves: a standalone registry can verify one process binding, obtain
  exactly one real OS-CSPRNG guard, copy it to 24 concurrent real pthread
  reservations, publish complete lifecycle receipts, and fail closed without
  owning pthread, TP, a constructor, or the Musl global guard.
- What this does not prove: product call-site integration, namespace pthread translation,
  Bionic global-symbol ownership, target execution, Unity load, or first frame.

## Corrected Android semantic

An earlier version of this module incorrectly generated a distinct guard on
every thread. Frozen AOSP source disproved that model:

- `android_reset_stack_guards()` fills the global `__stack_chk_guard` once and
  immediately copies it into the main TCB.
- `__init_tcb_stack_guard()` copies that global into each new pthread TCB.
- AArch64 defines the stack guard as TLS slot 5.
- AOSP's `same_guard_per_thread` test requires global/TLS equality and exactly
  one value across all tested threads.

The implementation and tests now enforce the AOSP model. The machine-readable
proof is `out/aosp-guard-semantics.json`.

## Environment

- Host: Clang host build, 24 real pthreads, ASan, UBSan, TSan.
- Target build: AArch64 OHOS, project-local frozen clang/sysroot, locked
  network-disabled read-only container recorded in `var/evidence/PROVENANCE.json`.
- Tool path: `.work/product-tls-generation/frozen/toolchain/bin` and
  `.work/product-tls-generation/frozen/sysroot`, both project-local.
- Artifact path: `adapter/framework/native-compat/thread-guard-registry/out/target/libwestlake_thread_guard_registry.so`.
- Device: none. 5EAB5 was not written, rebooted, or launched.
- App: the CardWords APK was neither modified nor executed.
- Reproduce:
  `adapter/framework/native-compat/thread-guard-registry/tests/run_all.sh`.

## Status

- Label: `real_impl` for the standalone mechanism; target is `build_pass`.
- Why: lifecycle and publication are implemented and tested, while product
  issuer/call graphs and device evidence remain absent.
- AArch64 artifact: `build_pass`; SHA256 is recorded in
  `out/target/verification.json` and `out/target/sha256.txt`.
- Product integration: `product_activation=false`.
- Target/device runtime: `device_verified=false`.
- Unity/CardWords: NOT_PROVEN.

## Proven

- `WLTG_ProcessArm()` accepts one verified process/generation/policy binding,
  calls the exact-quality OS-CSPRNG callback once, rejects failure/zero/wrong
  epoch/wrong quality, and release-publishes one canonical process guard.
- Ticket issuance uses a non-entropy lifecycle nonce. It cannot silently become
  a random fallback or create extra guard values.
- `WLTG_PrepareCurrentThread()` validates the current MAIN-ELF reservation,
  copies the canonical guard through the hidden write/readback backend, verifies
  it still equals the process guard, completes the receipt, then publishes READY.
- MAIN and JNI_ATTACH tickets are same-thread. Namespace-pthread tickets must be
  consumed by a different real thread. Tickets are one-shot; cancellation,
  retirement, capacity, replay, tamper, audit rejection, and revoke are covered.
- Twenty-four concurrent real host pthreads plus the main thread all received
  the same non-zero process guard; the CSPRNG callback count remained exactly
  one. Every worker retired without zeroing its slot.
- Fourteen host groups pass for the good build and for 20 stress iterations.
  ASan, UBSan, and TSan pass. Six dangerous host mutants are killed: fixed
  fallback, READY-before-receipt, skipped owner bounds, cross-thread replay,
  creator-as-new-thread, and per-thread re-randomization.
- Two AArch64 builds are byte-identical. The DSO has exact versioned C exports,
  one local process registry, no PT_TLS/TLS relocation/constructor/DT_NEEDED,
  no TP/system-register access, no Musl-global guard reference, and no
  pthread/signal/loader interposition.
- The hidden data-plane publisher is exactly one caller-addressed store followed
  by readback. The separate MAIN-owner fixture proves TLS-symbol relocation;
  PT_TLS, constructor, and literal-`TP+0x28` mutants are rejected.
- Frozen AOSP warns that a guard reset cannot return through an existing
  stack-protected frame. The required product owner must preserve that timing.

## Product guard-owner audit

- Current `misc_compat.cpp::android_reset_stack_guards()` writes
  `__stack_chk_guard` through `/dev/urandom` and installs a fixed constant on
  failure. That is a fail-open Musl-global mutation and blocks activation.
- Current `bionic_tls_abi.c` independently creates another guard, writes the
  Musl global, has the same fixed fallback, performs direct TP writes, and runs
  from a constructor. The generation verifier correctly forbids this path.
- Current `native_compat_prepare.cpp` creates a third independent guard for
  slot 5. Even though it fails closed, it does not prove equality with the
  Bionic global object and forcibly clears its low byte. Frozen Bionic fills
  the full guard width from `arc4random_buf` (or kernel `AT_RANDOM` during early
  init) without that mask, so it is not yet an AOSP-equivalent product owner.
- Frozen AOSP places `android_reset_stack_guards()` in the native zygote fork
  child branch before application initialization. `ZygoteHooks.postForkChild`
  itself does not call it. WestLake's external appspawn Route A bypasses that
  native fork branch, so the observed hook order does not imply a second guard
  reset. The unresolved issue is competing owners, not that Java hook.
- Correct product contract: one post-fork, pre-guest, no-protected-return issuer
  generates the process guard; the registry copies that exact value to MAIN and
  later admitted threads; a Bionic-namespace global provider exposes the same
  value if imported. Musl's global guard remains untouched.

## Not proven

- No integrated process issuer supplies sealed generation bytes and the one
  canonical guard. Host callbacks are fixtures, not product authority.
- No Bionic-namespace `__stack_chk_guard` provider is binary-proven to expose
  the same canonical value. The Musl global is explicitly not an acceptable
  substitute.
- No same-generation appspawn-x binary proves:
  `setcon success -> reset/arm -> MAIN prepare/READY -> ART post-fork`.
- No APK-namespace-only typed Bionic pthread bridge calls real Musl
  `pthread_create` and prepares the new thread before its guest start routine.
- No central adapter wrapper owns all JNI attach paths or their existing-thread
  receipt verification.
- No READY gate precedes guest `dlopen_ns()` constructors.
- No final callback after guest pthread-key/C++ TLS destructors is proven.
- No AArch64 target execution, SELinux Enforcing cold launch, Unity native
  initialization, Surface/EGL, RenderService present, or first-frame evidence.

## Failed

- The superseded “one fresh guard per thread” model failed the frozen-AOSP
  semantic gate and was removed before product activation. No product binary
  ever used it.
- The first target mutation run recognized only objdump's hexadecimal immediate
  spelling. The verifier now rejects both hexadecimal and decimal `TP+0x28`;
  the retained record is `var/evidence/INITIAL_TARGET_GATE_FAILURE.md`.
- Product activation remains intentionally rejected while call graphs and guard
  ownership are incomplete. This is an acceptance result, not a workaround.

## Next evidence

- Command: run this module's `tests/run_all.sh`, the final provider/TP closure,
  unified Bionic/Musl gate, then one immutable Enforcing cold generation on
  5EAB5 after all owners below exist.
- Expected output: same-generation binaries prove one canonical process guard,
  MAIN/worker/attach preparation before guest execution, and no unresolved
  pre-prepare access; cold runs reach the next Unity wall.
- If it fails: retain generation, first failed ticket/receipt, owner identity,
  hilog, and tombstone; reject fixed fallback, global broker, permissive mode,
  and partial activation.

1. Replace competing guard owners with one adapter-owned issuer. Entropy failure,
   zero, wrong epoch, or inability to publish global/TLS equality must terminate
   before guest code; fixed fallback is forbidden.
2. Prove in the same-generation appspawn-x binary that guard generation occurs
   once after fork and after stock specialization, and that MAIN slot publication
   precedes any guarded guest frame or thread restart. Do not change a guard from
   a stack-protected frame that returns.
3. Add a namespace-scoped typed Bionic pthread bridge: translate attributes,
   issue before real Musl `pthread_create`, cancel on create failure, prepare in
   the new-thread trampoline, and retire only after guest destructors.
4. Centralize JNI attach admission and put `WLTG_VerifyCurrentThreadReady()`
   immediately before guest `dlopen_ns()`/constructors.
5. Re-run the standalone gate, final provider/TP closure, unified Bionic/Musl
   gate, then deploy one immutable generation for Enforcing truly-cold tests on
   5EAB5.

Expected next result: same-generation binaries prove one process guard copied
to every admitted thread, with no unresolved pre-prepare guest access. If not,
retain the exact generation, first failed ticket/receipt, owner, hilog, and
tombstone; do not enable a global broker, fixed fallback, permissive mode, or
partial activation.

## Shim/stub/bypass inventory

- Item: test-only platform callbacks, synthetic owned regions, and mutation
  variants under this module's `tests/`; none is in a product generation.
- Owner: `framework/native-compat/thread-guard-registry/tests`.
- Removal condition: keep as regression fixtures; product activation must use
  separately reviewed issuer, MAIN owner, namespace bridge, and attach owner.
- Test coverage: 14 groups, 24 concurrent pthreads, 20 stress iterations,
  ASan/UBSan/TSan, 6 host mutants, frozen-AOSP semantic gate, deterministic
  AArch64 build, and 3 target mutants.
- Product shim/stub/bypass added: none.
- No package allowlist, APK mutation, fake success, LD_PRELOAD, direct procattr,
  global pthread/signal broker, fixed guard, or Musl/ART/BCP edit was added.

## Memory/skill/CI/review updates

- Memory: `README.md`, `ARCHITECTURE.md`, and `THREAD_BOUNDARY_AUDIT.md` preserve the
  split between Musl thread ownership, MAIN-ELF address ownership, process
  issuer, registry control plane/publisher, namespace bridge, and loader gate.
- Skill: `_deep_debug_westlake`, `westlake-engineering-discipline`, and `design-check`
  were applied. All consulted AOSP code is copied locally with provenance.
- CI: `tests/run_all.sh` now includes an executable frozen-AOSP semantic gate.
- Review checklist: reject registry TLS, constructor activation, hard-coded TP access,
  per-thread re-randomization, Musl-global guard writes, fixed fallback, global
  pthread/signal interception, package allowlists, or READY before receipt.

## HanBing five-question design check

- Q1 ART/class_linker/vtable changed: no; no `FIX-VTABLE-A`.
- Q2 BCP Java/ActivityThread semantics changed: no.
- Q3 fix belongs to the adapter layer: yes, at the Bionic/Musl boundary.
- Q4 boot re-bake: not applicable; neither libart nor BCP changed.
- Q5 truly-cold target proof: not proven, so runtime acceptance is not claimed.
- Java zero-stub gate: not applicable; no Java/default-success path was added.
