// fixtures_us2.c — US2 (spec.md P2) negative-test ApkFixture builders.
// See fixtures_us2.h for the per-builder rationale (tasks.md T013).

#include "fixtures_us2.h"
#include "fixtures.h"

ApkFixture make_tampered_fixture(void) {
    ApkFixture fixture = make_base_fixture();

    // Verify-time content stays whatever make_base_fixture() set (seed
    // 0x5A). Publish-time content is a distinct, differently-seeded buffer
    // of the same length, so the two sha256 digests are guaranteed to
    // differ (content actually changes, not just re-hashed identically).
    fixture.tampered_after_verify = 1;
    fixture.tampered_content_len = fixture.content_len;
    fill_deterministic_content(fixture.tampered_content, fixture.tampered_content_len, 0xA5u);

    return fixture;
}

ApkFixture make_multi_apk_fixture(void) {
    ApkFixture fixture = make_base_fixture();
    fixture.apk_count = 2;
    return fixture;
}

ApkFixture make_aab_nested_fixture(void) {
    ApkFixture fixture = make_base_fixture();
    fixture.abi_layout = ABI_LAYOUT_AAB_NESTED;
    return fixture;
}

ApkFixture make_empty_native_fixture(void) {
    ApkFixture fixture = make_base_fixture();
    fixture.abi_layout = ABI_LAYOUT_EMPTY_NATIVE;
    return fixture;
}

// T027 (Phase 5 Polish fix, adversarial verify-us1 finding): violates R1
// (apk_count!=1), R2 (AAB_NESTED) and R3 (SIG_NONE) simultaneously. The
// contract's "first hit wins" rule means R1 must decide this one.
ApkFixture make_multi_apk_and_other_violations_fixture(void) {
    ApkFixture fixture = make_base_fixture();
    fixture.apk_count = 2;                          // violates R1
    fixture.abi_layout = ABI_LAYOUT_AAB_NESTED;      // also violates R2
    fixture.signature_scheme = SIG_NONE;             // also violates R3
    return fixture;
}

// T027 (Phase 5 Polish fix, adversarial verify-us1 finding): R1-compliant
// (apk_count==1) but violates both R2 (AAB_NESTED) and R3 (SIG_NONE)
// simultaneously. The contract's "first hit wins" rule means R2 must
// decide this one (REJECT_NO_ARM64_SLICE), not R3 (REJECT_UNVERIFIED).
ApkFixture make_aab_nested_and_unverified_fixture(void) {
    ApkFixture fixture = make_base_fixture();
    fixture.abi_layout = ABI_LAYOUT_AAB_NESTED;      // violates R2
    fixture.signature_scheme = SIG_NONE;             // also violates R3
    return fixture;
}

// codex headless gate finding #3 (post-hoc fix): apk_count==1 alone, with
// bundle_path_count=2 — the half of FR-001's guard the original R1 check
// (apk_count-only) could not represent or catch.
ApkFixture make_bundle_path_violation_fixture(void) {
    ApkFixture fixture = make_base_fixture();
    fixture.bundle_path_count = 2;
    return fixture;
}

// codex headless gate finding #2 (post-hoc fix): R1- and R2-compliant,
// violates ONLY R3 (SIG_NONE) — isolates the "no signature" branch so it is
// actually the first (and only) hit, unlike every other SIG_NONE fixture in
// this suite (T027a/T027b) which also violate R1 or R2.
ApkFixture make_unverified_only_fixture(void) {
    ApkFixture fixture = make_base_fixture();
    fixture.signature_scheme = SIG_NONE;
    return fixture;
}

ApkFixture make_concurrent_replace_fixture(void) {
    ApkFixture fixture = make_base_fixture();

    // Distinct seeds from make_tampered_fixture() (0x11 / 0xEE rather than
    // 0x5A / 0xA5) purely so this fixture is a separately-constructed
    // instance for T019's TOCTOU edge-case assertion, not aliased state
    // shared with T014's tampered-byte scenario.
    fill_deterministic_content(fixture.content, fixture.content_len, 0x11u);
    fixture.tampered_after_verify = 1;
    fixture.tampered_content_len = fixture.content_len;
    fill_deterministic_content(fixture.tampered_content, fixture.tampered_content_len, 0xEEu);

    return fixture;
}
