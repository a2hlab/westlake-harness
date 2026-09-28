// fixtures_us1.h — US1 (spec.md P1, tasks.md T009) positive fixture:
// compliant fat multi-ABI arm64 il2cpp APK. See fixtures_us1.c.

#ifndef HP2_INSTALL_PLAN_TEST_FIXTURES_US1_H
#define HP2_INSTALL_PLAN_TEST_FIXTURES_US1_H

#include "fixtures.h"

#ifdef __cplusplus
extern "C" {
#endif

// spec.md P1 / Acceptance Scenarios 1-3: a single-bundle, fat multi-ABI
// (root lib/arm64-v8a/ + lib/armeabi-v7a/ both present) APK, correctly
// signed (SIG_V2_PLUS), not tampered. Drives US1's three test_us1.c
// scenarios (evaluate -> PLAN_INSTALLABLE + arm64-v8a; execute_staging ->
// byte-identical publish; package/version record queryable).
ApkFixture make_us1_positive_fixture(void);

#ifdef __cplusplus
}
#endif

#endif // HP2_INSTALL_PLAN_TEST_FIXTURES_US1_H
