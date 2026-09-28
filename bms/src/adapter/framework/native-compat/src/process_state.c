#include "native_compat_internal.h"

#include <stdatomic.h>

#if ATOMIC_INT_LOCK_FREE != 2 || ATOMIC_LLONG_LOCK_FREE != 2 || \
    ATOMIC_POINTER_LOCK_FREE != 2
#error "native-compat fork reset requires always-lock-free scalar atomics"
#endif

typedef struct WlncOwner {
    _Atomic uint32_t fork_seeded;
    _Atomic uint32_t init_gate;
    _Atomic uint32_t thread_state;
    _Atomic uint32_t mechanism;
    _Atomic uint32_t thread_role;
    _Atomic uint32_t target_build_id_size;
    _Atomic uint64_t adapter_generation;
    _Atomic uint64_t process_epoch;
    _Atomic uint64_t policy_epoch;
    _Atomic uint64_t thread_generation;
    _Atomic uint64_t thread_process_epoch;
    _Atomic uint64_t thread_policy_epoch;
    _Atomic uint64_t thread_id;
    _Atomic uint64_t audit_sequence;
    _Atomic uint64_t audit_drop_count;
    _Atomic uint64_t process_status;
    _Atomic uint64_t profile_digest[4];
    _Atomic uint64_t target_digest[4];
    _Atomic uint64_t target_build_id[4];
    _Atomic(void *) platform_context;
    _Atomic(WlncGetGuardSource) get_guard_source;
    _Atomic(WlncGetThreadId) get_thread_id;
    _Atomic(WlncEmitAuditEvent) emit_audit_event;
} WlncOwner;

/* The process has exactly one compatibility-state owner in this DSO. */
static WlncOwner g_wlnc_owner;

static uint64_t WlncPackProcessStatus(WlncProcessState state,
                                      WlncReason reason)
{
    return ((uint64_t)(uint32_t)reason << UINT32_C(32)) |
           (uint64_t)(uint32_t)state;
}

static WlncProcessState WlncStatusProcessState(uint64_t status)
{
    return (WlncProcessState)(uint32_t)status;
}

static WlncReason WlncStatusReason(uint64_t status)
{
    return (WlncReason)(uint32_t)(status >> UINT32_C(32));
}

static uint64_t WlncLoadProcessStatus(memory_order order)
{
    return atomic_load_explicit(&g_wlnc_owner.process_status, order);
}

static void WlncStoreProcessStatus(WlncProcessState state, WlncReason reason,
                                   memory_order order)
{
    atomic_store_explicit(&g_wlnc_owner.process_status,
                          WlncPackProcessStatus(state, reason), order);
}

static uint64_t WlncPackU64(const uint8_t *bytes)
{
    uint64_t value = 0;
    uint32_t i;
    for (i = 0; i < UINT32_C(8); ++i) {
        value |= ((uint64_t)bytes[i]) << (i * UINT32_C(8));
    }
    return value;
}

static void WlncUnpackU64(uint64_t value, uint8_t *bytes)
{
    uint32_t i;
    for (i = 0; i < UINT32_C(8); ++i) {
        bytes[i] = (uint8_t)(value >> (i * UINT32_C(8)));
    }
}

static int WlncBytesEqual(const uint8_t *left, const uint8_t *right,
                          uint32_t size)
{
    uint8_t difference = 0;
    uint32_t i;
    for (i = 0; i < size; ++i) {
        difference |= (uint8_t)(left[i] ^ right[i]);
    }
    return difference == 0;
}

static int WlncBytesAllZero(const uint8_t *bytes, uint32_t size)
{
    uint8_t combined = 0;
    uint32_t i;
    for (i = 0; i < size; ++i) {
        combined |= bytes[i];
    }
    return combined == 0;
}

static void WlncStoreDigest(_Atomic uint64_t destination[4],
                            const uint8_t source[WLNC_DIGEST_SIZE])
{
    uint32_t i;
    for (i = 0; i < UINT32_C(4); ++i) {
        atomic_store_explicit(&destination[i],
                              WlncPackU64(source + i * UINT32_C(8)),
                              memory_order_relaxed);
    }
}

static void WlncClearDigest(_Atomic uint64_t destination[4])
{
    uint32_t i;
    for (i = 0; i < UINT32_C(4); ++i) {
        atomic_store_explicit(&destination[i], UINT64_C(0),
                              memory_order_relaxed);
    }
}

static void WlncLoadDigest(const _Atomic uint64_t source[4],
                           uint8_t destination[WLNC_DIGEST_SIZE])
{
    uint32_t i;
    for (i = 0; i < UINT32_C(4); ++i) {
        uint64_t word = atomic_load_explicit(&source[i], memory_order_relaxed);
        WlncUnpackU64(word, destination + i * UINT32_C(8));
    }
}

static int WlncStoredDigestEquals(const _Atomic uint64_t stored[4],
                                  const uint8_t candidate[WLNC_DIGEST_SIZE])
{
    uint32_t i;
    uint64_t difference = 0;
    for (i = 0; i < UINT32_C(4); ++i) {
        difference |= atomic_load_explicit(&stored[i], memory_order_relaxed) ^
                      WlncPackU64(candidate + i * UINT32_C(8));
    }
    return difference == 0;
}

static WlncProcessState WlncLoadProcessState(memory_order order)
{
    return WlncStatusProcessState(WlncLoadProcessStatus(order));
}

static WlncReason WlncLoadLastReason(memory_order order)
{
    return WlncStatusReason(WlncLoadProcessStatus(order));
}

static WlncThreadState WlncLoadThreadState(memory_order order)
{
    return (WlncThreadState)atomic_load_explicit(
        &g_wlnc_owner.thread_state, order);
}

