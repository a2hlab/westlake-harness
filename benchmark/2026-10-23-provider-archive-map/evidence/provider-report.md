# ARM64 Bionic/AOSP provider generation — v12 no-broad-ART-stub

## Outcome

The strict, project-local ARM64 provider generation produces two byte-identical
output sets. Each contains 23 typed provider DSOs, including the namespace
backend, Bionic compatibility boundary, AOSP base/ART companions and the full
`libart.so`. The former 487-export `libart_runtime_stubs.so` is absent both as a
file and from every `DT_NEEDED` edge.

This is `ARTIFACT_VERIFIED_NOT_PRODUCT_ACTIVATED`.  It closes the stale
generation's AOSP provider metadata problem; it does not prove a deployable
appspawn product or Unity startup.

## Boundary

- Boundary: ARM64 Bionic/AOSP provider build, SONAME/Build-ID ownership and
  app-private NativeLoader backend; no application lifecycle or rendering
  behavior is implemented here.
- Android behavior: APK, Unity DSOs, ART source semantics and BCP are not
  patched to obtain this result.
- OpenHarmony mapping: exact OH Musl sysroot and exact 5EAB5 link-provider bytes
  are frozen locally.  Link aliases are build-only; embedded SONAME is the
  runtime identity.
- Fix layer: adapter-owned Bionic/Musl provider and namespace build boundary.
- External origins are read only by the one-time importer.  The compiler phase
  has no external source mount, no network and no path to `16.12-HanBing`.

## Evidence target

- What this proves: the exact frozen provider source closure produces 23
  strict-link ARM64 DSOs twice with identical bytes, complete Build-IDs, unique
  SONAME owners, the enumerated direct ABI edges and exact real replacements
  for the two former broad-stub consumers.
- What this does not prove: product activation, remaining narrow capability
  stub policy,
  appspawn child execution, a device runtime, Unity load, render present or a
  visible first frame.

## Environment

- Host: current project workspace plus locked, network-disabled
  `westlake-oharm64build:local-tools` Linux container.
- Device: not used; no read, write, deployment, reboot or application launch.
- Tool path: `adapter/build/provider_generation/`; exact compiler/readelf and
  target inputs are under the immutable v12 frozen root.
- Artifact path: `.work/bionic-musl-provider/provider-inputs-v12-nobroadstub/artifacts{,-repro}/`
  and `.work/bionic-musl-provider/provider-inputs-v12-nobroadstub/evidence/verification.json`.
- App: CardWords context only; APK and Unity DSOs were not executed or changed.

## Status

- Label: `build_pass / real_impl provider set / artifact_verified`;
  `product_activation=false`, `device_verified=false`.
- Why: both strict builds and the identity/owner verifier pass, but the fixed
  guard fallback, remaining narrow capability policy, stock appspawn integration and final
  TP/prepare certificate remain product blockers.

## Proven

- 21,011 frozen source/header/sysroot/tool files are individually hashed below
  `.work/bionic-musl-provider/provider-inputs-v12-nobroadstub/` before compilation.
- AOSP's own cpp-define-generator emits the ARM64 ART assembly contract;
  `POINTER_SIZE=8` and shift `3` are mandatory.  The contaminated historical
  ARM32 generated header is never consumed.
- All provider links use strict undefined-symbol checking, SHA1 Build-ID and an
  exact filename-matching SONAME.
- Two independent builds produce the same 23 SHA256 values and Build-IDs.
- All 23 SONAMEs have exactly one owner; no provider has RPATH, RUNPATH or
  TEXTREL.
- `_Z15ErrorCodeStringi` has exactly one owner, the real
  `libziparchive.so`; compat and ART stubs own none.
- Direct typed edges are present:
  `libartbase -> libziparchive`, `libart -> libnativeloader`, and
  `libnativeloader -> libapp_native_loader`.
- `libbionic_compat.so` owns no PT_TLS and no global pthread/signal broker.
- `libart_runtime_stubs.so` is absent, no provider needs it, and no generated
  provider defines the broad DSO's process-control interposers `abort`/`raise`.
- `libprofile.so` directly consumes real `libartpalette.so` trace APIs and real
  `libartbase.so` `FdFile` methods. `libunwindstack.so` contains the real AOSP
  C++ demangler and static dex-support binding and directly consumes the real
  external dex API in `libdexfile.so`.
- Namespace backend target fixtures and source-policy checks pass before the
  provider build.

Primary identity manifest SHA256:
`3177745fafb7b4cc9f49c1c535a11de0c79bbec51b4a7cee6f42ee2386425752`.
Verification JSON SHA256:
`66e5173f7094b67439d718538ae6f56f5d9640f420d3aca4b7d1a12303eee242`.

## Failed

