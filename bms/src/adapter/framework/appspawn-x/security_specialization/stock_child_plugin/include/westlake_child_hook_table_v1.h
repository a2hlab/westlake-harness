#ifndef WESTLAKE_CHILD_HOOK_TABLE_V1_H
#define WESTLAKE_CHILD_HOOK_TABLE_V1_H

/*
 * Fn02-CHILD-HOOK-TABLE-V1 shared ABI.
 *
 * Design authority:
 *   spec/concepts/Fn02/child-hook-table.yaml
 *   SHA-256 12e3f5e6a592d227a9a91b85ca696d56901d82d249d5b976063ee7a869b1d6ec
 *
 * The table is populated in one specialized child, validated completely, and
 * release-published once.  It is immutable after publication.  Mutable
 * lifecycle and call-accounting words live in the separate control object and
 * must be accessed atomically by the implementation lane.
 */

#include <stddef.h>
#include <stdint.h>

#if defined(__cplusplus)
#define WESTLAKE_CHILD_HOOK_STATIC_ASSERT(condition, message) \
    static_assert((condition), message)
#define WESTLAKE_CHILD_HOOK_ALIGNAS(alignment) alignas(alignment)
#define WESTLAKE_CHILD_HOOK_ALIGNOF(type) alignof(type)
extern "C" {
#else
#define WESTLAKE_CHILD_HOOK_STATIC_ASSERT(condition, message) \
    _Static_assert((condition), message)
#define WESTLAKE_CHILD_HOOK_ALIGNAS(alignment) _Alignas(alignment)
#define WESTLAKE_CHILD_HOOK_ALIGNOF(type) _Alignof(type)
#endif

#define WESTLAKE_CHILD_HOOK_TABLE_V1_MAGIC UINT64_C(0x574c484f4f4b5631)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MAJOR UINT16_C(1)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MINOR UINT16_C(0)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE UINT32_C(32)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_CAPABILITY_COUNT UINT32_C(10)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_KNOWN_PREFIX_SIZE UINT32_C(160)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_MAX_STRUCT_SIZE UINT32_C(256)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT UINT32_C(8)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_POINTER_SIZE UINT16_C(8)
#define WESTLAKE_CHILD_HOOK_TABLE_V1_SCHEMA_SHA256_HEX \
    "12e3f5e6a592d227a9a91b85ca696d56901d82d249d5b976063ee7a869b1d6ec"

/* Capability bit positions are ABI, not an implementation-owned enum. */
typedef enum westlake_child_hook_capability_v1 {
    WESTLAKE_CHILD_HOOK_CAP_THREAD_CREATE = 0,
    WESTLAKE_CHILD_HOOK_CAP_THREAD_JOIN = 1,
    WESTLAKE_CHILD_HOOK_CAP_THREAD_DETACH = 2,
    WESTLAKE_CHILD_HOOK_CAP_THREAD_SELF = 3,
    WESTLAKE_CHILD_HOOK_CAP_TLS_KEY_CREATE = 4,
    WESTLAKE_CHILD_HOOK_CAP_TLS_GET_SET = 5,
    WESTLAKE_CHILD_HOOK_CAP_SIGNAL_ROUTE = 6,
    WESTLAKE_CHILD_HOOK_CAP_ALLOCATOR_DOMAIN = 7,
    WESTLAKE_CHILD_HOOK_CAP_UNWIND_DOMAIN = 8,
    WESTLAKE_CHILD_HOOK_CAP_CPP_RUNTIME_DOMAIN = 9
} westlake_child_hook_capability_v1;

#define WESTLAKE_CHILD_HOOK_CAPABILITY_BIT(id) (UINT64_C(1) << (id))
#define WESTLAKE_CHILD_HOOK_THREAD_TLS_SIGNAL_BITMAP UINT64_C(0x000000000000007f)
#define WESTLAKE_CHILD_HOOK_ALLOCATOR_BITMAP UINT64_C(0x0000000000000080)
#define WESTLAKE_CHILD_HOOK_UNWIND_CPP_BITMAP UINT64_C(0x0000000000000300)
#define WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP UINT64_C(0x00000000000003ff)
#define WESTLAKE_CHILD_HOOK_KNOWN_BITMAP WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP

typedef enum westlake_child_hook_owner_partition_v1 {
    WESTLAKE_CHILD_HOOK_OWNER_THREAD_TLS_SIGNAL = 1,
    WESTLAKE_CHILD_HOOK_OWNER_ALLOCATOR = 2,
    WESTLAKE_CHILD_HOOK_OWNER_UNWIND_CPP = 3
} westlake_child_hook_owner_partition_v1;

typedef enum westlake_child_hook_lifecycle_v1 {
    WESTLAKE_CHILD_HOOK_UNPUBLISHED = 0,
    WESTLAKE_CHILD_HOOK_INSTALLING = 1,
    WESTLAKE_CHILD_HOOK_READY = 2,
    WESTLAKE_CHILD_HOOK_REVOKING = 3,
    WESTLAKE_CHILD_HOOK_DRAINING = 4,
    WESTLAKE_CHILD_HOOK_INVALID = 5
} westlake_child_hook_lifecycle_v1;

typedef enum westlake_child_hook_status_v1 {
    WESTLAKE_CHILD_HOOK_OK = 0,
    WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT = -1,
    WESTLAKE_CHILD_HOOK_INSTALL_RACE = -2,
    WESTLAKE_CHILD_HOOK_TABLE_REJECTED = -3,
    WESTLAKE_CHILD_HOOK_GENERATION_STALE = -4,
    WESTLAKE_CHILD_HOOK_OWNER_MISMATCH = -5,
    WESTLAKE_CHILD_HOOK_REVOKED = -6,
    WESTLAKE_CHILD_HOOK_REVOKE_CONFLICT = -7,
    WESTLAKE_CHILD_HOOK_DRAIN_TIMEOUT = -8,
    WESTLAKE_CHILD_HOOK_INVALIDATE_TIMEOUT = -9,
    WESTLAKE_CHILD_HOOK_CAPACITY_EXHAUSTED = -10,
    WESTLAKE_CHILD_HOOK_TOKEN_INVALID = -11
} westlake_child_hook_status_v1;

typedef enum westlake_child_hook_tls_operation_v1 {
    WESTLAKE_CHILD_HOOK_TLS_GET = 0,
    WESTLAKE_CHILD_HOOK_TLS_SET = 1
} westlake_child_hook_tls_operation_v1;

typedef enum westlake_child_hook_allocator_operation_v1 {
    WESTLAKE_CHILD_HOOK_ALLOCATE = 0,
    WESTLAKE_CHILD_HOOK_REALLOCATE = 1,
    WESTLAKE_CHILD_HOOK_FREE = 2
} westlake_child_hook_allocator_operation_v1;

/*
 * Tokens are opaque registry identities scoped to the table's exact 32-byte
 * generation digest and monotonic child epoch.  A token value is never a
 * pthread/TLS/allocator/signal/unwind/C++/JNI pointer encoded as an integer.
 */
typedef struct westlake_child_hook_token_v1 {
    uint64_t opaque_id;
} westlake_child_hook_token_v1;

typedef struct westlake_child_hook_result_v1 {
    int32_t status;
    uint32_t reserved_zero;
    westlake_child_hook_token_v1 value;
} westlake_child_hook_result_v1;

typedef westlake_child_hook_result_v1 (*westlake_child_hook_thread_create_v1)(
    westlake_child_hook_token_v1 entry_token,
    westlake_child_hook_token_v1 argument_token,
    westlake_child_hook_token_v1 attributes_token);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_thread_join_v1)(
    westlake_child_hook_token_v1 thread_token);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_thread_detach_v1)(
    westlake_child_hook_token_v1 thread_token);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_thread_self_v1)(void);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_tls_key_create_v1)(
    westlake_child_hook_token_v1 destructor_token);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_tls_get_set_v1)(
    westlake_child_hook_token_v1 key_token,
    westlake_child_hook_token_v1 value_token,
    uint32_t operation);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_signal_route_v1)(
    int32_t signal_number,
    westlake_child_hook_token_v1 disposition_token,
    westlake_child_hook_token_v1 mask_token);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_allocator_domain_v1)(
    westlake_child_hook_token_v1 domain_token,
    westlake_child_hook_token_v1 pointer_token,
    uint64_t size,
    uint64_t alignment,
    uint32_t operation);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_unwind_domain_v1)(
    uint32_t operation,
    westlake_child_hook_token_v1 context_token,
    westlake_child_hook_token_v1 frame_sink_token);
