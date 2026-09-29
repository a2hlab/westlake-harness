#include "westlake_child_hook_table_v1.h"

#include <stdint.h>
#include <string.h>

/*
 * The V1 control object has a deliberately fixed ABI and therefore cannot
 * grow an unbounded registry.  Admission is capped here and every admitted
 * lease consumes exactly one count until release.
 */
#define WESTLAKE_CHILD_HOOK_MAX_INFLIGHT UINT64_C(1024)
#define WESTLAKE_CHILD_HOOK_LEASE_RESERVED UINT64_MAX

typedef struct westlake_child_hook_lease_record_v1 {
    uint64_t atomic_token;
    uint8_t generation_digest[
        WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE];
    uint64_t child_epoch;
    const westlake_child_hook_table_v1 *table;
} westlake_child_hook_lease_record_v1;

static uint64_t g_lease_sequence = UINT64_C(1);
static westlake_child_hook_lease_record_v1
    g_lease_records[WESTLAKE_CHILD_HOOK_MAX_INFLIGHT];

static int BytesAllZero(const uint8_t *bytes, size_t size)
{
    uint8_t value = UINT8_C(0);
    size_t index;

    for (index = 0; index < size; ++index) {
        value = (uint8_t)(value | bytes[index]);
    }
    return value == UINT8_C(0);
}

static int BytesEqual(const uint8_t *left, const uint8_t *right, size_t size)
{
    uint8_t difference = UINT8_C(0);
    size_t index;

    for (index = 0; index < size; ++index) {
        difference = (uint8_t)(difference | (left[index] ^ right[index]));
    }
    return difference == UINT8_C(0);
}

static westlake_child_hook_result_v1 RejectedResult(void)
{
    westlake_child_hook_result_v1 result;

    result.status = WESTLAKE_CHILD_HOOK_TABLE_REJECTED;
    result.reserved_zero = UINT32_C(0);
    result.value.opaque_id = UINT64_C(0);
    return result;
}

/*
 * These ten entries are intentionally typed fail-closed boundaries.  The
 * frozen table can be published and its owner partition mechanically audited
 * before a provider is mapped, while no placeholder is allowed to fabricate
 * a thread, TLS, allocator, signal, unwind, or C++ success.  Owner-local token
 * registries replace these entries only as a whole sealed generation.
 */
static westlake_child_hook_result_v1 ThreadCreateRejected(
    westlake_child_hook_token_v1 entry_token,
    westlake_child_hook_token_v1 argument_token,
    westlake_child_hook_token_v1 attributes_token)
{
    (void)entry_token;
    (void)argument_token;
    (void)attributes_token;
    return RejectedResult();
}

static westlake_child_hook_result_v1 ThreadJoinRejected(
    westlake_child_hook_token_v1 thread_token)
{
    (void)thread_token;
    return RejectedResult();
}

static westlake_child_hook_result_v1 ThreadDetachRejected(
    westlake_child_hook_token_v1 thread_token)
{
    (void)thread_token;
    return RejectedResult();
}

static westlake_child_hook_result_v1 ThreadSelfRejected(void)
{
    return RejectedResult();
}

static westlake_child_hook_result_v1 TlsKeyCreateRejected(
    westlake_child_hook_token_v1 destructor_token)
{
    (void)destructor_token;
    return RejectedResult();
}

static westlake_child_hook_result_v1 TlsGetSetRejected(
    westlake_child_hook_token_v1 key_token,
    westlake_child_hook_token_v1 value_token,
    uint32_t operation)
{
    (void)key_token;
    (void)value_token;
    (void)operation;
    return RejectedResult();
}

static westlake_child_hook_result_v1 SignalRouteRejected(
    int32_t signal_number,
    westlake_child_hook_token_v1 disposition_token,
    westlake_child_hook_token_v1 mask_token)
{
    (void)signal_number;
    (void)disposition_token;
    (void)mask_token;
    return RejectedResult();
}

static westlake_child_hook_result_v1 AllocatorDomainRejected(
    westlake_child_hook_token_v1 domain_token,
    westlake_child_hook_token_v1 pointer_token,
    uint64_t size,
    uint64_t alignment,
    uint32_t operation)
{
    (void)domain_token;
    (void)pointer_token;
    (void)size;
    (void)alignment;
    (void)operation;
    return RejectedResult();
}

