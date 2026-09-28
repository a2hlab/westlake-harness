# Native-compat audit-only state owner handoff

## Boundary

- Boundary: appspawn-x child boundary and Bionic/Musl native compatibility control plane.
- Android behavior: bind one process generation and epochs, publish all current-thread metadata before READY, reject stale or foreign load identity, and never admit guest code before a real compatibility data plane exists.
- OpenHarmony mapping: the child receives an appspawn-owned fork seed plus an upstream-preverified metadata handoff; this adapter DSO owns the process state and audit callbacks without touching TLS or SELinux internals.
- Fix layer: project-local native adapter module `adapter/framework/native-compat`.

## Evidence target

- What this proves: the C state machine has one local owner; fork reset clears inherited state; terminal state and reason are one atomic publication; READY is release/acquire ordered; ABI v1 cannot issue a Unity load permit; host tests, mutation tests, sanitizers, deterministic AArch64 build and ELF forbidden-primitive checks pass.
- What this does not prove: a real Bionic stack guard, certificate authenticity, namespace pthread/callback brokerage, appspawn-x call-site order, target-device behavior, SELinux specialization, Unity load or a first frame.

## Environment

- Host: Darwin 25.4.0 arm64, Apple clang 21.0.0 for executable host diagnostics.
- Device: none; 5EAB5 was not written or started by this task.
- Tool path: project-local frozen OH clang/readelf/objdump/sysroot under `.work/product-tls-generation/frozen/`, executed in the image identity pinned by `.work/product-tls-generation/tool_runtime.lock` with network disabled.
- Artifact path: `adapter/framework/native-compat/out/target/libwestlake_native_compat.so`, SHA256 `7626fa4c8562f3ec596fddd940cdf0f0e1ed20f6e0e2669f1437e6bf25f9d0b2`.
- App: original CardWords Unity APK; it was not consumed or launched in this control-plane test.

## Status

- Label: real_impl for the audit-only state owner; the AArch64 artifact itself is build_pass and is not deployable guest-load authority.
- Why: all specified state transitions and denial semantics are implemented and exercised, while real guard publication and device integration intentionally remain absent.

## Proven

- A valid child reset requires non-zero adapter generation, process epoch and policy epoch; init before reset fails with stable reason `fork_reset_required`.
- Parent READY, callback pointers, digests, identity, thread owner and inherited init-gate state are cleared at the child reset boundary.
- Process state and terminal reason are packed into one lock-free 64-bit atomic. A 200-iteration concurrent revoke-versus-reject test observes only `(REVOKED, profile_revoked)` or `(REJECTED, thread_owner_mismatch)`.
- The external guard-source callback cannot revive or overwrite a terminal state: init advances only through CAS transitions, and a revoke performed inside that callback remains terminal.
- Thread generation, epochs, ID and role are staged before the release publication of `WLNC_THREAD_READY`; the load-side path acquires READY before consuming them.
- `WlncPreverifiedCapabilityV1` is explicitly non-authenticating. Its marker is only a structure discriminator and cannot be represented as a signature or certificate result.
- Even that non-authenticating handoff is fail-closed: guest scan, final initial closure, prepare order, exact-loader provenance and same-generation manifest must each be explicitly proven, while direct/CFG unknowns, overlaps, missing entries and pre-prepare slot-5 accesses must each be zero.
- `WLNC_AuthorizeLoad()` validates identity but returns `audit_only_no_load_authority` and a zeroed permit in ABI v1.
- Ten host test groups pass. Three negative mutants are killed: READY-before-metadata, inherited-parent-READY, and load-before-READY. AddressSanitizer, UndefinedBehaviorSanitizer and ThreadSanitizer also pass.
- Two AArch64 OHOS builds are byte-identical. The target verifier proves exact `WLNC_1.0` C exports, one local state owner, no `PT_TLS`, TLS section/relocation, constructor/init array, runtime dependency, RPATH/RUNPATH/TEXTREL, system-register instruction, stack-guard consumer, dynamic-loader primitive or test-hook export.
- ABI v1 is pinned to 64-bit enum/structure sizes and security-relevant field offsets by assertions compiled by both the host and AArch64 target toolchains.
- The target ELF SHA256 is `7626fa4c8562f3ec596fddd940cdf0f0e1ed20f6e0e2669f1437e6bf25f9d0b2`.

