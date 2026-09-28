# Runtime generation red-team verdict

## Boundary

- Boundary: appspawn-x / Route-A dynamic-loader admission and Bionic/Musl
  generation provenance.
- Android behavior: exact Android runtime/bridge selection and fail-closed JNI
  initialization.
- OpenHarmony mapping: explicit namespace/provider/FD identity admission while
  stock OH appspawn retains security specialization ownership.
- Fix layer: host verification/evidence layer only.
- Product source changed by this verification: none.
- Device touched: none.
- APK, ART, BCP, appspawn architecture, SELinux, and installed SO changed: none.

## Evidence target

- What this proves: `<exact current-byte host admission claim>`
- What this does not prove: device execution, production-init, Enforcing,
  truly-cold, Unity load, EGL/RS present, pixels, input, or stability.
- Project root: `<absolute project root>`
- Source root: `<absolute current source snapshot>`
- Build root: `<absolute generation output>`
- Candidate manifest: `<path>`
- Candidate manifest SHA-256: `<sha256>`
- Red-team observation ID: `<observation_id>`
- Verifier commit: `<commit>`

## Environment

- Host: `<host>`
- Device: none
- Tool path: `<llvm-readelf path and SHA-256; verifier path and commit>`
- Artifact path: `<exact source/build roots and candidate artifact root>`
- App: CardWords `com.CardWordsStudio.CardWords` (not executed by this gate)
- Command: `<exact verify_candidate.py command>`
- Test command/result: `<run_tests.sh result>`

## Status

- Label: build_pass
- Why: `<accepted host artifact candidate, or change Label to stub and record
  exact rejection>`
- Route-A device admission eligible: `<true|false>`
- Product activation: `false`
- Device verified: `false`
- First frame proven: `false`

## Proven

- `<only claims directly supported by the current verdict JSON>`

## Not proven

- Production-init listener ownership, SELinux Enforcing, reboot + NO_JIT first
  cold fork, live namespace winner, Unity JNI/native initialization, EGL/RS
  present, visible pixels, input, and five-minute stability.

## Failed

- `<gate code, exact failure, and whether it is a source, artifact, receipt, or
  evidence-envelope defect>`

## Next evidence

- Command: `<next exact command>`
- Expected output: `<exact marker and decision fields>`
- If it fails: `<owner and fail-closed response>`
- `<smallest exact change and next independent rerun required>`
- A candidate may enter a device lane only after the exact current manifest
  returns `eligible_for_route_a_device_admission=true`.

## Shim/stub/bypass inventory

- Item: synthetic ELF fixtures.
- Owner: runtime-generation red-team test suite.
- Why it exists: deterministic positive and mutant discrimination.
- Removal condition: never deploy; retain while the admission contract exists.
- Test coverage: positive candidate, focused mutants, and parameterized CLI.
- App-specific or common: common admission tooling; fixtures are test-only.

## Memory/skill/CI/review updates

- Memory: current verdict is bound to exact manifest/observation hashes.
- Skill: WestLake five-iron-rule gate Q1-Q4 consistent; Q5 not proven by this host
  verifier.
- CI: preserve one positive control, every focused mutant, CLI, and no-output
  rule.
- Review checklist: compare verdict manifest SHA and observation ID with exact
  candidate handed to the integrator; an older JSON is not transferable.
