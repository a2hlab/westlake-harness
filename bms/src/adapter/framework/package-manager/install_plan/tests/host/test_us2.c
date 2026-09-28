// test_us2.c — spec.md User Story 2 (P2) negative-test + mutant-facing
// scenarios for the HP-2 install-plan host oracle.
//
// Covers tasks.md T014-T021: 4 negative-fixture Acceptance Scenarios
// (tampered / multi-APK / AAB-nested / empty-native) each fail-closed and
// zero-residue (T014-T018), plus 3 Edge Cases (TOCTOU concurrent replace,
// cleanup idempotency, repeated submission consistency; T019-T021).
//
// Deliberately independent of test_us1.c / fixtures_us1.c — only reads
// fixtures.h's make_base_fixture()-derived builders from fixtures_us2.h and
// the install_plan.h contract, per spec.md "US2 Independent Test".

#include "test_harness.h"
#include "fixtures_us2.h"
#include "fixtures.h"
#include "install_plan.h"

#include <errno.h>
#include <string.h>
#include <sys/stat.h>

// --- T018: zero-residue assertion helper, shared by T014-T017 --------------
//
// Checks the real filesystem (stat()/errno==ENOENT), not just the in-memory
// StagingState.cleaned flag — a mutant (e.g. MUTANT_STAGING_CLEANUP) could
// set cleaned=1 without actually removing the directory, and this helper
// must be able to catch that.
static void assert_zero_residue(const StagingState* state, const char* scenario) {
    struct stat st;

    int staging_rc = stat(state->staging_dir, &st);
    CHECK(staging_rc != 0 && errno == ENOENT,
          "%s: staging_dir '%s' must not exist on disk after REJECT (stat rc=%d errno=%d)",
          scenario, state->staging_dir, staging_rc, errno);

    int final_rc = stat(state->final_dir, &st);
    CHECK(final_rc != 0 && errno == ENOENT,
          "%s: final_dir '%s' must not exist on disk after REJECT (stat rc=%d errno=%d)",
          scenario, state->final_dir, final_rc, errno);
}

// Runs one negative fixture end-to-end (evaluate -> execute_staging) and
// asserts: the expected verdict, staging_cleaned==1, execute_staging()
// itself reports success (rc==0, published==0, cleaned==1), and zero
// residue on disk. Shared by T014-T017.
static void run_reject_scenario(const char* scenario, ApkFixture* fixture,
                                 PlanVerdict expected_verdict) {
    InstallPlan plan = evaluate_install_plan(fixture);
    CHECK(plan.verdict == expected_verdict,
          "%s: expected verdict %d, got %d", scenario, (int)expected_verdict, (int)plan.verdict);
    CHECK(plan.staging_cleaned == 1, "%s: plan.staging_cleaned must be 1", scenario);
    CHECK(plan.record_written == 0, "%s: REJECT verdict must not report record_written", scenario);

    StagingState state;
    int rc = execute_staging(&plan, fixture, &state);
    CHECK(rc == 0, "%s: execute_staging() must succeed on the cleanup path (rc=%d)", scenario, rc);
    CHECK(state.published == 0, "%s: REJECT path must not publish", scenario);
    CHECK(state.cleaned == 1, "%s: REJECT path must report cleaned=1", scenario);
    // codex headless gate round 3 (contract-drift finding): a fixture
    // already rejected at evaluate_install_plan() time (verdict!=
    // PLAN_INSTALLABLE) must report identity_reverified_ok==0 — the
    // staging-time re-check is not applicable here (it never ran), it is
    // NOT "1 because these particular bytes happen to still hash the
    // same". Round 3 caught exactly this drift: it used to read 1 for
    // untouched-content REJECT fixtures like T015's multi-apk case.
    CHECK(state.identity_reverified_ok == 0,
          "%s: identity_reverified_ok must be 0 on a fixture rejected before the staging-time re-check was reached",
          scenario);

    assert_zero_residue(&state, scenario);
}

