# Thread-template publisher host-core checkpoint

## Boundary

- Boundary: a caller has already prepared a process guard in the current
  thread's main-ELF TLS reservation and asks this component to publish it into
  the future-thread initialization image.
- Android behavior: Bionic copies one process stack guard into each new thread
  before its start routine.
- OpenHarmony mapping: the eventual adapter maps that behavior onto the
  unmodified loader's main-ELF `PT_TLS` template; this checkpoint tests the
  portable ELF/template mechanism only.
- Fix layer: adapter-owned native-compat component; no APK, Unity DSO, ART, BCP,
  Musl, appspawn security owner, or device change.

## Evidence target

- What this proves: the host fixture can locate the exact main image, patch the
  correct 8-byte guard position, preserve the rest of a 48-byte template, make
  a new pthread observe the value, and admit exactly one concurrent publisher.
- What this does not prove: AArch64/OH-loader behavior, product integration,
  parent/child epoch wiring, complete thread admission, Unity load, device
  startup, rendering, or first frame.

## Environment

- Host: locked, networkless Linux build/runtime container selected by the
  project-local tool-runtime lock.
- Device: not used; no production-init, Enforcing, truly-cold, hilog, or pixel
  evidence.
- Tool path: `tests/run_host_tests.sh`.
- Artifact path: generated executables/logs are under ignored
  `.work/thread-template-publisher-host/` and are not committed.
- App: no APK was launched.

## Status

- Label: `build_pass` for the host fixture; `real_impl=true` for this portable
  component; `stub=false`; `device_verified=false`; `product_activation=false`.
- Why: the implementation and four causal negative controls pass in the locked
  host environment, while target/product/device evidence is explicitly absent.

## Proven

- A file-backed 48-byte main `PT_TLS` fixture copies the published guard into a
  later pthread before its start body observes the slot.
- A process-global, non-TLS atomic CAS admits exactly one of two racing
  publishers and returns `ALREADY_PUBLISHED` to the other.
- Four mutants are killed: no template patch, wrong offset, competing writer,
  and missing exact-once enforcement.
- The publisher does not create threads, generate/fallback entropy, mutate a
  Musl global guard, reference ART/BCP, or modify guest binaries.

## Not proven

- The future production executable's exact AArch64 `PT_TLS`, RELRO, loader,
  generation identity, fork epoch, call order, and strict link are not covered
  by this host-core commit.
- WLTG MAIN/pthread/JNI/callback/signal admission and CardWords runtime behavior
  are outside this checkpoint.

## Failed

- The no-patch, wrong-offset, competing-writer, and no-exact-once variants are
  all rejected by observable negative controls.
- Treating host success as an OH target or device result is rejected.

## Next evidence

- Command: build the same source twice for the frozen AArch64 OH target, inspect
  the exact ELF/RELRO layout, and execute it with the exact frozen OH loader.
- Expected output: byte-identical artifacts, correct 48/48 `PT_TLS`, restored
  protection, and every target/order mutant rejected without product activation.
- If it fails: keep this component host-only and fix the first target invariant;
  do not wire or deploy it.

## Shim/stub/bypass inventory

- Item: no shim, stub, fake success, or security bypass; this is a narrowly
  scoped adapter mechanism.
- Owner: `adapter/framework/native-compat/thread-template-publisher/`.
- Why it exists: provide the future loader-template translation point without
  altering Musl or Bionic guest binaries.
- Removal condition: remove only if Android guest execution no longer shares
  the OH thread/TLS substrate.
- Test coverage: host template copy, concurrent exact-once, and four mutants;
  target, product, and device coverage remain pending.

## Memory/skill/CI/review updates

- Memory: host template publication is a mechanism proof, not thread admission
  or product activation.
- Skill: WestLake boundary-first and evidence-level separation were applied; no
  skill file was modified.
- CI: `tests/run_host_tests.sh` is the commit-level replay.
- Review checklist: preserve exact-main-image binding, full-width slot copy,
  non-TLS exact-once state, no entropy fallback, no thread creation, and no
  product/device claim from this host gate.
