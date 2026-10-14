// install_plan.h — HP-2 host-only install-plan logic model.
//
// This is a from-scratch host oracle that re-implements (does NOT link
// against) the judgment rules documented in
// specs/001-hp2-apk-install/research.md (R1-R6) and data-model.md. It does
// not connect to a real BMS/installd process and does not touch any 02
// source production file. See specs/001-hp2-apk-install/plan.md for scope.
//
// STUB scope note: this header/impl pair covers ONLY the install-plan
// judgment (single-APK guard / primary-ABI selection / apkSha256 identity /
// atomic staging-publish). Framework loading (L01.A02), display (L05),
// input, audio are entirely out of scope for this feature — not even
// stubbed here, per FR-010.

#ifndef HP2_INSTALL_PLAN_H
#define HP2_INSTALL_PLAN_H

#include <stddef.h>
#include <limits.h>

// musl's <limits.h> only defines PATH_MAX when a POSIX feature-test macro
// (_POSIX_C_SOURCE / _XOPEN_SOURCE / _GNU_SOURCE / _BSD_SOURCE) is set; a
// plain -std=c11 build on OH aarch64-linux-ohos leaves it undefined even
// though the same source compiles fine on host (glibc/Apple libc define it
// unconditionally). Fall back to the musl non-LiteOS value so this header
// is portable across host and OH musl targets without relying on every
// caller's build flags.
#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Upper bound on synthetic fixture content size. This is NOT a real APK size
// limit — it only needs to be large enough to hold hand-written synthetic
// test content for this feature's fixtures (data-model.md ApkFixture).
#define FIXTURE_MAX_BYTES 4096u

// --- ApkFixture -------------------------------------------------------

// research.md R2: root-level lib/<abi>/ layout shape of the synthetic
// fixture. Mirrors data-model.md ApkFixture.abi_layout.
typedef enum {
    ABI_LAYOUT_ARM64_FAT,    // root lib/arm64-v8a/ + lib/armeabi-v7a/ both present
    ABI_LAYOUT_ARM64_ONLY,   // only root lib/arm64-v8a/
    ABI_LAYOUT_V7A_ONLY,     // only root lib/armeabi-v7a/ (old mono packages)
    ABI_LAYOUT_AAB_NESTED,   // lib/<abi>/ exists but under a non-root prefix (e.g. base/lib/)
    ABI_LAYOUT_EMPTY_NATIVE  // native extraction result is empty
} AbiLayout;

// research.md R5: signature scheme modeled for this round. NONE is
// fail-closed; V1_ONLY/V2_PLUS are both treated as "verified" this round.
typedef enum {
    SIG_NONE,
    SIG_V1_ONLY,
    SIG_V2_PLUS
} SignatureScheme;

// data-model.md ApkFixture — synthetic test input driving both the
// evaluate_install_plan() judgment and execute_staging() filesystem model.
typedef struct ApkFixture {
    int apk_count;                                    // single-APK guard input; normal=1
    // FR-001 / spec.md "apkCount!=1 || bundlePaths.size()!=1": the two halves
    // of the single-APK guard are independent conditions in the real active
    // chain (base_bundle_installer.cpp.patch guard one) - apk_count==1 does
    // NOT imply bundle_path_count==1. Added post-hoc (codex headless gate
    // finding #3): the original R1 check only modeled apk_count, so a
    // fixture with apk_count==1 but bundle_path_count>1 was structurally
    // unrepresentable and untested. normal=1.
    int bundle_path_count;
    AbiLayout abi_layout;
    SignatureScheme signature_scheme;
    unsigned char content[FIXTURE_MAX_BYTES];         // verify-time-original content bytes
    size_t content_len;
    int tampered_after_verify;                        // 1 = content is swapped before publish
    unsigned char tampered_content[FIXTURE_MAX_BYTES];
    size_t tampered_content_len;
    // US1 Acceptance Scenario 3 (tasks.md T012, FR-008 "package/version 记录
    // 写入成功"): minimal synthetic manifest metadata carried directly by the
    // fixture. This is NOT a manifest parser — the host oracle does not parse
    // `content`; it models "what a real manifest parser would have extracted"
    // as plain input fields, which is enough to exercise the "record success
    // is queryable" judgment surface without a real BMS/package-record store.
    char package_name[128];
    int version_code;
} ApkFixture;

// --- InstallPlan --------------------------------------------------------

