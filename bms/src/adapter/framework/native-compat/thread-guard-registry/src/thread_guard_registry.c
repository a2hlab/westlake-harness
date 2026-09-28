#include "thread_guard_registry_internal.h"

#include <stdatomic.h>
#include <stdbool.h>

#if ATOMIC_INT_LOCK_FREE != 2 || ATOMIC_LLONG_LOCK_FREE != 2 || \
    ATOMIC_POINTER_LOCK_FREE != 2
#error "thread guard registry requires always-lock-free scalar atomics"
#endif

typedef struct WltgRecord {
    _Atomic uint32_t state;
    _Atomic uint32_t admission_kind;
    _Atomic uint32_t role;
    _Atomic uint32_t capacity_held;
    _Atomic uint64_t ticket_id;
    _Atomic uint64_t one_shot_nonce;
    _Atomic uint64_t adapter_generation;
    _Atomic uint64_t process_epoch;
    _Atomic uint64_t policy_epoch;
    _Atomic uint64_t issuer_thread_id;
    _Atomic uint64_t current_thread_id;
    _Atomic uint64_t owner_cookie;
    _Atomic uintptr_t written_address;
    _Atomic uint32_t tp_offset;
    _Atomic uint32_t width;
    _Atomic uint64_t publication_sequence;
    _Atomic uint64_t guard_value;
} WltgRecord;

typedef struct WltgOwner {
    _Atomic uint32_t fork_seeded;
    _Atomic uint32_t arm_gate;
    _Atomic uint32_t main_ticket_issued;
    _Atomic uint32_t active_ticket_count;
    _Atomic uint64_t process_status;
    _Atomic uint64_t adapter_generation;
    _Atomic uint64_t process_epoch;
    _Atomic uint64_t policy_epoch;
    _Atomic uint64_t next_ticket_id;
    _Atomic uint64_t audit_sequence;
    _Atomic uint64_t audit_drop_count;
    _Atomic uint64_t publication_sequence;
    _Atomic uint64_t process_guard;
    WltgProcessBindingV1 binding;
    WltgPlatformOpsV1 ops;
    WltgRecord records[WLTG_MAX_THREAD_RECORDS];
} WltgOwner;

/* One adapter-owned process registry. It owns no pthread object and no TLS. */
static WltgOwner g_wltg_owner;

static uint64_t WltgPackProcessStatus(WltgProcessState state,
                                      WltgReason reason)
{
    return ((uint64_t)(uint32_t)reason << UINT32_C(32)) |
           (uint64_t)(uint32_t)state;
}

static WltgProcessState WltgUnpackProcessState(uint64_t packed)
{
    return (WltgProcessState)(uint32_t)packed;
}

static WltgReason WltgUnpackReason(uint64_t packed)
{
    return (WltgReason)(uint32_t)(packed >> UINT32_C(32));
}

static uint64_t WltgLoadProcessStatus(memory_order order)
{
    return atomic_load_explicit(&g_wltg_owner.process_status, order);
}

static WltgProcessState WltgLoadProcessState(memory_order order)
{
    return WltgUnpackProcessState(WltgLoadProcessStatus(order));
}

static bool WltgProcessIsTerminal(WltgProcessState state)
{
    return state == WLTG_PROCESS_REVOKED || state == WLTG_PROCESS_REJECTED;
}

static void WltgClearBytes(void *memory, size_t size)
{
    volatile uint8_t *bytes = (volatile uint8_t *)memory;
    size_t index;
    for (index = 0; index < size; ++index) {
        bytes[index] = UINT8_C(0);
    }
}

static void WltgCopyBytes(uint8_t *destination, const uint8_t *source,
                          size_t size)
{
    size_t index;
    for (index = 0; index < size; ++index) {
        destination[index] = source[index];
    }
}

static bool WltgBytesEqual(const uint8_t *left, const uint8_t *right,
                           size_t size)
{
    uint8_t difference = UINT8_C(0);
    size_t index;
    for (index = 0; index < size; ++index) {
        difference = (uint8_t)(difference |
                               (uint8_t)(left[index] ^ right[index]));
    }
    return difference == UINT8_C(0);
}

static bool WltgBytesAllZero(const uint8_t *bytes, size_t size)
{
    uint8_t combined = UINT8_C(0);
    size_t index;
    for (index = 0; index < size; ++index) {
        combined = (uint8_t)(combined | bytes[index]);
    }
    return combined == UINT8_C(0);
}

static WltgThreadState WltgRecordState(const WltgRecord *record,
                                       memory_order order)
{
    if (record == (const WltgRecord *)0) {
        return WLTG_THREAD_FREE;
    }
    return (WltgThreadState)atomic_load_explicit(&record->state, order);
}

static WltgResult WltgResultValue(WltgStatus status, WltgReason reason,
                                  const WltgRecord *record)
{
    WltgResult result;
    result.status = status;
    result.reason = reason;
    result.process_state = WltgLoadProcessState(memory_order_acquire);
    result.thread_state = WltgRecordState(record, memory_order_acquire);
    return result;
}

static void WltgClearRecord(WltgRecord *record, WltgThreadState final_state)
{
    atomic_store_explicit(&record->admission_kind,
                          (uint32_t)WLTG_ADMISSION_INVALID,
                          memory_order_relaxed);
    atomic_store_explicit(&record->role, (uint32_t)WLTG_THREAD_ROLE_INVALID,
                          memory_order_relaxed);
    atomic_store_explicit(&record->capacity_held, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->ticket_id, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->one_shot_nonce, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->adapter_generation, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->process_epoch, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->policy_epoch, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->issuer_thread_id, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->current_thread_id, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->owner_cookie, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->written_address, (uintptr_t)0,
                          memory_order_relaxed);
    atomic_store_explicit(&record->tp_offset, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->width, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->publication_sequence, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->guard_value, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->state, (uint32_t)final_state,
                          memory_order_release);
}

static bool WltgBindingShapeValid(const WltgProcessBindingV1 *binding)
{
    if (binding == (const WltgProcessBindingV1 *)0 ||
        binding->abi_version != WLTG_ABI_VERSION ||
        binding->struct_size != sizeof(WltgProcessBindingV1) ||
        binding->adapter_generation == UINT64_C(0) ||
        binding->process_epoch == UINT64_C(0) ||
        binding->policy_epoch == UINT64_C(0) ||
        binding->binding_nonce == UINT64_C(0) ||
        binding->reserved_zero != UINT32_C(0) ||
        binding->max_live_threads == UINT32_C(0) ||
        binding->max_live_threads > WLTG_MAX_THREAD_RECORDS) {
        return false;
    }
    if (binding->reservation_tp_start != WLTG_RESERVATION_TP_START ||
        binding->reservation_size != WLTG_RESERVATION_SIZE ||
        binding->stack_guard_tp_offset != WLTG_STACK_GUARD_TP_OFFSET ||
        binding->stack_guard_width != WLTG_STACK_GUARD_WIDTH) {
        return false;
    }
    if (WltgBytesAllZero(binding->profile_digest, WLTG_DIGEST_SIZE) ||
        WltgBytesAllZero(binding->target_digest, WLTG_DIGEST_SIZE)) {
        return false;
    }
    return true;
}

static bool WltgOpsShapeValid(const WltgPlatformOpsV1 *ops)
{
    return ops != (const WltgPlatformOpsV1 *)0 &&
           ops->abi_version == WLTG_ABI_VERSION &&
           ops->struct_size == sizeof(WltgPlatformOpsV1) &&
           ops->verify_process_binding != (WltgVerifyProcessBinding)0 &&
           ops->get_current_thread_id != (WltgGetCurrentThreadId)0 &&
           ops->resolve_current_thread_region !=
               (WltgResolveCurrentThreadRegion)0 &&
           ops->get_os_csprng != (WltgGetOsCsprng)0 &&
           ops->emit_audit_event != (WltgEmitAuditEvent)0;
}