static westlake_child_hook_result_v1 UnwindDomainRejected(
    uint32_t operation,
    westlake_child_hook_token_v1 context_token,
    westlake_child_hook_token_v1 frame_sink_token)
{
    (void)operation;
    (void)context_token;
    (void)frame_sink_token;
    return RejectedResult();
}

static westlake_child_hook_result_v1 CppRuntimeDomainRejected(
    uint32_t operation,
    westlake_child_hook_token_v1 object_token,
    westlake_child_hook_token_v1 type_token)
{
    (void)operation;
    (void)object_token;
    (void)type_token;
    return RejectedResult();
}

/* Private same-binary construction seam; it is not part of the exported ABI. */
int32_t westlake_child_hook_table_v1_prepare_candidate(
    westlake_child_hook_table_v1 *candidate,
    const uint8_t generation_digest[
        WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE],
    uint64_t owner_cookie)
{
    if (candidate == (westlake_child_hook_table_v1 *)0 ||
        generation_digest == (const uint8_t *)0 ||
        BytesAllZero(generation_digest,
                     WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE) ||
        owner_cookie == UINT64_C(0)) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }

    memset(candidate, 0, sizeof(*candidate));
    candidate->magic = WESTLAKE_CHILD_HOOK_TABLE_V1_MAGIC;
    candidate->abi_major = WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MAJOR;
    candidate->abi_minor = WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MINOR;
    candidate->struct_size = (uint32_t)sizeof(*candidate);
    candidate->struct_alignment =
        WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT;
    candidate->capability_bitmap = WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP;
    memcpy(candidate->generation_digest, generation_digest,
           WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE);
    candidate->owner_cookie = owner_cookie;
    candidate->data_pointer_size = (uint16_t)sizeof(void *);
    candidate->data_pointer_alignment =
        (uint16_t)WESTLAKE_CHILD_HOOK_ALIGNOF(void *);
    candidate->function_pointer_size =
        (uint16_t)sizeof(westlake_child_hook_thread_create_v1);
    candidate->function_pointer_alignment =
        (uint16_t)WESTLAKE_CHILD_HOOK_ALIGNOF(
            westlake_child_hook_thread_create_v1);

    /* Fn02.A14: seven thread/TLS/signal capabilities. */
    candidate->thread_create = ThreadCreateRejected;
    candidate->thread_join = ThreadJoinRejected;
    candidate->thread_detach = ThreadDetachRejected;
    candidate->thread_self = ThreadSelfRejected;
    candidate->tls_key_create = TlsKeyCreateRejected;
    candidate->tls_get_set = TlsGetSetRejected;
    candidate->signal_route = SignalRouteRejected;
    /* Fn02.A15: exactly one allocator capability. */
    candidate->allocator_domain = AllocatorDomainRejected;
    /* Fn02.A16: exactly two unwind/C++ capabilities. */
    candidate->unwind_domain = UnwindDomainRejected;
    candidate->cpp_runtime_domain = CppRuntimeDomainRejected;
    return WESTLAKE_CHILD_HOOK_OK;
}

static int CandidateValid(const westlake_child_hook_table_v1 *candidate)
{
    return candidate != (const westlake_child_hook_table_v1 *)0 &&
        ((uintptr_t)candidate %
             WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT) == 0U &&
        candidate->magic == WESTLAKE_CHILD_HOOK_TABLE_V1_MAGIC &&
        candidate->abi_major == WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MAJOR &&
        candidate->abi_minor == WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MINOR &&
        candidate->struct_size ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_KNOWN_PREFIX_SIZE &&
        candidate->struct_size <=
            WESTLAKE_CHILD_HOOK_TABLE_V1_MAX_STRUCT_SIZE &&
        candidate->struct_alignment ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT &&
        candidate->capability_bitmap ==
            WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP &&
        (candidate->capability_bitmap &
             ~WESTLAKE_CHILD_HOOK_KNOWN_BITMAP) == UINT64_C(0) &&
        !BytesAllZero(candidate->generation_digest,
                      WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE) &&
        candidate->owner_cookie != UINT64_C(0) &&
        candidate->data_pointer_size ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_POINTER_SIZE &&
        candidate->data_pointer_alignment ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT &&
        candidate->function_pointer_size ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_POINTER_SIZE &&
        candidate->function_pointer_alignment ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT &&
        candidate->thread_create == ThreadCreateRejected &&
        candidate->thread_join == ThreadJoinRejected &&
        candidate->thread_detach == ThreadDetachRejected &&
        candidate->thread_self == ThreadSelfRejected &&
        candidate->tls_key_create == TlsKeyCreateRejected &&
        candidate->tls_get_set == TlsGetSetRejected &&
        candidate->signal_route == SignalRouteRejected &&
        candidate->allocator_domain == AllocatorDomainRejected &&
        candidate->unwind_domain == UnwindDomainRejected &&
        candidate->cpp_runtime_domain == CppRuntimeDomainRejected;
}