// --- T014: tampered bytes (verify-time A, publish-time B) -> REJECT_TAMPERED
static void test_us2_tampered_rejected(void) {
    ApkFixture fixture = make_tampered_fixture();
    run_reject_scenario("T014 tampered-after-verify", &fixture, REJECT_TAMPERED);
}

// --- T015: apk_count=2 -> REJECT_MULTI_APK
static void test_us2_multi_apk_rejected(void) {
    ApkFixture fixture = make_multi_apk_fixture();
    CHECK(fixture.apk_count == 2, "T015: fixture sanity, apk_count should be 2");
    run_reject_scenario("T015 multi-apk", &fixture, REJECT_MULTI_APK);
}

// --- T016: AAB-nested (non-root lib/<abi>/) -> REJECT_NO_ARM64_SLICE
static void test_us2_aab_nested_rejected(void) {
    ApkFixture fixture = make_aab_nested_fixture();
    CHECK(fixture.abi_layout == ABI_LAYOUT_AAB_NESTED, "T016: fixture sanity, layout should be AAB_NESTED");
    run_reject_scenario("T016 aab-nested", &fixture, REJECT_NO_ARM64_SLICE);
}

// --- T017: empty native-stage -> REJECT_EMPTY_NATIVE
static void test_us2_empty_native_rejected(void) {
    ApkFixture fixture = make_empty_native_fixture();
    CHECK(fixture.abi_layout == ABI_LAYOUT_EMPTY_NATIVE, "T017: fixture sanity, layout should be EMPTY_NATIVE");
    run_reject_scenario("T017 empty-native", &fixture, REJECT_EMPTY_NATIVE);
}

// --- T019: Edge Case - concurrent replace (TOCTOU) between verify and
// publish must still land on REJECT_TAMPERED, not just "some rejection".
static void test_us2_concurrent_replace_toctou(void) {
    ApkFixture fixture = make_concurrent_replace_fixture();
    CHECK(fixture.tampered_after_verify == 1,
          "T019: fixture sanity, must model a verify/publish byte swap");
    CHECK(memcmp(fixture.content, fixture.tampered_content, fixture.content_len) != 0,
          "T019: fixture sanity, verify-time and publish-time bytes must actually differ");
    run_reject_scenario("T019 toctou-concurrent-replace", &fixture, REJECT_TAMPERED);
}

// --- T020: Edge Case - cleanup path called twice on the same StagingState
// must be idempotent: second call does not error, does not crash, and the
// state is still "cleaned" with zero residue.
static void test_us2_cleanup_idempotent(void) {
    ApkFixture fixture = make_multi_apk_fixture();  // any REJECT-verdict fixture works
    InstallPlan plan = evaluate_install_plan(&fixture);
    CHECK(plan.verdict == REJECT_MULTI_APK, "T020: fixture sanity, expected REJECT_MULTI_APK");

    StagingState state;
    int rc1 = execute_staging(&plan, &fixture, &state);
    CHECK(rc1 == 0, "T020: first execute_staging() (which cleans up) must succeed (rc=%d)", rc1);
    CHECK(state.cleaned == 1, "T020: state.cleaned must be 1 after first cleanup");
    assert_zero_residue(&state, "T020 first-cleanup");

    // Second call to the *same* production cleanup path on the *same*
    // StagingState (staging_dir already gone). Must not error/crash, and
    // must leave the state consistent (still cleaned==1, still zero
    // residue) — this is the idempotency property research.md R4 commits
    // to ("remove_tree tolerant of ENOENT").
    int rc2 = cleanup_staging(&state);
    CHECK(rc2 == 0, "T020: second cleanup_staging() call must not report an error (rc=%d)", rc2);
    CHECK(state.cleaned == 1, "T020: state.cleaned must still be 1 after second cleanup call");
    CHECK(state.published == 0, "T020: state.published must still be 0 after second cleanup call");
    assert_zero_residue(&state, "T020 second-cleanup");
}