static bool WltgBindingMatches(const WltgProcessBindingV1 *binding)
{
    const WltgProcessBindingV1 *owned = &g_wltg_owner.binding;
    return binding->abi_version == owned->abi_version &&
           binding->struct_size == owned->struct_size &&
           binding->adapter_generation == owned->adapter_generation &&
           binding->process_epoch == owned->process_epoch &&
           binding->policy_epoch == owned->policy_epoch &&
           binding->binding_nonce == owned->binding_nonce &&
           binding->reservation_tp_start == owned->reservation_tp_start &&
           binding->reservation_size == owned->reservation_size &&
           binding->stack_guard_tp_offset == owned->stack_guard_tp_offset &&
           binding->stack_guard_width == owned->stack_guard_width &&
           binding->max_live_threads == owned->max_live_threads &&
           binding->reserved_zero == owned->reserved_zero &&
           WltgBytesEqual(binding->profile_digest, owned->profile_digest,
                          WLTG_DIGEST_SIZE) &&
           WltgBytesEqual(binding->target_digest, owned->target_digest,
                          WLTG_DIGEST_SIZE);
}

static bool WltgOpsMatch(const WltgPlatformOpsV1 *ops)
{
    const WltgPlatformOpsV1 *owned = &g_wltg_owner.ops;
    return ops->abi_version == owned->abi_version &&
           ops->struct_size == owned->struct_size &&
           ops->context == owned->context &&
           ops->verify_process_binding == owned->verify_process_binding &&
           ops->get_current_thread_id == owned->get_current_thread_id &&
           ops->resolve_current_thread_region ==
               owned->resolve_current_thread_region &&
           ops->get_os_csprng == owned->get_os_csprng &&
           ops->emit_audit_event == owned->emit_audit_event;
}

static void WltgCopyBinding(WltgProcessBindingV1 *destination,
                            const WltgProcessBindingV1 *source)
{
    destination->abi_version = source->abi_version;
    destination->struct_size = source->struct_size;
    destination->adapter_generation = source->adapter_generation;
    destination->process_epoch = source->process_epoch;
    destination->policy_epoch = source->policy_epoch;
    destination->binding_nonce = source->binding_nonce;
    WltgCopyBytes(destination->profile_digest, source->profile_digest,
                  WLTG_DIGEST_SIZE);
    WltgCopyBytes(destination->target_digest, source->target_digest,
                  WLTG_DIGEST_SIZE);
    destination->reservation_tp_start = source->reservation_tp_start;
    destination->reservation_size = source->reservation_size;
    destination->stack_guard_tp_offset = source->stack_guard_tp_offset;
    destination->stack_guard_width = source->stack_guard_width;
    destination->max_live_threads = source->max_live_threads;
    destination->reserved_zero = source->reserved_zero;
}

static bool WltgEmit(WltgEventType type, WltgReason reason,
                     const WltgRecord *record)
{
    WltgAuditEvent event;
    uint64_t sequence;
    int accepted;
    sequence = atomic_fetch_add_explicit(&g_wltg_owner.audit_sequence,
                                         UINT64_C(1),
                                         memory_order_relaxed) +
               UINT64_C(1);
    event.abi_version = WLTG_ABI_VERSION;
    event.type = type;
    event.reason = reason;
    event.process_state = WltgLoadProcessState(memory_order_acquire);
    event.thread_state = WltgRecordState(record, memory_order_acquire);
    event.admission_kind = record == (const WltgRecord *)0
                               ? WLTG_ADMISSION_INVALID
                               : (WltgAdmissionKind)atomic_load_explicit(
                                     &record->admission_kind,
                                     memory_order_relaxed);
    event.role = record == (const WltgRecord *)0
                     ? WLTG_THREAD_ROLE_INVALID
                     : (WltgThreadRole)atomic_load_explicit(
                           &record->role, memory_order_relaxed);
    event.reserved_zero = UINT32_C(0);
    event.sequence = sequence;
    event.adapter_generation = record == (const WltgRecord *)0
                                   ? g_wltg_owner.binding.adapter_generation
                                   : atomic_load_explicit(
                                         &record->adapter_generation,
                                         memory_order_relaxed);
    event.process_epoch = record == (const WltgRecord *)0
                              ? g_wltg_owner.binding.process_epoch
                              : atomic_load_explicit(&record->process_epoch,
                                                     memory_order_relaxed);
    event.policy_epoch = record == (const WltgRecord *)0
                             ? g_wltg_owner.binding.policy_epoch
                             : atomic_load_explicit(&record->policy_epoch,
                                                    memory_order_relaxed);
    event.ticket_id = record == (const WltgRecord *)0
                          ? UINT64_C(0)
                          : atomic_load_explicit(&record->ticket_id,
                                                 memory_order_relaxed);
    event.issuer_thread_id = record == (const WltgRecord *)0
                                 ? UINT64_C(0)
                                 : atomic_load_explicit(
                                       &record->issuer_thread_id,
                                       memory_order_relaxed);
    event.current_thread_id = record == (const WltgRecord *)0
                                  ? UINT64_C(0)
                                  : atomic_load_explicit(
                                        &record->current_thread_id,
                                        memory_order_relaxed);
    event.owner_cookie = record == (const WltgRecord *)0
                             ? UINT64_C(0)
                             : atomic_load_explicit(&record->owner_cookie,
                                                    memory_order_relaxed);
    event.written_address = record == (const WltgRecord *)0
                                ? (uintptr_t)0
                                : atomic_load_explicit(
                                      &record->written_address,
                                      memory_order_relaxed);
    event.publication_sequence = record == (const WltgRecord *)0
                                     ? UINT64_C(0)
                                     : atomic_load_explicit(
                                           &record->publication_sequence,
                                           memory_order_relaxed);
    accepted = g_wltg_owner.ops.emit_audit_event(
        g_wltg_owner.ops.context, &event);
    if (accepted != 1) {
        (void)atomic_fetch_add_explicit(&g_wltg_owner.audit_drop_count,
                                        UINT64_C(1), memory_order_relaxed);
        return false;
    }
    return true;
}

static void WltgRejectProcess(WltgReason reason, const WltgRecord *record,
                              bool emit_event)
{
    uint64_t observed = WltgLoadProcessStatus(memory_order_acquire);
    while (!WltgProcessIsTerminal(WltgUnpackProcessState(observed))) {
        uint64_t desired = WltgPackProcessStatus(WLTG_PROCESS_REJECTED,
                                                 reason);
        if (atomic_compare_exchange_weak_explicit(
                &g_wltg_owner.process_status, &observed, desired,
                memory_order_release, memory_order_acquire)) {
            if (emit_event) {
                (void)WltgEmit(WLTG_EVENT_PROCESS_REJECTED, reason, record);
            }
            return;
        }
    }
}

static void WltgReleaseCapacity(WltgRecord *record)
{
    if (atomic_exchange_explicit(&record->capacity_held, UINT32_C(0),
                                 memory_order_acq_rel) == UINT32_C(1)) {
        (void)atomic_fetch_sub_explicit(&g_wltg_owner.active_ticket_count,
                                        UINT32_C(1), memory_order_acq_rel);
    }
}

static WltgResult WltgFailRecord(WltgRecord *record, WltgReason reason,
                                 bool audit_is_usable)
{
    atomic_store_explicit(&record->guard_value, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&record->state, (uint32_t)WLTG_THREAD_FAILED,
                          memory_order_release);
    WltgReleaseCapacity(record);
    WltgRejectProcess(reason, record, audit_is_usable);
    return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL, reason, record);
}

static bool WltgAcquireCapacity(void)
{
    uint32_t observed = atomic_load_explicit(
        &g_wltg_owner.active_ticket_count, memory_order_acquire);
    uint32_t maximum = g_wltg_owner.binding.max_live_threads;
    while (observed < maximum) {
        if (atomic_compare_exchange_weak_explicit(
                &g_wltg_owner.active_ticket_count, &observed,
                observed + UINT32_C(1), memory_order_acq_rel,
                memory_order_acquire)) {
            return true;
        }
    }
    return false;
}

static WltgRecord *WltgReserveRecord(void)
{
    uint32_t index;
    for (index = 0; index < WLTG_MAX_THREAD_RECORDS; ++index) {
        WltgRecord *record = &g_wltg_owner.records[index];
        uint32_t observed = atomic_load_explicit(&record->state,
                                                 memory_order_acquire);
        if (observed != (uint32_t)WLTG_THREAD_FREE &&
            observed != (uint32_t)WLTG_THREAD_RETIRED &&
            observed != (uint32_t)WLTG_THREAD_CANCELLED) {
            continue;
        }
        if (atomic_compare_exchange_strong_explicit(
                &record->state, &observed,
                (uint32_t)WLTG_THREAD_ALLOCATING,
                memory_order_acq_rel, memory_order_acquire)) {
            WltgClearRecord(record, WLTG_THREAD_ALLOCATING);
            return record;
        }
    }
    return (WltgRecord *)0;
}