static int ControlHeaderValid(const westlake_child_hook_control_v1 *control)
{
    return control != (const westlake_child_hook_control_v1 *)0 &&
        ((uintptr_t)control %
             WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT) == 0U &&
        control->magic == WESTLAKE_CHILD_HOOK_TABLE_V1_MAGIC &&
        control->abi_major == WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MAJOR &&
        control->abi_minor == WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MINOR &&
        control->struct_size == sizeof(*control) &&
        control->struct_alignment ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT &&
        control->data_pointer_size ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_POINTER_SIZE &&
        control->data_pointer_alignment ==
            WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT &&
        !BytesAllZero(control->generation_digest,
                      WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE) &&
        control->owner_cookie != UINT64_C(0) &&
        control->child_epoch != UINT64_C(0);
}

static int SameCandidate(const westlake_child_hook_control_v1 *control,
                         const westlake_child_hook_table_v1 *candidate)
{
    return CandidateValid(candidate) && ControlHeaderValid(control) &&
        control->owner_cookie == candidate->owner_cookie &&
        BytesEqual(control->generation_digest, candidate->generation_digest,
                   WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE);
}

static westlake_child_hook_lease_record_v1 *ReserveLeaseRecord(void)
{
    uint64_t index;

    for (index = UINT64_C(0);
         index < WESTLAKE_CHILD_HOOK_MAX_INFLIGHT; ++index) {
        uint64_t expected = UINT64_C(0);
        if (__atomic_compare_exchange_n(
                &g_lease_records[index].atomic_token, &expected,
                WESTLAKE_CHILD_HOOK_LEASE_RESERVED, 0,
                __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
            return &g_lease_records[index];
        }
    }
    return (westlake_child_hook_lease_record_v1 *)0;
}

static westlake_child_hook_lease_record_v1 *ClaimLeaseRecord(
    uint64_t token)
{
    uint64_t index;

    for (index = UINT64_C(0);
         index < WESTLAKE_CHILD_HOOK_MAX_INFLIGHT; ++index) {
        uint64_t expected = token;
        if (__atomic_compare_exchange_n(
                &g_lease_records[index].atomic_token, &expected,
                WESTLAKE_CHILD_HOOK_LEASE_RESERVED, 0,
                __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
            return &g_lease_records[index];
        }
    }
    return (westlake_child_hook_lease_record_v1 *)0;
}

int32_t westlake_child_hook_table_v1_begin_install(
    westlake_child_hook_control_v1 *control,
    const westlake_child_hook_table_v1 *candidate,
    uint64_t child_epoch)
{
    uint64_t expected = WESTLAKE_CHILD_HOOK_UNPUBLISHED;
    uint64_t state;

    if (control == (westlake_child_hook_control_v1 *)0 ||
        !CandidateValid(candidate) || child_epoch == UINT64_C(0)) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }

    state = __atomic_load_n(&control->atomic_lifecycle_state,
                            __ATOMIC_ACQUIRE);
    if (state == WESTLAKE_CHILD_HOOK_READY &&
        SameCandidate(control, candidate) &&
        control->child_epoch == child_epoch) {
        return WESTLAKE_CHILD_HOOK_OK;
    }
    if (!__atomic_compare_exchange_n(&control->atomic_lifecycle_state,
                                     &expected,
                                     WESTLAKE_CHILD_HOOK_INSTALLING, 0,
                                     __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        return WESTLAKE_CHILD_HOOK_INSTALL_RACE;
    }

    control->magic = WESTLAKE_CHILD_HOOK_TABLE_V1_MAGIC;
    control->abi_major = WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MAJOR;
    control->abi_minor = WESTLAKE_CHILD_HOOK_TABLE_V1_ABI_MINOR;
    control->struct_size = (uint32_t)sizeof(*control);
    control->struct_alignment =
        WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT;
    control->data_pointer_size =
        WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_POINTER_SIZE;
    control->data_pointer_alignment =
        WESTLAKE_CHILD_HOOK_TABLE_V1_REQUIRED_ALIGNMENT;
    memcpy(control->generation_digest, candidate->generation_digest,
           WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE);
    control->owner_cookie = candidate->owner_cookie;
    control->child_epoch = child_epoch;
    __atomic_store_n(&control->atomic_published_table_address, UINT64_C(0),
                     __ATOMIC_RELAXED);
    __atomic_store_n(&control->atomic_admission_open, UINT64_C(0),
                     __ATOMIC_RELAXED);
    __atomic_store_n(&control->atomic_inflight_count, UINT64_C(0),
                     __ATOMIC_RELAXED);
    __atomic_store_n(&control->atomic_first_cause, INT64_C(0),
                     __ATOMIC_RELAXED);
    /* Publish initialized metadata to observers of INSTALLING. */
    __atomic_store_n(&control->atomic_lifecycle_state,
                     WESTLAKE_CHILD_HOOK_INSTALLING, __ATOMIC_RELEASE);
    return WESTLAKE_CHILD_HOOK_OK;
}

int32_t westlake_child_hook_table_v1_publish(
    westlake_child_hook_control_v1 *control,
    const westlake_child_hook_table_v1 *candidate)
{
    uint64_t expected_address = UINT64_C(0);
    uint64_t state;

    if (!SameCandidate(control, candidate)) {
        return WESTLAKE_CHILD_HOOK_TABLE_REJECTED;
    }
    state = __atomic_load_n(&control->atomic_lifecycle_state,
                            __ATOMIC_ACQUIRE);
    if (state == WESTLAKE_CHILD_HOOK_READY &&
        __atomic_load_n(&control->atomic_published_table_address,
                        __ATOMIC_ACQUIRE) == (uint64_t)(uintptr_t)candidate) {
        return WESTLAKE_CHILD_HOOK_OK;
    }
    if (state != WESTLAKE_CHILD_HOOK_INSTALLING ||
        !__atomic_compare_exchange_n(
            &control->atomic_published_table_address, &expected_address,
            (uint64_t)(uintptr_t)candidate, 0,
            __ATOMIC_RELEASE, __ATOMIC_ACQUIRE)) {
        return WESTLAKE_CHILD_HOOK_TABLE_REJECTED;
    }

    __atomic_store_n(&control->atomic_lifecycle_state,
                     WESTLAKE_CHILD_HOOK_READY, __ATOMIC_RELEASE);
    __atomic_store_n(&control->atomic_admission_open, UINT64_C(1),
                     __ATOMIC_RELEASE);
    return WESTLAKE_CHILD_HOOK_OK;
}

int32_t westlake_child_hook_table_v1_record_first_cause(
    westlake_child_hook_control_v1 *control,
    int32_t first_cause)
{
    int64_t expected = INT64_C(0);

    if (!ControlHeaderValid(control) || first_cause >= 0) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }
    (void)__atomic_compare_exchange_n(
        &control->atomic_first_cause, &expected, (int64_t)first_cause, 0,
        __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE);
    return WESTLAKE_CHILD_HOOK_OK;
}

int32_t westlake_child_hook_table_v1_revoke(
    westlake_child_hook_control_v1 *control,
    int32_t first_cause)
{
    uint64_t expected = WESTLAKE_CHILD_HOOK_READY;

    if (!ControlHeaderValid(control) || first_cause >= 0) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }
    if (westlake_child_hook_table_v1_record_first_cause(
            control, first_cause) != WESTLAKE_CHILD_HOOK_OK) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }
    __atomic_store_n(&control->atomic_admission_open, UINT64_C(0),
                     __ATOMIC_RELEASE);
    if (!__atomic_compare_exchange_n(&control->atomic_lifecycle_state,
                                     &expected,
                                     WESTLAKE_CHILD_HOOK_REVOKING, 0,
                                     __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        return WESTLAKE_CHILD_HOOK_REVOKE_CONFLICT;
    }
    return WESTLAKE_CHILD_HOOK_OK;
}

