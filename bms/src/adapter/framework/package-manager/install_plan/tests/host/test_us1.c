// test_us1.c — US1 (spec.md P1, tasks.md T010-T012) positive-path host
// oracle tests: a compliant fat-ABI arm64 il2cpp APK must be judged
// PLAN_INSTALLABLE, published byte-identical, and leave a queryable
// package/version record.
//
// Independent of US2 (tests/host/test_us2.c, Phase 4): only exercises
// make_us1_positive_fixture() (fixtures_us1.c) against the shared
// evaluate_install_plan()/execute_staging() judgment logic.

#include "test_harness.h"
#include "fixtures_us1.h"
#include "install_plan.h"
#include "sha256.h"

#include <stdio.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>

// Test-local recursive directory removal, used only to keep this test's own
// /tmp staging/final directories from accumulating across runs. Not part of
// the install_plan.c contract under test (execute_staging()'s own
// staging-cleanup path, R4, is exercised separately by US2/T018-T020) —
// this is just test hygiene for the PLAN_INSTALLABLE publish path, which
// intentionally leaves final_dir behind (it is the "installed" result).
static void test_remove_tree(const char* path) {
    struct stat st;
    if (lstat(path, &st) != 0) return;
    if (S_ISDIR(st.st_mode)) {
        DIR* dir = opendir(path);
        if (dir == NULL) return;
        struct dirent* entry;
        char child[4096];
        while ((entry = readdir(dir)) != NULL) {
            if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;
            int n = snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
            if (n < 0 || (size_t)n >= sizeof(child)) continue;
            test_remove_tree(child);
        }
        closedir(dir);
        rmdir(path);
        return;
    }
    unlink(path);
}

// Reads a file fully into `buf` (capacity `cap`), returns the number of
// bytes read, or (size_t)-1 on error. Deliberately re-reads the published
// file from disk (does not trust any in-memory hash) so the sha256
// comparison below is a real "reopen and recompute" check, per FR-008 and
// this task's explicit instruction not to compare only in-memory values.
static size_t read_all(const char* path, unsigned char* buf, size_t cap) {
    FILE* f = fopen(path, "rb");
    if (f == NULL) return (size_t)-1;
    size_t total = fread(buf, 1, cap, f);
    int eof = feof(f);
    int err = ferror(f);
    fclose(f);
    if (err || !eof) return (size_t)-1;
    return total;
}

void run_us1_tests(void) {
    // --- Acceptance Scenario 1: judged PLAN_INSTALLABLE, arm64-v8a chosen ---
    ApkFixture fixture = make_us1_positive_fixture();
    InstallPlan plan = evaluate_install_plan(&fixture);

    CHECK(plan.verdict == PLAN_INSTALLABLE,
          "expected PLAN_INSTALLABLE for compliant fat-ABI fixture, got verdict=%d",
          (int)plan.verdict);
    CHECK(strcmp(plan.primary_abi, "arm64-v8a") == 0,
          "expected primary_abi==\"arm64-v8a\", got \"%s\"", plan.primary_abi);
    CHECK(plan.staging_cleaned == 0,
          "PLAN_INSTALLABLE must not report staging_cleaned==1, got %d", plan.staging_cleaned);

    // --- Acceptance Scenario 2: staging->publish, base.apk byte-identical ---
    StagingState state;
    int rc = execute_staging(&plan, &fixture, &state);

    CHECK(rc == 0, "execute_staging() returned non-zero internal error rc=%d", rc);
    if (rc != 0) {
        // Staging itself failed (e.g. mkdtemp() on a read-only staging
        // base — see HP2_STAGING_BASE in install_plan.c). `state` past
        // this point is the zeroed-out memset from execute_staging(), so
        // state.final_dir is empty and reading it back below would pass a
        // (size_t)-1 error length into sha256() and read out of bounds.
        // Report this scenario as failed and stop here rather than crash.
        return;
    }
    CHECK(state.published == 1, "expected published==1 after staging a PLAN_INSTALLABLE fixture, got %d",
          state.published);
    CHECK(state.cleaned == 0, "expected cleaned==0 on the publish path, got %d", state.cleaned);
    CHECK(state.identity_reverified_ok == 1,
          "expected identity_reverified_ok==1 on an unmutated publish path, got %d", state.identity_reverified_ok);

    struct stat st;
    CHECK(stat(state.staging_dir, &st) != 0,
          "staging_dir must no longer exist after a successful rename-publish: %s", state.staging_dir);
    CHECK(stat(state.final_dir, &st) == 0,
          "final_dir must exist after a successful publish: %s", state.final_dir);

    char final_apk_path[8192];
    int n = snprintf(final_apk_path, sizeof(final_apk_path), "%s/base.apk", state.final_dir);
    CHECK(n > 0 && (size_t)n < sizeof(final_apk_path), "final_apk_path construction failed");

    unsigned char readback[FIXTURE_MAX_BYTES];
    size_t readback_len = read_all(final_apk_path, readback, sizeof(readback));
    CHECK(readback_len == fixture.content_len,
          "readback length %zu != fixture.content_len %zu", readback_len, fixture.content_len);

    // The core FR-008 assertion: recompute sha256 over the bytes actually
    // read back from final_dir/base.apk (a fresh, independent hash — not a
    // reuse of plan.apk_sha256_at_publish) and compare it against a sha256
    // freshly computed over the fixture's original (pre-staging) content.
    unsigned char sha_readback[32];
    unsigned char sha_original[32];
    sha256(readback, readback_len, sha_readback);
    sha256(fixture.content, fixture.content_len, sha_original);

    CHECK(memcmp(sha_readback, sha_original, 32) == 0,
          "published base.apk sha256 does not match input fixture content sha256 (byte-for-byte identity, FR-008)");

    // --- Acceptance Scenario 3: package/version record queryable ---
    CHECK(plan.record_written == 1,
          "expected record_written==1 after a successful PLAN_INSTALLABLE judgment, got %d",
          plan.record_written);
    CHECK(strcmp(plan.package_name, fixture.package_name) == 0,
          "queried package_name \"%s\" != fixture package_name \"%s\"", plan.package_name,
          fixture.package_name);
    CHECK(plan.version_code == fixture.version_code,
          "queried version_code %d != fixture version_code %d", plan.version_code,
          fixture.version_code);
    CHECK(plan.package_name[0] != '\0', "package_name record must be non-empty on success");

    test_remove_tree(state.final_dir);
}