typedef westlake_child_hook_result_v1 (*westlake_child_hook_cpp_runtime_domain_v1)(
    uint32_t operation,
    westlake_child_hook_token_v1 object_token,
    westlake_child_hook_token_v1 type_token);

typedef struct westlake_child_hook_callbacks_v1 {
    westlake_child_hook_thread_create_v1 thread_create;
    westlake_child_hook_thread_join_v1 thread_join;
    westlake_child_hook_thread_detach_v1 thread_detach;
    westlake_child_hook_thread_self_v1 thread_self;
    westlake_child_hook_tls_key_create_v1 tls_key_create;
    westlake_child_hook_tls_get_set_v1 tls_get_set;
    westlake_child_hook_signal_route_v1 signal_route;
    westlake_child_hook_allocator_domain_v1 allocator_domain;
    westlake_child_hook_unwind_domain_v1 unwind_domain;
    westlake_child_hook_cpp_runtime_domain_v1 cpp_runtime_domain;
} westlake_child_hook_callbacks_v1;

/*
 * Immutable table.  The first 72 bytes exactly follow the design header-field
 * order.  The 8-byte bounded tail metadata makes data/function pointer size
 * and alignment explicit before the ten fixed capability slots.
 */
typedef struct westlake_child_hook_table_v1 {
    uint64_t magic;
    uint16_t abi_major;
    uint16_t abi_minor;
    uint32_t struct_size;
    uint32_t struct_alignment;
    uint64_t capability_bitmap;
    uint8_t generation_digest[WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE];
    uint64_t owner_cookie;
    uint16_t data_pointer_size;
    uint16_t data_pointer_alignment;
    uint16_t function_pointer_size;
    uint16_t function_pointer_alignment;
    westlake_child_hook_thread_create_v1 thread_create;
    westlake_child_hook_thread_join_v1 thread_join;
    westlake_child_hook_thread_detach_v1 thread_detach;
    westlake_child_hook_thread_self_v1 thread_self;
    westlake_child_hook_tls_key_create_v1 tls_key_create;
    westlake_child_hook_tls_get_set_v1 tls_get_set;
    westlake_child_hook_signal_route_v1 signal_route;
    westlake_child_hook_allocator_domain_v1 allocator_domain;
    westlake_child_hook_unwind_domain_v1 unwind_domain;
    westlake_child_hook_cpp_runtime_domain_v1 cpp_runtime_domain;
} westlake_child_hook_table_v1;