int32_t westlake_child_hook_table_v1_drain(
    westlake_child_hook_control_v1 *control)
{
    uint64_t expected = WESTLAKE_CHILD_HOOK_REVOKING;
    uint64_t state;

    if (!ControlHeaderValid(control)) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }
    state = __atomic_load_n(&control->atomic_lifecycle_state,
                            __ATOMIC_ACQUIRE);
    if (state == WESTLAKE_CHILD_HOOK_REVOKING) {
        if (!__atomic_compare_exchange_n(&control->atomic_lifecycle_state,
                                         &expected,
                                         WESTLAKE_CHILD_HOOK_DRAINING, 0,
                                         __ATOMIC_ACQ_REL,
                                         __ATOMIC_ACQUIRE)) {
            return WESTLAKE_CHILD_HOOK_REVOKE_CONFLICT;
        }
    } else if (state != WESTLAKE_CHILD_HOOK_DRAINING) {
        return WESTLAKE_CHILD_HOOK_REVOKE_CONFLICT;
    }
    if (__atomic_load_n(&control->atomic_inflight_count,
                        __ATOMIC_ACQUIRE) != UINT64_C(0)) {
        return WESTLAKE_CHILD_HOOK_DRAIN_TIMEOUT;
    }
    return WESTLAKE_CHILD_HOOK_OK;
}