## Not proven

- The preverified handoff has no issuer trust, signature, anti-replay registry, revocation freshness or sealed-byte provenance.
- The CSPRNG callback only probes that a non-zero same-epoch sample is available; the sample is erased and never published to a Bionic TLS slot.
- No native-compat mechanism owns slot 5, TPIDR_EL0, pthread creation, signal state or guest callbacks.
- No final appspawn-x initial-closure scan proves this DSO is called before every possible Bionic slot-5 read.
- No target-device, production-init, SELinux Enforcing, setcon, ActivityThread, Unity, Surface/EGL or RenderService evidence exists for this artifact.

## Failed

- The Darwin linker cannot consume the GNU ELF version script, and the Darwin host has no native `readelf`; therefore host dylib shape was rejected as target evidence.
- Target evidence instead uses the already frozen project-local OHOS toolchain in a locked, network-disabled Linux container. This is still static `build_pass`, not device verification.
- The copied generic design-check tree mode expects an ART source layout and reports missing ART paths for this isolated adapter module; its target-ELF mode finds no `FIX-VTABLE-A`, and the five questions below provide the applicable review.

## Next evidence

- Command: `adapter/framework/native-compat/tests/run_all.sh`, followed by the final-generation initial-closure scanner and an integration test that calls `WLNC_AfterForkChildReset` immediately after fork and `WLNC_PrepareCurrentThread` only after stock `setcon()`.
- Expected output: this module retains `tests=10`, `mutants_killed=3`, sanitizer passes and deterministic AArch64 structural PASS; the closure evidence independently proves zero pre-prepare slot-5 access.
- If it fails: do not deploy or weaken a reason gate; preserve the failing generation/epoch/ELF receipt and correct the owner/order mismatch at the adapter boundary.

## Shim/stub/bypass inventory

- Item: `WlncPreverifiedCapabilityV1` audit handoff; it is scaffolding and explicitly not a signature or load capability.
- Owner: future appspawn/package-verification certificate consumer at the native adapter boundary.
- Why it exists: permit state/order testing without inventing issuer trust or silently bypassing the missing verifier.
- Removal condition: a project-local, reviewed certificate/sealed-FD verifier binds the exact profile, target ELF, generation and policy epoch before this API is called; ABI naming must continue to distinguish verified bytes from authenticity.
- Test coverage: marker/origin, hard-count, target SHA, Build-ID, generation, process epoch, policy epoch, replay and platform-owner negative cases.
- App-specific or common: common adapter capability; no CardWords package allowlist or APK mutation exists.

## Memory/skill/CI/review updates

- Memory: `README.md` records the permanent rule that audit READY is not guard READY and cannot authorize guest load.
- Skill: WestLake discipline and design-check were applied; copied tool provenance is in `var/evidence/PROVENANCE.json`.
- CI: add `adapter/framework/native-compat/tests/run_all.sh` to the generation gate before this module is linked into appspawn-x.
- Review checklist: reject any future change that adds a constructor, TLS storage, TP register access, slot writer, fake certificate marker, non-zero permit under `AUDIT_ONLY`, or target/device claims based only on host evidence.

## HanBing five-question design check

- Q1 ART/class_linker/vtable semantics changed: no; this module has no ART source or dependency.
- Q2 BCP Java/ActivityThread semantics changed: no; the ABI and implementation are C-only.
- Q3 fix is in the adapter layer: yes; ownership is `framework/native-compat` at the appspawn/Bionic-Musl boundary.
- Q4 coherent boot re-bake required: not applicable because neither libart nor BCP changed.
- Q5 truly-cold device proof: not proven; this report does not grant runtime acceptance.
- Java zero-stub gate: not applicable; no Java code or default-success behavior was added.