/*
 * Mutable child-local control plane.  Each atomic_* member has a fixed
 * uint64_t representation so this layout is identical in C and C++; all
 * accesses must use acquire/release/CAS atomics in the implementation.
 * atomic_published_table_address may hold only this ABI table's child-local
 * address; it is not a foreign-runtime object token.
 */
typedef struct westlake_child_hook_control_v1 {
    uint64_t magic;
    uint16_t abi_major;
    uint16_t abi_minor;
    uint32_t struct_size;
    uint32_t struct_alignment;
    uint16_t data_pointer_size;
    uint16_t data_pointer_alignment;
    uint8_t generation_digest[WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE];
    uint64_t owner_cookie;
    uint64_t child_epoch;
    WESTLAKE_CHILD_HOOK_ALIGNAS(8) uint64_t atomic_published_table_address;
    WESTLAKE_CHILD_HOOK_ALIGNAS(8) uint64_t atomic_lifecycle_state;
    WESTLAKE_CHILD_HOOK_ALIGNAS(8) uint64_t atomic_admission_open;
    WESTLAKE_CHILD_HOOK_ALIGNAS(8) uint64_t atomic_inflight_count;
    WESTLAKE_CHILD_HOOK_ALIGNAS(8) int64_t atomic_first_cause;
} westlake_child_hook_control_v1;

typedef struct westlake_child_hook_lease_v1 {
    uint8_t generation_digest[WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE];
    uint64_t child_epoch;
    const westlake_child_hook_table_v1 *table;
    westlake_child_hook_token_v1 lease_token;
} westlake_child_hook_lease_v1;

/* Lifecycle implementation belongs to the later implementation lanes. */
int32_t westlake_child_hook_table_v1_begin_install(
    westlake_child_hook_control_v1 *control,
    const westlake_child_hook_table_v1 *candidate,
    uint64_t child_epoch);
int32_t westlake_child_hook_table_v1_prepare_candidate_with_callbacks(
    westlake_child_hook_table_v1 *candidate,
    const uint8_t generation_digest[
        WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE],
    uint64_t owner_cookie,
    const westlake_child_hook_callbacks_v1 *callbacks);