static WlncResult WlncMakeResult(WlncStatus status, WlncReason reason)
{
    WlncResult result;
    result.status = status;
    result.reason = reason;
    result.process_state = WlncLoadProcessState(memory_order_acquire);
    result.thread_state = WlncLoadThreadState(memory_order_acquire);
    return result;
}

static int WlncProcessStateIsTerminal(WlncProcessState state)
{
    return state == WLNC_PROCESS_REVOKED || state == WLNC_PROCESS_REJECTED;
}

static void WlncEmitEvent(WlncAuditEventType type, WlncReason reason)
{
    WlncEmitAuditEvent sink = atomic_load_explicit(
        &g_wlnc_owner.emit_audit_event, memory_order_acquire);
    WlncAuditEvent event;
    int accepted = 0;

    event.abi_version = WLNC_ABI_VERSION;
    event.type = type;
    event.sequence = atomic_fetch_add_explicit(
                         &g_wlnc_owner.audit_sequence, UINT64_C(1),
                         memory_order_relaxed) +
                     UINT64_C(1);
    event.reason = reason;
    event.process_state = WlncLoadProcessState(memory_order_acquire);
    event.thread_state = WlncLoadThreadState(memory_order_acquire);
    event.thread_role = (WlncThreadRole)atomic_load_explicit(
        &g_wlnc_owner.thread_role, memory_order_relaxed);
    event.adapter_generation = atomic_load_explicit(
        &g_wlnc_owner.adapter_generation, memory_order_relaxed);
    event.process_epoch = atomic_load_explicit(
        &g_wlnc_owner.process_epoch, memory_order_relaxed);
    event.policy_epoch = atomic_load_explicit(
        &g_wlnc_owner.policy_epoch, memory_order_relaxed);
    event.thread_id = atomic_load_explicit(&g_wlnc_owner.thread_id,
                                           memory_order_relaxed);

    if (sink != (WlncEmitAuditEvent)0) {
        void *context = atomic_load_explicit(&g_wlnc_owner.platform_context,
                                             memory_order_acquire);
        accepted = sink(context, &event);
    }
    if (accepted == 0) {
        (void)atomic_fetch_add_explicit(&g_wlnc_owner.audit_drop_count,
                                        UINT64_C(1), memory_order_relaxed);
    }
}

static WlncResult WlncTerminalReject(WlncReason reason)
{
    uint64_t observed = WlncLoadProcessStatus(memory_order_acquire);
    int transitioned = 0;

    atomic_store_explicit(&g_wlnc_owner.thread_state,
                          (uint32_t)WLNC_THREAD_INVALID,
                          memory_order_release);

    while (!WlncProcessStateIsTerminal(WlncStatusProcessState(observed))) {
        uint64_t desired = WlncPackProcessStatus(WLNC_PROCESS_REJECTED,
                                                 reason);
        if (atomic_compare_exchange_weak_explicit(
                &g_wlnc_owner.process_status, &observed, desired,
                memory_order_release,
                memory_order_acquire)) {
            transitioned = 1;
            break;
        }
    }
    if (transitioned != 0) {
        WlncEmitEvent(WLNC_EVENT_REJECT, reason);
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL, reason);
    }
    return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                          WlncStatusReason(observed));
}

static void WlncStoreBuildId(const uint8_t build_id[WLNC_BUILD_ID_MAX_SIZE])
{
    WlncStoreDigest(g_wlnc_owner.target_build_id, build_id);
}

static int WlncStoredBuildIdEquals(const uint8_t *build_id,
                                   uint32_t build_id_size)
{
    uint8_t stored[WLNC_BUILD_ID_MAX_SIZE];
    uint32_t stored_size = atomic_load_explicit(
        &g_wlnc_owner.target_build_id_size, memory_order_relaxed);

    if (stored_size != build_id_size) {
        return 0;
    }
    WlncLoadDigest(g_wlnc_owner.target_build_id, stored);
    return WlncBytesEqual(stored, build_id, build_id_size);
}

static WlncReason WlncValidateStaticInputs(
    const WlncPreverifiedCapabilityV1 *capability,
    const WlncTargetIdentity *expected_target,
    const WlncPlatformOps *platform_ops)
{
    if (capability == (const WlncPreverifiedCapabilityV1 *)0 ||
        expected_target == (const WlncTargetIdentity *)0 ||
        platform_ops == (const WlncPlatformOps *)0) {
        return WLNC_REASON_INVALID_ARGUMENT;
    }
    if (capability->abi_version != WLNC_ABI_VERSION ||
        capability->target.abi_version != WLNC_ABI_VERSION ||
        expected_target->abi_version != WLNC_ABI_VERSION ||
        platform_ops->abi_version != WLNC_ABI_VERSION) {
        return WLNC_REASON_ABI_VERSION_MISMATCH;
    }
    if (capability->marker != WLNC_PREVERIFIED_CAPABILITY_MARKER ||
        capability->origin != WLNC_CAPABILITY_ORIGIN_UPSTREAM_PREVERIFIED) {
        return WLNC_REASON_CAPABILITY_NOT_PREVERIFIED;
    }
    if (capability->mechanism != WLNC_MECHANISM_AUDIT_ONLY) {
        return WLNC_REASON_MECHANISM_UNSUPPORTED;
    }
    if (capability->inline_unknown_count != 0 ||
        capability->cfg_unknown_count != 0 ||
        capability->unproven_overlap_count != 0 ||
        capability->missing_thread_entry_count != 0 ||
        capability->pre_prepare_slot5_access_count != 0) {
        return WLNC_REASON_HARD_COUNT_NONZERO;
    }
    if (capability->guest_scan_complete != 1 ||
        capability->initial_closure_complete != 1 ||
        capability->prepare_order_proven != 1 ||
        capability->loader_provenance_complete != 1 ||
        capability->generation_manifest_complete != 1) {
        return WLNC_REASON_REQUIRED_PROOF_MISSING;
    }
    if (capability->reserved_zero != 0 || platform_ops->reserved_zero != 0 ||
        expected_target->adapter_generation == 0 ||
        capability->process_epoch == 0 || capability->policy_epoch == 0 ||
        expected_target->build_id_size == 0 ||
        expected_target->build_id_size > WLNC_BUILD_ID_MAX_SIZE ||
        capability->target.build_id_size == 0 ||
        capability->target.build_id_size > WLNC_BUILD_ID_MAX_SIZE ||
        platform_ops->get_guard_source == (WlncGetGuardSource)0 ||
        platform_ops->get_thread_id == (WlncGetThreadId)0) {
        return WLNC_REASON_INVALID_ARGUMENT;
    }
    if (WlncBytesAllZero(capability->profile_sha256, WLNC_DIGEST_SIZE) ||
        WlncBytesAllZero(expected_target->target_sha256, WLNC_DIGEST_SIZE)) {
        return WLNC_REASON_INVALID_ARGUMENT;
    }
    if (!WlncBytesEqual(capability->target.target_sha256,
                        expected_target->target_sha256, WLNC_DIGEST_SIZE)) {
        return WLNC_REASON_TARGET_SHA_MISMATCH;
    }
    if (capability->target.build_id_size != expected_target->build_id_size ||
        !WlncBytesEqual(capability->target.build_id,
                        expected_target->build_id,
                        expected_target->build_id_size)) {
        return WLNC_REASON_TARGET_BUILD_ID_MISMATCH;
    }
    if (capability->target.adapter_generation !=
        expected_target->adapter_generation) {
        return WLNC_REASON_GENERATION_MISMATCH;
    }
    return WLNC_REASON_NONE;
}

