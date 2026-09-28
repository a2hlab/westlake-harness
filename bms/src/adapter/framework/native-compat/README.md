# WestLake native-compat audit core

This directory owns the child-process compatibility **control-plane state**.
It does not implement the Bionic TLS data plane.

## Boundary

- Android behavior preserved: a guest thread may be admitted only after its
  process generation, process epoch, policy epoch, target ELF identity and
  per-thread ownership have been bound in a deterministic order.
- OpenHarmony mapping: appspawn-x supplies a child-only fork seed and an
  upstream-preverified profile handoff.  This DSO records one process owner,
  publishes thread metadata with release/acquire ordering, and emits audit
  events through caller-owned callbacks.
- Owner: `framework/native-compat`, native OS-boundary control plane.

`WlncPreverifiedCapabilityV1` is deliberately named and documented as a
preverified handoff.  Its marker is only a structure discriminator.  It is not
a signature, certificate, sealed-FD proof, issuer assertion, or anti-replay
authority.

## State contract

1. `WLNC_AfterForkChildReset()` must run at the earliest child boundary.  It
   clears inherited parent READY, callback, digest and init-gate state and
   binds non-zero generation/process/policy epochs.  It invokes no callback.
2. `WLNC_ProcessInitPreverified()` admits exactly one platform owner, validates
   all hard-count and target-identity fields, requires explicit guest-scan,
   initial-closure, prepare-order, exact-loader-provenance and same-generation
   manifest proofs, checks that a non-zero same-epoch OS-CSPRNG sample is
   available, then arms the audit control plane.
3. `WLNC_PrepareCurrentThread()` stages all thread metadata first and publishes
   `WLNC_THREAD_READY` with release semantics.  Consumers acquire READY before
   reading metadata.
4. `WLNC_AuthorizeLoad()` validates that acquire/identity contract but always
   returns `WLNC_REASON_AUDIT_ONLY_NO_LOAD_AUTHORITY`.  ABI v1 has no slot
   publisher and therefore cannot issue a real guest-load permit.
5. Any generation/epoch/profile/owner mismatch is fail-closed with a stable
   numeric reason and `WLNC_ReasonString()` diagnostic name.

## Explicit non-capabilities

The target DSO contains no constructor, `PT_TLS`, `_Thread_local`, `__thread`,
inline assembly, TPIDR_EL0 access, stack-guard consumer, slot-5 writer, dynamic
loader call, or runtime DSO dependency.  There is no fake success path.

The OS-CSPRNG callback is a prerequisite probe only.  The sampled word is
cleared and never stored or published.  A future reviewed data-plane backend
must own real guard generation/publication and upgrade the mechanism before
any Unity load can be authorized.

ABI v1 is explicitly a 64-bit process ABI.  The host and AArch64 target builds
both compile exact enum/structure-size and security-relevant offset assertions
from `tests/abi_layout_asserts.c`; layout drift fails the build.

## Reproduce

From the project root:

```sh
adapter/framework/native-compat/tests/run_all.sh
```

The host suite exercises ten state/identity/concurrency groups (including a
200-iteration revoke-versus-reject terminal-reason race) and must kill
three dangerous mutants: READY-before-metadata, inherited parent READY, and
load-before-READY.  The same suite also passes AddressSanitizer,
UndefinedBehaviorSanitizer and ThreadSanitizer.  The target phase builds an
AArch64 OHOS DSO twice from the
project-local frozen toolchain/sysroot and requires byte identity plus the
structural forbidden-primitive gate.

Outputs stay under `adapter/framework/native-compat/out/`.  They are
`build_pass` evidence only, never `device_verified` evidence.
