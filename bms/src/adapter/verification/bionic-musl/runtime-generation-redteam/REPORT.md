# Route-A runtime generation verifier implementation report

## Boundary

- Boundary: appspawn-x/Route-A dynamic roots, Bionic/Musl loader namespaces,
  ELF/link provenance, and FD admission identity.
- Android behavior: Android runtime and adapter bridge loads must resolve to
  their exact intended ELF and fail closed before JNI/framework side effects.
- OpenHarmony mapping: verify the explicit OH namespace/provider graph and
  pinned FD-backed mappings without changing stock OH security specialization.
- Fix layer: independent host verifier and test-only synthetic ELF oracle under
  `adapter/verification/bionic-musl`; no product implementation change.
- This change contains only an independent verifier, synthetic oracle fixtures,
  tests, and report documentation.
- Product source, APK, ART, BCP, appspawn architecture, device, and external
  OH/AOSP trees were not modified.

## Evidence target

- What this proves: a verifier can re-derive the admission decision from arbitrary
  integrator-selected project/source/build roots without trusting stale result
  JSON or the product build's own PASS marker.
- What this does not prove: Linux ARM64 product build, runtime namespace
  execution, target mapping identity, production-init, or Unity pixels.

## Environment

- Host: macOS host-only deterministic oracle.
- Device: none; no HDC/ADB command was issued.
- Tool path: project verifier plus OH SDK `clang` and `llvm-readelf`.
- Artifact path: `adapter/verification/bionic-musl/runtime-generation-redteam/`;
  synthetic ELF exists only in OS temporary directories during tests.
- App: CardWords `com.CardWordsStudio.CardWords` (not executed).
- OH SDK `clang` and `llvm-readelf` produce/inspect synthetic ELF64/AArch64
  discriminators in OS temporary directories.
- No network, remote build executor, or device is used.

## Status

- Label: real_impl
- Why: the independent verifier and deterministic oracle suite are implemented;
  the synthetic ELF64/AArch64 positive control is host build evidence only.
- Not `device_verified`; not a product generation; not a Unity first-frame
  result.

## Proven

- The positive oracle passes 20 independent gates and the parameterized CLI.
- Twenty single-variable mutants are rejected: stale source, symlink, ARM32,
  SONAME, Build-ID, RUNPATH, dynamic-root/callsite/failure contracts,
  runtime/startReg/preload fake success, namespace reachability/ambiguity,
  strict argv, project-local input escape, strong UND, common token, path swap,
  and duplicate mapping.
- Reports are tied to the current manifest SHA and a pre/post-rehashed
  observation ID; their decision scope is exact bytes only.

## Not proven

- Neither the Route-A worktree nor ARM64 generation worktree currently supplies
  a complete `westlake.runtime-generation-candidate.v1` manifest and sealed
  payload accepted by this verifier.
- No Linux ARM64 product build, target namespace execution, production-init,
  SELinux Enforcing, truly-cold fork, Unity load, EGL/RS present, or first frame
  is proven here.

## Failed

- The first test invocation used `python -m unittest` with a path beginning in
  `02.*`, which Python treated as module `02`; the canonical runner executes the
  test file directly.
- The first direct run resolved the OH SDK `llvm-readelf` symlink to
  `llvm-readobj`; that multicall binary changes behavior by `argv[0]`. The
  verifier now preserves the `llvm-readelf` alias and the full suite passes.

## Next evidence

- Command: emit a complete candidate manifest, then run the parameterized
  `verify_candidate.py` command shown in `README.md` against the joined exact
  Route-A/runtime generation.
- Expected output: exit 0 with
  `eligible_for_route_a_device_admission=true`, all 20 gates PASS, current
  manifest SHA, and a new observation ID.
- If it fails: keep the candidate out of the device lane and repair the first
  exact gate code; never reuse an older verdict JSON.
- Route-A owner must emit current source contracts, exact callsites/failure
  behavior, namespace graph, and FD admission records.
- Generation owner must emit the complete generated/immutable artifact set,
  exact link receipts, strong-UND closure, and embedded common token.
- The integrator reruns this verifier against the joined exact candidate; only
  an accepted current-byte verdict may enter the D600 device lane.

## Shim/stub/bypass inventory

- Item: synthetic ELF fixtures.
- Owner: runtime-generation red-team test suite.
- Why it exists: provide positive and single-variable negative discriminators
  for the independent verifier.
- Removal condition: retain as CI oracle while this admission contract exists;
  never include in a product payload.
- Test coverage: one complete positive candidate, 20 focused mutants, and one
  parameterized CLI test.
- App-specific or common: common Route-A/runtime generation admission tooling;
  synthetic artifacts are test-only.

## Memory/skill/CI/review updates

- Memory: current-byte verdicts are non-transferable across source/artifact/
  receipt changes; no hidden session state is an evidence source.
- Skill: WestLake iron-rule review found no ART/BCP/product implementation edit;
  Q1-Q4 are
  consistent and Q5 remains explicitly unproven.
- CI: retain the positive control, all 20 mutants, CLI test, and
  no-generated-output rule.
- Review checklist: verify branch/worktree ownership, manifest SHA,
  observation ID, no generated files, and explicit non-device scope before
  integration; verdict JSON is non-transferable when manifest/source/
  artifact/receipt bytes change.