// --- T021: Edge Case - repeated submission of the same fixture (fresh
// install run twice) must not produce inconsistent partial state: both
// runs must independently reach the same verdict and each leave a fully
// clean-or-published state, never a half-done mix.
static void test_us2_repeat_submission_consistent(void) {
    ApkFixture fixture = make_aab_nested_fixture();

    InstallPlan plan_a = evaluate_install_plan(&fixture);
    InstallPlan plan_b = evaluate_install_plan(&fixture);
    CHECK(plan_a.verdict == plan_b.verdict,
          "T021: evaluate_install_plan() must be deterministic across repeated calls on the same fixture");
    CHECK(memcmp(plan_a.apk_sha256_at_verify, plan_b.apk_sha256_at_verify, 32) == 0,
          "T021: apk_sha256_at_verify must be identical across repeated evaluations");

    StagingState state_a;
    StagingState state_b;
    int rc_a = execute_staging(&plan_a, &fixture, &state_a);
    int rc_b = execute_staging(&plan_b, &fixture, &state_b);
    CHECK(rc_a == 0 && rc_b == 0, "T021: both execute_staging() runs must succeed (rc_a=%d rc_b=%d)", rc_a, rc_b);

    // Each run's own state must be fully one thing or the other, never a
    // mix (FR-004's "no partial-publish state" in data-model.md terms).
    CHECK((state_a.published == 1) != (state_a.cleaned == 1),
          "T021: run A's state must be exactly one of published/cleaned, not both/neither");
    CHECK((state_b.published == 1) != (state_b.cleaned == 1),
          "T021: run B's state must be exactly one of published/cleaned, not both/neither");
    CHECK(state_a.published == state_b.published && state_a.cleaned == state_b.cleaned,
          "T021: repeated submission of the same fixture must reach the same disposition (published/cleaned) both times");

    // AAB-nested is a REJECT_NO_ARM64_SLICE fixture, so both independent
    // runs must land on zero residue, not just "some" residue-free state.
    assert_zero_residue(&state_a, "T021 run-a");
    assert_zero_residue(&state_b, "T021 run-b");
}

// --- T027: judgment-order priority ("first hit wins", contracts/
// install_plan_contract.md "判定顺序 (MUST)"). Phase 5 Polish fix for an
// adversarial verify-us1 finding: prior to this task, no fixture in the
// suite violated more than one rule at once, so a refactor that silently
// reordered R1/R2/R3 inside evaluate_install_plan() would not have been
// caught by any test (confirmed by manually swapping the R1/R2 checks and
// observing 80/0 still passing). These two scenarios close that gap.
//
// R1 must fire before R2 and R3: a fixture violating all three at once
// must still be judged REJECT_MULTI_APK, not REJECT_NO_ARM64_SLICE or
// REJECT_UNVERIFIED.
static void test_us2_priority_r1_before_r2_and_r3(void) {
    ApkFixture fixture = make_multi_apk_and_other_violations_fixture();
    CHECK(fixture.apk_count == 2 && fixture.abi_layout == ABI_LAYOUT_AAB_NESTED &&
              fixture.signature_scheme == SIG_NONE,
          "T027a: fixture sanity, must simultaneously violate R1+R2+R3");
    run_reject_scenario("T027a priority-r1-before-r2-and-r3", &fixture, REJECT_MULTI_APK);
}

// R2 must fire before R3: an R1-compliant fixture violating both R2 and R3
// at once must be judged REJECT_NO_ARM64_SLICE, not REJECT_UNVERIFIED.
static void test_us2_priority_r2_before_r3(void) {
    ApkFixture fixture = make_aab_nested_and_unverified_fixture();
    CHECK(fixture.apk_count == 1 && fixture.abi_layout == ABI_LAYOUT_AAB_NESTED &&
              fixture.signature_scheme == SIG_NONE,
          "T027b: fixture sanity, must be R1-compliant but violate both R2+R3");
    run_reject_scenario("T027b priority-r2-before-r3", &fixture, REJECT_NO_ARM64_SLICE);
}

