# Main-ELF thread-template publisher checkpoint

## Boundary

- Boundary: after the fork child has reset inherited parent state and WLTG has
  prepared/read back the child MAIN slot, but before any guest-capable thread
  can be created.
- Android behavior: Bionic uses one full-width process stack guard and copies
  that value into every thread's slot 5 before the thread start routine runs.
- OpenHarmony mapping: the adapter publishes the child guard into the
  file-backed main-ELF `PT_TLS` initialization image that the exact OH Musl
  loader copies for later pthreads; the parent retains its own epoch/template.
- Fix layer: adapter-owned appspawn/native-compat boundary. It does not modify
  Musl, ART, BCP, the APK, or a Unity DSO.

## Evidence target

- What this proves: the standalone publisher mechanism, parent-A to child-B
  reset/order contract, exact-once publication, RELRO restore, and future
  pthread template copy work under the frozen observed OH loader.
- What this does not prove: final Route-A link/activation, all six thread-entry
  admissions, CardWords native loading, device startup, rendering, or a visible
  Unity frame.

## Environment

- Host: host concurrency tests plus locked-container ELF64/AArch64 builds.
- Device: not used; no production-init, Enforcing, truly-cold, hilog, or pixel
  evidence.
- Tool path: `tests/run_all.sh`; the target replay uses the locked runtime in
  `tests/target_runtime.lock`.
- Artifact path: generated replay outputs are under ignored `out/target/`; no
  generated ELF is a deployable product artifact.
- App: no APK was launched. CardWords is only the eventual consumer.

## Status

- Label: `build_pass` for the standalone fixture; `real_impl=true` for the
  publisher component; `stub=false`; `device_verified=false`;
  `product_activation=false`.
- Why: the independent full replay passes host, deterministic AArch64,
  structural-mutant, and exact-loader runtime gates, while final Route-A and
  device evidence do not yet exist.

## Proven

- The fixture and product source gate use the same
  `thread_template_publisher.c` implementation.
- Two deterministic AArch64 builds contain one file-backed main `PT_TLS` with
  `filesz=memsz=48`, alignment 16, slot-5 relative offset 24, and a RELRO-
  covered non-executable containing LOAD.
- The frozen observed OH loader with SHA-256
  `316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98`
  executes the valid fixture. A later Musl pthread observes the published guard
  before its start body, and the template mapping is restored read-only.
- A process-global non-TLS CAS admits exactly one publisher under a concurrent
  race. Publication failure is terminal in the product caller.
- The fork child performs a full 48-byte inherited-template reset, re-arms a
  child-specific epoch, prepares/reads back MAIN, then publishes child B; no
  parent A template is reused.
- Nine structural/product-source mutants and eight frozen-loader runtime/order
  mutants are rejected. The main reservation is a zero-filled 48-byte `.tdata`
  image; nonzero canaries exist only in the nondeployable fixture.

## Not proven

- The publisher object, reservation, WLTG registry, and callers have not passed
  a final same-generation Route-A strict link and final appspawn ELF audit.
- The observed loader is a mechanism oracle, not proof of the future production
  generation or the target device.
- Namespace pthread admission, central JNI attach/native-entry admission,
  signal-entry policy, Unity native load, Surface/EGL/RenderService present, and
  first frame remain unproved.

## Failed

- The former `.tbss` reservation was rejected because `p_filesz=0` supplies no
  initialization image for future threads.
- Reusing parent A in the child, skipping the 48-byte reset, wrong image/offset,
  no protection restore, multiple publishers, and publication omission are all
  killed by negative controls.
- Global pthread interposition, Musl `__stack_chk_guard` mutation, ART patches,
  and a second template owner remain forbidden.

## Next evidence

- Command: build the complete immutable Route-A generation twice and run the
  final appspawn TLS/phase/identity verifier on its exact ELF closure.
- Expected output: byte-identical strict-linked appspawn/provider artifacts;
  final main `PT_TLS 48/48`, zero file image, non-RWX LOAD, RELRO coverage,
  hidden publisher symbols, parent-A/child-B receipt, and all six admissions
  closed.
- If it fails: reject the generation and fix the first failing ownership,
  order, identity, or admission gate; do not deploy a partial product set.

Replay the standalone evidence with:

```sh
adapter/framework/native-compat/thread-template-publisher/tests/run_all.sh
```

The final line must be:

```text
PASS exact frozen OH loader product-publisher runtime_mutants=8 product_activation=false
```

## Shim/stub/bypass inventory

- Item: no shim, stub, fake success, or security bypass; this is an
  adapter-owned TLS template publication mechanism.
- Owner: `adapter/framework/native-compat/thread-template-publisher/` plus the
  explicit appspawn MAIN call boundary.
- Why it exists: translate Bionic per-thread stack-guard initialization onto
  the unmodified OH Musl TLS template mechanism.
- Removal condition: retain while Bionic guest code executes in-process; remove
  only if the guest is isolated behind a different runtime boundary that no
  longer shares the OH thread/TLS substrate.
- Test coverage: host exact-once race, deterministic target build, 9 structural
  mutants, 8 exact-loader runtime mutants, and product source-order gate; final
  product link and device coverage remain pending.

## Memory/skill/CI/review updates

- Memory: `.tbss` cannot initialize future pthread TLS; parent and fork child
  require different generation/epoch templates even when COW initially shares
  bytes.
- Skill: `_deep_debug_westlake`, `westlake-engineering-discipline`, and
  `design-check` constraints were applied; no skill file was modified.
- CI: keep `tests/run_all.sh` as the component gate and add the final immutable
  Route-A ELF/receipt gate before product activation.
- Review checklist: do not infer thread admission from template bytes; require
  reset -> arm -> issue -> prepare -> verify -> publish -> READY order, no
  guest-capable thread before publication, no stack-protected frame spanning an
  A-to-B switch, and no device claim without truly-cold evidence.