static WltgReason WltgGetCsprngGuard(const WltgPlatformOpsV1 *ops,
                                     uint64_t required_process_epoch,
                                     uint64_t *out_guard)
{
    WltgGuardSample sample;
    int ok;
    WltgReason reason = WLTG_REASON_NONE;
    WltgClearBytes(&sample, sizeof(sample));
    ok = ops->get_os_csprng(ops->context, required_process_epoch, &sample);
#if defined(WLTG_MUTANT_FIXED_FALLBACK)
    if (ok != 1) {
        sample.value = UINT64_C(0x574c544746495845);
        sample.source_epoch = required_process_epoch;
        sample.quality = WLTG_GUARD_SOURCE_OS_CSPRNG;
        sample.reserved_zero = UINT32_C(0);
        ok = 1;
    }
#endif
    if (ok != 1) {
        reason = WLTG_REASON_CSPRNG_FAILED;
    } else if (sample.source_epoch != required_process_epoch ||
        sample.quality != WLTG_GUARD_SOURCE_OS_CSPRNG ||
        sample.reserved_zero != UINT32_C(0)) {
        reason = WLTG_REASON_CSPRNG_QUALITY;
    } else if (sample.value == UINT64_C(0)) {
        reason = WLTG_REASON_GUARD_VALUE_INVALID;
    } else {
        *out_guard = sample.value;
    }
    WltgClearBytes(&sample, sizeof(sample));
    return reason;
}

static bool WltgAdmissionPairValid(WltgAdmissionKind admission_kind,
                                   WltgThreadRole role)
{
    return (admission_kind == WLTG_ADMISSION_MAIN_POST_SPECIALIZATION &&
            role == WLTG_THREAD_ROLE_MAIN) ||
           (admission_kind == WLTG_ADMISSION_PARENT_PRELOAD &&
            role == WLTG_THREAD_ROLE_PARENT_PRELOAD) ||
           (admission_kind == WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE &&
            role == WLTG_THREAD_ROLE_GUEST_PTHREAD) ||
           (admission_kind == WLTG_ADMISSION_ADAPTER_JNI_ATTACH &&
            role == WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH);
}

static void WltgFillTicket(const WltgRecord *record,
                           WltgThreadTicketV1 *ticket)
{
    ticket->abi_version = WLTG_ABI_VERSION;
    ticket->struct_size = (uint32_t)sizeof(*ticket);
    ticket->ticket_id = atomic_load_explicit(&record->ticket_id,
                                             memory_order_relaxed);
    ticket->one_shot_nonce = atomic_load_explicit(&record->one_shot_nonce,
                                                  memory_order_relaxed);
    ticket->adapter_generation = atomic_load_explicit(
        &record->adapter_generation, memory_order_relaxed);
    ticket->process_epoch = atomic_load_explicit(&record->process_epoch,
                                                 memory_order_relaxed);
    ticket->policy_epoch = atomic_load_explicit(&record->policy_epoch,
                                                memory_order_relaxed);
    ticket->issuer_thread_id = atomic_load_explicit(
        &record->issuer_thread_id, memory_order_relaxed);
    ticket->admission_kind = (WltgAdmissionKind)atomic_load_explicit(
        &record->admission_kind, memory_order_relaxed);
    ticket->role = (WltgThreadRole)atomic_load_explicit(
        &record->role, memory_order_relaxed);
    ticket->reserved_zero = UINT32_C(0);
    ticket->reserved_zero_2 = UINT32_C(0);
}

static bool WltgTicketShapeValid(const WltgThreadTicketV1 *ticket)
{
    return ticket != (const WltgThreadTicketV1 *)0 &&
           ticket->abi_version == WLTG_ABI_VERSION &&
           ticket->struct_size == sizeof(WltgThreadTicketV1) &&
           ticket->ticket_id != UINT64_C(0) &&
           ticket->one_shot_nonce != UINT64_C(0) &&
           ticket->adapter_generation != UINT64_C(0) &&
           ticket->process_epoch != UINT64_C(0) &&
           ticket->policy_epoch != UINT64_C(0) &&
           ticket->issuer_thread_id != UINT64_C(0) &&
           ticket->reserved_zero == UINT32_C(0) &&
           ticket->reserved_zero_2 == UINT32_C(0) &&
           WltgAdmissionPairValid(ticket->admission_kind, ticket->role);
}

static bool WltgTicketMatchesBinding(const WltgThreadTicketV1 *ticket)
{
    return ticket->adapter_generation ==
               g_wltg_owner.binding.adapter_generation &&
           ticket->process_epoch == g_wltg_owner.binding.process_epoch &&
           ticket->policy_epoch == g_wltg_owner.binding.policy_epoch;
}

static WltgRecord *WltgFindRecord(uint64_t ticket_id,
                                  WltgThreadState *out_state)
{
    uint32_t index;
    for (index = 0; index < WLTG_MAX_THREAD_RECORDS; ++index) {
        WltgRecord *record = &g_wltg_owner.records[index];
        WltgThreadState state = WltgRecordState(record, memory_order_acquire);
        if (state == WLTG_THREAD_FREE || state == WLTG_THREAD_ALLOCATING) {
            continue;
        }
        if (atomic_load_explicit(&record->ticket_id,
                                 memory_order_relaxed) == ticket_id) {
            WltgThreadState after = WltgRecordState(record,
                                                    memory_order_acquire);
            if (after == state &&
                atomic_load_explicit(&record->ticket_id,
                                     memory_order_relaxed) == ticket_id) {
                *out_state = state;
                return record;
            }
        }
    }
    *out_state = WLTG_THREAD_FREE;
    return (WltgRecord *)0;
}

static bool WltgTicketMatchesRecord(const WltgThreadTicketV1 *ticket,
                                    const WltgRecord *record)
{
    return ticket->ticket_id == atomic_load_explicit(
               &record->ticket_id, memory_order_relaxed) &&
           ticket->one_shot_nonce == atomic_load_explicit(
               &record->one_shot_nonce, memory_order_relaxed) &&
           ticket->adapter_generation == atomic_load_explicit(
               &record->adapter_generation, memory_order_relaxed) &&
           ticket->process_epoch == atomic_load_explicit(
               &record->process_epoch, memory_order_relaxed) &&
           ticket->policy_epoch == atomic_load_explicit(
               &record->policy_epoch, memory_order_relaxed) &&
           ticket->issuer_thread_id == atomic_load_explicit(
               &record->issuer_thread_id, memory_order_relaxed) &&
           ticket->admission_kind == (WltgAdmissionKind)atomic_load_explicit(
               &record->admission_kind, memory_order_relaxed) &&
           ticket->role == (WltgThreadRole)atomic_load_explicit(
               &record->role, memory_order_relaxed);
}

static bool WltgCurrentThreadAlreadyAdmitted(uint64_t thread_id,
                                             const WltgRecord *except)
{
    uint32_t index;
    for (index = 0; index < WLTG_MAX_THREAD_RECORDS; ++index) {
        const WltgRecord *record = &g_wltg_owner.records[index];
        WltgThreadState state;
        if (record == except) {
            continue;
        }
        state = WltgRecordState(record, memory_order_acquire);
        if (state != WLTG_THREAD_PREPARING && state != WLTG_THREAD_READY &&
            state != WLTG_THREAD_RETIRING) {
            continue;
        }
        if (atomic_load_explicit(&record->current_thread_id,
                                 memory_order_relaxed) == thread_id &&
            WltgRecordState(record, memory_order_acquire) == state) {
            return true;
        }
    }
    return false;
}

