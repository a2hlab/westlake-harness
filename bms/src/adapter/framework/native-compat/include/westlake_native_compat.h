#ifndef WESTLAKE_NATIVE_COMPAT_H
#define WESTLAKE_NATIVE_COMPAT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__) || defined(__clang__)
#define WLNC_EXPORT __attribute__((visibility("default")))
#else
#define WLNC_EXPORT
#endif

#define WLNC_ABI_VERSION UINT32_C(1)
#define WLNC_DIGEST_SIZE UINT32_C(32)
#define WLNC_BUILD_ID_MAX_SIZE UINT32_C(32)
#define WLNC_PREVERIFIED_CAPABILITY_MARKER UINT64_C(0x574c4e4350563031)

typedef enum WlncStatus {
    WLNC_STATUS_OK = 0,
    WLNC_STATUS_OK_IDEMPOTENT = 1,
    WLNC_STATUS_DENIED_TRANSIENT = 2,
    WLNC_STATUS_DENIED_TERMINAL = 3,
    WLNC_STATUS_INVALID_ARGUMENT = 4
} WlncStatus;

typedef enum WlncReason {
    WLNC_REASON_NONE = 0,
    WLNC_REASON_ALREADY_INITIALIZED = 1,
    WLNC_REASON_INVALID_ARGUMENT = 2,
    WLNC_REASON_ABI_VERSION_MISMATCH = 3,
    WLNC_REASON_CAPABILITY_NOT_PREVERIFIED = 4,
    WLNC_REASON_TARGET_SHA_MISMATCH = 5,
    WLNC_REASON_TARGET_BUILD_ID_MISMATCH = 6,
    WLNC_REASON_GENERATION_MISMATCH = 7,
    WLNC_REASON_PROCESS_EPOCH_MISMATCH = 8,
    WLNC_REASON_POLICY_EPOCH_MISMATCH = 9,
    WLNC_REASON_MECHANISM_UNSUPPORTED = 10,
    WLNC_REASON_HARD_COUNT_NONZERO = 11,
    WLNC_REASON_GUARD_SOURCE_FAILED = 12,
    WLNC_REASON_GUARD_VALUE_INVALID = 13,
    WLNC_REASON_GUARD_EPOCH_MISMATCH = 14,
    WLNC_REASON_PROCESS_TERMINAL = 15,
    WLNC_REASON_CONCURRENT_INIT = 16,
    WLNC_REASON_PROFILE_REPLAY = 17,
    WLNC_REASON_PROFILE_REVOKED = 18,
    WLNC_REASON_THREAD_NOT_READY = 19,
    WLNC_REASON_THREAD_OWNER_MISMATCH = 20,
    WLNC_REASON_THREAD_PUBLICATION_RACE = 21,
    WLNC_REASON_INVALID_THREAD_ROLE = 22,
    WLNC_REASON_LOAD_IDENTITY_MISMATCH = 23,
    WLNC_REASON_INTERNAL_STATE = 24,
    WLNC_REASON_FORK_RESET_REQUIRED = 25,
    WLNC_REASON_PLATFORM_OWNER_MISMATCH = 26,
    WLNC_REASON_AUDIT_ONLY_NO_LOAD_AUTHORITY = 27,
    WLNC_REASON_REQUIRED_PROOF_MISSING = 28
} WlncReason;

typedef enum WlncProcessState {
    WLNC_PROCESS_UNINITIALIZED = 0,
    WLNC_PROCESS_INITIALIZING = 1,
    WLNC_PROCESS_PROFILE_VERIFIED = 2,
    WLNC_PROCESS_ARMED = 3,
    WLNC_PROCESS_REVOKED = 4,
    WLNC_PROCESS_REJECTED = 5
} WlncProcessState;

typedef enum WlncThreadState {
    WLNC_THREAD_UNSEEN = 0,
    WLNC_THREAD_PREPARING = 1,
    WLNC_THREAD_READY = 2,
    WLNC_THREAD_INVALID = 3
} WlncThreadState;

typedef enum WlncThreadRole {
    WLNC_THREAD_ROLE_INVALID = 0,
    WLNC_THREAD_ROLE_MAIN = 1
} WlncThreadRole;

typedef enum WlncMechanism {
    WLNC_MECHANISM_INVALID = 0,
    WLNC_MECHANISM_AUDIT_ONLY = 1
} WlncMechanism;

typedef enum WlncCapabilityOrigin {
    WLNC_CAPABILITY_ORIGIN_INVALID = 0,
    WLNC_CAPABILITY_ORIGIN_UPSTREAM_PREVERIFIED = 1
} WlncCapabilityOrigin;

typedef enum WlncGuardSourceQuality {
    WLNC_GUARD_SOURCE_QUALITY_INVALID = 0,
    WLNC_GUARD_SOURCE_QUALITY_OS_CSPRNG = 1,
    WLNC_GUARD_SOURCE_QUALITY_TEST_DETERMINISTIC = 2
} WlncGuardSourceQuality;

typedef enum WlncAuditEventType {
    WLNC_EVENT_PROFILE_PREVERIFIED = 1,
    WLNC_EVENT_PROCESS_ARMED = 2,
    WLNC_EVENT_THREAD_PREPARING = 3,
    WLNC_EVENT_THREAD_METADATA_STAGED = 4,
    WLNC_EVENT_THREAD_READY = 5,
    WLNC_EVENT_LOAD_GATE_DENIED = 6,
    WLNC_EVENT_PROCESS_REVOKED = 7,
    WLNC_EVENT_REJECT = 8
} WlncAuditEventType;