static int WlncCapabilityMatchesOwner(
    const WlncPreverifiedCapabilityV1 *capability,
    const WlncTargetIdentity *expected_target)
{
    uint64_t generation = atomic_load_explicit(
        &g_wlnc_owner.adapter_generation, memory_order_relaxed);
    uint64_t process_epoch = atomic_load_explicit(
        &g_wlnc_owner.process_epoch, memory_order_relaxed);
    uint64_t policy_epoch = atomic_load_explicit(
        &g_wlnc_owner.policy_epoch, memory_order_relaxed);

    return capability->mechanism == (WlncMechanism)atomic_load_explicit(
               &g_wlnc_owner.mechanism, memory_order_relaxed) &&
           capability->target.adapter_generation == generation &&
           expected_target->adapter_generation == generation &&
           capability->process_epoch == process_epoch &&
           capability->policy_epoch == policy_epoch &&
           WlncStoredDigestEquals(g_wlnc_owner.profile_digest,
                                  capability->profile_sha256) &&
           WlncStoredDigestEquals(g_wlnc_owner.target_digest,
                                  expected_target->target_sha256) &&
           WlncStoredBuildIdEquals(expected_target->build_id,
                                   expected_target->build_id_size);
}

static int WlncPlatformOpsMatchOwner(const WlncPlatformOps *platform_ops)
{
    return atomic_load_explicit(&g_wlnc_owner.platform_context,
                                memory_order_relaxed) ==
               platform_ops->context &&
           atomic_load_explicit(&g_wlnc_owner.get_guard_source,
                                memory_order_relaxed) ==
               platform_ops->get_guard_source &&
           atomic_load_explicit(&g_wlnc_owner.get_thread_id,
                                memory_order_relaxed) ==
               platform_ops->get_thread_id &&
           atomic_load_explicit(&g_wlnc_owner.emit_audit_event,
                                memory_order_relaxed) ==
               platform_ops->emit_audit_event;
}

uint32_t WLNC_GetAbiVersion(void)
{
    return WLNC_ABI_VERSION;
}

const char *WLNC_ReasonString(WlncReason reason)
{
    switch (reason) {
        case WLNC_REASON_NONE: return "none";
        case WLNC_REASON_ALREADY_INITIALIZED: return "already_initialized";
        case WLNC_REASON_INVALID_ARGUMENT: return "invalid_argument";
        case WLNC_REASON_ABI_VERSION_MISMATCH: return "abi_version_mismatch";
        case WLNC_REASON_CAPABILITY_NOT_PREVERIFIED:
            return "capability_not_preverified";
        case WLNC_REASON_TARGET_SHA_MISMATCH: return "target_sha_mismatch";
        case WLNC_REASON_TARGET_BUILD_ID_MISMATCH:
            return "target_build_id_mismatch";
        case WLNC_REASON_GENERATION_MISMATCH: return "generation_mismatch";
        case WLNC_REASON_PROCESS_EPOCH_MISMATCH:
            return "process_epoch_mismatch";
        case WLNC_REASON_POLICY_EPOCH_MISMATCH:
            return "policy_epoch_mismatch";
        case WLNC_REASON_MECHANISM_UNSUPPORTED:
            return "mechanism_unsupported";
        case WLNC_REASON_HARD_COUNT_NONZERO: return "hard_count_nonzero";
        case WLNC_REASON_GUARD_SOURCE_FAILED: return "guard_source_failed";
        case WLNC_REASON_GUARD_VALUE_INVALID: return "guard_value_invalid";
        case WLNC_REASON_GUARD_EPOCH_MISMATCH:
            return "guard_epoch_mismatch";
        case WLNC_REASON_PROCESS_TERMINAL: return "process_terminal";
        case WLNC_REASON_CONCURRENT_INIT: return "concurrent_init";
        case WLNC_REASON_PROFILE_REPLAY: return "profile_replay";
        case WLNC_REASON_PROFILE_REVOKED: return "profile_revoked";
        case WLNC_REASON_THREAD_NOT_READY: return "thread_not_ready";
        case WLNC_REASON_THREAD_OWNER_MISMATCH:
            return "thread_owner_mismatch";
        case WLNC_REASON_THREAD_PUBLICATION_RACE:
            return "thread_publication_race";
        case WLNC_REASON_INVALID_THREAD_ROLE:
            return "invalid_thread_role";
        case WLNC_REASON_LOAD_IDENTITY_MISMATCH:
            return "load_identity_mismatch";
        case WLNC_REASON_INTERNAL_STATE: return "internal_state";
        case WLNC_REASON_FORK_RESET_REQUIRED:
            return "fork_reset_required";
        case WLNC_REASON_PLATFORM_OWNER_MISMATCH:
            return "platform_owner_mismatch";
        case WLNC_REASON_AUDIT_ONLY_NO_LOAD_AUTHORITY:
            return "audit_only_no_load_authority";
        case WLNC_REASON_REQUIRED_PROOF_MISSING:
            return "required_proof_missing";
        default: return "unknown";
    }
}