static WltgReason WltgValidateOwner(const WltgOwnedRegion *region,
                                    uint64_t current_thread_id,
                                    uintptr_t *out_slot)
{
    uint32_t relative_offset;
    uintptr_t base;
    if (region->abi_version != WLTG_ABI_VERSION ||
        region->owner_kind != WLTG_OWNER_MAIN_ELF_TLS_RESERVATION ||
        region->base == (uint8_t *)0 ||
        region->owner_cookie == UINT64_C(0) ||
        region->current_thread_id != current_thread_id ||
        region->adapter_generation !=
            g_wltg_owner.binding.adapter_generation ||
        region->process_epoch != g_wltg_owner.binding.process_epoch ||
        region->policy_epoch != g_wltg_owner.binding.policy_epoch) {
        return WLTG_REASON_OWNER_MISMATCH;
    }
#if !defined(WLTG_MUTANT_SKIP_OWNER_BOUNDS)
    if (region->tp_start_offset !=
            g_wltg_owner.binding.reservation_tp_start ||
        region->byte_size != g_wltg_owner.binding.reservation_size ||
        g_wltg_owner.binding.stack_guard_tp_offset <
            region->tp_start_offset ||
        g_wltg_owner.binding.stack_guard_width > region->byte_size) {
        return WLTG_REASON_OWNER_BOUNDS;
    }
#endif
    relative_offset = g_wltg_owner.binding.stack_guard_tp_offset -
                      region->tp_start_offset;
    if (relative_offset >
        region->byte_size - g_wltg_owner.binding.stack_guard_width) {
        return WLTG_REASON_OWNER_BOUNDS;
    }
    base = (uintptr_t)region->base;
    if (base > UINTPTR_MAX - (uintptr_t)relative_offset ||
        ((base + (uintptr_t)relative_offset) &
         (uintptr_t)(WLTG_STACK_GUARD_WIDTH - UINT32_C(1))) !=
            (uintptr_t)0) {
        return WLTG_REASON_OWNER_BOUNDS;
    }
    *out_slot = base + (uintptr_t)relative_offset;
    return WLTG_REASON_NONE;
}

static void WltgFillReceipt(const WltgRecord *record,
                            WltgThreadReceiptV1 *receipt,
                            WltgThreadState state)
{
    receipt->abi_version = WLTG_ABI_VERSION;
    receipt->struct_size = (uint32_t)sizeof(*receipt);
    receipt->state = state;
    receipt->admission_kind = (WltgAdmissionKind)atomic_load_explicit(
        &record->admission_kind, memory_order_relaxed);
    receipt->role = (WltgThreadRole)atomic_load_explicit(
        &record->role, memory_order_relaxed);
    receipt->reserved_zero = UINT32_C(0);
    receipt->ticket_id = atomic_load_explicit(&record->ticket_id,
                                              memory_order_relaxed);
    receipt->one_shot_nonce = atomic_load_explicit(
        &record->one_shot_nonce, memory_order_relaxed);
    receipt->adapter_generation = atomic_load_explicit(
        &record->adapter_generation, memory_order_relaxed);
    receipt->process_epoch = atomic_load_explicit(&record->process_epoch,
                                                  memory_order_relaxed);
    receipt->policy_epoch = atomic_load_explicit(&record->policy_epoch,
                                                 memory_order_relaxed);
    receipt->issuer_thread_id = atomic_load_explicit(
        &record->issuer_thread_id, memory_order_relaxed);
    receipt->current_thread_id = atomic_load_explicit(
        &record->current_thread_id, memory_order_relaxed);
    receipt->owner_cookie = atomic_load_explicit(&record->owner_cookie,
                                                 memory_order_relaxed);
    receipt->written_address = atomic_load_explicit(
        &record->written_address, memory_order_relaxed);
    receipt->tp_offset = atomic_load_explicit(&record->tp_offset,
                                              memory_order_relaxed);
    receipt->width = atomic_load_explicit(&record->width,
                                          memory_order_relaxed);
    receipt->publication_sequence = atomic_load_explicit(
        &record->publication_sequence, memory_order_relaxed);
}

static bool WltgReceiptShapeValid(const WltgThreadReceiptV1 *receipt)
{
    return receipt != (const WltgThreadReceiptV1 *)0 &&
           receipt->abi_version == WLTG_ABI_VERSION &&
           receipt->struct_size == sizeof(WltgThreadReceiptV1) &&
           receipt->state == WLTG_THREAD_READY &&
           receipt->reserved_zero == UINT32_C(0) &&
           receipt->ticket_id != UINT64_C(0) &&
           receipt->one_shot_nonce != UINT64_C(0) &&
           receipt->current_thread_id != UINT64_C(0) &&
           receipt->owner_cookie != UINT64_C(0) &&
           receipt->written_address != (uintptr_t)0 &&
           receipt->tp_offset == WLTG_STACK_GUARD_TP_OFFSET &&
           receipt->width == WLTG_STACK_GUARD_WIDTH &&
           receipt->publication_sequence != UINT64_C(0) &&
           WltgAdmissionPairValid(receipt->admission_kind, receipt->role);
}

static bool WltgReceiptMatchesRecord(const WltgThreadReceiptV1 *receipt,
                                     const WltgRecord *record)
{
    return receipt->ticket_id == atomic_load_explicit(
               &record->ticket_id, memory_order_relaxed) &&
           receipt->one_shot_nonce == atomic_load_explicit(
               &record->one_shot_nonce, memory_order_relaxed) &&
           receipt->adapter_generation == atomic_load_explicit(
               &record->adapter_generation, memory_order_relaxed) &&
           receipt->process_epoch == atomic_load_explicit(
               &record->process_epoch, memory_order_relaxed) &&
           receipt->policy_epoch == atomic_load_explicit(
               &record->policy_epoch, memory_order_relaxed) &&
           receipt->issuer_thread_id == atomic_load_explicit(
               &record->issuer_thread_id, memory_order_relaxed) &&
           receipt->current_thread_id == atomic_load_explicit(
               &record->current_thread_id, memory_order_relaxed) &&
           receipt->owner_cookie == atomic_load_explicit(
               &record->owner_cookie, memory_order_relaxed) &&
           receipt->written_address == atomic_load_explicit(
               &record->written_address, memory_order_relaxed) &&
           receipt->tp_offset == atomic_load_explicit(
               &record->tp_offset, memory_order_relaxed) &&
           receipt->width == atomic_load_explicit(
               &record->width, memory_order_relaxed) &&
           receipt->publication_sequence == atomic_load_explicit(
               &record->publication_sequence, memory_order_relaxed) &&
           receipt->admission_kind == (WltgAdmissionKind)atomic_load_explicit(
               &record->admission_kind, memory_order_relaxed) &&
           receipt->role == (WltgThreadRole)atomic_load_explicit(
               &record->role, memory_order_relaxed);
}

uint32_t WLTG_GetAbiVersion(void)
{
    return WLTG_ABI_VERSION;
}

const char *WLTG_ReasonString(WltgReason reason)
{
    switch (reason) {
        case WLTG_REASON_NONE: return "none";
        case WLTG_REASON_ALREADY_INITIALIZED: return "already_initialized";
        case WLTG_REASON_INVALID_ARGUMENT: return "invalid_argument";
        case WLTG_REASON_ABI_MISMATCH: return "abi_mismatch";
        case WLTG_REASON_FORK_RESET_REQUIRED: return "fork_reset_required";
        case WLTG_REASON_PROCESS_NOT_ARMED: return "process_not_armed";
        case WLTG_REASON_PROCESS_TERMINAL: return "process_terminal";
        case WLTG_REASON_BINDING_REJECTED: return "binding_rejected";
        case WLTG_REASON_BINDING_MISMATCH: return "binding_mismatch";
        case WLTG_REASON_CONCURRENT_ARM: return "concurrent_arm";
        case WLTG_REASON_REGISTRY_FULL: return "registry_full";
        case WLTG_REASON_TICKET_UNKNOWN: return "ticket_unknown";
        case WLTG_REASON_TICKET_STATE: return "ticket_state";
        case WLTG_REASON_TICKET_REPLAY: return "ticket_replay";
        case WLTG_REASON_TICKET_ROLE_MISMATCH: return "ticket_role_mismatch";
        case WLTG_REASON_TICKET_CREATOR_MISMATCH:
            return "ticket_creator_mismatch";
        case WLTG_REASON_CURRENT_THREAD_INVALID:
            return "current_thread_invalid";
        case WLTG_REASON_THREAD_ALREADY_ADMITTED:
            return "thread_already_admitted";
        case WLTG_REASON_OWNER_UNAVAILABLE: return "owner_unavailable";
        case WLTG_REASON_OWNER_MISMATCH: return "owner_mismatch";
        case WLTG_REASON_OWNER_BOUNDS: return "owner_bounds";
        case WLTG_REASON_CSPRNG_FAILED: return "csprng_failed";
        case WLTG_REASON_CSPRNG_QUALITY: return "csprng_quality";
        case WLTG_REASON_GUARD_VALUE_INVALID: return "guard_value_invalid";
        case WLTG_REASON_PROCESS_GUARD_MISMATCH:
            return "process_guard_mismatch";
        case WLTG_REASON_READBACK_MISMATCH: return "readback_mismatch";
        case WLTG_REASON_RECEIPT_MISMATCH: return "receipt_mismatch";
        case WLTG_REASON_AUDIT_SINK_REJECTED:
            return "audit_sink_rejected";
        case WLTG_REASON_STATE_RACE: return "state_race";
        case WLTG_REASON_INVALID_THREAD_ROLE: return "invalid_thread_role";
        case WLTG_REASON_MAIN_TICKET_ALREADY_ISSUED:
            return "main_ticket_already_issued";
        case WLTG_REASON_PROFILE_REVOKED: return "profile_revoked";
        case WLTG_REASON_INTERNAL_STATE: return "internal_state";
        default: return "unknown";
    }
}

