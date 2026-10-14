// install_plan.c — HP-2 host-only install-plan judgment + staging model.
//
// Implements the two contract functions declared in install_plan.h, per
// specs/001-hp2-apk-install/contracts/install_plan_contract.md and the
// R1-R4 rules in specs/001-hp2-apk-install/research.md.
//
// Judgment order (contract, MUST): R1 (single-APK guard) -> R2 (ABI /
// native-stage) -> R3 (signature + apkSha256 identity). First hit wins.
//
// MUTANT HOOKS (tasks.md T022, research.md R6): each fail-closed decision
// below has an `#ifdef MUTANT_<NAME>` inverted branch, compiled in only
// when `run_host_tests.sh` is invoked with `HOST_CFLAGS="-DMUTANT_<NAME>"`.
// Normal builds (no -DMUTANT_*) are completely unaffected.
//   - MUTANT_MULTI_APK:       R1 single-APK guard never rejects.
//   - MUTANT_NO_ARM64_SLICE:  AAB-nested layout is (wrongly) treated as a
//                             found arm64-v8a slice.
//   - MUTANT_TAMPERED:        R3 verify-vs-publish sha256 comparison is
//                             skipped (always treated as consistent).
//   - MUTANT_STAGING_CLEANUP: R4 cleanup path reports cleaned=1 without
//                             actually removing the staging directory
//                             (residue left behind).
//   - MUTANT_UNVERIFIED:      R3 "no signature" fail-closed check is skipped
//                             (SIG_NONE silently treated as verified).
//
// POST-HOC FIXES (codex headless gate, this round's independent review,
// found real gaps the earlier Claude-side adversarial-verify pass missed):
//   1. execute_staging() now independently recomputes sha256 over the bytes
//      it is about to publish and compares against plan->apk_sha256_at_verify
//      immediately before the publish/cleanup decision, instead of trusting
//      plan->verdict alone. This closes a real TOCTOU gap: a caller that
//      calls evaluate_install_plan() (getting PLAN_INSTALLABLE), then
//      mutates fixture->content in place, then calls execute_staging(),
//      would previously have had the mutated bytes published anyway.
//   2. R1's single-APK guard now also checks bundle_path_count!=1 (FR-001's
//      second half), not just apk_count!=1.
//   3. R3's SIG_NONE check gained its own MUTANT_UNVERIFIED hook and (see
//      fixtures_us2.c) a dedicated isolated fixture, since previously every
//      SIG_NONE fixture in the suite also violated an earlier rule, so
//      deleting the SIG_NONE check entirely still left the suite 98/0 green.

#include "install_plan.h"
#include "sha256.h"

#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

// --- internal helpers -----------------------------------------------------

static int abi_layout_selects_arm64(AbiLayout layout) {
#ifdef MUTANT_NO_ARM64_SLICE
    // MUTANT: AAB-nested (non-root lib/<abi>/) is wrongly accepted as if a
    // root-level arm64-v8a slice had been found. research.md R2 / spec.md
    // P2 Acceptance Scenario 3 requires this to stay REJECT_NO_ARM64_SLICE
    // in a real build — this branch only exists to prove tests/host/test_us2.c
    // (T016) actually catches the inversion (tasks.md T022, SC-004).
    if (layout == ABI_LAYOUT_AAB_NESTED) {
        return 1;
    }
#endif
    return layout == ABI_LAYOUT_ARM64_FAT || layout == ABI_LAYOUT_ARM64_ONLY;
}