Earlier immutable attempts were retained rather than overwritten.  They
exposed, in order, an escaping AOSP include symlink, missing linker runtime,
missing AArch64 tool runtime, an undeclared host utility, the internal-helper
capability gate, the ARM32 ART header contamination, target libc++ selection,
and missing OH link interfaces.  Each attempt stopped before eligibility; no
device was touched and no partial set was promoted.

## Not proven

- The v12 compat source still contains the historical fixed fallback in
  `android_reset_stack_guards`; therefore these artifacts are not deployable.
  The reviewed guard issuer must replace it and fail closed on entropy failure.
- The broad ART runtime stub DSO is closed, but AOSP's own Rust demangle fallback
  and platform palette/diagnostic implementations still require explicit
  capability classification in the final same-generation release certificate.
- Stock appspawn host + Android child plugin final integration is linked in an
  independent lane but not yet combined with the reviewed thread-guard owner.
- Main-thread and every Android-owned worker/callback guard publication are not
  product activated.
- The initial TP/prepare certificate still retains exact risk and residual
  flows; host evidence is not a production runtime receipt.
- Full 40-provider OH/AOSP namespace identity, production init order, SELinux
  specialization, Unity load, Surface/EGL present and visible first frame are
  not proven.

## Next evidence

1. Replace all competing guard owners with the reviewed process guard registry,
   prove MAIN/pthread/JNI-attach/loader order and rebuild a new immutable
   provider generation.
2. Complete stock appspawn host/plugin final linking and prove the order:
   stock stage31 specialization -> receipt -> guard READY -> ART post-fork.
3. Re-run provider fixed point/identity and initial TP/prepare gates over that
   single generation.
4. Only after those pass, deploy through production init on 5EAB5 under SELinux
   Enforcing and perform one bounded truly-cold CardWords trial.

- Command: after the reviewed guard and stock-child providers land, create a
  new immutable input generation, build it twice, run
  `tests/run_regression_tests.sh`, then feed its DSOs to the provider
  fixed-point and initial TP/prepare certifiers.
- Expected output: 23/23 unique provider identities remain byte deterministic,
  the fixed canary is absent, all required product issuers/call-order gates are
  proven, and the combined release certificate—not this report—returns PASS.
- If it fails: retain the first immutable failure, reject its artifacts and
  correct the exact source/tool/provider boundary; do not relax SONAME,
  Build-ID, undefined-symbol, namespace or stub-call-closure policy.

## Shim/stub/bypass inventory

- Item: the broad ART runtime stub DSO is removed. C++ demangling and dex support
  use real AOSP sources. The AOSP-build-defined Rust demangle C fallback remains
  explicit and returns unsupported for Rust names; platform palette/diagnostic
  behavior remains separately inventoried and cannot inherit this build PASS as
  a first-frame-use certificate.
- Owner: adapter Bionic/Musl provider boundary plus the exact AOSP source modules
  identified in the verification report.
- Removal condition: every callable first-frame symbol has a unique real owner,
  or a reviewed unused-before-first-frame certificate names the explicit stub.
- Test coverage: two complete strict builds, 23-DSO identity/owner verification,
  ErrorCodeString and NativeLoader edge checks, exact replacement-owner checks,
  one determinism mutant and one typed-owner mutant.

## Memory/skill/CI/review updates

- Memory: this v12 report and the top-level Unity first-frame state checkpoint
  record the provider-generation transition; v11 and failed v1-v10 roots remain as
  immutable evidence.
- Skill: WestLake boundary-first, exact-generation, fail-closed and design-check
  disciplines were applied; no skill source was modified.
- CI: `tests/run_no_broad_art_stub_regression_tests.sh` is the v12 replay entry and must be
  added to the unified Bionic/Musl lane after the live product contract stops
  changing.
- Review checklist: require project-local frozen inputs, two byte-identical
  builds, exact SONAME/Build-ID ownership, no global fallback path, no fixed
  guard, explicit stub closure, and product/device claims only from the later
  combined generation.

## Reproduction

```sh
WESTLAKE_PROVIDER_GENERATION_ID=provider-inputs-v12-nobroadstub \
  adapter/build/provider_generation/build_generation.sh
WESTLAKE_PROVIDER_GENERATION_ID=provider-inputs-v12-nobroadstub \
  WESTLAKE_PROVIDER_BUILD_RUN=repro \
  adapter/build/provider_generation/build_generation.sh
WESTLAKE_PROVIDER_GENERATION_ID=provider-inputs-v12-nobroadstub \
  WESTLAKE_PROVIDER_POLICY=no-broad-art-stub-v1 \
  adapter/build/provider_generation/verify_generation.sh
adapter/build/provider_generation/tests/run_no_broad_art_stub_regression_tests.sh
```

No command above deploys or touches a device.