WlncResult WLNC_AfterForkChildReset(const WlncForkSeed *seed)
{
    WlncReason reason = WLNC_REASON_NONE;
    uint64_t generation = UINT64_C(0);
    uint64_t process_epoch = UINT64_C(0);
    uint64_t policy_epoch = UINT64_C(0);

    if (seed == (const WlncForkSeed *)0) {
        reason = WLNC_REASON_INVALID_ARGUMENT;
    } else if (seed->abi_version != WLNC_ABI_VERSION) {
        reason = WLNC_REASON_ABI_VERSION_MISMATCH;
    } else if (seed->reserved_zero != 0 || seed->adapter_generation == 0 ||
               seed->process_epoch == 0 || seed->policy_epoch == 0) {
        reason = WLNC_REASON_INVALID_ARGUMENT;
    } else {
        generation = seed->adapter_generation;
        process_epoch = seed->process_epoch;
        policy_epoch = seed->policy_epoch;
    }

    atomic_store_explicit(&g_wlnc_owner.fork_seeded, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                          memory_order_relaxed);
    WlncStoreProcessStatus(WLNC_PROCESS_UNINITIALIZED, WLNC_REASON_NONE,
                           memory_order_relaxed);
#if !defined(WLNC_MUTANT_INHERIT_PARENT_READY)
    atomic_store_explicit(&g_wlnc_owner.thread_state,
                          (uint32_t)WLNC_THREAD_UNSEEN,
                          memory_order_relaxed);
#endif
    atomic_store_explicit(&g_wlnc_owner.mechanism,
                          (uint32_t)WLNC_MECHANISM_INVALID,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_role,
                          (uint32_t)WLNC_THREAD_ROLE_INVALID,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.target_build_id_size, UINT32_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.adapter_generation, generation,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.process_epoch, process_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.policy_epoch, policy_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_generation, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_process_epoch, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_policy_epoch, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_id, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.audit_sequence, UINT64_C(0),
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.audit_drop_count, UINT64_C(0),
                          memory_order_relaxed);
    WlncClearDigest(g_wlnc_owner.profile_digest);
    WlncClearDigest(g_wlnc_owner.target_digest);
    WlncClearDigest(g_wlnc_owner.target_build_id);
    atomic_store_explicit(&g_wlnc_owner.platform_context, (void *)0,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.get_guard_source,
                          (WlncGetGuardSource)0, memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.get_thread_id,
                          (WlncGetThreadId)0, memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.emit_audit_event,
                          (WlncEmitAuditEvent)0, memory_order_relaxed);

    if (reason != WLNC_REASON_NONE) {
        atomic_store_explicit(&g_wlnc_owner.thread_state,
                              (uint32_t)WLNC_THREAD_INVALID,
                              memory_order_relaxed);
        WlncStoreProcessStatus(WLNC_PROCESS_REJECTED, reason,
                               memory_order_release);
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL, reason);
    }

    atomic_store_explicit(&g_wlnc_owner.fork_seeded, UINT32_C(1),
                          memory_order_release);
    WlncStoreProcessStatus(WLNC_PROCESS_UNINITIALIZED, WLNC_REASON_NONE,
                           memory_order_release);
    return WlncMakeResult(WLNC_STATUS_OK, WLNC_REASON_NONE);
}