int32_t westlake_child_hook_table_v1_publish(
    westlake_child_hook_control_v1 *control,
    const westlake_child_hook_table_v1 *candidate);
int32_t westlake_child_hook_table_v1_revoke(
    westlake_child_hook_control_v1 *control,
    int32_t first_cause);
int32_t westlake_child_hook_table_v1_drain(
    westlake_child_hook_control_v1 *control);
int32_t westlake_child_hook_table_v1_invalidate(
    westlake_child_hook_control_v1 *control,
    uint32_t child_fail_stop);
int32_t westlake_child_hook_table_v1_record_first_cause(
    westlake_child_hook_control_v1 *control,
    int32_t first_cause);
int32_t westlake_child_hook_table_v1_admit(
    westlake_child_hook_control_v1 *control,
    const uint8_t generation_digest[
        WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE],
    westlake_child_hook_lease_v1 *lease);
int32_t westlake_child_hook_table_v1_release(
    westlake_child_hook_control_v1 *control,
    westlake_child_hook_lease_v1 *lease);

WESTLAKE_CHILD_HOOK_STATIC_ASSERT(sizeof(void *) == 8,
    "Fn02 child-hook ABI requires 64-bit data pointers");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    sizeof(westlake_child_hook_thread_create_v1) == 8,
    "Fn02 child-hook ABI requires 64-bit function pointers");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(WESTLAKE_CHILD_HOOK_ALIGNOF(void *) == 8,
    "Fn02 child-hook ABI requires 8-byte data-pointer alignment");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_ALIGNOF(westlake_child_hook_thread_create_v1) == 8,
    "Fn02 child-hook ABI requires 8-byte function-pointer alignment");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(sizeof(westlake_child_hook_token_v1) == 8,
    "opaque token ABI drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(sizeof(westlake_child_hook_result_v1) == 16,
    "hook result ABI drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, magic) == 0,
    "table magic offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, abi_major) == 8,
    "table ABI-major offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, struct_size) == 12,
    "table size offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, struct_alignment) == 16,
    "table alignment offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, capability_bitmap) == 24,
    "table capability offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, generation_digest) == 32,
    "table generation-digest offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, owner_cookie) == 64,
    "table owner-cookie offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, thread_create) == 80,
    "table capability-slot offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(offsetof(westlake_child_hook_table_v1, cpp_runtime_domain) == 152,
    "table final capability-slot offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(sizeof(westlake_child_hook_table_v1) ==
    WESTLAKE_CHILD_HOOK_TABLE_V1_KNOWN_PREFIX_SIZE,
    "Fn02 child-hook table size drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_ALIGNOF(westlake_child_hook_table_v1) ==
        WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT,
    "Fn02 child-hook table alignment drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(sizeof(westlake_child_hook_control_v1) == 112,
    "Fn02 child-hook control size drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    offsetof(westlake_child_hook_control_v1, atomic_published_table_address) == 72,
    "control publication offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    offsetof(westlake_child_hook_control_v1, atomic_first_cause) == 104,
    "control first-cause offset drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(sizeof(westlake_child_hook_lease_v1) == 56,
    "Fn02 child-hook lease size drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    (WESTLAKE_CHILD_HOOK_THREAD_TLS_SIGNAL_BITMAP |
     WESTLAKE_CHILD_HOOK_ALLOCATOR_BITMAP |
     WESTLAKE_CHILD_HOOK_UNWIND_CPP_BITMAP) ==
        WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP,
    "Fn02 capability-owner partition drift");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    (WESTLAKE_CHILD_HOOK_THREAD_TLS_SIGNAL_BITMAP &
     WESTLAKE_CHILD_HOOK_ALLOCATOR_BITMAP) == 0 &&
    (WESTLAKE_CHILD_HOOK_THREAD_TLS_SIGNAL_BITMAP &
     WESTLAKE_CHILD_HOOK_UNWIND_CPP_BITMAP) == 0 &&
    (WESTLAKE_CHILD_HOOK_ALLOCATOR_BITMAP &
     WESTLAKE_CHILD_HOOK_UNWIND_CPP_BITMAP) == 0,
    "Fn02 capability-owner partitions must be disjoint");

#if defined(__cplusplus)
} /* extern "C" */
#endif

#endif /* WESTLAKE_CHILD_HOOK_TABLE_V1_H */
