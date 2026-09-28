#ifndef TEST_UTIL_H
#define TEST_UTIL_H

#include <stdio.h>
#include <stdlib.h>

static int g_test_failures = 0;

#define CHECK(cond, fmt, ...) do { \
    if (!(cond)) { \
        fprintf(stderr, "  FAIL: " fmt " (at %s:%d)\n", ##__VA_ARGS__, __FILE__, __LINE__); \
        g_test_failures++; \
    } \
} while (0)

#define TEST_MAIN_EXIT() do { \
    if (g_test_failures > 0) { \
        fprintf(stderr, "=== %d check(s) FAILED ===\n", g_test_failures); \
        return 1; \
    } \
    fprintf(stdout, "=== ALL CHECKS PASSED ===\n"); \
    return 0; \
} while (0)

#endif /* TEST_UTIL_H */