// Recursively removes a directory tree. Tolerant of the path already being
// gone (ENOENT) so that repeated cleanup calls are idempotent (spec.md Edge
// Case: staging interrupted then cleaned up twice, T020).
static int remove_tree(const char* path) {
    struct stat st;
    if (lstat(path, &st) != 0) {
        return (errno == ENOENT) ? 0 : -1;
    }

    if (S_ISDIR(st.st_mode)) {
        DIR* dir = opendir(path);
        if (dir == NULL) {
            return (errno == ENOENT) ? 0 : -1;
        }
        struct dirent* entry;
        char child[PATH_MAX];
        int rc = 0;
        while ((entry = readdir(dir)) != NULL) {
            if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
                continue;
            }
            int n = snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
            if (n < 0 || (size_t)n >= sizeof(child)) {
                rc = -1;
                break;
            }
            if (remove_tree(child) != 0) {
                rc = -1;
                break;
            }
        }
        closedir(dir);
        if (rc != 0) return rc;
        if (rmdir(path) != 0 && errno != ENOENT) return -1;
        return 0;
    }

    if (unlink(path) != 0 && errno != ENOENT) return -1;
    return 0;
}

static int write_all(const char* path, const unsigned char* data, size_t len) {
    FILE* f = fopen(path, "wb");
    if (f == NULL) return -1;
    size_t written = (len == 0) ? 0 : fwrite(data, 1, len, f);
    int close_rc = fclose(f);
    if (written != len || close_rc != 0) return -1;
    return 0;
}

// --- evaluate_install_plan -------------------------------------------------

InstallPlan evaluate_install_plan(const ApkFixture* fixture) {
    InstallPlan plan;
    memset(&plan, 0, sizeof(plan));

    // FR-003: apkSha256 is computed at "verify time" up front, regardless
    // of which rule ultimately decides the verdict.
    sha256(fixture->content, fixture->content_len, plan.apk_sha256_at_verify);

    // R1: single-APK guard. FR-001 / spec.md: "apkCount != 1 || bundlePaths
    // .size() != 1" — two independent conditions in the real active chain,
    // checked together here (codex headless gate finding #3 fix).
#ifndef MUTANT_MULTI_APK
    if (fixture->apk_count != 1 || fixture->bundle_path_count != 1) {
        plan.verdict = REJECT_MULTI_APK;
        plan.staging_cleaned = 1;
        return plan;
    }
#endif
    // MUTANT_MULTI_APK: guard above is compiled out entirely, so
    // apk_count!=1 (or bundle_path_count!=1) falls through into R2/R3 as if
    // it were a normal single-APK submission (tasks.md T022 / T015 must
    // catch this).

    // R2: ABI / native-stage judgment.
    if (fixture->abi_layout == ABI_LAYOUT_EMPTY_NATIVE) {
        plan.verdict = REJECT_EMPTY_NATIVE;
        plan.staging_cleaned = 1;
        return plan;
    }
    if (!abi_layout_selects_arm64(fixture->abi_layout)) {
        // Covers ABI_LAYOUT_V7A_ONLY and ABI_LAYOUT_AAB_NESTED: only a
        // root-level lib/arm64-v8a/ prefix selects a primary ABI (R2
        // rationale) — anything else is "no slice", not a silent fallback.
        plan.verdict = REJECT_NO_ARM64_SLICE;
        plan.staging_cleaned = 1;
        return plan;
    }

    // R3: signature verification, then apkSha256 identity across the
    // verify -> publish window (TOCTOU detection).
#ifndef MUTANT_UNVERIFIED
    if (fixture->signature_scheme == SIG_NONE) {
        plan.verdict = REJECT_UNVERIFIED;
        plan.staging_cleaned = 1;
        return plan;
    }
#endif
    // MUTANT_UNVERIFIED: guard above is compiled out entirely, so SIG_NONE
    // silently falls through as if it were verified (codex headless gate
    // finding #2 — an isolated make_unverified_only_fixture() in
    // fixtures_us2.c + test_us2.c must catch this).

    const unsigned char* publish_bytes = fixture->tampered_after_verify
                                              ? fixture->tampered_content
                                              : fixture->content;
    size_t publish_len = fixture->tampered_after_verify ? fixture->tampered_content_len
                                                         : fixture->content_len;
    sha256(publish_bytes, publish_len, plan.apk_sha256_at_publish);

#ifndef MUTANT_TAMPERED
    if (memcmp(plan.apk_sha256_at_verify, plan.apk_sha256_at_publish, 32) != 0) {
        plan.verdict = REJECT_TAMPERED;
        plan.staging_cleaned = 1;
        return plan;
    }
#endif
    // MUTANT_TAMPERED: comparison above compiled out entirely, so a
    // verify-time/publish-time byte swap silently falls through to
    // PLAN_INSTALLABLE (tasks.md T022 / T014 & T019 must catch this).

    plan.verdict = PLAN_INSTALLABLE;
    plan.staging_cleaned = 0;
    strncpy(plan.primary_abi, "arm64-v8a", sizeof(plan.primary_abi) - 1);
    plan.primary_abi[sizeof(plan.primary_abi) - 1] = '\0';

    // T012 (US1 Acceptance Scenario 3, FR-008): package/version record is
    // only considered "written" on the accept path; REJECT paths leave
    // plan.record_written at its memset-zero default.
    strncpy(plan.package_name, fixture->package_name, sizeof(plan.package_name) - 1);
    plan.package_name[sizeof(plan.package_name) - 1] = '\0';
    plan.version_code = fixture->version_code;
    plan.record_written = 1;
    return plan;
}

