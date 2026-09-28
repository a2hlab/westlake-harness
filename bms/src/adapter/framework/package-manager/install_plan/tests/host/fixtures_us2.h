// fixtures_us2.h — US2 (spec.md P2) negative-test ApkFixture builders.
//
// Each builder starts from fixtures.h's make_base_fixture() ("everything is
// fine") and overrides only the field(s) relevant to the one rule under
// test (research.md R1/R2/R3), per data-model.md. See tasks.md T013.

#ifndef HP2_INSTALL_PLAN_TEST_FIXTURES_US2_H
#define HP2_INSTALL_PLAN_TEST_FIXTURES_US2_H

#include "install_plan.h"

#ifdef __cplusplus
extern "C" {
#endif

// spec.md P2 Acceptance Scenario 1 / research.md R3: verify-time content is
// A, publish-time content is B (tampered_after_verify=1 with a distinct
// tampered_content). Expected verdict: REJECT_TAMPERED.
ApkFixture make_tampered_fixture(void);

// spec.md P2 Acceptance Scenario 2 / research.md R1: apk_count=2 (single-APK
// guard). Expected verdict: REJECT_MULTI_APK.
ApkFixture make_multi_apk_fixture(void);

// spec.md P2 Acceptance Scenario 3 / research.md R2: native libs present but
// only under a non-root prefix (AAB/#16 shape). Expected verdict:
// REJECT_NO_ARM64_SLICE.
ApkFixture make_aab_nested_fixture(void);

// spec.md P2 Acceptance Scenario 4 / research.md R2 variant: native
// extraction result is empty. Expected verdict: REJECT_EMPTY_NATIVE.
ApkFixture make_empty_native_fixture(void);

// spec.md Edge Cases #2 (TOCTOU) / tasks.md T019: a fixture variant built
// with deliberately distinct "content" (verify-time, byte A) and
// "tampered_content" (publish-time, byte B) seeds, modeling a concurrent
// replace between verify and publish. Distinct helper from
// make_tampered_fixture() only so T019's test can construct/assert on its
// own instance independent of T014's; the judgment path exercised is the
// same R3 TOCTOU check.
ApkFixture make_concurrent_replace_fixture(void);

// contracts/install_plan_contract.md "判定顺序 (MUST)": R1 -> R2 -> R3,
// first-hit-wins when a single input simultaneously violates more than one
// rule. Previously ungenerated combined-violation fixture (adversarial
// verify-us1 finding, Phase 5 Polish fix, T027): apk_count=2 (violates R1)
// AND abi_layout=AAB_NESTED (violates R2) AND signature_scheme=SIG_NONE
// (violates R3), all at once. Expected verdict MUST be REJECT_MULTI_APK
// (R1 fires first) -- this is the fixture the contract explicitly calls
// for ("供测试断言...最先命中哪条") that no prior task actually built.
ApkFixture make_multi_apk_and_other_violations_fixture(void);

// contracts/install_plan_contract.md "判定顺序 (MUST)": R2 must fire before
// R3. Single-APK (R1-compliant) fixture that violates both R2 (AAB-nested,
// no root-level arm64-v8a slice) and R3 (SIG_NONE, unverified) at once.
// Expected verdict MUST be REJECT_NO_ARM64_SLICE (R2 fires before R3).
ApkFixture make_aab_nested_and_unverified_fixture(void);

// codex headless gate finding #3 (post-hoc fix): FR-001's "apkCount!=1 ||
// bundlePaths.size()!=1" has two independent halves. apk_count==1 here, but
// bundle_path_count=2 — a shape the original R1 check couldn't even
// represent before install_plan.h gained the bundle_path_count field.
// Expected verdict: REJECT_MULTI_APK.
ApkFixture make_bundle_path_violation_fixture(void);

// codex headless gate finding #2 (post-hoc fix): every other SIG_NONE
// fixture in this suite also violates an earlier rule (R1 or R2), so R3's
// "no signature" branch was never the *first* hit and deleting it entirely
// left the suite green. This fixture is R1- and R2-compliant and violates
// ONLY R3 (SIG_NONE), isolating that check. Expected verdict:
// REJECT_UNVERIFIED.
ApkFixture make_unverified_only_fixture(void);

#ifdef __cplusplus
}
#endif

#endif // HP2_INSTALL_PLAN_TEST_FIXTURES_US2_H
