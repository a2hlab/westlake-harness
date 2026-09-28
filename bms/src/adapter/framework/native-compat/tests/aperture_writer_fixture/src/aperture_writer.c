#include "wlnc_aperture_fixture.h"

#include <stdbool.h>

/* Architecture implementation: exactly one aperture store and one readback. */
uint64_t WLAF_StoreAndReadback(uint64_t *address, uint64_t value);

_Static_assert(sizeof(uintptr_t) == 8, "fixture is a 64-bit ABI");
_Static_assert(sizeof(_Atomic uint32_t) == sizeof(uint32_t),
               "publication state must have a stable 32-bit ABI");
_Static_assert(offsetof(WlafPublication, reason) == 4,
               "publication ABI drift");
_Static_assert(WLAF_STACK_GUARD_TP_OFFSET >= WLAF_RESERVATION_TP_START,
               "guard must be inside the reservation");
_Static_assert(WLAF_STACK_GUARD_TP_OFFSET + WLAF_STACK_GUARD_WIDTH <=
                   WLAF_RESERVATION_TP_START + WLAF_RESERVATION_SIZE,
               "guard exceeds the reservation");

static bool BytesEqual(const uint8_t *left, const uint8_t *right,
                       size_t size)
{
    size_t index;
    uint8_t difference = UINT8_C(0);
    for (index = 0; index < size; ++index) {
        difference = (uint8_t)(difference | (uint8_t)(left[index] ^ right[index]));
    }
    return difference == UINT8_C(0);
}

static bool BytesAllZero(const uint8_t *bytes, size_t size)
{
    size_t index;
    uint8_t value = UINT8_C(0);
    for (index = 0; index < size; ++index) {
        value = (uint8_t)(value | bytes[index]);
    }
    return value == UINT8_C(0);
}

static void ClearBytes(void *memory, size_t size)
{
    volatile uint8_t *bytes = (volatile uint8_t *)memory;
    size_t index;
    for (index = 0; index < size; ++index) {
        bytes[index] = UINT8_C(0);
    }
}

static WlafPublicationState LoadState(const WlafPublication *publication)
{
    if (publication == (const WlafPublication *)0) {
        return WLAF_PUBLICATION_UNSEEN;
    }
    return (WlafPublicationState)atomic_load_explicit(
        &publication->state, memory_order_acquire);
}

static WlafResult Result(WlafStatus status, WlafReason reason,
                         const WlafPublication *publication)
{
    WlafResult result;
    result.status = status;
    result.reason = reason;
    result.publication_state = LoadState(publication);
    result.reserved_zero = UINT32_C(0);
    return result;
}

static void Emit(const WlafFixtureOps *ops, WlafEventType type,
                 WlafReason reason, const WlafFixturePermitV1 *permit,
                 const WlafPublication *publication)
{
    WlafEvent event;
    if (ops == (const WlafFixtureOps *)0 ||
        ops->emit_event == (WlafEmitEvent)0) {
        return;
    }
    event.abi_version = WLAF_ABI_VERSION;
    event.type = type;
    event.reason = reason;
    event.publication_state = LoadState(publication);
    event.adapter_generation = permit == (const WlafFixturePermitV1 *)0
                                   ? UINT64_C(0)
                                   : permit->adapter_generation;
    event.process_epoch = permit == (const WlafFixturePermitV1 *)0
                              ? UINT64_C(0)
                              : permit->process_epoch;
    event.policy_epoch = permit == (const WlafFixturePermitV1 *)0
                             ? UINT64_C(0)
                             : permit->policy_epoch;
    event.one_shot_nonce = permit == (const WlafFixturePermitV1 *)0
                               ? UINT64_C(0)
                               : permit->one_shot_nonce;
    ops->emit_event(ops->context, &event);
}

static WlafResult Deny(const WlafFixtureOps *ops,
                       const WlafFixturePermitV1 *permit,
                       WlafReason reason)
{
    Emit(ops, WLAF_EVENT_REJECTED, reason, permit,
         (const WlafPublication *)0);
    return Result(WLAF_STATUS_DENIED, reason,
                  (const WlafPublication *)0);
}