WltgResult WLTG_AfterForkChildReset(const WltgForkSeed *seed)
{
    WltgReason reason = WLTG_REASON_NONE;
    uint64_t generation = UINT64_C(0);
    uint64_t process_epoch = UINT64_C(0);
    uint64_t policy_epoch = UINT64_C(0);
    uint32_t index;
    if (seed == (const WltgForkSeed *)0) {
        reason = WLTG_REASON_INVALID_ARGUMENT;
    } else if (seed->abi_version != WLTG_ABI_VERSION) {
        reason = WLTG_REASON_ABI_MISMATCH;
    } else if (seed->reserved_zero != UINT32_C(0) ||
               seed->adapter_generation == UINT64_C(0) ||
               seed->process_epoch == UINT64_C(0) ||
               seed->policy_epoch == UINT64_C(0)) {
        reason = WLTG_REASON_INVALID_ARGUMENT;
    } else {
        generation = seed->adapter_generation;
        process_epoch = seed->process_epoch;
        policy_epoch = seed->policy_epoch;
    }

    atomic_store_explicit(&g_wltg_owner.fork_seeded, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.arm_gate, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.main_ticket_issued, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.active_ticket_count, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.adapter_generation, generation,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.process_epoch, process_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.policy_epoch, policy_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.next_ticket_id, UINT64_C(1),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.audit_sequence, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.audit_drop_count, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.publication_sequence, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wltg_owner.process_guard, UINT64_C(0),
                          memory_order_relaxed);
    WltgClearBytes(&g_wltg_owner.binding, sizeof(g_wltg_owner.binding));
    WltgClearBytes(&g_wltg_owner.ops, sizeof(g_wltg_owner.ops));
    for (index = 0; index < WLTG_MAX_THREAD_RECORDS; ++index) {
        WltgClearRecord(&g_wltg_owner.records[index], WLTG_THREAD_FREE);
    }
    if (reason != WLTG_REASON_NONE) {
        atomic_store_explicit(&g_wltg_owner.process_status,
                              WltgPackProcessStatus(WLTG_PROCESS_REJECTED,
                                                    reason),
                              memory_order_release);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL, reason,
                               (const WltgRecord *)0);
    }
    atomic_store_explicit(&g_wltg_owner.fork_seeded, UINT32_C(1),
                          memory_order_release);
    atomic_store_explicit(&g_wltg_owner.process_status,
                          WltgPackProcessStatus(WLTG_PROCESS_SEEDED,
                                                WLTG_REASON_NONE),
                          memory_order_release);
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE,
                           (const WltgRecord *)0);
}

WltgResult WLTG_ProcessArm(const WltgProcessBindingV1 *binding,
                           const WltgPlatformOpsV1 *platform_ops)
{
    uint32_t expected_gate = UINT32_C(0);
    uint64_t expected_status;
    uint64_t process_guard = UINT64_C(0);
    WltgReason guard_reason;
    if (!WltgBindingShapeValid(binding) || !WltgOpsShapeValid(platform_ops)) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    if (WltgLoadProcessState(memory_order_acquire) == WLTG_PROCESS_ARMED) {
        if (WltgBindingMatches(binding) && WltgOpsMatch(platform_ops)) {
            return WltgResultValue(WLTG_STATUS_OK_IDEMPOTENT,
                                   WLTG_REASON_ALREADY_INITIALIZED,
                                   (const WltgRecord *)0);
        }
        WltgRejectProcess(WLTG_REASON_BINDING_MISMATCH,
                          (const WltgRecord *)0, true);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_BINDING_MISMATCH,
                               (const WltgRecord *)0);
    }
    if (!atomic_compare_exchange_strong_explicit(
            &g_wltg_owner.arm_gate, &expected_gate, UINT32_C(1),
            memory_order_acquire, memory_order_relaxed)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_CONCURRENT_ARM,
                               (const WltgRecord *)0);
    }
    if (atomic_load_explicit(&g_wltg_owner.fork_seeded,
                             memory_order_acquire) != UINT32_C(1) ||
        WltgLoadProcessState(memory_order_acquire) != WLTG_PROCESS_SEEDED) {
        atomic_store_explicit(&g_wltg_owner.arm_gate, UINT32_C(0),
                              memory_order_release);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_FORK_RESET_REQUIRED,
                               (const WltgRecord *)0);
    }
    if (binding->adapter_generation != atomic_load_explicit(
            &g_wltg_owner.adapter_generation, memory_order_relaxed) ||
        binding->process_epoch != atomic_load_explicit(
            &g_wltg_owner.process_epoch, memory_order_relaxed) ||
        binding->policy_epoch != atomic_load_explicit(
            &g_wltg_owner.policy_epoch, memory_order_relaxed)) {
        atomic_store_explicit(&g_wltg_owner.process_status,
                              WltgPackProcessStatus(WLTG_PROCESS_REJECTED,
                                                    WLTG_REASON_BINDING_MISMATCH),
                              memory_order_release);
        atomic_store_explicit(&g_wltg_owner.arm_gate, UINT32_C(0),
                              memory_order_release);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_BINDING_MISMATCH,
                               (const WltgRecord *)0);
    }
    expected_status = WltgPackProcessStatus(WLTG_PROCESS_SEEDED,
                                            WLTG_REASON_NONE);
    if (!atomic_compare_exchange_strong_explicit(
            &g_wltg_owner.process_status, &expected_status,
            WltgPackProcessStatus(WLTG_PROCESS_ARMING, WLTG_REASON_NONE),
            memory_order_acq_rel, memory_order_acquire)) {
        atomic_store_explicit(&g_wltg_owner.arm_gate, UINT32_C(0),
                              memory_order_release);
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_STATE_RACE,
                               (const WltgRecord *)0);
    }
    if (platform_ops->verify_process_binding(platform_ops->context,
                                             binding) != 1) {
        atomic_store_explicit(&g_wltg_owner.process_status,
                              WltgPackProcessStatus(WLTG_PROCESS_REJECTED,
                                                    WLTG_REASON_BINDING_REJECTED),
                              memory_order_release);
        atomic_store_explicit(&g_wltg_owner.arm_gate, UINT32_C(0),
                              memory_order_release);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_BINDING_REJECTED,
                               (const WltgRecord *)0);
    }
    WltgCopyBinding(&g_wltg_owner.binding, binding);
    g_wltg_owner.ops = *platform_ops;
    guard_reason = WltgGetCsprngGuard(platform_ops, binding->process_epoch,
                                     &process_guard);
    if (guard_reason != WLTG_REASON_NONE) {
        atomic_store_explicit(&g_wltg_owner.process_guard, UINT64_C(0),
                              memory_order_relaxed);
        atomic_store_explicit(&g_wltg_owner.process_status,
                              WltgPackProcessStatus(WLTG_PROCESS_REJECTED,
                                                    guard_reason),
                              memory_order_release);
        atomic_store_explicit(&g_wltg_owner.arm_gate, UINT32_C(0),
                              memory_order_release);
        (void)WltgEmit(WLTG_EVENT_PROCESS_REJECTED, guard_reason,
                       (const WltgRecord *)0);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL, guard_reason,
                               (const WltgRecord *)0);
    }
    atomic_store_explicit(&g_wltg_owner.process_guard, process_guard,
                          memory_order_release);
    atomic_store_explicit(&g_wltg_owner.process_status,
                          WltgPackProcessStatus(WLTG_PROCESS_ARMED,
                                                WLTG_REASON_NONE),
                          memory_order_release);
    atomic_store_explicit(&g_wltg_owner.arm_gate, UINT32_C(0),
                          memory_order_release);
    if (!WltgEmit(WLTG_EVENT_PROCESS_ARMED, WLTG_REASON_NONE,
                  (const WltgRecord *)0)) {
        WltgRejectProcess(WLTG_REASON_AUDIT_SINK_REJECTED,
                          (const WltgRecord *)0, false);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_AUDIT_SINK_REJECTED,
                               (const WltgRecord *)0);
    }
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE,
                           (const WltgRecord *)0);
}