typedef struct WlncResult {
    WlncStatus status;
    WlncReason reason;
    WlncProcessState process_state;
    WlncThreadState thread_state;
} WlncResult;

typedef struct WlncTargetIdentity {
    uint32_t abi_version;
    uint32_t build_id_size;
    uint64_t adapter_generation;
    uint8_t target_sha256[WLNC_DIGEST_SIZE];
    uint8_t build_id[WLNC_BUILD_ID_MAX_SIZE];
} WlncTargetIdentity;

/*
 * This structure is an explicitly preverified handoff, not a signature.
 * PR-02 checks its internal identity contract only. Authenticity, issuer trust,
 * revocation freshness, and sealed-byte provenance remain NOT_PROVEN until the
 * upstream certificate verifier is integrated by a later PR.
 */
typedef struct WlncPreverifiedCapabilityV1 {
    uint32_t abi_version;
    WlncCapabilityOrigin origin;
    uint64_t marker;
    WlncMechanism mechanism;
    uint32_t inline_unknown_count;
    uint32_t cfg_unknown_count;
    uint32_t unproven_overlap_count;
    uint32_t missing_thread_entry_count;
    uint32_t pre_prepare_slot5_access_count;
    uint32_t guest_scan_complete;
    uint32_t initial_closure_complete;
    uint32_t prepare_order_proven;
    uint32_t loader_provenance_complete;
    uint32_t generation_manifest_complete;
    uint32_t reserved_zero;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint8_t profile_sha256[WLNC_DIGEST_SIZE];
    WlncTargetIdentity target;
} WlncPreverifiedCapabilityV1;

typedef struct WlncForkSeed {
    uint32_t abi_version;
    uint32_t reserved_zero;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
} WlncForkSeed;

typedef struct WlncGuardSourceSample {
    uint64_t value;
    uint64_t source_epoch;
    WlncGuardSourceQuality quality;
    uint32_t reserved_zero;
} WlncGuardSourceSample;

typedef struct WlncAuditEvent {
    uint32_t abi_version;
    WlncAuditEventType type;
    uint64_t sequence;
    WlncReason reason;
    WlncProcessState process_state;
    WlncThreadState thread_state;
    WlncThreadRole thread_role;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t thread_id;
} WlncAuditEvent;

typedef int (*WlncGetGuardSource)(void *context,
                                 uint64_t required_process_epoch,
                                 WlncGuardSourceSample *out_sample);
typedef uint64_t (*WlncGetThreadId)(void *context);
typedef int (*WlncEmitAuditEvent)(void *context,
                                 const WlncAuditEvent *event);

/* Callback contracts: guard/audit return exactly 1 on success/acceptance. */

typedef struct WlncPlatformOps {
    uint32_t abi_version;
    uint32_t reserved_zero;
    void *context;
    WlncGetGuardSource get_guard_source;
    WlncGetThreadId get_thread_id;
    WlncEmitAuditEvent emit_audit_event;
} WlncPlatformOps;

typedef struct WlncLoadIdentity {
    uint32_t abi_version;
    uint32_t reserved_zero;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint8_t profile_sha256[WLNC_DIGEST_SIZE];
} WlncLoadIdentity;

typedef struct WlncLoadPermit {
    uint32_t abi_version;
    WlncMechanism mechanism;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t thread_id;
} WlncLoadPermit;

typedef struct WlncAuditSnapshot {
    uint32_t abi_version;
    uint32_t fork_seeded;
    WlncProcessState process_state;
    WlncThreadState thread_state;
    WlncReason last_reason;
    WlncMechanism mechanism;
    WlncThreadRole thread_role;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t thread_id;
    uint64_t audit_event_count;
    uint64_t audit_drop_count;
    uint8_t profile_sha256[WLNC_DIGEST_SIZE];
} WlncAuditSnapshot;

WLNC_EXPORT uint32_t WLNC_GetAbiVersion(void);

/* Stable, allocation-free diagnostic name. Unknown values map to "unknown". */
WLNC_EXPORT const char *WLNC_ReasonString(WlncReason reason);

/* Earliest child-side reset: atomic stores only; no callback is invoked. */
WLNC_EXPORT WlncResult WLNC_AfterForkChildReset(const WlncForkSeed *seed);

WLNC_EXPORT WlncResult WLNC_ProcessInitPreverified(
    const WlncPreverifiedCapabilityV1 *capability,
    const WlncTargetIdentity *expected_target,
    const WlncPlatformOps *platform_ops);

WLNC_EXPORT WlncResult WLNC_PrepareCurrentThread(WlncThreadRole role);

/*
 * Audit-only ABI v1 deliberately never returns a usable permit.  It consumes
 * READY with acquire semantics and validates all bound identity fields, then
 * returns WLNC_REASON_AUDIT_ONLY_NO_LOAD_AUTHORITY.  A later data-plane ABI
 * may issue a permit only after a real guard publisher has been integrated.
 */
WLNC_EXPORT WlncResult WLNC_AuthorizeLoad(const WlncLoadIdentity *load,
                                          WlncLoadPermit *out_permit);

WLNC_EXPORT WlncResult WLNC_Revoke(void);

WLNC_EXPORT WlncResult WLNC_GetAuditSnapshot(WlncAuditSnapshot *out_snapshot);

#ifdef __cplusplus
}
#endif

#endif
