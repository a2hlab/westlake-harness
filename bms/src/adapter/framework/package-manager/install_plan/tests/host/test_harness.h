// test_harness.h — shared CHECK() macro + counters for the HP-2
// install-plan host oracle test suite.
//
// Factored out of install_plan_host_test.c so that run_us1_tests()
// (tests/host/test_us1.c, Phase 3/US1) and run_us2_tests()
// (tests/host/test_us2.c, Phase 4/US2) can #include this header and
// contribute CHECK()s to the same single "N checks, M failures" summary
// that main() prints, without needing to link a separate counter set per
// file. Style follows
// 02.unity.cardwords/adapter/framework/app-native-loader/tests/host/app_native_loader_host_test.c's
// CHECK() convention.

#ifndef HP2_INSTALL_PLAN_TEST_HARNESS_H
#define HP2_INSTALL_PLAN_TEST_HARNESS_H

#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

extern int g_checks;
extern int g_failures;

#ifdef __cplusplus
}
#endif

#define CHECK(condition, ...)                                                   \
    do {                                                                        \
        ++g_checks;                                                             \
        if (!(condition)) {                                                     \
            ++g_failures;                                                       \
            fprintf(stderr, "FAIL %s:%d: ", __func__, __LINE__);              \
            fprintf(stderr, __VA_ARGS__);                                       \
            fputc('\n', stderr);                                                \
        }                                                                       \
    } while (0)

#endif // HP2_INSTALL_PLAN_TEST_HARNESS_H
