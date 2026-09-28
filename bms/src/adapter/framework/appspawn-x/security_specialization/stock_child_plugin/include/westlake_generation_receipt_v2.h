#ifndef WESTLAKE_GENERATION_RECEIPT_V2_H
#define WESTLAKE_GENERATION_RECEIPT_V2_H

/*
 * Fn02 generation/receipt shared ABI revision 2.
 *
 * Frozen authorities:
 *   spec/atoms/Fn02/A06/DESIGN_SPEC.md
 *     SHA-256 f27a691051395aebe18117017efabd93fcb1ef6edf3f55e975f40ed5847a9dfe
 *   spec/concepts/Fn02/route-instance.yaml
 *     SHA-256 11a7dd0df8212223551cfa37ff480b32fcecb7b077f1de28ec9d54cf02a76a17
 *   spec/concepts/Fn02/child-hook-table.yaml
 *     SHA-256 12e3f5e6a592d227a9a91b85ca696d56901d82d249d5b976063ee7a869b1d6ec
 *
 * Every public structure below contains fixed-width values and inline arrays
 * only.  No pointer, handle, VM/JNI object, pthread/TLS object, allocator
 * address, loader object, or C++ object crosses this ABI.
 */

#include <stddef.h>
#include <stdint.h>

#if defined(__cplusplus)
#define WLGR_V2_STATIC_ASSERT(condition, message) static_assert((condition), message)
#define WLGR_V2_ALIGNOF(type) alignof(type)
extern "C" {
#else
#define WLGR_V2_STATIC_ASSERT(condition, message) _Static_assert((condition), message)
#define WLGR_V2_ALIGNOF(type) _Alignof(type)
#endif

#define WLGR_V2_ABI_VERSION UINT32_C(2)
#define WLGR_V2_REQUIRED_ALIGNMENT UINT32_C(8)
#define WLGR_V2_SHA256_SIZE UINT32_C(32)
#define WLGR_V2_BOOT_ID_SIZE UINT32_C(16)
#define WLGR_V2_NONCE_SIZE UINT32_C(16)
#define WLGR_V2_PACKAGE_NAME_SIZE UINT32_C(256)
#define WLGR_V2_PROCESS_NAME_SIZE UINT32_C(256)
#define WLGR_V2_A02_PREREQUISITE_COUNT UINT32_C(6)
#define WLGR_V2_RUNTIME_KEY_SIZE UINT32_C(576)
#define WLGR_V2_IDENTITY_SIZE UINT32_C(816)
#define WLGR_V2_RECEIPT_SIZE UINT32_C(1040)
#define WLGR_V2_REPLAY_RESULT_SIZE UINT32_C(112)
#define WLGR_V2_A02_BUNDLE_SIZE UINT32_C(7200)

#define WLGR_V2_RUNTIME_KEY_MAGIC UINT64_C(0x574c47524b455932)
#define WLGR_V2_IDENTITY_MAGIC UINT64_C(0x574c475249445632)
#define WLGR_V2_RECEIPT_MAGIC UINT64_C(0x574c475252435632)
#define WLGR_V2_REPLAY_MAGIC UINT64_C(0x574c475252505632)
#define WLGR_V2_A02_BUNDLE_MAGIC UINT64_C(0x574c4752424e4432)

typedef enum westlake_generation_action_v2 {
    WLGR_V2_ACTION_FN02_A02 = 2,
    WLGR_V2_ACTION_FN02_A06 = 6
} westlake_generation_action_v2;

/* Numeric values are the stable suffixes of R1-F02-Txx. */
typedef enum westlake_generation_transition_v2 {
    WLGR_V2_TRANSITION_T03 = 3,
    WLGR_V2_TRANSITION_T07 = 7,
    WLGR_V2_TRANSITION_T08 = 8,
    WLGR_V2_TRANSITION_T09 = 9,
    WLGR_V2_TRANSITION_T10 = 10,
    WLGR_V2_TRANSITION_T11 = 11,
    WLGR_V2_TRANSITION_T12 = 12,
    WLGR_V2_TRANSITION_T13 = 13
} westlake_generation_transition_v2;

typedef enum westlake_generation_stage_v2 {
    WLGR_V2_STAGE_INVALID = 0,
    WLGR_V2_STAGE_CHILD_BOUND = 1,
    WLGR_V2_STAGE_GENERATION_VALIDATED = 2,
    WLGR_V2_STAGE_HOOK_TABLE_READY = 3,
    WLGR_V2_STAGE_PROVIDER_MAPPED = 4,
    WLGR_V2_STAGE_CONSTRUCTORS_COMPLETED = 5,
    WLGR_V2_STAGE_VM_CREATED = 6,
    WLGR_V2_STAGE_JNI_READY = 7,
    WLGR_V2_STAGE_RUNTIME_BOUND = 8,
    WLGR_V2_STAGE_STOPPING = 9,
    WLGR_V2_STAGE_RECONCILE_REQUIRED = 10,
    WLGR_V2_STAGE_TERMINATED = 11
} westlake_generation_stage_v2;

typedef enum westlake_generation_owner_v2 {
    WLGR_V2_OWNER_GENERATION_REDUCER = 1,
    WLGR_V2_OWNER_CHILD_HOOK = 2,
    WLGR_V2_OWNER_CHILD_LOADER = 3,
    WLGR_V2_OWNER_PROVIDER_CONSTRUCTORS = 4,
    WLGR_V2_OWNER_ART_VM = 5,
    WLGR_V2_OWNER_ART_JNI = 6,
    WLGR_V2_OWNER_ACTIVITY_THREAD = 7,
    WLGR_V2_OWNER_PROCESS = 8
} westlake_generation_owner_v2;

typedef enum westlake_generation_publication_v2 {
    WLGR_V2_PUBLICATION_EMPTY = 0,
    WLGR_V2_PUBLICATION_IN_PROGRESS = 1,
    WLGR_V2_PUBLICATION_COMMITTED = 2,
    WLGR_V2_PUBLICATION_RECONCILE_REQUIRED = 3,
    WLGR_V2_PUBLICATION_TERMINAL = 4
} westlake_generation_publication_v2;

typedef enum westlake_generation_result_v2 {
    WLGR_V2_RESULT_OK = 0,
    WLGR_V2_RESULT_IN_PROGRESS = 1,
    WLGR_V2_ERROR_INVALID_ARGUMENT = -3001,
    WLGR_V2_ERROR_IDENTITY_MISMATCH = -3002,
    WLGR_V2_ERROR_SEQUENCE_INVALID = -3003,
    WLGR_V2_ERROR_OWNER_MISMATCH = -3004,
    WLGR_V2_ERROR_DIGEST_INVALID = -3005,
    WLGR_V2_ERROR_EVENT_CONFLICT = -3006,
    WLGR_V2_ERROR_MISSING_PREREQUISITE = -3007,
    WLGR_V2_ERROR_GENERATION_MISMATCH = -3008,
    WLGR_V2_ERROR_HOOK_INSTALL_RACE = -3009,
    WLGR_V2_ERROR_HOOK_TABLE_REJECTED = -3010,
    WLGR_V2_ERROR_HOOK_GENERATION_STALE = -3011,
    WLGR_V2_ERROR_HOOK_OWNER_MISMATCH = -3012,
    WLGR_V2_ERROR_PROVIDER_LOAD_FAILED = -3013,
    WLGR_V2_ERROR_CONSTRUCTOR_FAILED = -3014,
    WLGR_V2_ERROR_VM_CREATE_FAILED = -3015,
    WLGR_V2_ERROR_JNI_REGISTER_FAILED = -3016,
    WLGR_V2_ERROR_HOOK_DRAIN_TIMEOUT = -3017,
    WLGR_V2_ERROR_TERMINAL_CONFLICT = -3018,
    WLGR_V2_ERROR_INTERNAL = -3099
} westlake_generation_result_v2;

typedef enum westlake_generation_replay_disposition_v2 {
    WLGR_V2_REPLAY_ACCEPT_NEW = 0,
    WLGR_V2_REPLAY_RETURN_RECORDED = 1,
    WLGR_V2_REPLAY_RETURN_IN_PROGRESS = 2,
    WLGR_V2_REPLAY_RETURN_RECONCILE_REQUIRED = 3,
    WLGR_V2_REPLAY_REJECT_EVENT_CONFLICT = 4,
    WLGR_V2_REPLAY_REJECT_IDENTITY_CONFLICT = 5
} westlake_generation_replay_disposition_v2;

typedef enum westlake_generation_bundle_state_v2 {
    WLGR_V2_BUNDLE_INVALID = 0,
    WLGR_V2_BUNDLE_READY_FOR_A02 = 1
} westlake_generation_bundle_state_v2;

typedef struct westlake_runtime_instance_key_v2 {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t struct_alignment;
    uint32_t android_uid;
    uint64_t launch_generation;
    char android_package[WLGR_V2_PACKAGE_NAME_SIZE];
    char android_process_name[WLGR_V2_PROCESS_NAME_SIZE];
    uint32_t reserved_zero[8];
} westlake_runtime_instance_key_v2;

typedef struct westlake_generation_identity_v2 {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t struct_alignment;
    uint32_t reserved_zero0;
    westlake_runtime_instance_key_v2 runtime_key;
    uint8_t boot_id[WLGR_V2_BOOT_ID_SIZE];
    uint8_t artifact_generation[WLGR_V2_SHA256_SIZE];
    uint64_t policy_epoch;
    uint64_t child_pid;
    uint64_t child_proc_start_time_ticks;
    uint8_t specialization_receipt_digest[WLGR_V2_SHA256_SIZE];
    uint8_t artifact_manifest_digest[WLGR_V2_SHA256_SIZE];
    uint8_t hook_schema_digest[WLGR_V2_SHA256_SIZE];
    uint8_t request_nonce[WLGR_V2_NONCE_SIZE];
    uint32_t reserved_zero[8];
} westlake_generation_identity_v2;

typedef struct westlake_runtime_stage_receipt_v2 {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t struct_alignment;
    uint32_t reserved_zero0;
    westlake_generation_identity_v2 identity;
    uint32_t action_id;
    uint32_t transition_id;
    uint32_t stage_before;
    uint32_t stage_after;
    uint32_t owner;
    uint32_t publication_state;
    int32_t result_code;
    int32_t first_cause;
    int32_t native_cause;
    uint32_t receipt_flags;
    uint64_t child_thread_id;
    uint64_t sequence;
    uint64_t monotonic_timestamp_ns;
    uint64_t reserved_zero1;
    uint8_t input_digest[WLGR_V2_SHA256_SIZE];
    uint8_t output_digest[WLGR_V2_SHA256_SIZE];
    uint8_t terminal_tombstone_digest[WLGR_V2_SHA256_SIZE];
    uint32_t reserved_zero[8];
} westlake_runtime_stage_receipt_v2;

/*
 * Pure reducer answer for duplicate submission.  RETURN_RECORDED carries the
 * first committed result and does not authorize repeating any side effect.
 */
typedef struct westlake_generation_replay_result_v2 {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t struct_alignment;
    uint32_t reserved_zero0;
    uint32_t disposition;
    uint32_t recorded_publication_state;
    int32_t recorded_result;
    int32_t recorded_first_cause;
    uint64_t recorded_sequence;
    uint8_t recorded_output_digest[WLGR_V2_SHA256_SIZE];
    uint32_t reserved_zero[8];
} westlake_generation_replay_result_v2;

/*
 * A06's immutable success handoff.  It contains T03 and T07..T11 only.
 * next_transition_id names T12, but t12_receipt_present must remain zero:
 * Fn02.A02 is the only owner allowed to execute and publish T12.
 */
typedef struct westlake_a02_prerequisite_bundle_v2 {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t struct_alignment;
    uint32_t reserved_zero0;
    westlake_generation_identity_v2 identity;
    uint32_t producer_action_id;
    uint32_t consumer_action_id;
    uint32_t producer_terminal_transition_id;
    uint32_t next_transition_id;
    uint32_t bundle_state;
    uint32_t receipt_count;
    uint32_t t12_receipt_present;
    uint32_t reserved_zero1;
    uint64_t first_sequence;
    uint64_t last_sequence;
    uint64_t monotonic_created_timestamp_ns;
    westlake_runtime_stage_receipt_v2
        receipts[WLGR_V2_A02_PREREQUISITE_COUNT];
    uint8_t bundle_digest[WLGR_V2_SHA256_SIZE];
    uint32_t reserved_zero[8];
} westlake_a02_prerequisite_bundle_v2;

static inline int wlgr_v2_bytes_zero(const uint8_t *value, size_t size)
{
    size_t index;
    uint8_t combined = UINT8_C(0);
    if (value == (const uint8_t *)0) {
        return 0;
    }
    for (index = 0U; index < size; ++index) {
        combined = (uint8_t)(combined | value[index]);
    }
    return combined == UINT8_C(0);
}

static inline int wlgr_v2_bytes_equal(const uint8_t *left,
                                      const uint8_t *right, size_t size)
{
    size_t index;
    uint8_t difference = UINT8_C(0);
    if (left == (const uint8_t *)0 || right == (const uint8_t *)0) {
        return 0;
    }
    for (index = 0U; index < size; ++index) {
        difference = (uint8_t)(difference | (uint8_t)(left[index] ^ right[index]));
    }
    return difference == UINT8_C(0);
}

static inline void wlgr_v2_clear_bytes(uint8_t *value, size_t size)
{
    size_t index;
    if (value == (uint8_t *)0) {
        return;
    }
    for (index = 0U; index < size; ++index) {
        value[index] = UINT8_C(0);
    }
}

static inline int wlgr_v2_fixed_string_canonical(const char *value,
                                                  size_t capacity)
{
    size_t index;
    int terminated = 0;
    if (value == (const char *)0 || capacity < 2U || value[0] == '\0') {
        return 0;
    }
    for (index = 0U; index < capacity; ++index) {
        if (!terminated && value[index] == '\0') {
            terminated = 1;
        } else if (terminated && value[index] != '\0') {
            return 0;
        }
    }
    return terminated;
}

static inline int wlgr_v2_runtime_key_valid(
    const westlake_runtime_instance_key_v2 *key)
{
    return key != (const westlake_runtime_instance_key_v2 *)0 &&
        key->magic == WLGR_V2_RUNTIME_KEY_MAGIC &&
        key->abi_version == WLGR_V2_ABI_VERSION &&
        key->struct_size == WLGR_V2_RUNTIME_KEY_SIZE &&
        key->struct_alignment == WLGR_V2_REQUIRED_ALIGNMENT &&
        key->launch_generation != UINT64_C(0) &&
        wlgr_v2_fixed_string_canonical(
            key->android_package, sizeof(key->android_package)) &&
        wlgr_v2_fixed_string_canonical(
            key->android_process_name, sizeof(key->android_process_name)) &&
        wlgr_v2_bytes_zero((const uint8_t *)key->reserved_zero,
                           sizeof(key->reserved_zero));
}

static inline int wlgr_v2_runtime_key_equal(
    const westlake_runtime_instance_key_v2 *left,
    const westlake_runtime_instance_key_v2 *right)
{
    return wlgr_v2_runtime_key_valid(left) &&
        wlgr_v2_runtime_key_valid(right) &&
        left->android_uid == right->android_uid &&
        left->launch_generation == right->launch_generation &&
        wlgr_v2_bytes_equal((const uint8_t *)left->android_package,
                            (const uint8_t *)right->android_package,
                            sizeof(left->android_package)) &&
        wlgr_v2_bytes_equal((const uint8_t *)left->android_process_name,
                            (const uint8_t *)right->android_process_name,
                            sizeof(left->android_process_name));
}

static inline int wlgr_v2_identity_valid(
    const westlake_generation_identity_v2 *identity)
{
    return identity != (const westlake_generation_identity_v2 *)0 &&
        identity->magic == WLGR_V2_IDENTITY_MAGIC &&
        identity->abi_version == WLGR_V2_ABI_VERSION &&
        identity->struct_size == WLGR_V2_IDENTITY_SIZE &&
        identity->struct_alignment == WLGR_V2_REQUIRED_ALIGNMENT &&
        identity->reserved_zero0 == UINT32_C(0) &&
        wlgr_v2_runtime_key_valid(&identity->runtime_key) &&
        !wlgr_v2_bytes_zero(identity->boot_id, sizeof(identity->boot_id)) &&
        !wlgr_v2_bytes_zero(identity->artifact_generation,
                            sizeof(identity->artifact_generation)) &&
        identity->policy_epoch != UINT64_C(0) &&
        identity->child_pid > UINT64_C(1) &&
        identity->child_proc_start_time_ticks != UINT64_C(0) &&
        !wlgr_v2_bytes_zero(identity->specialization_receipt_digest,
                            sizeof(identity->specialization_receipt_digest)) &&
        !wlgr_v2_bytes_zero(identity->artifact_manifest_digest,
                            sizeof(identity->artifact_manifest_digest)) &&
        !wlgr_v2_bytes_zero(identity->hook_schema_digest,
                            sizeof(identity->hook_schema_digest)) &&
        !wlgr_v2_bytes_zero(identity->request_nonce,
                            sizeof(identity->request_nonce)) &&
        wlgr_v2_bytes_zero((const uint8_t *)identity->reserved_zero,
                           sizeof(identity->reserved_zero));
}

static inline int wlgr_v2_generation_equal(
    const westlake_generation_identity_v2 *left,
    const westlake_generation_identity_v2 *right)
{
    return wlgr_v2_identity_valid(left) && wlgr_v2_identity_valid(right) &&
        wlgr_v2_runtime_key_equal(&left->runtime_key, &right->runtime_key) &&
        wlgr_v2_bytes_equal(left->boot_id, right->boot_id,
                            sizeof(left->boot_id)) &&
        wlgr_v2_bytes_equal(left->artifact_generation,
                            right->artifact_generation,
                            sizeof(left->artifact_generation)) &&
        left->policy_epoch == right->policy_epoch &&
        left->child_pid == right->child_pid &&
        left->child_proc_start_time_ticks ==
            right->child_proc_start_time_ticks &&
        wlgr_v2_bytes_equal(left->specialization_receipt_digest,
                            right->specialization_receipt_digest,
                            sizeof(left->specialization_receipt_digest)) &&
        wlgr_v2_bytes_equal(left->artifact_manifest_digest,
                            right->artifact_manifest_digest,
                            sizeof(left->artifact_manifest_digest)) &&
        wlgr_v2_bytes_equal(left->hook_schema_digest,
                            right->hook_schema_digest,
                            sizeof(left->hook_schema_digest));
}

static inline int wlgr_v2_identity_equal(
    const westlake_generation_identity_v2 *left,
    const westlake_generation_identity_v2 *right)
{
    return wlgr_v2_generation_equal(left, right) &&
        wlgr_v2_bytes_equal(left->request_nonce, right->request_nonce,
                            sizeof(left->request_nonce));
}

static inline uint32_t wlgr_v2_expected_action(uint32_t transition_id)
{
    return transition_id == WLGR_V2_TRANSITION_T12 ?
        WLGR_V2_ACTION_FN02_A02 : WLGR_V2_ACTION_FN02_A06;
}

static inline uint32_t wlgr_v2_expected_owner(uint32_t transition_id)
{
    switch (transition_id) {
        case WLGR_V2_TRANSITION_T03:
        case WLGR_V2_TRANSITION_T13:
            return WLGR_V2_OWNER_GENERATION_REDUCER;
        case WLGR_V2_TRANSITION_T07:
            return WLGR_V2_OWNER_CHILD_HOOK;
        case WLGR_V2_TRANSITION_T08:
            return WLGR_V2_OWNER_CHILD_LOADER;
        case WLGR_V2_TRANSITION_T09:
            return WLGR_V2_OWNER_PROVIDER_CONSTRUCTORS;
        case WLGR_V2_TRANSITION_T10:
            return WLGR_V2_OWNER_ART_VM;
        case WLGR_V2_TRANSITION_T11:
            return WLGR_V2_OWNER_ART_JNI;
        case WLGR_V2_TRANSITION_T12:
            return WLGR_V2_OWNER_ACTIVITY_THREAD;
        default:
            return UINT32_C(0);
    }
}

static inline uint32_t wlgr_v2_expected_stage_before(uint32_t transition_id)
{
    switch (transition_id) {
        case WLGR_V2_TRANSITION_T03:
            return WLGR_V2_STAGE_CHILD_BOUND;
        case WLGR_V2_TRANSITION_T07:
            return WLGR_V2_STAGE_GENERATION_VALIDATED;
        case WLGR_V2_TRANSITION_T08:
            return WLGR_V2_STAGE_HOOK_TABLE_READY;
        case WLGR_V2_TRANSITION_T09:
            return WLGR_V2_STAGE_PROVIDER_MAPPED;
        case WLGR_V2_TRANSITION_T10:
            return WLGR_V2_STAGE_CONSTRUCTORS_COMPLETED;
        case WLGR_V2_TRANSITION_T11:
            return WLGR_V2_STAGE_VM_CREATED;
        case WLGR_V2_TRANSITION_T12:
            return WLGR_V2_STAGE_JNI_READY;
        default:
            return WLGR_V2_STAGE_INVALID;
    }
}

static inline uint32_t wlgr_v2_expected_stage_after(uint32_t transition_id)
{
    switch (transition_id) {
        case WLGR_V2_TRANSITION_T03:
            return WLGR_V2_STAGE_GENERATION_VALIDATED;
        case WLGR_V2_TRANSITION_T07:
            return WLGR_V2_STAGE_HOOK_TABLE_READY;
        case WLGR_V2_TRANSITION_T08:
            return WLGR_V2_STAGE_PROVIDER_MAPPED;
        case WLGR_V2_TRANSITION_T09:
            return WLGR_V2_STAGE_CONSTRUCTORS_COMPLETED;
        case WLGR_V2_TRANSITION_T10:
            return WLGR_V2_STAGE_VM_CREATED;
        case WLGR_V2_TRANSITION_T11:
            return WLGR_V2_STAGE_JNI_READY;
        case WLGR_V2_TRANSITION_T12:
            return WLGR_V2_STAGE_RUNTIME_BOUND;
        default:
            return WLGR_V2_STAGE_INVALID;
    }
}

static inline int wlgr_v2_failure_stage_valid(uint32_t stage)
{
    return (stage >= WLGR_V2_STAGE_CHILD_BOUND &&
            stage <= WLGR_V2_STAGE_JNI_READY) ||
        stage == WLGR_V2_STAGE_STOPPING ||
        stage == WLGR_V2_STAGE_RECONCILE_REQUIRED;
}

static inline int wlgr_v2_receipt_valid(
    const westlake_runtime_stage_receipt_v2 *receipt)
{
    int tombstone_zero;
    if (receipt == (const westlake_runtime_stage_receipt_v2 *)0 ||
        receipt->magic != WLGR_V2_RECEIPT_MAGIC ||
        receipt->abi_version != WLGR_V2_ABI_VERSION ||
        receipt->struct_size != WLGR_V2_RECEIPT_SIZE ||
        receipt->struct_alignment != WLGR_V2_REQUIRED_ALIGNMENT ||
        receipt->reserved_zero0 != UINT32_C(0) ||
        receipt->receipt_flags != UINT32_C(0) ||
        receipt->child_thread_id == UINT64_C(0) ||
        receipt->sequence == UINT64_C(0) ||
        receipt->monotonic_timestamp_ns == UINT64_C(0) ||
        receipt->reserved_zero1 != UINT64_C(0) ||
        !wlgr_v2_identity_valid(&receipt->identity) ||
        wlgr_v2_bytes_zero(receipt->input_digest,
                           sizeof(receipt->input_digest)) ||
        wlgr_v2_bytes_zero(receipt->output_digest,
                           sizeof(receipt->output_digest)) ||
        !wlgr_v2_bytes_zero((const uint8_t *)receipt->reserved_zero,
                            sizeof(receipt->reserved_zero))) {
        return 0;
    }
    tombstone_zero = wlgr_v2_bytes_zero(
        receipt->terminal_tombstone_digest,
        sizeof(receipt->terminal_tombstone_digest));
    if (receipt->transition_id != WLGR_V2_TRANSITION_T13) {
        return receipt->action_id ==
                   wlgr_v2_expected_action(receipt->transition_id) &&
            receipt->owner == wlgr_v2_expected_owner(receipt->transition_id) &&
            receipt->stage_before ==
                wlgr_v2_expected_stage_before(receipt->transition_id) &&
            receipt->stage_after ==
                wlgr_v2_expected_stage_after(receipt->transition_id) &&
            receipt->publication_state == WLGR_V2_PUBLICATION_COMMITTED &&
            receipt->result_code == WLGR_V2_RESULT_OK &&
            receipt->first_cause == WLGR_V2_RESULT_OK &&
            receipt->native_cause == 0 && tombstone_zero;
    }
    if (receipt->action_id != WLGR_V2_ACTION_FN02_A06 ||
        receipt->owner != WLGR_V2_OWNER_GENERATION_REDUCER ||
        !wlgr_v2_failure_stage_valid(receipt->stage_before) ||
        receipt->first_cause >= WLGR_V2_RESULT_OK ||
        receipt->result_code != receipt->first_cause) {
        return 0;
    }
    if (receipt->publication_state == WLGR_V2_PUBLICATION_IN_PROGRESS) {
        return receipt->stage_after == WLGR_V2_STAGE_STOPPING &&
            tombstone_zero;
    }
    if (receipt->publication_state ==
            WLGR_V2_PUBLICATION_RECONCILE_REQUIRED) {
        return receipt->stage_after == WLGR_V2_STAGE_RECONCILE_REQUIRED &&
            tombstone_zero;
    }
    return receipt->publication_state == WLGR_V2_PUBLICATION_TERMINAL &&
        receipt->stage_after == WLGR_V2_STAGE_TERMINATED && !tombstone_zero;
}

static inline int32_t wlgr_v2_classify_replay(
    const westlake_runtime_stage_receipt_v2 *recorded,
    const westlake_runtime_stage_receipt_v2 *incoming,
    westlake_generation_replay_result_v2 *out_result)
{
    uint32_t disposition;
    if (!wlgr_v2_receipt_valid(recorded) || !wlgr_v2_receipt_valid(incoming) ||
        out_result == (westlake_generation_replay_result_v2 *)0) {
        return WLGR_V2_ERROR_INVALID_ARGUMENT;
    }
    if (!wlgr_v2_runtime_key_equal(&recorded->identity.runtime_key,
                                   &incoming->identity.runtime_key)) {
        disposition = WLGR_V2_REPLAY_ACCEPT_NEW;
    } else if (!wlgr_v2_generation_equal(&recorded->identity,
                                         &incoming->identity)) {
        disposition = WLGR_V2_REPLAY_REJECT_IDENTITY_CONFLICT;
    } else if (!wlgr_v2_bytes_equal(recorded->identity.request_nonce,
                                    incoming->identity.request_nonce,
                                    sizeof(recorded->identity.request_nonce))) {
        disposition = WLGR_V2_REPLAY_ACCEPT_NEW;
    } else if (recorded->action_id != incoming->action_id ||
               recorded->transition_id != incoming->transition_id ||
               recorded->owner != incoming->owner ||
               recorded->stage_before != incoming->stage_before ||
               !wlgr_v2_bytes_equal(recorded->input_digest,
                                    incoming->input_digest,
                                    sizeof(recorded->input_digest))) {
        disposition = WLGR_V2_REPLAY_REJECT_EVENT_CONFLICT;
    } else if (recorded->publication_state ==
               WLGR_V2_PUBLICATION_IN_PROGRESS) {
        disposition = WLGR_V2_REPLAY_RETURN_IN_PROGRESS;
    } else if (recorded->publication_state ==
               WLGR_V2_PUBLICATION_RECONCILE_REQUIRED) {
        disposition = WLGR_V2_REPLAY_RETURN_RECONCILE_REQUIRED;
    } else {
        disposition = WLGR_V2_REPLAY_RETURN_RECORDED;
    }

    wlgr_v2_clear_bytes((uint8_t *)out_result, sizeof(*out_result));
    out_result->magic = WLGR_V2_REPLAY_MAGIC;
    out_result->abi_version = WLGR_V2_ABI_VERSION;
    out_result->struct_size = WLGR_V2_REPLAY_RESULT_SIZE;
    out_result->struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    out_result->disposition = disposition;
    out_result->recorded_publication_state = recorded->publication_state;
    out_result->recorded_result = recorded->result_code;
    out_result->recorded_first_cause = recorded->first_cause;
    out_result->recorded_sequence = recorded->sequence;
    {
        size_t index;
        for (index = 0U; index < sizeof(out_result->recorded_output_digest);
             ++index) {
            out_result->recorded_output_digest[index] =
                recorded->output_digest[index];
        }
    }
    return WLGR_V2_RESULT_OK;
}

static inline int wlgr_v2_a02_bundle_valid(
    const westlake_a02_prerequisite_bundle_v2 *bundle)
{
    static const uint32_t expected_transitions[WLGR_V2_A02_PREREQUISITE_COUNT] = {
        WLGR_V2_TRANSITION_T03,
        WLGR_V2_TRANSITION_T07,
        WLGR_V2_TRANSITION_T08,
        WLGR_V2_TRANSITION_T09,
        WLGR_V2_TRANSITION_T10,
        WLGR_V2_TRANSITION_T11,
    };
    size_t index;
    if (bundle == (const westlake_a02_prerequisite_bundle_v2 *)0 ||
        bundle->magic != WLGR_V2_A02_BUNDLE_MAGIC ||
        bundle->abi_version != WLGR_V2_ABI_VERSION ||
        bundle->struct_size != WLGR_V2_A02_BUNDLE_SIZE ||
        bundle->struct_alignment != WLGR_V2_REQUIRED_ALIGNMENT ||
        bundle->reserved_zero0 != UINT32_C(0) ||
        !wlgr_v2_identity_valid(&bundle->identity) ||
        bundle->producer_action_id != WLGR_V2_ACTION_FN02_A06 ||
        bundle->consumer_action_id != WLGR_V2_ACTION_FN02_A02 ||
        bundle->producer_terminal_transition_id != WLGR_V2_TRANSITION_T11 ||
        bundle->next_transition_id != WLGR_V2_TRANSITION_T12 ||
        bundle->bundle_state != WLGR_V2_BUNDLE_READY_FOR_A02 ||
        bundle->receipt_count != WLGR_V2_A02_PREREQUISITE_COUNT ||
        bundle->t12_receipt_present != UINT32_C(0) ||
        bundle->reserved_zero1 != UINT32_C(0) ||
        bundle->first_sequence == UINT64_C(0) ||
        bundle->last_sequence < bundle->first_sequence ||
        bundle->monotonic_created_timestamp_ns == UINT64_C(0) ||
        wlgr_v2_bytes_zero(bundle->bundle_digest,
                           sizeof(bundle->bundle_digest)) ||
        !wlgr_v2_bytes_zero((const uint8_t *)bundle->reserved_zero,
                            sizeof(bundle->reserved_zero))) {
        return 0;
    }
    for (index = 0U; index < WLGR_V2_A02_PREREQUISITE_COUNT; ++index) {
        const westlake_runtime_stage_receipt_v2 *receipt =
            &bundle->receipts[index];
        if (!wlgr_v2_receipt_valid(receipt) ||
            receipt->transition_id != expected_transitions[index] ||
            receipt->action_id != WLGR_V2_ACTION_FN02_A06 ||
            receipt->publication_state != WLGR_V2_PUBLICATION_COMMITTED ||
            !wlgr_v2_identity_equal(&receipt->identity, &bundle->identity) ||
            (index > 0U &&
             (receipt->sequence <= bundle->receipts[index - 1U].sequence ||
              receipt->monotonic_timestamp_ns <
                  bundle->receipts[index - 1U].monotonic_timestamp_ns))) {
            return 0;
        }
    }
    return bundle->first_sequence == bundle->receipts[0].sequence &&
        bundle->last_sequence ==
            bundle->receipts[WLGR_V2_A02_PREREQUISITE_COUNT - 1U].sequence &&
        bundle->monotonic_created_timestamp_ns >=
            bundle->receipts[WLGR_V2_A02_PREREQUISITE_COUNT - 1U]
                .monotonic_timestamp_ns;
}

WLGR_V2_STATIC_ASSERT(sizeof(void *) == 8,
    "Fn02 generation receipt ABI requires 64-bit consumers");
WLGR_V2_STATIC_ASSERT(sizeof(westlake_runtime_instance_key_v2) ==
                          WLGR_V2_RUNTIME_KEY_SIZE,
    "runtime instance key layout drift");
WLGR_V2_STATIC_ASSERT(WLGR_V2_ALIGNOF(westlake_runtime_instance_key_v2) == 8,
    "runtime instance key alignment drift");
WLGR_V2_STATIC_ASSERT(sizeof(westlake_generation_identity_v2) ==
                          WLGR_V2_IDENTITY_SIZE,
    "generation identity layout drift");
WLGR_V2_STATIC_ASSERT(WLGR_V2_ALIGNOF(westlake_generation_identity_v2) == 8,
    "generation identity alignment drift");
WLGR_V2_STATIC_ASSERT(sizeof(westlake_runtime_stage_receipt_v2) ==
                          WLGR_V2_RECEIPT_SIZE,
    "runtime stage receipt layout drift");
WLGR_V2_STATIC_ASSERT(WLGR_V2_ALIGNOF(westlake_runtime_stage_receipt_v2) == 8,
    "runtime stage receipt alignment drift");
WLGR_V2_STATIC_ASSERT(sizeof(westlake_generation_replay_result_v2) ==
                          WLGR_V2_REPLAY_RESULT_SIZE,
    "replay result layout drift");
WLGR_V2_STATIC_ASSERT(sizeof(westlake_a02_prerequisite_bundle_v2) ==
                          WLGR_V2_A02_BUNDLE_SIZE,
    "A02 prerequisite bundle layout drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_runtime_instance_key_v2,
                              launch_generation) == 24,
    "launch generation offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_generation_identity_v2,
                              artifact_generation) == 616,
    "artifact generation offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_generation_identity_v2,
                              specialization_receipt_digest) == 672,
    "specialization digest offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_generation_identity_v2,
                              request_nonce) == 768,
    "request nonce offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_runtime_stage_receipt_v2,
                              identity) == 24,
    "receipt identity offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_runtime_stage_receipt_v2,
                              child_thread_id) == 880,
    "receipt child TID offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_runtime_stage_receipt_v2,
                              sequence) == 888,
    "receipt sequence offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_runtime_stage_receipt_v2,
                              input_digest) == 912,
    "receipt input digest offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_runtime_stage_receipt_v2,
                              terminal_tombstone_digest) == 976,
    "terminal tombstone offset drift");
WLGR_V2_STATIC_ASSERT(offsetof(westlake_a02_prerequisite_bundle_v2,
                              receipts) == 896,
    "A02 receipt array offset drift");
WLGR_V2_STATIC_ASSERT(WLGR_V2_A02_PREREQUISITE_COUNT == 6,
    "A02 prerequisite count must cover T03 and T07 through T11 exactly");

#if defined(__cplusplus)
} /* extern "C" */
#endif

#endif /* WESTLAKE_GENERATION_RECEIPT_V2_H */