static WlafResult FailConsumed(const WlafFixtureOps *ops,
                               const WlafFixturePermitV1 *permit,
                               WlafPublication *publication,
                               WlafReason reason)
{
    publication->reason = (uint32_t)reason;
    atomic_store_explicit(&publication->state,
                          (uint32_t)WLAF_PUBLICATION_FAILED,
                          memory_order_release);
    Emit(ops, WLAF_EVENT_REJECTED, reason, permit, publication);
    return Result(WLAF_STATUS_TERMINAL, reason, publication);
}

static WlafReason ValidatePermitShape(const WlafFixturePermitV1 *permit)
{
    if (permit->abi_version != WLAF_ABI_VERSION ||
        permit->struct_size != sizeof(WlafFixturePermitV1) ||
        permit->struct_type != WLAF_PERMIT_STRUCT_TYPE) {
        return WLAF_REASON_ABI_MISMATCH;
    }
    if (permit->permit_kind != WLAF_PERMIT_KIND_FIXTURE_ONLY) {
        return WLAF_REASON_NOT_FIXTURE_PERMIT;
    }
    if (permit->mechanism != WLAF_MECHANISM_APERTURE_NATIVE_FIXTURE) {
        return WLAF_REASON_MECHANISM_MISMATCH;
    }
    if (permit->signature_size != WLAF_SIGNATURE_SIZE ||
        permit->adapter_generation == UINT64_C(0) ||
        permit->process_epoch == UINT64_C(0) ||
        permit->policy_epoch == UINT64_C(0) ||
        permit->one_shot_nonce == UINT64_C(0) ||
        permit->tp_offset != WLAF_STACK_GUARD_TP_OFFSET ||
        permit->width != WLAF_STACK_GUARD_WIDTH ||
        BytesAllZero(permit->target_digest, WLAF_TARGET_DIGEST_SIZE)) {
        return WLAF_REASON_PERMIT_FIELDS_INVALID;
    }
    if (BytesAllZero(permit->signature, WLAF_SIGNATURE_SIZE)) {
        return WLAF_REASON_SIGNATURE_REQUIRED;
    }
    return WLAF_REASON_NONE;
}

static WlafReason ValidateBinding(const WlafFixturePermitV1 *permit,
                                  const WlafCurrentBinding *binding)
{
    if (binding->abi_version != WLAF_ABI_VERSION ||
        binding->reserved_zero != UINT32_C(0)) {
        return WLAF_REASON_BINDING_UNAVAILABLE;
    }
    if (binding->adapter_generation != permit->adapter_generation ||
        binding->process_epoch != permit->process_epoch ||
        binding->policy_epoch != permit->policy_epoch ||
        !BytesEqual(binding->target_digest, permit->target_digest,
                    WLAF_TARGET_DIGEST_SIZE)) {
        return WLAF_REASON_BINDING_MISMATCH;
    }
    return WLAF_REASON_NONE;
}

static WlafReason ValidateRegion(const WlafFixturePermitV1 *permit,
                                 const WlafOwnedRegion *region)
{
    uintptr_t base_address;
    uint32_t relative_offset;
    if (region->abi_version != WLAF_ABI_VERSION ||
        region->owner_kind != WLAF_OWNER_MAIN_ELF_TLS_RESERVATION ||
        region->base == (uint8_t *)0 ||
        region->publication == (WlafPublication *)0 ||
        region->owner_cookie == UINT64_C(0)) {
        return WLAF_REASON_OWNER_MISMATCH;
    }
    if (region->adapter_generation != permit->adapter_generation ||
        region->process_epoch != permit->process_epoch ||
        region->policy_epoch != permit->policy_epoch) {
        return WLAF_REASON_OWNER_MISMATCH;
    }
#if !defined(WLAF_MUTANT_IGNORE_OWNER_BOUNDS)
    if (region->tp_start_offset != WLAF_RESERVATION_TP_START ||
        region->byte_size != WLAF_RESERVATION_SIZE ||
        permit->tp_offset < region->tp_start_offset ||
        permit->width > region->byte_size) {
        return WLAF_REASON_OWNER_BOUNDS;
    }
#endif
    relative_offset = permit->tp_offset - region->tp_start_offset;
    if (relative_offset > region->byte_size - permit->width) {
        return WLAF_REASON_OWNER_BOUNDS;
    }
    base_address = (uintptr_t)region->base;
    if (base_address > UINTPTR_MAX - relative_offset ||
        ((base_address + relative_offset) &
         (uintptr_t)(WLAF_STACK_GUARD_WIDTH - UINT32_C(1))) != 0U) {
        return WLAF_REASON_OWNER_BOUNDS;
    }
    return WLAF_REASON_NONE;
}

