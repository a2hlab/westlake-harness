# Frozen appspawn-x generation handoff — 2026-07-12

## Boundary

- Boundary: `appspawn-x`, `Permission/Security`, and `Bionic/Musl`.
- Android behavior: preserve the pre-fork Android runtime process and its
  fixed positive TLS-slot address contract without changing ART, BCP, or APK.
- OpenHarmony mapping: stock
  `HapContext::HapDomainSetcontext(HapDomainInfo&)` remains the only SELinux
  specialization path; a POD pure-C wrapper contains the OH C++ ABI.
- Fix layer: adapter-owned appspawn main ELF, compatibility library, C ABI
  wrapper, and fail-closed producer/verifier.

## Evidence target

- What this proves: a byte-frozen, project-local linux/amd64 producer can
  deterministically build the compat library, stock wrapper, and appspawn-x;
  the resulting ELF identities, dependency order, wrapper pin, and 48-byte
  main-ELF TLS reservation pass the static gates below.
- What this does not prove: Bionic slot-5 stack-guard semantics, production
  init, SELinux-Enforcing child specialization, ActivityThread, Unity native
  load, Surface/RS present, or a visible frame. It also does not prove that the
  pre-existing fdsan/malloc/log compatibility stubs are unused before first
  frame.

## Environment

- Host: macOS workspace; all writes below
  `/opt/21.Game/02.unity.cardwords`.
- Device: none used; device writes were prohibited for this task.
- Tool path: frozen OH clang15 closure under
  `.work/product-tls-generation/frozen/toolchain`; read-only linux/amd64 image
  `sha256:76236bc11d9359a260c3e715cfee437bed387f76ff86c9ac086c1a52c3536797`.
- Artifact path: `.work/product-tls-generation/artifacts`.
- App: CardWords is the target, but no APK execution is claimed here.

## Status

- Label: `build_pass`.
- Why: two consecutive builds from the same 2,638-file frozen closure produced
  byte-identical artifact SHA manifests and both passed the fail-closed ELF
  verifier. This is not `device_verified`.

## Proven

- Input closure:
  - 2,638 files, approximately 299 MiB, all project-local during build.
  - `frozen.sha256` SHA256:
    `b3dc1bff5afcf7d564f5df30feac1832a010fc59cc9ee37df197bebe810906ac`.
  - `provenance.tsv` SHA256:
    `b3e32813ca16f7fe9b8c528ea26a5e9ea2476512b2de117e4020e06c1044f186`.
  - Every provenance row records origin path, origin SHA256, copied SHA256,
    input kind, and deployability. The final build command contains no external
    source/sysroot/library or `16.12` path.
- `libwestlake_hap_domain_wrapper.so`:
  - SHA256:
    `f5ce5d50972e7a293ad4d0c5b31120dee227913b96a7d7ddc95ed94b860551a7`.
  - sha1 Build-ID: `007c6462ffdf5c01a9906d46b8a2492a9ca2f6c1`.
  - SONAME is exactly `libwestlake_hap_domain_wrapper.so`; NEEDED is exactly
    `libhap_restorecon.z.so`, `libc++.so`.
  - No RPATH/RUNPATH/TEXTREL; pure-C export is globally defined; source calls
    stock `HapContext::HapDomainSetcontext`; no direct `/proc` path exists.
- `appspawn-x`:
  - SHA256:
    `417f3f38d4ee24e32f6322e04b07a197285c7271c7e19005369740507916754a`.
  - sha1 Build-ID: `66e4ea35bd2e3923b59775ac5eb46305e8bc1b17`.
  - `child_main.cpp` pins the exact wrapper Build-ID and fixed production path
    `/system/lib64/libwestlake_hap_domain_wrapper.so`.
  - PT_TLS is exactly `filesz=0`, `memsz=0x30`, `align=0x10`.
  - Same-Build-ID unstripped sidecar contains the 48-byte TLS symbol at module
    offset zero.
  - NEEDED order is exactly: `libc.so`, `libhilog.so`,
    `libipc_single.z.so`, `libsamgr_proxy.z.so`, `libbegetutil.z.so`,
    `libselinux.z.so`, `libhap_restorecon.z.so`,
    `libtokensetproc_shared.z.so`, `libnativehelper.so`, `liblog.so`,
    `libbionic_compat.so`, `libart.so`, `libc++.so`.
  - Every direct NEEDED has a unique byte identity in the frozen closure.
- `libbionic_compat.so`:
  - SHA256:
    `6c4e41b22d412c1487f73ca2d1d3d0725426e5b60c870849cd5cca8d210d11e5`.
  - sha1 Build-ID: `c2208a6221e6e0325ca96316502ab078ec6912c2`.
  - Built only from the admitted six-source producer. It contains no
    `bionic_tls_abi`, `unity_pthread_box`, `unity_signal_box`, `pthread_create`,
    or TPIDR_EL0 access.
- Evidence-only import libraries from the earlier prototype are not consumed.
  Real frozen target OH libraries satisfy all links with `-z defs`.