WlncResult WLNC_ProcessInitPreverified(
    const WlncPreverifiedCapabilityV1 *capability,
    const WlncTargetIdentity *expected_target,
    const WlncPlatformOps *platform_ops)
{
    uint32_t expected_gate = UINT32_C(0);
    WlncReason reason;
    WlncProcessState state;
    WlncGetGuardSource guard_source;
    WlncGuardSourceSample sample;
    int source_ok;
    uint64_t expected_status;

    if (!atomic_compare_exchange_strong_explicit(
            &g_wlnc_owner.init_gate, &expected_gate, UINT32_C(1),
            memory_order_acquire, memory_order_relaxed)) {
        return WlncMakeResult(WLNC_STATUS_DENIED_TRANSIENT,
                              WLNC_REASON_CONCURRENT_INIT);
    }

    state = WlncLoadProcessState(memory_order_acquire);
    if (WlncProcessStateIsTerminal(state)) {
        atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                              memory_order_release);
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                              WlncLoadLastReason(memory_order_relaxed));
    }

    if (atomic_load_explicit(&g_wlnc_owner.fork_seeded,
                             memory_order_acquire) != UINT32_C(1)) {
        WlncResult rejected = WlncTerminalReject(
            WLNC_REASON_FORK_RESET_REQUIRED);
        atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                              memory_order_release);
        return rejected;
    }

    reason = WlncValidateStaticInputs(capability, expected_target,
                                      platform_ops);
    if (reason != WLNC_REASON_NONE) {
        WlncResult rejected = WlncTerminalReject(reason);
        atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                              memory_order_release);
        return rejected;
    }

    if (state == WLNC_PROCESS_ARMED) {
        if (WlncCapabilityMatchesOwner(capability, expected_target) &&
            WlncPlatformOpsMatchOwner(platform_ops)) {
            atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                                  memory_order_release);
            return WlncMakeResult(WLNC_STATUS_OK_IDEMPOTENT,
                                  WLNC_REASON_ALREADY_INITIALIZED);
        }
        {
            WlncReason replay_reason =
                WlncCapabilityMatchesOwner(capability, expected_target)
                    ? WLNC_REASON_PLATFORM_OWNER_MISMATCH
                    : WLNC_REASON_PROFILE_REPLAY;
            WlncResult rejected = WlncTerminalReject(replay_reason);
            atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                                  memory_order_release);
            return rejected;
        }
    }
    if (state != WLNC_PROCESS_UNINITIALIZED) {
        WlncResult rejected = WlncTerminalReject(WLNC_REASON_INTERNAL_STATE);
        atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                              memory_order_release);
        return rejected;
    }

    if (capability->target.adapter_generation != atomic_load_explicit(
            &g_wlnc_owner.adapter_generation, memory_order_relaxed)) {
        reason = WLNC_REASON_GENERATION_MISMATCH;
    } else if (capability->process_epoch != atomic_load_explicit(
                   &g_wlnc_owner.process_epoch, memory_order_relaxed)) {
        reason = WLNC_REASON_PROCESS_EPOCH_MISMATCH;
    } else if (capability->policy_epoch != atomic_load_explicit(
                   &g_wlnc_owner.policy_epoch, memory_order_relaxed)) {
        reason = WLNC_REASON_POLICY_EPOCH_MISMATCH;
    }
    if (reason != WLNC_REASON_NONE) {
        WlncResult rejected = WlncTerminalReject(reason);
        atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                              memory_order_release);
        return rejected;
    }

    atomic_store_explicit(&g_wlnc_owner.platform_context,
                          platform_ops->context, memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.get_guard_source,
                          platform_ops->get_guard_source,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.get_thread_id,
                          platform_ops->get_thread_id, memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.emit_audit_event,
                          platform_ops->emit_audit_event,
                          memory_order_release);
    WlncStoreProcessStatus(WLNC_PROCESS_INITIALIZING, WLNC_REASON_NONE,
                           memory_order_release);

    guard_source = platform_ops->get_guard_source;
    sample.value = UINT64_C(0);
    sample.source_epoch = UINT64_C(0);
    sample.quality = WLNC_GUARD_SOURCE_QUALITY_INVALID;
    sample.reserved_zero = UINT32_C(0);
    source_ok = guard_source(platform_ops->context,
                             capability->process_epoch, &sample);
    if (source_ok != 1) {
        reason = WLNC_REASON_GUARD_SOURCE_FAILED;
    } else if (sample.value == 0 || sample.reserved_zero != 0) {
        reason = WLNC_REASON_GUARD_VALUE_INVALID;
    } else if (sample.source_epoch != capability->process_epoch) {
        reason = WLNC_REASON_GUARD_EPOCH_MISMATCH;
#if defined(WLNC_TESTING)
    } else if (sample.quality != WLNC_GUARD_SOURCE_QUALITY_OS_CSPRNG &&
               sample.quality !=
                   WLNC_GUARD_SOURCE_QUALITY_TEST_DETERMINISTIC) {
#else
    } else if (sample.quality != WLNC_GUARD_SOURCE_QUALITY_OS_CSPRNG) {
#endif
        reason = WLNC_REASON_GUARD_SOURCE_FAILED;
    }
    {
        volatile uint64_t *erase = &sample.value;
        *erase = UINT64_C(0);
    }
    if (reason != WLNC_REASON_NONE) {
        WlncResult rejected = WlncTerminalReject(reason);
        atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                              memory_order_release);
        return rejected;
    }

    WlncStoreDigest(g_wlnc_owner.profile_digest,
                    capability->profile_sha256);
    WlncStoreDigest(g_wlnc_owner.target_digest,
                    expected_target->target_sha256);
    WlncStoreBuildId(expected_target->build_id);
    atomic_store_explicit(&g_wlnc_owner.target_build_id_size,
                          expected_target->build_id_size,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.mechanism,
                          (uint32_t)WLNC_MECHANISM_AUDIT_ONLY,
                          memory_order_relaxed);
    expected_status = WlncPackProcessStatus(WLNC_PROCESS_INITIALIZING,
                                            WLNC_REASON_NONE);
    if (!atomic_compare_exchange_strong_explicit(
            &g_wlnc_owner.process_status, &expected_status,
            WlncPackProcessStatus(WLNC_PROCESS_PROFILE_VERIFIED,
                                  WLNC_REASON_NONE),
            memory_order_release, memory_order_acquire)) {
        WlncReason terminal_reason = WlncStatusReason(expected_status);
        atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                              memory_order_release);
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                              terminal_reason == WLNC_REASON_NONE
                                  ? WLNC_REASON_PROCESS_TERMINAL
                                  : terminal_reason);
    }
    WlncEmitEvent(WLNC_EVENT_PROFILE_PREVERIFIED, WLNC_REASON_NONE);

    {
        expected_status = WlncPackProcessStatus(
            WLNC_PROCESS_PROFILE_VERIFIED, WLNC_REASON_NONE);
        uint64_t desired_status = WlncPackProcessStatus(
            WLNC_PROCESS_ARMED, WLNC_REASON_NONE);
        if (!atomic_compare_exchange_strong_explicit(
                &g_wlnc_owner.process_status, &expected_status,
                desired_status, memory_order_release,
                memory_order_acquire)) {
            WlncReason terminal_reason = WlncStatusReason(expected_status);
            atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                                  memory_order_release);
            return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                                  terminal_reason == WLNC_REASON_NONE
                                      ? WLNC_REASON_PROCESS_TERMINAL
                                      : terminal_reason);
        }
    }
    WlncEmitEvent(WLNC_EVENT_PROCESS_ARMED, WLNC_REASON_NONE);
    atomic_store_explicit(&g_wlnc_owner.init_gate, UINT32_C(0),
                          memory_order_release);

    if (WlncLoadProcessState(memory_order_acquire) != WLNC_PROCESS_ARMED) {
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                              WLNC_REASON_PROCESS_TERMINAL);
    }
    return WlncMakeResult(WLNC_STATUS_OK, WLNC_REASON_NONE);
}

