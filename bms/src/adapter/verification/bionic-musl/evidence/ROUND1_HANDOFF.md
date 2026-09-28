# M05 Round-One Handoff

- Branch: `lane/m05-bionic-musl-audit-r1`
- Base: `c919f07c347ceba092b6b5112cb9daa1eefaec15`
- Integrator contract correction: `main@2a4f426` supplied by the integrator;
  this lane was not merged or rebased.
- Owned paths changed:
  `adapter/verification/bionic-musl/**` and
  `adapter/scripts/ci/bionic_musl_validate_baseline.py`.

## Boundary

- Boundary: independent Bionic/Musl/Unity reliability evidence and promotion
  control.
- Android behavior: exact unchanged APK/Unity bytes retain Bionic-side
  generation and runtime identity; unsupported or mismatched evidence fails
  closed.
- OpenHarmony mapping: exact loader/Musl/typed-bridge/provider evidence is
  normalized without changing any OH service or product implementation.
- Fix layer: M05-only schema, scanner/validator, synthetic controls, risk ledger
  and evidence request. No product ABI or shared schema is defined.

## Evidence target

- What this proves: the M05 report format and semantic validator preserve the
  first missing-input gate, distinguish offline `NativeGenerationReceiptV1`
  from the child/spawn runtime-ready binding, require exactly 22
  current-generation red-team gates, verify repository-local hashes and reject
  promotion of synthetic evidence.
- What this does not prove: any M04 implementation, current candidate, S1-S7,
  runtime child, device, Unity, first frame, rendering, interaction, resource
  convergence or 5/30-minute stability.

## Environment

- Host: `Darwin 25.4.0 arm64`.
- Device: none; device access count is zero.
- Tool path: `/usr/bin/python3` (`Python 3.9.6`); installed `jsonschema 4.25.1`
  was used only for an additional schema conformance check.
- Artifact path: `adapter/verification/bionic-musl/**` and
  `adapter/scripts/ci/bionic_musl_validate_baseline.py`.
- App: none; no APK or product DSO was loaded.

## Status

- Label: `real_impl`.
- Why: the verifier contract has an executable local-hash/semantic validator,
  one non-promotable synthetic positive and 15 discriminating tests. This label
  applies only to the verifier, not to candidate bytes or device behavior.

## Proven

- The checked-in current report is schema-valid and semantically valid while
  remaining `assessment=not_evaluated`, `device_admission=false` at
  `F00_REQUIRED_LOCAL_INPUTS`.
- A complete local synthetic report with exactly 22 synthetic gates passes but
  cannot be promoted.
- Single-variable mutants for 21/22 gates, duplicate gate IDs, stale generation,
  hash drift, sibling-project path escape, self-test promotion, offline/runtime
  receipt conflation, wrong child generation and wrong receipt schema fail.
- An offline-only report can be preserved as valid evidence, but runtime gates
  cannot run and admission stays false until `ChildRuntimeReadyReceiptV1` binds
  `SpawnBirthReceiptV1`, pid, startSeq, generation and epoch.
- HP-9/02d and all product/system-service sources were not consumed or changed.

## Not proven

- The missing canonical bootstrap or its S1-S7 definitions.
- The missing canonical 22-gate source or any transfer of its old PASS.
- Any `NativeGenerationReceiptV1`, `ChildRuntimeReadyReceiptV1` or
  `SpawnBirthReceiptV1` for current product bytes.
- Any host sanitizer result, 10M operation stress, ARM64 weak-order result,
  target device behavior, Unity/first-frame result or bounded soak.
- `device_verified`; this remains false.

## Failed

- The required bootstrap, canonical 22-gate source and M04 offline receipt are
  absent, so F00 cannot execute and current admission is denied.
- The explicit current-report `--require-admission` negative returned rc=1 with
  `required admission was not achieved`, as expected.
- The first expanded unit-test run was 14/15: the validator correctly rejected a
  self-test runtime-ready request, but the test expected the wrong diagnostic
  substring. The assertion was corrected; the rerun is 15/15.

## Next evidence

- Command: `python3 adapter/scripts/ci/bionic_musl_validate_baseline.py --require-offline-ready adapter/verification/bionic-musl/baselines/<current-candidate>.json`
- Expected output: rc=0 only after the canonical bootstrap/S1-S7, all 22
  current-generation red-team gates, `NativeGenerationReceiptV1` and every
  closure/identity/namespace/sealed-FD gate are present and pass.
- If it fails: preserve the first exact diagnostic and receipt hashes; do not
  attach to a child or request device execution. After offline PASS, run the
  separate `--require-runtime-ready` gate before attach.

## Shim/stub/bypass inventory

- Item: none added.
- Owner: M05 verifier owns only synthetic text fixtures.
- Why it exists: the fixtures discriminate validator behavior and are explicitly
  marked non-product/non-promotable.
- Removal condition: retain as regression controls; replace no product input.
- Test coverage: 15 unit tests plus schema and CLI checks.
- App-specific or common: verifier-only, no app-specific or common-adapter shim.

## Memory/skill/CI/review updates

- Memory: no external memory or sibling project was read or updated.
- Skill: WestLake engineering discipline enforced evidence labels, fail-closed
  handoff and no host-to-device promotion. `design-check` five questions: no ART
  change, no BCP change, no product fix, boot rebuild not applicable, truly-cold
  explicitly not proven. Its external 16.13 mechanical script was not run
  because the lane contract permits only current-worktree inputs.
- CI: added the owned `bionic_musl_validate_baseline.py` entry point; shared CI
  wiring was not changed.
- Review checklist: product source, shared schema/build/coordination/Kanban,
  main, other worktrees, 5EAB5, HP-9/02d and OH system-service patches untouched;
  no stub, bypass, ELF, object, log or generated out directory is delivered.
