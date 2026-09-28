# PR-08A disabled aperture-writer fixture handoff

## Boundary

- Boundary: Bionic/Musl data-plane mechanism fixture at the appspawn main-ELF
  TLS reservation boundary.
- Android behavior: model a real non-zero Bionic stack-guard publication at
  slot 5, without changing original Unity instructions, APK/DSO bytes or
  Musl's global `__stack_chk_guard`.
- OpenHarmony mapping: the main ELF owns the reserved TLS bytes and returns
  their current-thread address through an explicit callback; a separate
  fixture-only backend validates a one-shot permit, obtains OS CSPRNG data,
  writes, reads back, stages metadata and publishes READY.
- Fix layer: adapter-owned native fixture under
  `framework/native-compat/tests/aperture_writer_fixture`; no ART, BCP, Musl,
  Unity, package manager, appspawn product call site or device was changed.

## Evidence target

- What this proves: the writer contract can be implemented without a
  constructor, backend TLS, hardcoded TP address, global stack-guard write,
  fixed/zero fallback, package/env allowlist or audit-core permit upgrade.  It
  also proves the existing reservation symbol is safely addressable by a
  main-owned AArch64 linker TLS relocation.
- What this does not prove: exact device execution, six guest-entry classes,
  a real release certificate/signature issuer, appspawn/native-loader
  integration, target lifetime non-overlap, Unity load or a first frame.

## Environment

- Host: Darwin arm64 with local clang for the host model and ASan/UBSan.
- Target build: project-local frozen OH clang 15, sysroot, readelf and objdump
  under `.work/product-tls-generation/frozen`, inside the exact image pinned by
  `.work/product-tls-generation/tool_runtime.lock`; network disabled and all
  outputs below the project.
- Device: D600-B `5EAB5`; company-owned fixture-only execution receipt is
  `var/evidence/device-runs/20260712T220600Z/REPORT.md`. No APK/app was started,
  no system library was changed, and no reboot occurred.
- Tool path: `.work/product-tls-generation/frozen/toolchain` and the locked
  project-local scripts in this fixture directory.
- Artifact path: `adapter/framework/native-compat/tests/aperture_writer_fixture/out/target/`.
- App: no APK or third-party DSO is mapped by this fixture.
- Artifacts: backend SHA256
  `c0055d9e9be4559263279aaec5c8103b196f7e0541ea48423de5660837e55805`;
  main owner fixture SHA256
  `d9559ae1c9e4497d427a247ea52cd13be05181281fa69bd0b7b72fd6c36d0144`;
  separately rebuilt audit core SHA256
  `7626fa4c8562f3ec596fddd940cdf0f0e1ed20f6e0e2669f1437e6bf25f9d0b2`.

## Status

- Label: `real_impl` for the disabled fixture contract and host semantics;
  `build_pass` for the AArch64 artifacts; `stub/disabled` for every product
  integration claim.
- Why: the isolated writer semantics and structural artifact policy are
  implemented and tested, while no product permit issuer, caller or target
  runtime receipt exists.
- Product activation: false. Product load authority: false. Standalone
  aperture fixture device-verified: true. Product device-verified: false.

## Proven

- Nine host contract groups pass, including exact binding, signature tamper,
  offset/width, owner bounds, CSPRNG failure/zero, replay, core-permit type
  confusion and missing-callback denial.
- Four semantic mutants are killed: READY-before-metadata, signature bypass,
  fixed guard fallback and owner-bounds bypass.  ASan/UBSan passes.
- Permit data cannot choose the guard value or a pointer.  It binds non-zero
  generation/process/policy epochs, target digest, one-shot nonce, exact
  `TP+0x28` semantic offset and width 8.  The main owner callback supplies the
  only region pointer and publication state.
- Guard-source failure consumes the permit into terminal FAILED; zero, wrong
  source quality or wrong epoch cannot publish READY and has no fallback.
- The one AArch64 slot primitive is exactly `str x1,[x0]` followed by
  `ldr x0,[x0]`.  Receipt metadata is staged before a release-store of READY;
  readers use acquire loads.
- The backend DSO has no `PT_TLS`, TLS section/relocation, constructor,
  runtime dependency, RPATH/RUNPATH/TEXTREL, TPIDR_EL0/system-register access,
  reservation-symbol reference or Musl global `__stack_chk_guard` reference.
- The main owner object has exactly two TLSLE linker relocations against
  `westlake_bionic_tls_slots_2_7_reservation`.  The final main has one
  `PT_TLS filesz=0, memsz=0x30, align=0x10`; its owner accessor contains no
  literal `TP+0x28` implementation.
- Two independent AArch64 builds of backend, main fixture and audit core are
  byte-identical.  Three target mutants are killed: backend PT_TLS,
  constructor and hardcoded TP owner.
- The audit core remains `AUDIT_ONLY`, has no `WLAF_*` symbol or backend
  dependency, and independently passes its 10 host groups, three mutants,
  sanitizers and deterministic AArch64 no-writer gate.
- The 17-check final-ELF TLS ownership verifier remains PASS.  Product build
  inputs contain neither this fixture nor legacy `bionic_tls_abi.c`,
  `unity_pthread_box.c` or `unity_signal_box.c` as active commands.