WlncResult WLNC_PrepareCurrentThread(WlncThreadRole role)
{
    WlncProcessState process_state = WlncLoadProcessState(memory_order_acquire);
    WlncGetThreadId get_thread_id;
    void *context;
    uint64_t current_thread_id;
    uint32_t expected_thread_state;
    uint64_t generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;

    if (process_state != WLNC_PROCESS_ARMED) {
        if (WlncProcessStateIsTerminal(process_state)) {
            return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                                  WLNC_REASON_PROCESS_TERMINAL);
        }
        return WlncMakeResult(WLNC_STATUS_DENIED_TRANSIENT,
                              WLNC_REASON_PROCESS_TERMINAL);
    }
    if (role != WLNC_THREAD_ROLE_MAIN) {
        return WlncTerminalReject(WLNC_REASON_INVALID_THREAD_ROLE);
    }

    get_thread_id = atomic_load_explicit(&g_wlnc_owner.get_thread_id,
                                         memory_order_acquire);
    context = atomic_load_explicit(&g_wlnc_owner.platform_context,
                                   memory_order_acquire);
    if (get_thread_id == (WlncGetThreadId)0) {
        return WlncTerminalReject(WLNC_REASON_INTERNAL_STATE);
    }
    current_thread_id = get_thread_id(context);
    if (current_thread_id == 0) {
        return WlncTerminalReject(WLNC_REASON_THREAD_OWNER_MISMATCH);
    }

    if (WlncLoadThreadState(memory_order_acquire) == WLNC_THREAD_READY) {
        if (atomic_load_explicit(&g_wlnc_owner.thread_id,
                                 memory_order_relaxed) == current_thread_id &&
            atomic_load_explicit(&g_wlnc_owner.thread_role,
                                 memory_order_relaxed) == (uint32_t)role) {
            return WlncMakeResult(WLNC_STATUS_OK_IDEMPOTENT,
                                  WLNC_REASON_ALREADY_INITIALIZED);
        }
        return WlncTerminalReject(WLNC_REASON_THREAD_OWNER_MISMATCH);
    }

    expected_thread_state = (uint32_t)WLNC_THREAD_UNSEEN;
    if (!atomic_compare_exchange_strong_explicit(
            &g_wlnc_owner.thread_state, &expected_thread_state,
            (uint32_t)WLNC_THREAD_PREPARING, memory_order_acq_rel,
            memory_order_acquire)) {
        if (expected_thread_state == (uint32_t)WLNC_THREAD_INVALID) {
            return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                                  WLNC_REASON_PROCESS_TERMINAL);
        }
        return WlncMakeResult(WLNC_STATUS_DENIED_TRANSIENT,
                              WLNC_REASON_THREAD_NOT_READY);
    }
    WlncEmitEvent(WLNC_EVENT_THREAD_PREPARING, WLNC_REASON_NONE);

    if (WlncLoadProcessState(memory_order_acquire) != WLNC_PROCESS_ARMED) {
        expected_thread_state = (uint32_t)WLNC_THREAD_PREPARING;
        (void)atomic_compare_exchange_strong_explicit(
            &g_wlnc_owner.thread_state, &expected_thread_state,
            (uint32_t)WLNC_THREAD_INVALID, memory_order_release,
            memory_order_relaxed);
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                              WLNC_REASON_PROCESS_TERMINAL);
    }

    generation = atomic_load_explicit(&g_wlnc_owner.adapter_generation,
                                      memory_order_relaxed);
    process_epoch = atomic_load_explicit(&g_wlnc_owner.process_epoch,
                                         memory_order_relaxed);
    policy_epoch = atomic_load_explicit(&g_wlnc_owner.policy_epoch,
                                        memory_order_relaxed);

#if defined(WLNC_MUTANT_PUBLISH_READY_FIRST)
    atomic_store_explicit(&g_wlnc_owner.thread_state,
                          (uint32_t)WLNC_THREAD_READY,
                          memory_order_release);
    WlncEmitEvent(WLNC_EVENT_THREAD_METADATA_STAGED, WLNC_REASON_NONE);
#endif
    atomic_store_explicit(&g_wlnc_owner.thread_generation, generation,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_process_epoch, process_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_policy_epoch, policy_epoch,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_id, current_thread_id,
                          memory_order_relaxed);
    atomic_store_explicit(&g_wlnc_owner.thread_role, (uint32_t)role,
                          memory_order_relaxed);

#if !defined(WLNC_MUTANT_PUBLISH_READY_FIRST)
    WlncEmitEvent(WLNC_EVENT_THREAD_METADATA_STAGED, WLNC_REASON_NONE);
    expected_thread_state = (uint32_t)WLNC_THREAD_PREPARING;
    if (!atomic_compare_exchange_strong_explicit(
            &g_wlnc_owner.thread_state, &expected_thread_state,
            (uint32_t)WLNC_THREAD_READY, memory_order_release,
            memory_order_acquire)) {
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                              WLNC_REASON_PROCESS_TERMINAL);
    }