int32_t westlake_child_hook_table_v1_invalidate(
    westlake_child_hook_control_v1 *control,
    uint32_t child_fail_stop)
{
    uint64_t expected = WESTLAKE_CHILD_HOOK_DRAINING;

    if (!ControlHeaderValid(control) || child_fail_stop > UINT32_C(1)) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }
    if (__atomic_load_n(&control->atomic_lifecycle_state,
                        __ATOMIC_ACQUIRE) !=
            WESTLAKE_CHILD_HOOK_DRAINING) {
        return WESTLAKE_CHILD_HOOK_REVOKE_CONFLICT;
    }
    if (__atomic_load_n(&control->atomic_inflight_count,
                        __ATOMIC_ACQUIRE) != UINT64_C(0) &&
        child_fail_stop == UINT32_C(0)) {
        return WESTLAKE_CHILD_HOOK_INVALIDATE_TIMEOUT;
    }

    __atomic_store_n(&control->atomic_admission_open, UINT64_C(0),
                     __ATOMIC_RELEASE);
    __atomic_store_n(&control->atomic_published_table_address, UINT64_C(0),
                     __ATOMIC_RELEASE);
    if (!__atomic_compare_exchange_n(&control->atomic_lifecycle_state,
                                     &expected,
                                     WESTLAKE_CHILD_HOOK_INVALID, 0,
                                     __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        return WESTLAKE_CHILD_HOOK_REVOKE_CONFLICT;
    }
    return WESTLAKE_CHILD_HOOK_OK;
}

int32_t westlake_child_hook_table_v1_admit(
    westlake_child_hook_control_v1 *control,
    const uint8_t generation_digest[
        WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE],
    westlake_child_hook_lease_v1 *lease)
{
    uint64_t prior_inflight;
    uint64_t published_address;
    uint64_t token;
    westlake_child_hook_lease_record_v1 *record;

    if (!ControlHeaderValid(control) ||
        generation_digest == (const uint8_t *)0 ||
        lease == (westlake_child_hook_lease_v1 *)0) {
        return WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
    }
    memset(lease, 0, sizeof(*lease));

    if (!BytesEqual(control->generation_digest, generation_digest,
                    WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE)) {
        return WESTLAKE_CHILD_HOOK_GENERATION_STALE;
    }
    if (__atomic_load_n(&control->atomic_lifecycle_state,
                        __ATOMIC_ACQUIRE) != WESTLAKE_CHILD_HOOK_READY ||
        __atomic_load_n(&control->atomic_admission_open,
                        __ATOMIC_ACQUIRE) != UINT64_C(1)) {
        return WESTLAKE_CHILD_HOOK_REVOKED;
    }

    prior_inflight = __atomic_fetch_add(&control->atomic_inflight_count,
                                        UINT64_C(1), __ATOMIC_ACQ_REL);
    if (prior_inflight >= WESTLAKE_CHILD_HOOK_MAX_INFLIGHT) {
        (void)__atomic_fetch_sub(&control->atomic_inflight_count,
                                 UINT64_C(1), __ATOMIC_ACQ_REL);
        return WESTLAKE_CHILD_HOOK_CAPACITY_EXHAUSTED;
    }

    published_address = __atomic_load_n(
        &control->atomic_published_table_address, __ATOMIC_ACQUIRE);
    if (__atomic_load_n(&control->atomic_lifecycle_state,
                        __ATOMIC_ACQUIRE) != WESTLAKE_CHILD_HOOK_READY ||
        __atomic_load_n(&control->atomic_admission_open,
                        __ATOMIC_ACQUIRE) != UINT64_C(1) ||
        published_address == UINT64_C(0) ||
        !BytesEqual(control->generation_digest, generation_digest,
                    WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE)) {
        (void)__atomic_fetch_sub(&control->atomic_inflight_count,
                                 UINT64_C(1), __ATOMIC_ACQ_REL);
        return WESTLAKE_CHILD_HOOK_REVOKED;
    }

    record = ReserveLeaseRecord();
    if (record == (westlake_child_hook_lease_record_v1 *)0) {
        (void)__atomic_fetch_sub(&control->atomic_inflight_count,
                                 UINT64_C(1), __ATOMIC_ACQ_REL);
        return WESTLAKE_CHILD_HOOK_CAPACITY_EXHAUSTED;
    }
    token = __atomic_fetch_add(&g_lease_sequence, UINT64_C(1),
                               __ATOMIC_RELAXED);
    while (token == UINT64_C(0) ||
           token == WESTLAKE_CHILD_HOOK_LEASE_RESERVED) {
        token = __atomic_fetch_add(&g_lease_sequence, UINT64_C(1),
                                   __ATOMIC_RELAXED);
    }
    memcpy(record->generation_digest, generation_digest,
           WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE);
    record->child_epoch = control->child_epoch;
    record->table = (const westlake_child_hook_table_v1 *)(uintptr_t)
        published_address;
    __atomic_store_n(&record->atomic_token, token, __ATOMIC_RELEASE);
    memcpy(lease->generation_digest, generation_digest,
           WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE);
    lease->child_epoch = control->child_epoch;
    lease->table = (const westlake_child_hook_table_v1 *)(uintptr_t)
        published_address;
    lease->lease_token.opaque_id = token;
    return WESTLAKE_CHILD_HOOK_OK;
}