WltgResult WLTG_IssueThreadTicket(WltgAdmissionKind admission_kind,
                                  WltgThreadRole role,
                                  WltgThreadTicketV1 *out_ticket)
{
    WltgRecord *record;
    uint64_t current_thread_id;
    uint64_t ticket_id;
    uint64_t ticket_nonce;
    bool main_claimed = false;
    if (out_ticket == (WltgThreadTicketV1 *)0) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    WltgClearBytes(out_ticket, sizeof(*out_ticket));
    if (!WltgAdmissionPairValid(admission_kind, role)) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_THREAD_ROLE,
                               (const WltgRecord *)0);
    }
    if (WltgLoadProcessState(memory_order_acquire) != WLTG_PROCESS_ARMED) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WltgProcessIsTerminal(WltgLoadProcessState(
                                   memory_order_relaxed))
                                   ? WLTG_REASON_PROCESS_TERMINAL
                                   : WLTG_REASON_PROCESS_NOT_ARMED,
                               (const WltgRecord *)0);
    }
    current_thread_id = g_wltg_owner.ops.get_current_thread_id(
        g_wltg_owner.ops.context);
    if (current_thread_id == UINT64_C(0)) {
        WltgRejectProcess(WLTG_REASON_CURRENT_THREAD_INVALID,
                          (const WltgRecord *)0, true);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_CURRENT_THREAD_INVALID,
                               (const WltgRecord *)0);
    }
    if (admission_kind == WLTG_ADMISSION_MAIN_POST_SPECIALIZATION ||
        admission_kind == WLTG_ADMISSION_PARENT_PRELOAD) {
        uint32_t expected = UINT32_C(0);
        if (!atomic_compare_exchange_strong_explicit(
                &g_wltg_owner.main_ticket_issued, &expected, UINT32_C(1),
                memory_order_acq_rel, memory_order_acquire)) {
            return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                                   WLTG_REASON_MAIN_TICKET_ALREADY_ISSUED,
                                   (const WltgRecord *)0);
        }
        main_claimed = true;
    }
    if (!WltgAcquireCapacity()) {
        if (main_claimed) {
            atomic_store_explicit(&g_wltg_owner.main_ticket_issued,
                                  UINT32_C(0), memory_order_release);
        }
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_REGISTRY_FULL,
                               (const WltgRecord *)0);
    }
    record = WltgReserveRecord();
    if (record == (WltgRecord *)0) {
        (void)atomic_fetch_sub_explicit(&g_wltg_owner.active_ticket_count,
                                        UINT32_C(1), memory_order_acq_rel);
        if (main_claimed) {
            atomic_store_explicit(&g_wltg_owner.main_ticket_issued,
                                  UINT32_C(0), memory_order_release);
        }
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_REGISTRY_FULL,
                               (const WltgRecord *)0);
    }
    atomic_store_explicit(&record->capacity_held, UINT32_C(1),
                          memory_order_relaxed);
    ticket_id = atomic_fetch_add_explicit(&g_wltg_owner.next_ticket_id,
                                          UINT64_C(1),
                                          memory_order_relaxed);
    if (ticket_id == UINT64_C(0)) {
        return WltgFailRecord(record, WLTG_REASON_INTERNAL_STATE, true);
    }
    /*
     * This is a lifecycle correlation nonce, not a stack guard or entropy
     * fallback. Multiplication by an odd process-bound factor is a bijection
     * modulo 2^64, so every non-zero ticket id has a unique non-zero nonce.
     */
    ticket_nonce = ticket_id * (g_wltg_owner.binding.binding_nonce |
                                UINT64_C(1));
    if (ticket_nonce == UINT64_C(0)) {
        return WltgFailRecord(record, WLTG_REASON_INTERNAL_STATE, true);
    }
    atomic_store_explicit(&record->ticket_id, ticket_id,
                          memory_order_relaxed);
    atomic_store_explicit(&record->one_shot_nonce, ticket_nonce,
                          memory_order_relaxed);
    atomic_store_explicit(&record->adapter_generation,
                          g_wltg_owner.binding.adapter_generation,
                          memory_order_relaxed);
    atomic_store_explicit(&record->process_epoch,
                          g_wltg_owner.binding.process_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&record->policy_epoch,
                          g_wltg_owner.binding.policy_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&record->issuer_thread_id, current_thread_id,
                          memory_order_relaxed);
    atomic_store_explicit(&record->admission_kind, (uint32_t)admission_kind,
                          memory_order_relaxed);
    atomic_store_explicit(&record->role, (uint32_t)role,
                          memory_order_relaxed);
    atomic_store_explicit(&record->state, (uint32_t)WLTG_THREAD_ISSUED,
                          memory_order_release);
    WltgFillTicket(record, out_ticket);
    if (!WltgEmit(WLTG_EVENT_TICKET_ISSUED, WLTG_REASON_NONE, record)) {
        WltgClearBytes(out_ticket, sizeof(*out_ticket));
        return WltgFailRecord(record, WLTG_REASON_AUDIT_SINK_REJECTED,
                              false);
    }
    if (WltgLoadProcessState(memory_order_acquire) != WLTG_PROCESS_ARMED) {
        WltgClearBytes(out_ticket, sizeof(*out_ticket));
        return WltgFailRecord(record, WLTG_REASON_PROCESS_TERMINAL, true);
    }
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE, record);
}

WltgResult WLTG_CancelThreadTicket(const WltgThreadTicketV1 *ticket)
{
    WltgThreadState state;
    WltgRecord *record;
    uint64_t current_thread_id;
    uint32_t expected;
    if (!WltgTicketShapeValid(ticket)) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    record = WltgFindRecord(ticket->ticket_id, &state);
    if (record == (WltgRecord *)0) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_UNKNOWN,
                               (const WltgRecord *)0);
    }
    if (!WltgTicketMatchesRecord(ticket, record)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_REPLAY, record);
    }
    if (state == WLTG_THREAD_CANCELLED) {
        return WltgResultValue(WLTG_STATUS_OK_IDEMPOTENT,
                               WLTG_REASON_ALREADY_INITIALIZED, record);
    }
    if (state != WLTG_THREAD_ISSUED) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_STATE, record);
    }
    current_thread_id = g_wltg_owner.ops.get_current_thread_id(
        g_wltg_owner.ops.context);
    if (current_thread_id != ticket->issuer_thread_id) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_CREATOR_MISMATCH, record);
    }
    expected = (uint32_t)WLTG_THREAD_ISSUED;
    if (!atomic_compare_exchange_strong_explicit(
            &record->state, &expected, (uint32_t)WLTG_THREAD_CANCELLED,
            memory_order_release, memory_order_acquire)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_STATE_RACE, record);
    }
    WltgReleaseCapacity(record);
    if (!WltgEmit(WLTG_EVENT_TICKET_CANCELLED, WLTG_REASON_NONE, record)) {
        WltgRejectProcess(WLTG_REASON_AUDIT_SINK_REJECTED, record, false);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_AUDIT_SINK_REJECTED, record);
    }
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE, record);
}