#endif
    WlncEmitEvent(WLNC_EVENT_THREAD_READY, WLNC_REASON_NONE);

    if (WlncLoadProcessState(memory_order_acquire) != WLNC_PROCESS_ARMED ||
        atomic_load_explicit(&g_wlnc_owner.adapter_generation,
                             memory_order_relaxed) != generation ||
        atomic_load_explicit(&g_wlnc_owner.process_epoch,
                             memory_order_relaxed) != process_epoch ||
        atomic_load_explicit(&g_wlnc_owner.policy_epoch,
                             memory_order_relaxed) != policy_epoch) {
        expected_thread_state = (uint32_t)WLNC_THREAD_READY;
        (void)atomic_compare_exchange_strong_explicit(
            &g_wlnc_owner.thread_state, &expected_thread_state,
            (uint32_t)WLNC_THREAD_INVALID, memory_order_release,
            memory_order_relaxed);
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                              WLNC_REASON_PROCESS_TERMINAL);
    }
    return WlncMakeResult(WLNC_STATUS_OK, WLNC_REASON_NONE);
}

WlncResult WLNC_AuthorizeLoad(const WlncLoadIdentity *load,
                              WlncLoadPermit *out_permit)
{
    WlncThreadState thread_state;
    WlncProcessState process_state;
    WlncGetThreadId get_thread_id;
    void *context;
    uint64_t current_thread_id;
    uint64_t generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;

    if (out_permit != (WlncLoadPermit *)0) {
        out_permit->abi_version = UINT32_C(0);
        out_permit->mechanism = WLNC_MECHANISM_INVALID;
        out_permit->adapter_generation = UINT64_C(0);
        out_permit->process_epoch = UINT64_C(0);
        out_permit->policy_epoch = UINT64_C(0);
        out_permit->thread_id = UINT64_C(0);
    }
    if (load == (const WlncLoadIdentity *)0 ||
        out_permit == (WlncLoadPermit *)0) {
        return WlncMakeResult(WLNC_STATUS_INVALID_ARGUMENT,
                              WLNC_REASON_INVALID_ARGUMENT);
    }
    if (load->abi_version != WLNC_ABI_VERSION || load->reserved_zero != 0) {
        return WlncMakeResult(WLNC_STATUS_INVALID_ARGUMENT,
                              WLNC_REASON_ABI_VERSION_MISMATCH);
    }

    process_state = WlncLoadProcessState(memory_order_acquire);
    if (process_state != WLNC_PROCESS_ARMED) {
        return WlncMakeResult(WlncProcessStateIsTerminal(process_state)
                                  ? WLNC_STATUS_DENIED_TERMINAL
                                  : WLNC_STATUS_DENIED_TRANSIENT,
                              WLNC_REASON_PROCESS_TERMINAL);
    }
    thread_state = WlncLoadThreadState(memory_order_acquire);
#if defined(WLNC_MUTANT_ALLOW_LOAD_BEFORE_READY)
    if (thread_state != WLNC_THREAD_READY) {
        out_permit->abi_version = WLNC_ABI_VERSION;
        out_permit->mechanism = WLNC_MECHANISM_AUDIT_ONLY;
        out_permit->adapter_generation = load->adapter_generation;
        out_permit->process_epoch = load->process_epoch;
        out_permit->policy_epoch = load->policy_epoch;
        out_permit->thread_id = UINT64_C(1);
        WlncEmitEvent(WLNC_EVENT_LOAD_GATE_DENIED, WLNC_REASON_NONE);
        return WlncMakeResult(WLNC_STATUS_OK, WLNC_REASON_NONE);
    }
#else
    if (thread_state != WLNC_THREAD_READY) {
        return WlncMakeResult(WLNC_STATUS_DENIED_TRANSIENT,
                              WLNC_REASON_THREAD_NOT_READY);
    }
#endif

    generation = atomic_load_explicit(&g_wlnc_owner.thread_generation,
                                      memory_order_relaxed);
    process_epoch = atomic_load_explicit(&g_wlnc_owner.thread_process_epoch,
                                         memory_order_relaxed);
    policy_epoch = atomic_load_explicit(&g_wlnc_owner.thread_policy_epoch,
                                        memory_order_relaxed);
    current_thread_id = atomic_load_explicit(&g_wlnc_owner.thread_id,
                                             memory_order_relaxed);
    if (WlncLoadThreadState(memory_order_acquire) != WLNC_THREAD_READY ||
        WlncLoadProcessState(memory_order_acquire) != WLNC_PROCESS_ARMED) {
        return WlncMakeResult(WLNC_STATUS_DENIED_TRANSIENT,
                              WLNC_REASON_THREAD_PUBLICATION_RACE);
    }
    get_thread_id = atomic_load_explicit(&g_wlnc_owner.get_thread_id,
                                         memory_order_acquire);
    context = atomic_load_explicit(&g_wlnc_owner.platform_context,
                                   memory_order_acquire);
    if (get_thread_id == (WlncGetThreadId)0 ||
        get_thread_id(context) != current_thread_id) {
        return WlncTerminalReject(WLNC_REASON_THREAD_OWNER_MISMATCH);
    }
    if (generation != atomic_load_explicit(&g_wlnc_owner.adapter_generation,
                                           memory_order_relaxed) ||
        process_epoch != atomic_load_explicit(&g_wlnc_owner.process_epoch,
                                              memory_order_relaxed) ||
        policy_epoch != atomic_load_explicit(&g_wlnc_owner.policy_epoch,
                                             memory_order_relaxed) ||
        load->adapter_generation != generation ||
        load->process_epoch != process_epoch ||
        load->policy_epoch != policy_epoch ||
        !WlncStoredDigestEquals(g_wlnc_owner.profile_digest,
                                load->profile_sha256)) {
        return WlncTerminalReject(WLNC_REASON_LOAD_IDENTITY_MISMATCH);
    }

    /*
     * This release intentionally contains no data-plane publisher.  Returning
     * a permit here would turn an audit receipt into a fake capability.  Keep
     * the full acquire/identity check above so the ordering contract is tested,
     * but fail closed until a separately reviewed mechanism owns the real slot.
     */
    WlncEmitEvent(WLNC_EVENT_LOAD_GATE_DENIED,
                  WLNC_REASON_AUDIT_ONLY_NO_LOAD_AUTHORITY);
    return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                          WLNC_REASON_AUDIT_ONLY_NO_LOAD_AUTHORITY);
}