// data-model.md PlanVerdict. Judgment order is fixed by
// contracts/install_plan_contract.md: R1 -> R2 -> R3 (first hit wins).
typedef enum {
    PLAN_INSTALLABLE,
    REJECT_MULTI_APK,        // R1
    REJECT_NO_ARM64_SLICE,   // R2 (v7a-only or AAB-nested)
    REJECT_EMPTY_NATIVE,     // R2 variant (native-stage empty)
    REJECT_UNVERIFIED,       // R3 (signature missing/invalid)
    REJECT_TAMPERED          // R3 (verify-time vs publish-time sha256 mismatch, TOCTOU)
} PlanVerdict;

typedef struct InstallPlan {
    PlanVerdict verdict;
    char primary_abi[16];                     // "arm64-v8a" iff verdict==PLAN_INSTALLABLE
    unsigned char apk_sha256_at_verify[32];
    unsigned char apk_sha256_at_publish[32];   // only meaningful when PLAN_INSTALLABLE
    int staging_cleaned;                       // REJECT paths must set this to 1
    // US1 Acceptance Scenario 3 (tasks.md T012, FR-008): package/version
    // record surface. Copied from ApkFixture.package_name/version_code and
    // record_written set to 1 only when verdict==PLAN_INSTALLABLE (models
    // "package/version 记录写入成功"); left zeroed on all REJECT verdicts.
    char package_name[128];
    int version_code;
    int record_written;
} InstallPlan;

// --- StagingState --------------------------------------------------------

// data-model.md StagingState — host temp-directory model of the atomic
// staging -> publish / cleanup lifecycle (research.md R4).
typedef struct StagingState {
    char staging_dir[PATH_MAX];   // mkdtemp() output
    char final_dir[PATH_MAX];     // rename target when PLAN_INSTALLABLE
    int published;                 // 1 = renamed to final_dir
    int cleaned;                   // 1 = REJECT path recursively removed staging_dir
    // codex headless gate round 2 (contract-drift finding #1): execute_staging()
    // re-verifies identity against plan->apk_sha256_at_verify immediately
    // before publishing (see execute_staging doc comment below), so a call
    // can land on cleaned==1 even when plan->verdict==PLAN_INSTALLABLE — the
    // published/cleaned pair already fully disambiguates the outcome, but
    // this field makes WHY explicit and queryable without having to infer it
    // from plan->verdict vs published/cleaned: 1 = staging-time re-check
    // passed (bytes still matched plan->apk_sha256_at_verify); 0 = either
    // plan->verdict was already a REJECT (re-check not reached/not
    // applicable) or the re-check itself caught a mismatch.
    int identity_reverified_ok;
} StagingState;

// --- Function contracts (contracts/install_plan_contract.md) ------------

// Evaluates an ApkFixture and returns the judgment result. Pure function:
// no side effects (does not write files, does not create directories).
InstallPlan evaluate_install_plan(const ApkFixture* fixture);

// Performs staging, then either publish or cleanup. Has real filesystem
// side effects (mkdtemp/write/rename/recursive remove). Returns 0 on
// successful completion of the corresponding path (publish succeeded, or
// cleanup succeeded); non-zero = internal error (treated as a test failure,
// not part of the negative-test taxonomy).
//
// IMPORTANT (codex headless gate round 2, contract-drift finding #1):
// plan->verdict == PLAN_INSTALLABLE does NOT by itself guarantee
// out_state->published == 1. Immediately before publishing, this function
// independently recomputes sha256 over the bytes it is about to write and
// compares them against plan->apk_sha256_at_verify (FR-003 fail-closed
// re-check). If `fixture` was mutated after evaluate_install_plan() was
// called (whether via tampered_after_verify/tampered_content or by the
// caller changing fixture->content in place), that re-check fails and this
// function falls back to the cleanup path even though plan->verdict still
// says PLAN_INSTALLABLE — out_state->published/cleaned and
// out_state->identity_reverified_ok are the actual, authoritative outcome
// of THIS call; plan->verdict is only what evaluate_install_plan() saw at
// an earlier, possibly-stale point in time. See contracts/
// install_plan_contract.md's postcondition table for the precise rule.
int execute_staging(const InstallPlan* plan, const ApkFixture* fixture, StagingState* out_state);

// research.md R4 / tasks.md T020: the same recursive-remove-then-mark-cleaned
// cleanup path execute_staging() uses internally on its REJECT branch,
// exposed directly so tests can invoke it twice on one StagingState and
// assert idempotency (second call is a no-op success, not an error/crash).
// Safe to call more than once: tolerant of staging_dir already being gone.
int cleanup_staging(StagingState* state);

#ifdef __cplusplus
}
#endif

#endif // HP2_INSTALL_PLAN_H