// Idempotent staging-cleanup helper (research.md R4: "可以显式调用同一个清理
// 路径断言其幂等/完整"). Recursively removes state->staging_dir (tolerant of
// it already being gone) and marks state->cleaned=1. Exposed as its own
// function — rather than inlined only inside execute_staging()'s REJECT
// branch — specifically so tasks.md T020 can invoke the exact same
// production cleanup path twice on one StagingState and assert the second
// call is a no-op success (idempotent), not just re-run execute_staging()
// end-to-end (which would mkdtemp a brand-new directory each time and not
// actually re-exercise cleanup on the *same* state).
int cleanup_staging(StagingState* state) {
    if (state == NULL) return -1;
#ifdef MUTANT_STAGING_CLEANUP
    // MUTANT: claim success without touching the filesystem — staging_dir
    // is left behind (residue). research.md R4 / FR-004 require real
    // removal here; tasks.md T022 / T014-T017's zero-residue assertion
    // (T018) must catch this.
    state->published = 0;
    state->cleaned = 1;
    return 0;
#else
    if (remove_tree(state->staging_dir) != 0) return -1;
    state->published = 0;
    state->cleaned = 1;
    return 0;
#endif
}

// --- execute_staging --------------------------------------------------------

int execute_staging(const InstallPlan* plan, const ApkFixture* fixture, StagingState* out_state) {
    memset(out_state, 0, sizeof(*out_state));

    // Staging base is overridable via HP2_STAGING_BASE (default "/tmp",
    // matching pre-existing host test behavior byte-for-byte). Real OH
    // devices mount "/" (including "/tmp") read-only in production, so
    // callers running this off-host must point HP2_STAGING_BASE at a
    // writable path (e.g. /data/local/tmp) or mkdtemp() below fails closed
    // with rc=-1 — confirmed on 5EAB5 hardware (5eab586000000000000000001123012c).
    const char* staging_base = getenv("HP2_STAGING_BASE");
    if (staging_base == NULL || staging_base[0] == '\0') {
        staging_base = "/tmp";
    }

    char staging_template[PATH_MAX];
    int n = snprintf(staging_template, sizeof(staging_template), "%s/%s",
                      staging_base, "hp2-install-plan-staging.XXXXXX");
    if (n < 0 || (size_t)n >= sizeof(staging_template)) return -1;

    if (mkdtemp(staging_template) == NULL) return -1;
    strncpy(out_state->staging_dir, staging_template, sizeof(out_state->staging_dir) - 1);

    n = snprintf(out_state->final_dir, sizeof(out_state->final_dir), "%s.final",
                 out_state->staging_dir);
    if (n < 0 || (size_t)n >= (int)sizeof(out_state->final_dir)) {
        remove_tree(out_state->staging_dir);
        return -1;
    }

    // Model "CreateBundleDir -> write" (research.md R4): stage the bytes
    // that would actually be seen at publish time, whichever those are.
    const unsigned char* staged_bytes =
        fixture->tampered_after_verify ? fixture->tampered_content : fixture->content;
    size_t staged_len =
        fixture->tampered_after_verify ? fixture->tampered_content_len : fixture->content_len;

    // codex headless gate round 3 (contract-drift finding, POST-HOC FIX):
    // the staging-time identity re-check below is only MEANINGFUL — and
    // only the deciding factor — when evaluate_install_plan() already said
    // PLAN_INSTALLABLE. If plan->verdict is already a REJECT (R1/R2/R3
    // caught something at evaluate time), that rejection stands on its own;
    // the re-check is not applicable and identity_reverified_ok must read 0,
    // not "1 because these particular bytes happen to still hash the same"
    // (round 3 caught exactly this: a REJECT_MULTI_APK fixture whose
    // content was never mutated used to report identity_reverified_ok==1,
    // contradicting the contract's "otherwise ... identity_reverified_ok==0"
    // clause). No sha256 recompute is needed on this branch either.
    if (plan->verdict != PLAN_INSTALLABLE) {
        out_state->identity_reverified_ok = 0;
        return cleanup_staging(out_state);
    }

    // FR-003 fail-closed re-check (codex headless gate round 2 finding #1):
    // recompute sha256 over the bytes actually about to be staged/published
    // and compare against plan->apk_sha256_at_verify — the hash pinned at
    // evaluate_install_plan() time. plan->verdict==PLAN_INSTALLABLE alone is
    // NOT sufficient: `fixture` is a caller-owned pointer that can be
    // mutated in place (or have tampered_after_verify/tampered_content set)
    // at any point between the evaluate_install_plan() call and this
    // execute_staging() call. This re-check is the actual identity-pinning
    // enforcement point on the only path where it matters, exactly as a
    // sealed-FD verifier would refuse to publish bytes that no longer match
    // what was verified.
    unsigned char staged_hash[32];
    sha256(staged_bytes, staged_len, staged_hash);
#ifndef MUTANT_TAMPERED
    int identity_still_holds = (memcmp(staged_hash, plan->apk_sha256_at_verify, 32) == 0);
#else
    // MUTANT_TAMPERED: this re-check is compiled out too (consistent with
    // the evaluate-time comparison also being disabled under this mutant —
    // both represent "R3 tamper detection is entirely broken").
    int identity_still_holds = 1;
#endif
    out_state->identity_reverified_ok = identity_still_holds;

    if (!identity_still_holds) {
        // The identity re-check just caught a mutation evaluate-time
        // couldn't have seen: fail-closed, zero residue (research.md R4 /
        // FR-004). Nothing has been written to staging_dir yet, so cleanup
        // only has to remove the (still-empty) staging directory itself.
        return cleanup_staging(out_state);
    }

    char staged_apk_path[PATH_MAX];
    n = snprintf(staged_apk_path, sizeof(staged_apk_path), "%s/base.apk", out_state->staging_dir);
    if (n < 0 || (size_t)n >= (int)sizeof(staged_apk_path)) {
        remove_tree(out_state->staging_dir);
        return -1;
    }
    if (write_all(staged_apk_path, staged_bytes, staged_len) != 0) {
        remove_tree(out_state->staging_dir);
        return -1;
    }

    if (rename(out_state->staging_dir, out_state->final_dir) != 0) {
        remove_tree(out_state->staging_dir);
        return -1;
    }
    out_state->published = 1;
    out_state->cleaned = 0;
    return 0;
}