WlncResult WLNC_Revoke(void)
{
    uint64_t observed = WlncLoadProcessStatus(memory_order_acquire);
    uint32_t expected_thread_state;
    WlncProcessState observed_state = WlncStatusProcessState(observed);

    if (observed_state == WLNC_PROCESS_REJECTED) {
        return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                              WlncStatusReason(observed));
    }
    if (observed_state == WLNC_PROCESS_REVOKED) {
        return WlncMakeResult(WLNC_STATUS_OK_IDEMPOTENT,
                              WLNC_REASON_PROFILE_REVOKED);
    }

    expected_thread_state = atomic_load_explicit(&g_wlnc_owner.thread_state,
                                                 memory_order_relaxed);
    while (expected_thread_state != (uint32_t)WLNC_THREAD_INVALID &&
           !atomic_compare_exchange_weak_explicit(
               &g_wlnc_owner.thread_state, &expected_thread_state,
               (uint32_t)WLNC_THREAD_INVALID, memory_order_release,
               memory_order_relaxed)) {
    }

    while (!atomic_compare_exchange_weak_explicit(
        &g_wlnc_owner.process_status, &observed,
        WlncPackProcessStatus(WLNC_PROCESS_REVOKED,
                              WLNC_REASON_PROFILE_REVOKED),
        memory_order_release,
        memory_order_acquire)) {
        observed_state = WlncStatusProcessState(observed);
        if (observed_state == WLNC_PROCESS_REJECTED) {
            return WlncMakeResult(WLNC_STATUS_DENIED_TERMINAL,
                                  WlncStatusReason(observed));
        }
        if (observed_state == WLNC_PROCESS_REVOKED) {
            return WlncMakeResult(WLNC_STATUS_OK_IDEMPOTENT,
                                  WLNC_REASON_PROFILE_REVOKED);
        }
    }
    WlncEmitEvent(WLNC_EVENT_PROCESS_REVOKED,
                  WLNC_REASON_PROFILE_REVOKED);
    return WlncMakeResult(WLNC_STATUS_OK, WLNC_REASON_PROFILE_REVOKED);
}

WlncResult WLNC_GetAuditSnapshot(WlncAuditSnapshot *out_snapshot)
{
    uint32_t attempt;
    uint64_t process_before;
    uint64_t process_after;
    WlncThreadState thread_before;
    WlncThreadState thread_after;

    if (out_snapshot == (WlncAuditSnapshot *)0) {
        return WlncMakeResult(WLNC_STATUS_INVALID_ARGUMENT,
                              WLNC_REASON_INVALID_ARGUMENT);
    }

    for (attempt = 0; attempt < UINT32_C(4); ++attempt) {
        process_before = WlncLoadProcessStatus(memory_order_acquire);
        thread_before = WlncLoadThreadState(memory_order_acquire);
        out_snapshot->abi_version = WLNC_ABI_VERSION;
        out_snapshot->fork_seeded = atomic_load_explicit(
            &g_wlnc_owner.fork_seeded, memory_order_acquire);
        out_snapshot->process_state = WlncStatusProcessState(process_before);
        out_snapshot->thread_state = thread_before;
        out_snapshot->last_reason = WlncStatusReason(process_before);
        out_snapshot->mechanism = (WlncMechanism)atomic_load_explicit(
            &g_wlnc_owner.mechanism, memory_order_relaxed);
        out_snapshot->thread_role = (WlncThreadRole)atomic_load_explicit(
            &g_wlnc_owner.thread_role, memory_order_relaxed);
        out_snapshot->adapter_generation = atomic_load_explicit(
            &g_wlnc_owner.adapter_generation, memory_order_relaxed);
        out_snapshot->process_epoch = atomic_load_explicit(
            &g_wlnc_owner.process_epoch, memory_order_relaxed);
        out_snapshot->policy_epoch = atomic_load_explicit(
            &g_wlnc_owner.policy_epoch, memory_order_relaxed);
        out_snapshot->thread_id = atomic_load_explicit(
            &g_wlnc_owner.thread_id, memory_order_relaxed);
        out_snapshot->audit_event_count = atomic_load_explicit(
            &g_wlnc_owner.audit_sequence, memory_order_relaxed);
        out_snapshot->audit_drop_count = atomic_load_explicit(
            &g_wlnc_owner.audit_drop_count, memory_order_relaxed);
        WlncLoadDigest(g_wlnc_owner.profile_digest,
                       out_snapshot->profile_sha256);
        thread_after = WlncLoadThreadState(memory_order_acquire);
        process_after = WlncLoadProcessStatus(memory_order_acquire);
        if (process_before == process_after && thread_before == thread_after) {
            return WlncMakeResult(WLNC_STATUS_OK, WLNC_REASON_NONE);
        }
    }
    return WlncMakeResult(WLNC_STATUS_DENIED_TRANSIENT,
                          WLNC_REASON_THREAD_PUBLICATION_RACE);
}

#if defined(WLNC_TESTING)
void WLNC_TestSetInheritedInitGate(uint32_t value)
{
    atomic_store_explicit(&g_wlnc_owner.init_gate, value,
                          memory_order_relaxed);
}

uint32_t WLNC_TestGetInitGate(void)
{
    return atomic_load_explicit(&g_wlnc_owner.init_gate,
                                memory_order_relaxed);
}
#endif