- On exact 5EAB5 with Enforcing, the main/backend/loader hashes matched, the
  company-owned fixture returned zero, and its internal predicate proved one
  non-zero OS-CSPRNG guard publication with exact readback and READY-last
  ordering. Boot ID was unchanged and no third-party DSO was mapped.

## Not proven

- The fixture test seal is not a production cryptographic signature, release
  issuer, revocation mechanism, sealed-FD proof or anti-replay registry.
- Only the current main-thread owner shape is built.  Guest pthread, OH
  callback, thread pool, post-fork and signal entry receipts are absent.
- The current reservation addresses ownership, but whole-lifetime exact
  target non-overlap and every pre-prepare writer/reader still require the
  generation certificate and target execution receipts.
- No appspawn READY call order, SELinux Enforcing specialization, Unity native
  initialization, Surface/EGL/RenderService present or visible frame is
  proven.

## Failed

- The first target candidate embedded nonexistent
  `/system/bin/ld-musl-aarch64.so.1`; run `20260712T220200Z` rejected it before
  execution. No explicit-loader bypass was used. The producer now embeds and
  verifies exact `/lib/ld-musl-aarch64.so.1`; the rebuilt artifact is the one
  that passed the later device run.

- The legacy `appspawn-x/tls_prefix/tests/run_link_fixture.sh` still defaults
  to a Linux x86_64 compiler under external 16.12 and cannot execute directly
  on this Darwin host.  It is not used by this producer or verifier.  The same
  canonical reservation source is instead consumed from the project by the
  locked local container, and both this target gate and the 17-check ownership
  verifier pass.  The legacy runner should be converted separately rather
  than reintroducing an external build input.
- A literal `mrs TPIDR_EL0; add #0x28` owner was deliberately built as a
  negative mutant and rejected.  There is no fallback if TLSLE relocation
  ownership ceases to link.

## Next evidence

- Command: retain `run_all.sh` and the device runner as regression gates, then
  implement the separately reviewed real issuer/appspawn/thread-entry product
  chain without copying the fixture key or `WLAF_*` ABI into products.
- Expected output: all six product entry classes use one generation-bound
  owner and the product permit remains unreachable until closure and issuer
  evidence are complete.
- If it fails: keep product activation false.  Do not hardcode TP, add a
  constructor, accept a core audit permit, use a fixed guard, or deploy Unity
  to discover the result.  Correct the owner/permit/CSPRNG/order proof first.

## Shim/stub/bypass inventory

- Item: `WlafFixturePermitV1` and `test_fixture_signing.c`.
- Owner: L03.A15 PR-08A company-owned target fixture; no app/package owner.
- Why it exists: exercise a typed signed-permit boundary while the real
  release issuer and PR-00..07 control-plane consumers do not exist.
- Removal condition: product code never consumes the test key or fixture
  permit.  A separately reviewed cryptographic issuer/verifier and sealed
  generation permit must define a new product ABI before any backend is
  reachable.
- Test coverage: signature tamper/type confusion, identity/epoch/offset/width,
  replay, owner region, CSPRNG, READY ordering, target ELF and instruction
  mutants.
- App-specific or common: common adapter mechanism fixture; no CardWords title
  or package allowlist exists.

- Item: target fixture's raw AArch64 `getrandom(2)` source.
- Owner: company-owned target fixture only.
- Why it exists: prove there is no deterministic guard fallback without adding
  a libc dependency to the isolated artifact.
- Removal condition: a product platform CSPRNG owner is reviewed; this syscall
  source is never copied into product code.
- Test coverage: short/failure/zero source paths are fail-closed in the host
  model; exact target availability remains not proven.
- App-specific or common: fixture only.

## Memory/skill/CI/review updates

- Memory: the permanent ownership rule is now executable: the main ELF owns
  the reservation address; the backend owns the single write contract; the
  permit owns identity, never pointer or value; READY comes last.
- Skill: WestLake boundary-first, four-gate and HanBing design checks were
  applied.  No device trial was used to replace a host/static proof.
- CI: add `aperture_writer_fixture/run_all.sh` only to the fixture/static lane;
  do not add its DSO or test key to a generation producer.
- Review checklist: reject any product diff containing `WLAF_*`, the fixture
  test key, a literal TP slot address, backend TLS, constructor, package/env
  activation, fixed guard or conversion from `WlncLoadPermit`.

## HanBing five-question design check

- Q1 ART/class_linker/vtable changed: no; mechanical ELF gate finds no
  `FIX-VTABLE-A`, and no ART source is touched.
- Q2 BCP/ActivityThread changed: no; no Java or boot artifact is involved.
- Q3 fix is at the adapter boundary: yes; the fixture is isolated under the
  Bionic/Musl native compatibility boundary and leaves Musl/Unity unchanged.
- Q4 coherent boot rebake required: not applicable; neither libart nor BCP
  changed.
- Q5 truly-cold/product device proof: not proven and not claimed.
- Java zero-stub gate: not applicable.  The test permit is explicitly listed
  fixture scaffolding and cannot return product load success.