WltgResult WLTG_PrepareCurrentThread(const WltgThreadTicketV1 *ticket,
                                     WltgThreadReceiptV1 *out_receipt)
{
    WltgThreadState state;
    WltgRecord *record;
    uint64_t current_thread_id;
    uint32_t expected;
    WltgOwnedRegion region;
    WltgReason reason;
    uintptr_t slot_address = (uintptr_t)0;
    uint64_t guard;
    uint64_t readback;
    uint64_t publication_sequence;
    if (out_receipt == (WltgThreadReceiptV1 *)0) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    WltgClearBytes(out_receipt, sizeof(*out_receipt));
    WltgClearBytes(&region, sizeof(region));
    if (!WltgTicketShapeValid(ticket)) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    if (WltgLoadProcessState(memory_order_acquire) != WLTG_PROCESS_ARMED) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_PROCESS_TERMINAL,
                               (const WltgRecord *)0);
    }
    if (!WltgTicketMatchesBinding(ticket)) {
        WltgRejectProcess(WLTG_REASON_BINDING_MISMATCH,
                          (const WltgRecord *)0, true);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_BINDING_MISMATCH,
                               (const WltgRecord *)0);
    }
    record = WltgFindRecord(ticket->ticket_id, &state);
    if (record == (WltgRecord *)0) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_UNKNOWN,
                               (const WltgRecord *)0);
    }
    if (!WltgTicketMatchesRecord(ticket, record)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_REPLAY, record);
    }
    current_thread_id = g_wltg_owner.ops.get_current_thread_id(
        g_wltg_owner.ops.context);
    if (current_thread_id == UINT64_C(0)) {
        return WltgFailRecord(record, WLTG_REASON_CURRENT_THREAD_INVALID,
                              true);
    }
    if (state == WLTG_THREAD_READY) {
#if defined(WLTG_MUTANT_ALLOW_TICKET_REPLAY)
        WltgFillReceipt(record, out_receipt, WLTG_THREAD_READY);
        return WltgResultValue(WLTG_STATUS_OK_IDEMPOTENT,
                               WLTG_REASON_ALREADY_INITIALIZED, record);
#else
        if (atomic_load_explicit(&record->current_thread_id,
                                 memory_order_relaxed) == current_thread_id) {
            WltgFillReceipt(record, out_receipt, WLTG_THREAD_READY);
            return WltgResultValue(WLTG_STATUS_OK_IDEMPOTENT,
                                   WLTG_REASON_ALREADY_INITIALIZED, record);
        }
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_REPLAY, record);
#endif
    }
    if (state != WLTG_THREAD_ISSUED) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_STATE, record);
    }
    if (ticket->admission_kind == WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE) {
#if !defined(WLTG_MUTANT_ALLOW_CREATOR_AS_GUEST)
        if (current_thread_id == ticket->issuer_thread_id) {
            return WltgFailRecord(
                record, WLTG_REASON_TICKET_CREATOR_MISMATCH, true);
        }
#endif
    } else if (current_thread_id != ticket->issuer_thread_id) {
        return WltgFailRecord(record,
                              WLTG_REASON_TICKET_CREATOR_MISMATCH, true);
    }
    if (WltgCurrentThreadAlreadyAdmitted(current_thread_id, record)) {
        return WltgFailRecord(record,
                              WLTG_REASON_THREAD_ALREADY_ADMITTED, true);
    }
    atomic_store_explicit(&record->current_thread_id, current_thread_id,
                          memory_order_relaxed);
    expected = (uint32_t)WLTG_THREAD_ISSUED;
    if (!atomic_compare_exchange_strong_explicit(
            &record->state, &expected, (uint32_t)WLTG_THREAD_PREPARING,
            memory_order_acq_rel, memory_order_acquire)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_STATE_RACE, record);
    }
    if (!WltgEmit(WLTG_EVENT_THREAD_PREPARING, WLTG_REASON_NONE, record)) {
        return WltgFailRecord(record, WLTG_REASON_AUDIT_SINK_REJECTED,
                              false);
    }
    if (g_wltg_owner.ops.resolve_current_thread_region(
            g_wltg_owner.ops.context, &g_wltg_owner.binding, ticket,
            &region) != 1) {
        return WltgFailRecord(record, WLTG_REASON_OWNER_UNAVAILABLE, true);
    }
    reason = WltgValidateOwner(&region, current_thread_id, &slot_address);
    if (reason != WLTG_REASON_NONE) {
        return WltgFailRecord(record, reason, true);
    }
#if defined(WLTG_MUTANT_PER_THREAD_GUARD)
    reason = WltgGetCsprngGuard(&g_wltg_owner.ops,
                                g_wltg_owner.binding.process_epoch, &guard);
    if (reason != WLTG_REASON_NONE) {
        return WltgFailRecord(record, reason, true);
    }
#else
    guard = atomic_load_explicit(&g_wltg_owner.process_guard,
                                 memory_order_acquire);
#endif
    if (guard == UINT64_C(0)) {
        return WltgFailRecord(record, WLTG_REASON_GUARD_VALUE_INVALID, true);
    }
    atomic_store_explicit(&record->guard_value, guard, memory_order_release);

#if defined(WLTG_MUTANT_READY_BEFORE_RECEIPT)
    atomic_store_explicit(&record->state, (uint32_t)WLTG_THREAD_READY,
                          memory_order_release);
    (void)WltgEmit(WLTG_EVENT_THREAD_READY, WLTG_REASON_NONE, record);
#endif

    readback = WLTG_StoreGuardAndReadback(
        (uint64_t *)(void *)slot_address, guard);
    atomic_store_explicit(&record->written_address, slot_address,
                          memory_order_relaxed);
    if (!WltgEmit(WLTG_EVENT_GUARD_WRITTEN, WLTG_REASON_NONE, record)) {
        return WltgFailRecord(record, WLTG_REASON_AUDIT_SINK_REJECTED,
                              false);
    }
    if (readback != guard) {
        return WltgFailRecord(record, WLTG_REASON_READBACK_MISMATCH, true);
    }
    if (guard != atomic_load_explicit(&g_wltg_owner.process_guard,
                                      memory_order_acquire)) {
        return WltgFailRecord(record,
                              WLTG_REASON_PROCESS_GUARD_MISMATCH, true);
    }
    publication_sequence = atomic_fetch_add_explicit(
                               &g_wltg_owner.publication_sequence,
                               UINT64_C(1), memory_order_relaxed) +
                           UINT64_C(1);
    atomic_store_explicit(&record->owner_cookie, region.owner_cookie,
                          memory_order_relaxed);
    atomic_store_explicit(&record->tp_offset,
                          g_wltg_owner.binding.stack_guard_tp_offset,
                          memory_order_relaxed);
    atomic_store_explicit(&record->width,
                          g_wltg_owner.binding.stack_guard_width,
                          memory_order_relaxed);
    atomic_store_explicit(&record->publication_sequence,
                          publication_sequence, memory_order_relaxed);
#if !defined(WLTG_MUTANT_READY_BEFORE_RECEIPT)
    expected = (uint32_t)WLTG_THREAD_PREPARING;
    if (!atomic_compare_exchange_strong_explicit(
                &record->state, &expected, (uint32_t)WLTG_THREAD_READY,
                memory_order_release, memory_order_acquire)) {
        return WltgFailRecord(record, WLTG_REASON_STATE_RACE, true);
    }
#endif
    if (!WltgEmit(WLTG_EVENT_THREAD_READY, WLTG_REASON_NONE, record)) {
        return WltgFailRecord(record, WLTG_REASON_AUDIT_SINK_REJECTED,
                              false);
    }
    if (WltgLoadProcessState(memory_order_acquire) != WLTG_PROCESS_ARMED) {
        return WltgFailRecord(record, WLTG_REASON_PROCESS_TERMINAL, true);
    }
    WltgReleaseCapacity(record);
    WltgFillReceipt(record, out_receipt, WLTG_THREAD_READY);
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE, record);
}