// --- T028-T030: codex headless gate findings (post-hoc fix round) ---------
//
// The Phase 5 Polish round's Claude-side adversarial-verify agents (verify-
// us1/verify-us2/independent-run) reported NO_ISSUES_FOUND or only the T027
// priority-order gap. A subsequent independent codex headless gate run
// found three additional real gaps these tests close. See install_plan.c's
// top-of-file "POST-HOC FIXES" note and HANDOFF.md for the full writeup.

// --- T028: the REAL TOCTOU scenario — mutate the fixture AFTER
// evaluate_install_plan() has already returned PLAN_INSTALLABLE, THEN call
// execute_staging(). This is what a concurrent-replace attack actually looks
// like (verify a file, then have its bytes change before it's copied); the
// pre-existing T019 "concurrent replace" fixture only ever set
// tampered_after_verify=1 *before* evaluate_install_plan() ran, so
// evaluate_install_plan() itself already caught it — execute_staging()'s own
// re-verification (the actual fix here) was never exercised by any test.
static void test_us2_post_evaluation_mutation_toctou(void) {
    ApkFixture fixture = make_base_fixture();

    InstallPlan plan = evaluate_install_plan(&fixture);
    CHECK(plan.verdict == PLAN_INSTALLABLE,
          "T028: fixture sanity, must evaluate as installable before mutation");

    // Mutate the SAME fixture's content in place — no tampered_after_verify
    // flag involved at all — modeling bytes changing on disk between
    // verification and copy, after the decision has already been made.
    fixture.content[0] = (unsigned char)(fixture.content[0] ^ 0xFFu);

    StagingState state;
    int rc = execute_staging(&plan, &fixture, &state);
    CHECK(rc == 0, "T028: execute_staging() must complete the fail-closed cleanup path (rc=%d)", rc);
    CHECK(state.published == 0,
          "T028: post-evaluation mutation MUST NOT be published even though plan.verdict was PLAN_INSTALLABLE");
    CHECK(state.cleaned == 1, "T028: post-evaluation mutation path must report cleaned=1");
    CHECK(state.identity_reverified_ok == 0,
          "T028: identity_reverified_ok must be 0 — the staging-time re-check is what caught this, not plan.verdict");
    assert_zero_residue(&state, "T028 post-evaluation-mutation-toctou");
}

// --- T029: FR-001's second half — apk_count==1 but bundle_path_count!=1.
static void test_us2_bundle_path_violation_rejected(void) {
    ApkFixture fixture = make_bundle_path_violation_fixture();
    CHECK(fixture.apk_count == 1 && fixture.bundle_path_count == 2,
          "T029: fixture sanity, apk_count==1 but bundle_path_count==2");
    run_reject_scenario("T029 bundle-path-violation", &fixture, REJECT_MULTI_APK);
}

// --- T030: R3's SIG_NONE check in isolation (R1/R2-compliant), so deleting
// it can no longer hide behind an earlier rule already having rejected.
static void test_us2_unverified_only_rejected(void) {
    ApkFixture fixture = make_unverified_only_fixture();
    CHECK(fixture.apk_count == 1 && fixture.bundle_path_count == 1 &&
              fixture.abi_layout == ABI_LAYOUT_ARM64_FAT && fixture.signature_scheme == SIG_NONE,
          "T030: fixture sanity, R1/R2-compliant, violates ONLY R3 (SIG_NONE)");
    run_reject_scenario("T030 unverified-only", &fixture, REJECT_UNVERIFIED);
}

void run_us2_tests(void) {
    test_us2_tampered_rejected();
    test_us2_multi_apk_rejected();
    test_us2_aab_nested_rejected();
    test_us2_empty_native_rejected();
    test_us2_concurrent_replace_toctou();
    test_us2_cleanup_idempotent();
    test_us2_repeat_submission_consistent();
    test_us2_priority_r1_before_r2_and_r3();
    test_us2_priority_r2_before_r3();
    test_us2_post_evaluation_mutation_toctou();
    test_us2_bundle_path_violation_rejected();
    test_us2_unverified_only_rejected();
}
