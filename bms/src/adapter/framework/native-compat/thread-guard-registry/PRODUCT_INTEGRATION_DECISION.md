# Route-A product integration decision

Status: architecture decision before product edits; 2026-07-12.

## Gate 0 — invariants

1. Frozen AOSP Bionic owns one full-width process guard per post-fork process
   epoch. MAIN and every later admitted thread receive the identical value in
   TLS slot 5. Fixed/zero fallback and low-byte masking are not this contract.
2. Musl remains the real pthread/TCB owner. Its process-global
   `__stack_chk_guard` is a separate ABI and must never be changed by this
   integration, especially from a live Musl stack-protected frame.
3. Stock OH appspawn remains the only DAC/sandbox/SELinux security owner.
   Bionic guard preparation starts only after the validated stage-31 stock
   receipt and before ZygoteHooks, ART daemon restart, JNI attach, loader
   constructors, or guest guarded work.
4. appspawn-x MAIN ELF owns the `[TP+0x10, TP+0x40)` reservation. Only its
   TLS-symbol relocation accessor resolves an address; neither the registry nor
   a DSO may hard-code or read `TP+0x28`.
5. One shared registry instance must serve MAIN, the future APK namespace
   pthread bridge, central JNI attach owner, and guest loader gate. Duplicate
   static registries are forbidden.
6. A thread without a READY receipt cannot cross a guest loader/JNI/guest-start
   boundary. Missing integrations remain explicit fail-closed gaps, never
   implicit success.
7. Every linked provider and security path must be present exactly once in one
   immutable Route-A input closure and final binary proof.

## Gate 1 — deductions

- The standalone registry must become one startup `DT_NEEDED` DSO of the stock
  host. Compiling copies into multiple consumers would create multiple guards
  and state machines.
- `native_compat_prepare` is the product issuer/reservation callback owner. It
  may supply a full-width OS-CSPRNG sample to `WLTG_ProcessArm`, but it must not
  retain, mask, publish, or independently generate another guard.
- The prepare C ABI must receive the already-validated stock receipt identity
  from the runtime provider. A no-argument function cannot prove which stock
  child/generation it is arming.
- Therefore MAIN preparation belongs inside
  `WLAR_EnterAndroidAfterStockSpecialization`, after request/receipt/uid/gid
  validation and before `ChildMain::runAfterStockSpecialization`.
- The compat DSO in the final closure must be rebuilt without the fixed
  `android_reset_stack_guards` implementation and without any Musl-global guard
  relocation. The unsupported legacy reset entry may terminate, but may not
  return success or mutate a guard.
- Namespace pthread ownership cannot be obtained by adding another
  `pthread_create` to the global compat DSO: the provider ledger already proves
  that would be a second shadow/transitive candidate and would cross incompatible
  pthread object ABIs.

## Gate 2 — cheapest falsifiers

Before device work, the final Route-A ELFs must answer all of these mechanically:

- exactly one `libwestlake_thread_guard_registry.so` and one local registry
  owner;
- stock host has a direct `DT_NEEDED` edge to it;
- no final DSO defines legacy `bionic_tls_abi_init_main_thread`, directly reads
  `tpidr_el0` except the MAIN reservation accessor, or refers to Musl
  `__stack_chk_guard`;
- no fixed canary or low-byte mask exists in compiled source/objdump;
- provider disassembly calls MAIN prepare before the non-returning Android child
  entry; stock receipt validation dominates the call;
- registry DSO remains constructor/PT_TLS/pthread/signal/loader free;
- compat DSO contains no global `pthread_create` provider;
- absent pthread/attach/loader owners are recorded as product-blocking
  fail-closed gaps, not marked READY.

Any failed check kills activation without a device trial.

## Gate 3 — tripwires

- If the Route-A final link cannot use one shared registry DSO without unresolved
  or duplicate providers, stop and return to Gate 0; do not static-link copies.
- If MAIN identity cannot be proven from the stock receipt at the provider call
  site, do not arm from `ChildMain` by inference.
- If a namespace-scoped pthread bridge would require global interposition or
  leak Bionic pthread objects to Musl, leave it blocked and do not load Unity.
- If a central attach/loader binary is outside the same frozen generation, do
  not claim its source edit as product integration.
- No deployment or 5EAB5 run occurs until all offline binary gates pass.

## Rejected alternatives

- Independent `getrandom()` in `native_compat_prepare`: creates a second owner.
- Clearing the low byte: differs from this frozen AOSP Bionic version.
- Writing Musl `__stack_chk_guard`: crosses ABI ownership and can invalidate
  active Musl protected frames.
- Constructor/direct-TP seeding: wrong lifecycle and wrong address owner.
- Global pthread/signal interception or `LD_PRELOAD`: violates namespace and
  object-layout ownership.
- Continuing to guest code while worker/attach/loader boundaries are unknown:
  partial activation, not an architecture-preserving stub.

## HanBing design gate

- ART/class linker/vtable changed: no.
- BCP Java semantics changed: no.
- Fix layer: native adapter Bionic/Musl boundary.
- Boot re-bake: not applicable.
- Truly-cold/device proof: not yet; no runtime claim is permitted.
