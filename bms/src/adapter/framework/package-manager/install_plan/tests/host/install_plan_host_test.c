// install_plan_host_test.c — CHECK()-macro test harness skeleton + main()
// for the HP-2 install-plan host oracle.
//
// This file owns:
//   - the shared g_checks/g_failures counter storage (declared extern in
//     test_harness.h, defined here);
//   - main(), which drives the two per-user-story test entry points.
//
// It deliberately does NOT contain any US1 (spec.md P1, compliant fat
// arm64 fixture) or US2 (spec.md P2, negative-test fixtures) scenario
// logic. That belongs to tests/host/test_us1.c and tests/host/test_us2.c,
// authored in later phases (Phase 3 / Phase 4 of tasks.md) — this round
// (Phase 1/2, T001-T008) only builds the shared scaffolding.

#include "test_harness.h"
#include "fixtures.h"
#include "install_plan.h"

int g_checks = 0;
int g_failures = 0;

// Implemented in tests/host/test_us1.c (Phase 3/US1) and
// tests/host/test_us2.c (Phase 4/US2) respectively. Declared here so this
// skeleton compiles and links standalone before those files exist.
extern void run_us1_tests(void);
extern void run_us2_tests(void);

// STUB (placeholder only): weak no-op fallbacks so `run_host_tests.sh` can
// build+link+run this skeleton right now, before tests/host/test_us1.c /
// test_us2.c land. Once those files provide strong (non-weak) definitions
// of run_us1_tests()/run_us2_tests(), the linker prefers those over these
// placeholders automatically — nothing here needs to change.
// Real US1/US2 test content does NOT belong in this file.
//
// POST-HOC FIX (codex headless gate finding #4): these placeholders used to
// be silent no-ops, so if test_us1.c/test_us2.c were ever accidentally
// dropped from the build, the suite would print "0 checks, 0 failures" and
// exit 0 — a silent-green false pass, not a build/link error. They now each
// force a CHECK(0, ...) failure so a missing US1/US2 implementation is a
// guaranteed, loud test failure instead.
__attribute__((weak)) void run_us1_tests(void) {
    CHECK(0, "run_us1_tests: placeholder linked — US1 tests (tasks.md T009-T012) are missing from this build");
}

__attribute__((weak)) void run_us2_tests(void) {
    CHECK(0, "run_us2_tests: placeholder linked — US2 tests (tasks.md T013-T030) are missing from this build");
}

int main(void) {
    run_us1_tests();
    run_us2_tests();

    printf("HP-2 install-plan host oracle: %d checks, %d failures\n", g_checks, g_failures);
    // POST-HOC FIX (codex headless gate finding #4): a suite that ran zero
    // checks is not a pass, even if g_failures==0 — it means something
    // (fixtures/test files) silently failed to link/run. Require a sane
    // minimum so an empty run is a hard failure, not a silent green.
    if (g_checks < 10) {
        fprintf(stderr, "FAIL: only %d checks ran — suspiciously low, treating as failure (not a real pass)\n",
                g_checks);
        return 1;
    }
    return g_failures == 0 ? 0 : 1;
}
