#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct WlpbHostOpsV1 WlpbHostOpsV1;

#define WLNC_ABI_VERSION UINT32_C(1)
#define WLNC_SHA256_SIZE UINT32_C(32)
#define WLNC_AUDIT_EVENT_TYPE_SLOTS UINT32_C(10)

/* Parent generation-A identity, prepared before ART startVm/preload. */
typedef struct WlncParentIdentityV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t runtime_generation;
    uint32_t pid;
    uint32_t uid;
    uint32_t gid;
    uint32_t reserved_zero;
    uint8_t runtime_provider_sha256[WLNC_SHA256_SIZE];
    uint32_t reserved_zero2[4];
} WlncParentIdentityV1;

/*
 * Fixed POD identity passed only after the stock OH child tail succeeds.
 * No OH object, C++ object, pointer, or security operation crosses this ABI.
 */
typedef struct WlncProcessIdentityV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t runtime_generation;
    uint64_t message_id;
    uint32_t uid;
    uint32_t gid;
    uint32_t parent_stage_tail_reached;
    uint32_t child_stage_tail_reached;
    uint32_t bypass_guard_passed;
    uint32_t security_owner_stock_appspawn;
    uint32_t parent_tail_priority;
    uint32_t child_tail_priority;
    uint8_t runtime_provider_sha256[WLNC_SHA256_SIZE];
    uint32_t reserved_zero[4];
} WlncProcessIdentityV1;

typedef enum WlncPrepareResult {
    WLNC_PREPARE_OK = 0,
    WLNC_PREPARE_INVALID_IDENTITY = -1,
    WLNC_PREPARE_REPLAY = -2,
    WLNC_PREPARE_FORK_RESET_FAILED = -3,
    WLNC_PREPARE_PROCESS_ARM_FAILED = -4,
    WLNC_PREPARE_MAIN_TICKET_FAILED = -5,
    WLNC_PREPARE_MAIN_PUBLICATION_FAILED = -6,
    WLNC_PREPARE_MAIN_VERIFY_FAILED = -7,
    WLNC_PREPARE_PROCESS_NOT_READY = -8,
    WLNC_PREPARE_CURRENT_THREAD_NOT_READY = -9,
    WLNC_PREPARE_AUDIT_SNAPSHOT_INVALID = -10,
    WLNC_PREPARE_AUDIT_SNAPSHOT_RACE = -11,
    WLNC_PREPARE_THREAD_TEMPLATE_PUBLISH_FAILED = -12,
    WLNC_PREPARE_PROCESS_EPOCH_FAILED = -13,
    WLNC_PREPARE_GENERATION_MISMATCH = -14
} WlncPrepareResult;

/*
 * Lossless acceptance counters plus a compressed deterministic digest.
 * This is deliberately not represented as a complete per-event log.
 */
typedef struct WlncAuditSnapshotV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t product_state;
    uint32_t event_type_slots;
    uint64_t runtime_generation;
    uint64_t process_epoch;
    uint64_t accepted_event_count;
    uint64_t sequence_xor_digest;
    uint64_t payload_xor_digest;
    uint64_t registry_audit_sequence;
    uint64_t registry_audit_drop_count;
    uint64_t event_type_count[WLNC_AUDIT_EVENT_TYPE_SLOTS];
    uint32_t registry_ready_count;
    uint32_t registry_active_ticket_count;
    uint32_t reserved_zero[4];
} WlncAuditSnapshotV1;

/*
 * Product MAIN admission boundary:
 *
 * validated stock stage-31 receipt -> this function -> ZygoteHooks/ART/guest.
 *
 * The function does not own a second guard. It resets/arms the shared WLTG
 * process registry, supplies one full-width OS-CSPRNG sample to WLTG, then
 * issues and consumes the MAIN ticket. Musl's global __stack_chk_guard is
 * neither referenced nor modified.
 */
int westlake_native_compat_prepare_main_thread(
    const WlncProcessIdentityV1 *identity);

int westlake_native_compat_prepare_parent_runtime(
    const WlncParentIdentityV1 *identity);

int westlake_native_compat_verify_parent_preload_thread_ready(
    uint64_t runtime_generation);

/* Fail-closed gate for future loader/JNI/guest-start boundaries. */
int westlake_native_compat_verify_current_thread_ready(void);

/* Stable receipt snapshot; fails instead of returning a torn digest. */
int westlake_native_compat_get_audit_snapshot(
    WlncAuditSnapshotV1 *out_snapshot);

/* Versioned host callbacks copied into the namespace-only pthread bridge. */
int westlake_native_compat_get_pthread_bridge_ops(WlpbHostOpsV1 *out_ops);

#ifdef __cplusplus
}

namespace appspawnx {

int WestLakeNativeCompatPrepareParentRuntime(
    const WlncParentIdentityV1 *identity);
int WestLakeNativeCompatVerifyParentPreloadThreadReady(
    uint64_t runtime_generation);
int WestLakeNativeCompatPrepareMainThread(
    const WlncProcessIdentityV1 *identity);
int WestLakeNativeCompatVerifyCurrentThreadReady();
int WestLakeNativeCompatGetAuditSnapshot(WlncAuditSnapshotV1 *out_snapshot);
int WestLakeNativeCompatGetPthreadBridgeOps(WlpbHostOpsV1 *out_ops);

}  // namespace appspawnx
#endif