WltgResult WLTG_VerifyCurrentThreadReady(WltgThreadReceiptV1 *out_receipt)
{
    uint64_t current_thread_id;
    WltgRecord *match = (WltgRecord *)0;
    uint32_t index;
    if (out_receipt == (WltgThreadReceiptV1 *)0) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    WltgClearBytes(out_receipt, sizeof(*out_receipt));
    if (WltgLoadProcessState(memory_order_acquire) != WLTG_PROCESS_ARMED) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_PROCESS_TERMINAL,
                               (const WltgRecord *)0);
    }
    current_thread_id = g_wltg_owner.ops.get_current_thread_id(
        g_wltg_owner.ops.context);
    if (current_thread_id == UINT64_C(0)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_CURRENT_THREAD_INVALID,
                               (const WltgRecord *)0);
    }
    for (index = 0; index < WLTG_MAX_THREAD_RECORDS; ++index) {
        WltgRecord *record = &g_wltg_owner.records[index];
        if (WltgRecordState(record, memory_order_acquire) !=
            WLTG_THREAD_READY) {
            continue;
        }
        if (atomic_load_explicit(&record->current_thread_id,
                                 memory_order_relaxed) == current_thread_id &&
            WltgRecordState(record, memory_order_acquire) ==
                WLTG_THREAD_READY) {
            if (match != (WltgRecord *)0) {
                WltgRejectProcess(WLTG_REASON_INTERNAL_STATE, record, true);
                return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                                       WLTG_REASON_INTERNAL_STATE, record);
            }
            match = record;
        }
    }
    if (match == (WltgRecord *)0) {
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_PROCESS_NOT_ARMED,
                               (const WltgRecord *)0);
    }
    WltgFillReceipt(match, out_receipt, WLTG_THREAD_READY);
    if (WltgRecordState(match, memory_order_acquire) != WLTG_THREAD_READY ||
        WltgLoadProcessState(memory_order_acquire) != WLTG_PROCESS_ARMED) {
        WltgClearBytes(out_receipt, sizeof(*out_receipt));
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_STATE_RACE, match);
    }
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE, match);
}

WltgResult WLTG_RetireCurrentThread(const WltgThreadReceiptV1 *receipt)
{
    WltgThreadState state;
    WltgRecord *record;
    uint64_t current_thread_id;
    uint32_t expected;
    if (!WltgReceiptShapeValid(receipt)) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    record = WltgFindRecord(receipt->ticket_id, &state);
    if (record == (WltgRecord *)0) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_UNKNOWN,
                               (const WltgRecord *)0);
    }
    if (!WltgReceiptMatchesRecord(receipt, record)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_RECEIPT_MISMATCH, record);
    }
    current_thread_id = g_wltg_owner.ops.get_current_thread_id(
        g_wltg_owner.ops.context);
    if (current_thread_id != receipt->current_thread_id) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_CREATOR_MISMATCH, record);
    }
    if (state == WLTG_THREAD_RETIRED) {
        return WltgResultValue(WLTG_STATUS_OK_IDEMPOTENT,
                               WLTG_REASON_ALREADY_INITIALIZED, record);
    }
    if (state != WLTG_THREAD_READY) {
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_TICKET_STATE, record);
    }
    expected = (uint32_t)WLTG_THREAD_READY;
    if (!atomic_compare_exchange_strong_explicit(
            &record->state, &expected, (uint32_t)WLTG_THREAD_RETIRING,
            memory_order_acq_rel, memory_order_acquire)) {
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_STATE_RACE, record);
    }
    /* Never overwrite the current thread's slot during teardown. */
    atomic_store_explicit(&record->guard_value, UINT64_C(0),
                          memory_order_release);
    atomic_store_explicit(&record->state, (uint32_t)WLTG_THREAD_RETIRED,
                          memory_order_release);
    WltgReleaseCapacity(record);
    if (!WltgEmit(WLTG_EVENT_THREAD_RETIRED, WLTG_REASON_NONE, record)) {
        WltgRejectProcess(WLTG_REASON_AUDIT_SINK_REJECTED, record, false);
        return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                               WLTG_REASON_AUDIT_SINK_REJECTED, record);
    }
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE, record);
}

WltgResult WLTG_Revoke(void)
{
    uint64_t observed = WltgLoadProcessStatus(memory_order_acquire);
    for (;;) {
        WltgProcessState state = WltgUnpackProcessState(observed);
        if (state == WLTG_PROCESS_REVOKED) {
            return WltgResultValue(WLTG_STATUS_OK_IDEMPOTENT,
                                   WLTG_REASON_PROFILE_REVOKED,
                                   (const WltgRecord *)0);
        }
        if (state == WLTG_PROCESS_REJECTED) {
            return WltgResultValue(WLTG_STATUS_DENIED_TERMINAL,
                                   WltgUnpackReason(observed),
                                   (const WltgRecord *)0);
        }
        if (atomic_compare_exchange_weak_explicit(
                &g_wltg_owner.process_status, &observed,
                WltgPackProcessStatus(WLTG_PROCESS_REVOKED,
                                      WLTG_REASON_PROFILE_REVOKED),
                memory_order_release, memory_order_acquire)) {
            (void)WltgEmit(WLTG_EVENT_PROCESS_REVOKED,
                           WLTG_REASON_PROFILE_REVOKED,
                           (const WltgRecord *)0);
            return WltgResultValue(WLTG_STATUS_OK,
                                   WLTG_REASON_PROFILE_REVOKED,
                                   (const WltgRecord *)0);
        }
    }
}

WltgResult WLTG_GetProcessSnapshot(WltgProcessSnapshotV1 *out_snapshot)
{
    uint64_t before;
    uint64_t after;
    uint32_t index;
    if (out_snapshot == (WltgProcessSnapshotV1 *)0) {
        return WltgResultValue(WLTG_STATUS_INVALID_ARGUMENT,
                               WLTG_REASON_INVALID_ARGUMENT,
                               (const WltgRecord *)0);
    }
    WltgClearBytes(out_snapshot, sizeof(*out_snapshot));
    before = WltgLoadProcessStatus(memory_order_acquire);
    out_snapshot->abi_version = WLTG_ABI_VERSION;
    out_snapshot->struct_size = (uint32_t)sizeof(*out_snapshot);
    out_snapshot->process_state = WltgUnpackProcessState(before);
    out_snapshot->last_reason = WltgUnpackReason(before);
    out_snapshot->adapter_generation = atomic_load_explicit(
        &g_wltg_owner.adapter_generation, memory_order_relaxed);
    out_snapshot->process_epoch = atomic_load_explicit(
        &g_wltg_owner.process_epoch, memory_order_relaxed);
    out_snapshot->policy_epoch = atomic_load_explicit(
        &g_wltg_owner.policy_epoch, memory_order_relaxed);
    out_snapshot->binding_nonce = g_wltg_owner.binding.binding_nonce;
    out_snapshot->audit_sequence = atomic_load_explicit(
        &g_wltg_owner.audit_sequence, memory_order_relaxed);
    out_snapshot->audit_drop_count = atomic_load_explicit(
        &g_wltg_owner.audit_drop_count, memory_order_relaxed);
    out_snapshot->next_ticket_id = atomic_load_explicit(
        &g_wltg_owner.next_ticket_id, memory_order_relaxed);
    out_snapshot->active_ticket_count = atomic_load_explicit(
        &g_wltg_owner.active_ticket_count, memory_order_relaxed);
    for (index = 0; index < WLTG_MAX_THREAD_RECORDS; ++index) {
        switch (WltgRecordState(&g_wltg_owner.records[index],
                                memory_order_acquire)) {
            case WLTG_THREAD_ISSUED:
                out_snapshot->issued_count += UINT32_C(1);
                break;
            case WLTG_THREAD_PREPARING:
                out_snapshot->preparing_count += UINT32_C(1);
                break;
            case WLTG_THREAD_READY:
                out_snapshot->ready_count += UINT32_C(1);
                break;
            case WLTG_THREAD_RETIRED:
                out_snapshot->retired_count += UINT32_C(1);
                break;
            case WLTG_THREAD_CANCELLED:
                out_snapshot->cancelled_count += UINT32_C(1);
                break;
            case WLTG_THREAD_FAILED:
                out_snapshot->failed_count += UINT32_C(1);
                break;
            default:
                break;
        }
    }
    after = WltgLoadProcessStatus(memory_order_acquire);
    if (before != after) {
        WltgClearBytes(out_snapshot, sizeof(*out_snapshot));
        return WltgResultValue(WLTG_STATUS_DENIED_TRANSIENT,
                               WLTG_REASON_STATE_RACE,
                               (const WltgRecord *)0);
    }
    return WltgResultValue(WLTG_STATUS_OK, WLTG_REASON_NONE,
                           (const WltgRecord *)0);
}