## Not proven

- A slot-5 semantic writer does not exist in this compat generation. The TLS
  reservation owns the address range but does not seed the stack guard.
- The six-source compat artifact contains pre-existing explicit stubs/default
  behavior. Their absence from the first-frame call closure has not been
  proven, so this generation is not deployable under the project's
  "only proven-unused capabilities may be stubbed" rule.
- Existing appspawn security/sandbox partial implementations listed below are
  not resolved by a successful link.
- Production init + Enforcing truly-cold execution and two-repeat runtime
  stability remain untested.
- No visible Unity frame, present receipt, screenshot, or RS evidence exists
  from these artifacts.

## Failed

- The evidence-only predecessor wrapper was rejected: md5-style Build-ID,
  `$ORIGIN` RUNPATH, wrong `.z.so` SONAME, synthetic link interfaces, and stale
  appspawn pin.
- Initial frozen builds exposed two real closure gaps—target `libunwind.a` and
  the OH libc++ compatibility force-include. Both are now frozen inputs; no
  external include fallback was introduced.
- No device experiment was attempted because the static semantic-writer gate
  remains open.

## Next evidence

- Command: first implement and architecture-review a namespace-scoped/typed
  Bionic slot-5 publisher that does not reintroduce `bionic_tls_abi.c`, global
  pthread/signal brokers, or a direct SELinux procattr path; then rerun:
  `adapter/framework/appspawn-x/generation/import_inputs.sh --refresh` and
  `adapter/framework/appspawn-x/generation/build_generation.sh`.
- Expected output: the verifier must still report the exact PT_TLS and wrapper
  identity gates, plus a new explicit slot-5 writer certificate; only then may
  the root agent stage a production-init + Enforcing truly-cold device trial.
- If it fails: do not deploy. Return to the ownership/semantic certificate and
  reject any attempt to substitute old global pthread/signal boxes or a direct
  `/proc/thread-self/attr/current` write.

## Shim/stub/bypass inventory

- No **new** stub was introduced by the producer, but pre-existing stubs do
  participate in the emitted compat DSO. The earlier wording "none
  participates" was inaccurate and is withdrawn.
- `fdsan_stubs.cpp`: fdsan ownership checks are disabled/no-op; owner is the
  Bionic/Musl boundary. Removal or temporary exemption requires a first-frame
  import/call proof plus an explicit policy decision; neither exists yet.
- `malloc_compat.cpp`: several Bionic `android_mallopt` operations return
  success without an OH equivalent. This is not yet proven safe for the
  CardWords first-frame path.
- `liblog_android_supplement.cpp`: logd reader/event APIs contain EOF/default or
  success-without-persistence behavior. They remain explicit compatibility
  stubs, not real logd behavior.
- `misc_compat.cpp`: `android_reset_stack_guards` still contains a fixed-canary
  fallback and only writes Musl's global guard. This is rejected as the final
  Bionic slot-5 mechanism and must be replaced before deployment.
- The stock HAP-domain wrapper itself is a real C-ABI boundary, not a stub. It
  may be removed only when appspawn-x and the OH HAP library share a certified
  C++ ABI/build graph directly.
- Test coverage currently proves frozen link/ELF identity and deterministic
  rebuild only. It does not prove the above stubs are unused before first
  frame.
- Scope is common adapter code; no CardWords package-name allowlist is compiled
  into it.
- Existing item: `ChildMain::applySandbox()` still returns success with TODO
  behavior. Owner is appspawn-x; removal requires the real OH sandbox mapping
  and production-init Enforcing tests. Common, not app-specific.
- Existing item: zero/absent AccessToken handling remains partial and must not
  be silently promoted to security completion. Owner is appspawn-x; removal
  requires a real token from the spawn request and kernel-observed application.
- Existing item: `SpawnServer::initSecurity()` remains a success stub. Owner is
  appspawn-x; removal requires stock OH security initialization and failure
  propagation.
- Legacy item: `.work/tls-generation/{import,link-stage}` is marked
  `NEVER_DEPLOY`; the new producer has zero dependency on it.

## Memory/skill/CI/review updates

- Memory: this file and `.work/product-tls-generation/{provenance.tsv,
  build-result.env,evidence}` are the saved resume state.
- Skill: applied `_deep_debug_westlake`, `design-check`, and
  `westlake-engineering-discipline`; no device action occurred.
- CI: producer and verifier are project-local but are not yet wired to hosted
  CI. The frozen closure is intentionally local and fail-closed.
- Review checklist: static 5-question architecture audit executed; device gate intentionally remains open.
  - Q1 ART/class_linker/vtable changed? No.
  - Q2 BCP/ActivityThread semantics changed? No.
  - Q3 fix in adapter/boundary layer? Yes.
  - Q4 libart/BCP continuity required? No such artifact changed.
  - Q5 truly-cold verified? No; explicitly `Not proven`.
  - Java stub introduced? No Java was changed.