WlafResult WLAF_PublishFixtureAperture(const WlafFixturePermitV1 *permit,
                                       const WlafFixtureOps *ops)
{
    WlafReason reason;
    WlafCurrentBinding binding = {0};
    WlafOwnedRegion region = {0};
    WlafGuardSample sample = {0};
    WlafPublication *publication;
    uint32_t expected_state;
    uint32_t relative_offset;
    uint64_t *slot;
    uint64_t readback;

    if (permit == (const WlafFixturePermitV1 *)0 ||
        ops == (const WlafFixtureOps *)0 ||
        ops->abi_version != WLAF_ABI_VERSION ||
        ops->reserved_zero != UINT32_C(0) ||
        ops->read_current_binding == (WlafReadCurrentBinding)0 ||
        ops->verify_fixture_signature == (WlafVerifyFixtureSignature)0 ||
        ops->resolve_current_thread_region ==
            (WlafResolveCurrentThreadRegion)0 ||
        ops->get_os_csprng == (WlafGetOsCsprng)0) {
        return Result(WLAF_STATUS_INVALID_ARGUMENT,
                      WLAF_REASON_INVALID_ARGUMENT,
                      (const WlafPublication *)0);
    }

    reason = ValidatePermitShape(permit);
    if (reason != WLAF_REASON_NONE) {
        return Deny(ops, permit, reason);
    }
    if (ops->read_current_binding(ops->context, &binding) != 1) {
        return Deny(ops, permit, WLAF_REASON_BINDING_UNAVAILABLE);
    }
    reason = ValidateBinding(permit, &binding);
    if (reason != WLAF_REASON_NONE) {
        return Deny(ops, permit, reason);
    }
#if !defined(WLAF_MUTANT_SKIP_PERMIT_SIGNATURE)
    if (ops->verify_fixture_signature(ops->context, permit) != 1) {
        return Deny(ops, permit, WLAF_REASON_SIGNATURE_REJECTED);
    }
#endif
    Emit(ops, WLAF_EVENT_PERMIT_VERIFIED, WLAF_REASON_NONE, permit,
         (const WlafPublication *)0);

    if (ops->resolve_current_thread_region(ops->context, permit, &region) != 1) {
        return Deny(ops, permit, WLAF_REASON_OWNER_UNAVAILABLE);
    }
    reason = ValidateRegion(permit, &region);
    if (reason != WLAF_REASON_NONE) {
        return Deny(ops, permit, reason);
    }
    publication = region.publication;
    Emit(ops, WLAF_EVENT_OWNER_RESOLVED, WLAF_REASON_NONE, permit,
         publication);

    expected_state = (uint32_t)WLAF_PUBLICATION_UNSEEN;
    if (!atomic_compare_exchange_strong_explicit(
            &publication->state, &expected_state,
            (uint32_t)WLAF_PUBLICATION_PREPARING,
            memory_order_acq_rel, memory_order_acquire)) {
        return Deny(ops, permit, WLAF_REASON_PERMIT_REPLAY);
    }
    Emit(ops, WLAF_EVENT_PERMIT_CONSUMED, WLAF_REASON_NONE, permit,
         publication);

    if (ops->get_os_csprng(ops->context, permit->process_epoch, &sample) != 1) {
#if defined(WLAF_MUTANT_FIXED_FALLBACK)
        sample.value = UINT64_C(0x574c4e4346495845);
        sample.source_epoch = permit->process_epoch;
        sample.quality = WLAF_GUARD_SOURCE_OS_CSPRNG;
        sample.reserved_zero = UINT32_C(0);
#else
        ClearBytes(&sample, sizeof(sample));
        return FailConsumed(ops, permit, publication,
                            WLAF_REASON_CSPRNG_FAILED);
#endif
    }
    if (sample.quality != WLAF_GUARD_SOURCE_OS_CSPRNG ||
        sample.source_epoch != permit->process_epoch ||
        sample.reserved_zero != UINT32_C(0)) {
        ClearBytes(&sample, sizeof(sample));
        return FailConsumed(ops, permit, publication,
                            WLAF_REASON_CSPRNG_QUALITY);
    }
    if (sample.value == UINT64_C(0)) {
        ClearBytes(&sample, sizeof(sample));
        return FailConsumed(ops, permit, publication,
                            WLAF_REASON_GUARD_VALUE_INVALID);
    }

    relative_offset = permit->tp_offset - region.tp_start_offset;
    slot = (uint64_t *)(void *)(region.base + relative_offset);

#if defined(WLAF_MUTANT_READY_BEFORE_METADATA)
    atomic_store_explicit(&publication->state,
                          (uint32_t)WLAF_PUBLICATION_READY,
                          memory_order_release);
    Emit(ops, WLAF_EVENT_READY_PUBLISHED, WLAF_REASON_NONE, permit,
         publication);
#endif

    readback = WLAF_StoreAndReadback(slot, sample.value);
    Emit(ops, WLAF_EVENT_GUARD_WRITTEN, WLAF_REASON_NONE, permit,
         publication);
    if (readback != sample.value) {
        ClearBytes(&sample, sizeof(sample));
        return FailConsumed(ops, permit, publication,
                            WLAF_REASON_READBACK_MISMATCH);
    }
    Emit(ops, WLAF_EVENT_READBACK_VERIFIED, WLAF_REASON_NONE, permit,
         publication);

    /* Stage every receipt field before the release publication of READY. */
    publication->reason = (uint32_t)WLAF_REASON_NONE;
    publication->adapter_generation = permit->adapter_generation;
    publication->process_epoch = permit->process_epoch;
    publication->policy_epoch = permit->policy_epoch;
    publication->one_shot_nonce = permit->one_shot_nonce;
    publication->owner_cookie = region.owner_cookie;
    publication->written_address = (uintptr_t)slot;
    publication->tp_offset = permit->tp_offset;
    publication->width = permit->width;
    publication->guard_value = sample.value;
    publication->readback_value = readback;
    Emit(ops, WLAF_EVENT_METADATA_STAGED, WLAF_REASON_NONE, permit,
         publication);

#if !defined(WLAF_MUTANT_READY_BEFORE_METADATA)
    atomic_store_explicit(&publication->state,
                          (uint32_t)WLAF_PUBLICATION_READY,
                          memory_order_release);
    Emit(ops, WLAF_EVENT_READY_PUBLISHED, WLAF_REASON_NONE, permit,
         publication);
#endif

    ClearBytes(&sample, sizeof(sample));
    return Result(WLAF_STATUS_OK, WLAF_REASON_NONE, publication);
}