int32_t westlake_child_hook_table_v1_release(
    westlake_child_hook_control_v1 *control,
    westlake_child_hook_lease_v1 *lease)
{
    uint64_t published_address;
    uint64_t inflight;
    westlake_child_hook_lease_record_v1 *record;

    if (!ControlHeaderValid(control) ||
        lease == (westlake_child_hook_lease_v1 *)0 ||
        lease->lease_token.opaque_id == UINT64_C(0) ||
        lease->table == (const westlake_child_hook_table_v1 *)0) {
        return WESTLAKE_CHILD_HOOK_TOKEN_INVALID;
    }
    published_address = __atomic_load_n(
        &control->atomic_published_table_address, __ATOMIC_ACQUIRE);
    if (published_address == UINT64_C(0) ||
        lease->table !=
            (const westlake_child_hook_table_v1 *)(uintptr_t)
                published_address ||
        lease->child_epoch != control->child_epoch ||
        !BytesEqual(lease->generation_digest, control->generation_digest,
                    WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE)) {
        return WESTLAKE_CHILD_HOOK_GENERATION_STALE;
    }
    record = ClaimLeaseRecord(lease->lease_token.opaque_id);
    if (record == (westlake_child_hook_lease_record_v1 *)0) {
        return WESTLAKE_CHILD_HOOK_TOKEN_INVALID;
    }
    if (record->table != lease->table ||
        record->child_epoch != lease->child_epoch ||
        !BytesEqual(record->generation_digest, lease->generation_digest,
                    WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE)) {
        __atomic_store_n(&record->atomic_token,
                         lease->lease_token.opaque_id, __ATOMIC_RELEASE);
        return WESTLAKE_CHILD_HOOK_TOKEN_INVALID;
    }
    inflight = __atomic_load_n(&control->atomic_inflight_count,
                               __ATOMIC_ACQUIRE);
    do {
        if (inflight == UINT64_C(0)) {
            __atomic_store_n(&record->atomic_token,
                             lease->lease_token.opaque_id,
                             __ATOMIC_RELEASE);
            return WESTLAKE_CHILD_HOOK_TOKEN_INVALID;
        }
    } while (!__atomic_compare_exchange_n(
        &control->atomic_inflight_count, &inflight, inflight - UINT64_C(1),
        0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE));

    memset(record->generation_digest, 0, sizeof(record->generation_digest));
    record->child_epoch = UINT64_C(0);
    record->table = (const westlake_child_hook_table_v1 *)0;
    __atomic_store_n(&record->atomic_token, UINT64_C(0), __ATOMIC_RELEASE);
    memset(lease, 0, sizeof(*lease));
    return WESTLAKE_CHILD_HOOK_OK;
}