const char *WLAF_ReasonString(WlafReason reason)
{
    switch (reason) {
        case WLAF_REASON_NONE: return "none";
        case WLAF_REASON_INVALID_ARGUMENT: return "invalid_argument";
        case WLAF_REASON_ABI_MISMATCH: return "abi_mismatch";
        case WLAF_REASON_NOT_FIXTURE_PERMIT: return "not_fixture_permit";
        case WLAF_REASON_MECHANISM_MISMATCH: return "mechanism_mismatch";
        case WLAF_REASON_PERMIT_FIELDS_INVALID: return "permit_fields_invalid";
        case WLAF_REASON_SIGNATURE_REQUIRED: return "signature_required";
        case WLAF_REASON_SIGNATURE_REJECTED: return "signature_rejected";
        case WLAF_REASON_BINDING_UNAVAILABLE: return "binding_unavailable";
        case WLAF_REASON_BINDING_MISMATCH: return "binding_mismatch";
        case WLAF_REASON_OWNER_UNAVAILABLE: return "owner_unavailable";
        case WLAF_REASON_OWNER_MISMATCH: return "owner_mismatch";
        case WLAF_REASON_OWNER_BOUNDS: return "owner_bounds";
        case WLAF_REASON_PERMIT_REPLAY: return "permit_replay";
        case WLAF_REASON_CSPRNG_FAILED: return "csprng_failed";
        case WLAF_REASON_CSPRNG_QUALITY: return "csprng_quality";
        case WLAF_REASON_GUARD_VALUE_INVALID: return "guard_value_invalid";
        case WLAF_REASON_READBACK_MISMATCH: return "readback_mismatch";
        case WLAF_REASON_INTERNAL_STATE: return "internal_state";
        default: return "unknown";
    }
}
