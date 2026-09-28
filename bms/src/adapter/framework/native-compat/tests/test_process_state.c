#include "native_compat_internal.h"

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>

#define ARRAY_SIZE(array) (sizeof(array) / sizeof((array)[0]))

typedef struct TestFixture {
    _Atomic uint64_t thread_id;
    _Atomic int guard_entered;
    _Atomic int guard_release;
    _Atomic uint32_t event_count;
    _Atomic uint32_t publication_violation;
    int block_guard;
    int guard_return;
    uint64_t guard_value;
    uint64_t guard_epoch;
    WlncGuardSourceQuality guard_quality;
    uint32_t guard_reserved;
    int accept_audit;
    int revoke_in_guard;
    WlncAuditEvent events[64];
} TestFixture;

typedef struct TestInputs {
    WlncForkSeed seed;
    WlncTargetIdentity target;
    WlncPreverifiedCapabilityV1 capability;
    WlncPlatformOps ops;
    WlncLoadIdentity load;
} TestInputs;

typedef struct InitCall {
    const WlncPreverifiedCapabilityV1 *capability;
    const WlncTargetIdentity *target;
    const WlncPlatformOps *ops;
    WlncResult result;
} InitCall;

typedef struct TerminalRaceCall {
    _Atomic int *start;
    TestInputs *inputs;
    WlncResult result;
    int revoke;
} TerminalRaceCall;

static int g_failures;

#define CHECK(expression)                                                     \
    do {                                                                      \
        if (!(expression)) {                                                  \
            (void)fprintf(stderr, "%s:%d: CHECK failed: %s\n", __func__,     \
                          __LINE__, #expression);                             \
            return 0;                                                         \
        }                                                                     \
    } while (0)

static void FillBytes(uint8_t *bytes, uint32_t size, uint8_t seed)
{
    uint32_t i;
    for (i = 0; i < size; ++i) {
        bytes[i] = (uint8_t)(seed + (uint8_t)(i * UINT32_C(13)));
    }
}

static void InitFixture(TestFixture *fixture, uint64_t process_epoch)
{
    (void)memset(fixture, 0, sizeof(*fixture));
    atomic_init(&fixture->thread_id, UINT64_C(0xabc001));
    atomic_init(&fixture->guard_entered, 0);
    atomic_init(&fixture->guard_release, 1);
    atomic_init(&fixture->event_count, UINT32_C(0));
    atomic_init(&fixture->publication_violation, UINT32_C(0));
    fixture->guard_return = 1;
    fixture->guard_value = UINT64_C(0x9e3779b97f4a7c15);
    fixture->guard_epoch = process_epoch;
    fixture->guard_quality = WLNC_GUARD_SOURCE_QUALITY_TEST_DETERMINISTIC;
    fixture->accept_audit = 1;
}

static int GetGuardSource(void *context, uint64_t required_process_epoch,
                          WlncGuardSourceSample *out_sample)
{
    TestFixture *fixture = (TestFixture *)context;
    (void)required_process_epoch;
    if (fixture->block_guard != 0) {
        atomic_store_explicit(&fixture->guard_entered, 1,
                              memory_order_release);
        while (atomic_load_explicit(&fixture->guard_release,
                                    memory_order_acquire) == 0) {
            (void)sched_yield();
        }
    }
    if (fixture->guard_return != 1) {
        return fixture->guard_return;
    }
    if (fixture->revoke_in_guard != 0) {
        (void)WLNC_Revoke();
    }
    out_sample->value = fixture->guard_value;
    out_sample->source_epoch = fixture->guard_epoch;
    out_sample->quality = fixture->guard_quality;
    out_sample->reserved_zero = fixture->guard_reserved;
    return 1;
}

static uint64_t GetThreadId(void *context)
{
    TestFixture *fixture = (TestFixture *)context;
    return atomic_load_explicit(&fixture->thread_id, memory_order_relaxed);
}

static int EmitAuditEvent(void *context, const WlncAuditEvent *event)
{
    TestFixture *fixture = (TestFixture *)context;
    uint32_t index = atomic_fetch_add_explicit(
        &fixture->event_count, UINT32_C(1), memory_order_relaxed);
    if (index < (uint32_t)ARRAY_SIZE(fixture->events)) {
        fixture->events[index] = *event;
    }
    if (event->type == WLNC_EVENT_THREAD_METADATA_STAGED &&
        (event->thread_state != WLNC_THREAD_PREPARING ||
         event->thread_role != WLNC_THREAD_ROLE_MAIN ||
         event->thread_id == 0)) {
        atomic_store_explicit(&fixture->publication_violation, UINT32_C(1),
                              memory_order_relaxed);
    }
    return fixture->accept_audit;
}

static void InitInputs(TestInputs *inputs, TestFixture *fixture,
                       uint64_t generation, uint64_t process_epoch,
                       uint64_t policy_epoch)
{
    (void)memset(inputs, 0, sizeof(*inputs));
    inputs->seed.abi_version = WLNC_ABI_VERSION;
    inputs->seed.adapter_generation = generation;
    inputs->seed.process_epoch = process_epoch;
    inputs->seed.policy_epoch = policy_epoch;

    inputs->target.abi_version = WLNC_ABI_VERSION;
    inputs->target.build_id_size = UINT32_C(20);
    inputs->target.adapter_generation = generation;
    FillBytes(inputs->target.target_sha256, WLNC_DIGEST_SIZE, UINT8_C(0x21));
    FillBytes(inputs->target.build_id, inputs->target.build_id_size,
              UINT8_C(0x42));

    inputs->capability.abi_version = WLNC_ABI_VERSION;
    inputs->capability.origin = WLNC_CAPABILITY_ORIGIN_UPSTREAM_PREVERIFIED;
    inputs->capability.marker = WLNC_PREVERIFIED_CAPABILITY_MARKER;
    inputs->capability.mechanism = WLNC_MECHANISM_AUDIT_ONLY;
    inputs->capability.guest_scan_complete = 1;
    inputs->capability.initial_closure_complete = 1;
    inputs->capability.prepare_order_proven = 1;
    inputs->capability.loader_provenance_complete = 1;
    inputs->capability.generation_manifest_complete = 1;
    inputs->capability.process_epoch = process_epoch;
    inputs->capability.policy_epoch = policy_epoch;
    FillBytes(inputs->capability.profile_sha256, WLNC_DIGEST_SIZE,
              UINT8_C(0x63));
    inputs->capability.target = inputs->target;

    inputs->ops.abi_version = WLNC_ABI_VERSION;
    inputs->ops.context = fixture;
    inputs->ops.get_guard_source = GetGuardSource;
    inputs->ops.get_thread_id = GetThreadId;
    inputs->ops.emit_audit_event = EmitAuditEvent;

    inputs->load.abi_version = WLNC_ABI_VERSION;
    inputs->load.adapter_generation = generation;
    inputs->load.process_epoch = process_epoch;
    inputs->load.policy_epoch = policy_epoch;
    (void)memcpy(inputs->load.profile_sha256,
                 inputs->capability.profile_sha256, WLNC_DIGEST_SIZE);
}

static int PermitIsZero(const WlncLoadPermit *permit)
{
    return permit->abi_version == 0 &&
           permit->mechanism == WLNC_MECHANISM_INVALID &&
           permit->adapter_generation == 0 && permit->process_epoch == 0 &&
           permit->policy_epoch == 0 && permit->thread_id == 0;
}

static int DigestIsZero(const uint8_t digest[WLNC_DIGEST_SIZE])
{
    uint32_t i;
    uint8_t value = 0;
    for (i = 0; i < WLNC_DIGEST_SIZE; ++i) {
        value |= digest[i];
    }
    return value == 0;
}

static int ResetOwner(TestInputs *inputs)
{
    WlncResult result = WLNC_AfterForkChildReset(&inputs->seed);
    CHECK(result.status == WLNC_STATUS_OK);
    CHECK(result.reason == WLNC_REASON_NONE);
    CHECK(result.process_state == WLNC_PROCESS_UNINITIALIZED);
    CHECK(result.thread_state == WLNC_THREAD_UNSEEN);
    return 1;
}

static int ArmOwner(TestInputs *inputs)
{
    WlncResult result = WLNC_ProcessInitPreverified(
        &inputs->capability, &inputs->target, &inputs->ops);
    CHECK(result.status == WLNC_STATUS_OK);
    CHECK(result.reason == WLNC_REASON_NONE);
    CHECK(result.process_state == WLNC_PROCESS_ARMED);
    CHECK(result.thread_state == WLNC_THREAD_UNSEEN);
    return 1;
}

static int TestResetRequired(void)
{
    TestFixture fixture;
    TestInputs inputs;
    WlncResult result;
    InitFixture(&fixture, UINT64_C(1001));
    InitInputs(&inputs, &fixture, UINT64_C(701), UINT64_C(1001),
               UINT64_C(2001));
    result = WLNC_ProcessInitPreverified(&inputs.capability, &inputs.target,
                                        &inputs.ops);
    CHECK(result.status == WLNC_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLNC_REASON_FORK_RESET_REQUIRED);
    CHECK(ResetOwner(&inputs));
    return 1;
}

static int TestHappyAuditOnly(void)
{
    TestFixture fixture;
    TestInputs inputs;
    WlncResult result;
    WlncAuditSnapshot snapshot;
    WlncLoadPermit permit;
    InitFixture(&fixture, UINT64_C(1002));
    InitInputs(&inputs, &fixture, UINT64_C(702), UINT64_C(1002),
               UINT64_C(2002));
    CHECK(ResetOwner(&inputs));
    CHECK(ArmOwner(&inputs));

    (void)memset(&permit, 0xa5, sizeof(permit));
    result = WLNC_AuthorizeLoad(&inputs.load, &permit);
    CHECK(result.status == WLNC_STATUS_DENIED_TRANSIENT);
    CHECK(result.reason == WLNC_REASON_THREAD_NOT_READY);
    CHECK(PermitIsZero(&permit));

    result = WLNC_PrepareCurrentThread(WLNC_THREAD_ROLE_MAIN);
    CHECK(result.status == WLNC_STATUS_OK);
    CHECK(result.thread_state == WLNC_THREAD_READY);
    CHECK(atomic_load_explicit(&fixture.publication_violation,
                               memory_order_relaxed) == 0);

    result = WLNC_GetAuditSnapshot(&snapshot);
    CHECK(result.status == WLNC_STATUS_OK);
    CHECK(snapshot.abi_version == WLNC_ABI_VERSION);
    CHECK(snapshot.fork_seeded == 1);
    CHECK(snapshot.process_state == WLNC_PROCESS_ARMED);
    CHECK(snapshot.thread_state == WLNC_THREAD_READY);
    CHECK(snapshot.mechanism == WLNC_MECHANISM_AUDIT_ONLY);
    CHECK(snapshot.thread_role == WLNC_THREAD_ROLE_MAIN);
    CHECK(snapshot.thread_id == UINT64_C(0xabc001));
    CHECK(snapshot.adapter_generation == inputs.seed.adapter_generation);
    CHECK(snapshot.process_epoch == inputs.seed.process_epoch);
    CHECK(snapshot.policy_epoch == inputs.seed.policy_epoch);
    CHECK(memcmp(snapshot.profile_sha256,
                 inputs.capability.profile_sha256, WLNC_DIGEST_SIZE) == 0);

    (void)memset(&permit, 0xa5, sizeof(permit));
    result = WLNC_AuthorizeLoad(&inputs.load, &permit);
    CHECK(result.status == WLNC_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLNC_REASON_AUDIT_ONLY_NO_LOAD_AUTHORITY);
    CHECK(result.process_state == WLNC_PROCESS_ARMED);
    CHECK(result.thread_state == WLNC_THREAD_READY);
    CHECK(PermitIsZero(&permit));

    result = WLNC_PrepareCurrentThread(WLNC_THREAD_ROLE_MAIN);
    CHECK(result.status == WLNC_STATUS_OK_IDEMPOTENT);
    CHECK(result.reason == WLNC_REASON_ALREADY_INITIALIZED);
    result = WLNC_ProcessInitPreverified(&inputs.capability, &inputs.target,
                                        &inputs.ops);
    CHECK(result.status == WLNC_STATUS_OK_IDEMPOTENT);
    CHECK(result.reason == WLNC_REASON_ALREADY_INITIALIZED);
    return 1;
}

static int ExpectInitReject(TestInputs *inputs, WlncReason reason)
{
    WlncResult result;
    CHECK(ResetOwner(inputs));
    result = WLNC_ProcessInitPreverified(&inputs->capability, &inputs->target,
                                        &inputs->ops);
    CHECK(result.status == WLNC_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == reason);
    CHECK(result.process_state == WLNC_PROCESS_REJECTED);
    CHECK(result.thread_state == WLNC_THREAD_INVALID);
    return 1;
}

static int TestStaticAndEpochRejections(void)
{
    TestFixture fixture;
    TestInputs inputs;
    InitFixture(&fixture, UINT64_C(1003));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));

    inputs.capability.marker = 0;
    CHECK(ExpectInitReject(&inputs,
                           WLNC_REASON_CAPABILITY_NOT_PREVERIFIED));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.target.abi_version = WLNC_ABI_VERSION + 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_ABI_VERSION_MISMATCH));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.ops.reserved_zero = 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_INVALID_ARGUMENT));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.inline_unknown_count = 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_HARD_COUNT_NONZERO));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.cfg_unknown_count = 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_HARD_COUNT_NONZERO));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.pre_prepare_slot5_access_count = 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_HARD_COUNT_NONZERO));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.initial_closure_complete = 0;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_REQUIRED_PROOF_MISSING));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.loader_provenance_complete = 0;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_REQUIRED_PROOF_MISSING));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.target.target_sha256[0] ^= UINT8_C(1);
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_TARGET_SHA_MISMATCH));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.target.build_id[0] ^= UINT8_C(1);
    CHECK(ExpectInitReject(&inputs,
                           WLNC_REASON_TARGET_BUILD_ID_MISMATCH));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.capability.target.adapter_generation += 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_GENERATION_MISMATCH));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.seed.adapter_generation += 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_GENERATION_MISMATCH));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.seed.process_epoch += 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_PROCESS_EPOCH_MISMATCH));
    InitInputs(&inputs, &fixture, UINT64_C(703), UINT64_C(1003),
               UINT64_C(2003));
    inputs.seed.policy_epoch += 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_POLICY_EPOCH_MISMATCH));
    return 1;
}

static int TestGuardSourceRejections(void)
{
    TestFixture fixture;
    TestInputs inputs;
    InitFixture(&fixture, UINT64_C(1004));
    InitInputs(&inputs, &fixture, UINT64_C(704), UINT64_C(1004),
               UINT64_C(2004));
    fixture.guard_return = 0;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_GUARD_SOURCE_FAILED));
    InitFixture(&fixture, UINT64_C(1004));
    InitInputs(&inputs, &fixture, UINT64_C(704), UINT64_C(1004),
               UINT64_C(2004));
    fixture.guard_value = 0;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_GUARD_VALUE_INVALID));
    InitFixture(&fixture, UINT64_C(1004));
    InitInputs(&inputs, &fixture, UINT64_C(704), UINT64_C(1004),
               UINT64_C(2004));
    fixture.guard_reserved = 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_GUARD_VALUE_INVALID));
    InitFixture(&fixture, UINT64_C(1004));
    InitInputs(&inputs, &fixture, UINT64_C(704), UINT64_C(1004),
               UINT64_C(2004));
    fixture.guard_epoch += 1;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_GUARD_EPOCH_MISMATCH));
    InitFixture(&fixture, UINT64_C(1004));
    InitInputs(&inputs, &fixture, UINT64_C(704), UINT64_C(1004),
               UINT64_C(2004));
    fixture.guard_quality = WLNC_GUARD_SOURCE_QUALITY_INVALID;
    CHECK(ExpectInitReject(&inputs, WLNC_REASON_GUARD_SOURCE_FAILED));

    InitFixture(&fixture, UINT64_C(1004));
    InitInputs(&inputs, &fixture, UINT64_C(704), UINT64_C(1004),
               UINT64_C(2004));
    fixture.revoke_in_guard = 1;
    CHECK(ResetOwner(&inputs));
    {
        WlncResult result = WLNC_ProcessInitPreverified(
            &inputs.capability, &inputs.target, &inputs.ops);
        WlncAuditSnapshot snapshot;
        CHECK(result.status == WLNC_STATUS_DENIED_TERMINAL);
        CHECK(result.reason == WLNC_REASON_PROFILE_REVOKED);
        CHECK(WLNC_GetAuditSnapshot(&snapshot).status == WLNC_STATUS_OK);
        CHECK(snapshot.process_state == WLNC_PROCESS_REVOKED);
        CHECK(snapshot.last_reason == WLNC_REASON_PROFILE_REVOKED);
    }
    return 1;
}

static int TestReplayAndOwnerRejections(void)
{
    TestFixture fixture;
    TestFixture second_fixture;
    TestInputs inputs;
    WlncPlatformOps second_ops;
    WlncResult result;
    InitFixture(&fixture, UINT64_C(1005));
    InitInputs(&inputs, &fixture, UINT64_C(705), UINT64_C(1005),
               UINT64_C(2005));
    CHECK(ResetOwner(&inputs));
    CHECK(ArmOwner(&inputs));
    inputs.capability.profile_sha256[0] ^= UINT8_C(1);
    result = WLNC_ProcessInitPreverified(&inputs.capability, &inputs.target,
                                        &inputs.ops);
    CHECK(result.status == WLNC_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLNC_REASON_PROFILE_REPLAY);

    InitFixture(&fixture, UINT64_C(1005));
    InitFixture(&second_fixture, UINT64_C(1005));
    InitInputs(&inputs, &fixture, UINT64_C(705), UINT64_C(1005),
               UINT64_C(2005));
    CHECK(ResetOwner(&inputs));
    CHECK(ArmOwner(&inputs));
    second_ops = inputs.ops;
    second_ops.context = &second_fixture;
    result = WLNC_ProcessInitPreverified(&inputs.capability, &inputs.target,
                                        &second_ops);
    CHECK(result.status == WLNC_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLNC_REASON_PLATFORM_OWNER_MISMATCH);
    return 1;
}

static int TestForkResetClearsInheritedState(void)
{
    TestFixture fixture;
    TestInputs inputs;
    WlncAuditSnapshot snapshot;
    WlncResult result;
    InitFixture(&fixture, UINT64_C(1006));
    InitInputs(&inputs, &fixture, UINT64_C(706), UINT64_C(1006),
               UINT64_C(2006));
    CHECK(ResetOwner(&inputs));
    CHECK(ArmOwner(&inputs));
    result = WLNC_PrepareCurrentThread(WLNC_THREAD_ROLE_MAIN);
    CHECK(result.status == WLNC_STATUS_OK);
    WLNC_TestSetInheritedInitGate(UINT32_C(1));

    inputs.seed.adapter_generation = UINT64_C(1706);
    inputs.seed.process_epoch = UINT64_C(11006);
    inputs.seed.policy_epoch = UINT64_C(12006);
    result = WLNC_AfterForkChildReset(&inputs.seed);
    CHECK(result.status == WLNC_STATUS_OK);
    CHECK(WLNC_TestGetInitGate() == 0);
    CHECK(result.process_state == WLNC_PROCESS_UNINITIALIZED);
    CHECK(result.thread_state == WLNC_THREAD_UNSEEN);
    result = WLNC_GetAuditSnapshot(&snapshot);
    CHECK(result.status == WLNC_STATUS_OK);
    CHECK(snapshot.fork_seeded == 1);
    CHECK(snapshot.adapter_generation == UINT64_C(1706));
    CHECK(snapshot.process_epoch == UINT64_C(11006));
    CHECK(snapshot.policy_epoch == UINT64_C(12006));
    CHECK(snapshot.thread_id == 0);
    CHECK(snapshot.thread_role == WLNC_THREAD_ROLE_INVALID);
    CHECK(snapshot.audit_event_count == 0);
    CHECK(DigestIsZero(snapshot.profile_sha256));
    return 1;
}

static int TestRevocationAndThreadOwner(void)
{
    TestFixture fixture;
    TestInputs inputs;
    WlncAuditSnapshot snapshot;
    WlncLoadPermit permit;
    WlncResult result;
    InitFixture(&fixture, UINT64_C(1007));
    InitInputs(&inputs, &fixture, UINT64_C(707), UINT64_C(1007),
               UINT64_C(2007));
    CHECK(ResetOwner(&inputs));
    CHECK(ArmOwner(&inputs));
    CHECK(WLNC_PrepareCurrentThread(WLNC_THREAD_ROLE_MAIN).status ==
          WLNC_STATUS_OK);
    atomic_store_explicit(&fixture.thread_id, UINT64_C(0xabc002),
                          memory_order_relaxed);
    result = WLNC_AuthorizeLoad(&inputs.load, &permit);
    CHECK(result.status == WLNC_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLNC_REASON_THREAD_OWNER_MISMATCH);
    CHECK(result.process_state == WLNC_PROCESS_REJECTED);
    CHECK(result.thread_state == WLNC_THREAD_INVALID);

    InitFixture(&fixture, UINT64_C(1007));
    InitInputs(&inputs, &fixture, UINT64_C(707), UINT64_C(1007),
               UINT64_C(2007));
    CHECK(ResetOwner(&inputs));
    CHECK(ArmOwner(&inputs));
    CHECK(WLNC_PrepareCurrentThread(WLNC_THREAD_ROLE_MAIN).status ==
          WLNC_STATUS_OK);
    result = WLNC_Revoke();
    CHECK(result.status == WLNC_STATUS_OK);
    CHECK(result.reason == WLNC_REASON_PROFILE_REVOKED);
    CHECK(WLNC_GetAuditSnapshot(&snapshot).status == WLNC_STATUS_OK);
    CHECK(snapshot.process_state == WLNC_PROCESS_REVOKED);
    CHECK(snapshot.thread_state == WLNC_THREAD_INVALID);
    result = WLNC_Revoke();
    CHECK(result.status == WLNC_STATUS_OK_IDEMPOTENT);
    return 1;
}

static void *RunInit(void *opaque)
{
    InitCall *call = (InitCall *)opaque;
    call->result = WLNC_ProcessInitPreverified(call->capability, call->target,
                                               call->ops);
    return (void *)0;
}

static int TestConcurrentInitGate(void)
{
    TestFixture fixture;
    TestInputs inputs;
    InitCall call;
    pthread_t thread;
    WlncResult second;
    InitFixture(&fixture, UINT64_C(1008));
    InitInputs(&inputs, &fixture, UINT64_C(708), UINT64_C(1008),
               UINT64_C(2008));
    CHECK(ResetOwner(&inputs));
    fixture.block_guard = 1;
    atomic_store_explicit(&fixture.guard_release, 0, memory_order_relaxed);
    call.capability = &inputs.capability;
    call.target = &inputs.target;
    call.ops = &inputs.ops;
    CHECK(pthread_create(&thread, (const pthread_attr_t *)0, RunInit,
                         &call) == 0);
    while (atomic_load_explicit(&fixture.guard_entered,
                                memory_order_acquire) == 0) {
        (void)sched_yield();
    }
    second = WLNC_ProcessInitPreverified(&inputs.capability, &inputs.target,
                                        &inputs.ops);
    CHECK(second.status == WLNC_STATUS_DENIED_TRANSIENT);
    CHECK(second.reason == WLNC_REASON_CONCURRENT_INIT);
    atomic_store_explicit(&fixture.guard_release, 1, memory_order_release);
    CHECK(pthread_join(thread, (void **)0) == 0);
    CHECK(call.result.status == WLNC_STATUS_OK);
    CHECK(call.result.process_state == WLNC_PROCESS_ARMED);
    return 1;
}

static void *RunTerminalRace(void *opaque)
{
    TerminalRaceCall *call = (TerminalRaceCall *)opaque;
    while (atomic_load_explicit(call->start, memory_order_acquire) == 0) {
        (void)sched_yield();
    }
    if (call->revoke != 0) {
        call->result = WLNC_Revoke();
    } else {
        WlncLoadPermit permit;
        call->result = WLNC_AuthorizeLoad(&call->inputs->load, &permit);
    }
    return (void *)0;
}

static int TestTerminalReasonAtomicity(void)
{
    uint32_t iteration;
    for (iteration = 0; iteration < UINT32_C(200); ++iteration) {
        TestFixture fixture;
        TestInputs inputs;
        WlncAuditSnapshot snapshot;
        TerminalRaceCall reject_call;
        TerminalRaceCall revoke_call;
        _Atomic int start;
        pthread_t reject_thread;
        pthread_t revoke_thread;
        uint64_t epoch = UINT64_C(20000) + iteration;
        InitFixture(&fixture, epoch);
        InitInputs(&inputs, &fixture, UINT64_C(900), epoch,
                   UINT64_C(30000) + iteration);
        CHECK(ResetOwner(&inputs));
        CHECK(ArmOwner(&inputs));
        CHECK(WLNC_PrepareCurrentThread(WLNC_THREAD_ROLE_MAIN).status ==
              WLNC_STATUS_OK);
        atomic_store_explicit(&fixture.thread_id, UINT64_C(0xabc099),
                              memory_order_relaxed);
        atomic_init(&start, 0);
        (void)memset(&reject_call, 0, sizeof(reject_call));
        (void)memset(&revoke_call, 0, sizeof(revoke_call));
        reject_call.start = &start;
        reject_call.inputs = &inputs;
        revoke_call.start = &start;
        revoke_call.inputs = &inputs;
        revoke_call.revoke = 1;
        CHECK(pthread_create(&reject_thread, (const pthread_attr_t *)0,
                             RunTerminalRace, &reject_call) == 0);
        CHECK(pthread_create(&revoke_thread, (const pthread_attr_t *)0,
                             RunTerminalRace, &revoke_call) == 0);
        atomic_store_explicit(&start, 1, memory_order_release);
        CHECK(pthread_join(reject_thread, (void **)0) == 0);
        CHECK(pthread_join(revoke_thread, (void **)0) == 0);
        CHECK(WLNC_GetAuditSnapshot(&snapshot).status == WLNC_STATUS_OK);
        CHECK((snapshot.process_state == WLNC_PROCESS_REJECTED &&
               snapshot.last_reason == WLNC_REASON_THREAD_OWNER_MISMATCH) ||
              (snapshot.process_state == WLNC_PROCESS_REVOKED &&
               snapshot.last_reason == WLNC_REASON_PROFILE_REVOKED));
    }
    return 1;
}

static int TestStableReasonNames(void)
{
    static const char *const expected[] = {
        "none",
        "already_initialized",
        "invalid_argument",
        "abi_version_mismatch",
        "capability_not_preverified",
        "target_sha_mismatch",
        "target_build_id_mismatch",
        "generation_mismatch",
        "process_epoch_mismatch",
        "policy_epoch_mismatch",
        "mechanism_unsupported",
        "hard_count_nonzero",
        "guard_source_failed",
        "guard_value_invalid",
        "guard_epoch_mismatch",
        "process_terminal",
        "concurrent_init",
        "profile_replay",
        "profile_revoked",
        "thread_not_ready",
        "thread_owner_mismatch",
        "thread_publication_race",
        "invalid_thread_role",
        "load_identity_mismatch",
        "internal_state",
        "fork_reset_required",
        "platform_owner_mismatch",
        "audit_only_no_load_authority",
        "required_proof_missing",
    };
    uint32_t reason;
    CHECK(WLNC_GetAbiVersion() == WLNC_ABI_VERSION);
    for (reason = 0; reason < (uint32_t)ARRAY_SIZE(expected); ++reason) {
        CHECK(strcmp(WLNC_ReasonString((WlncReason)reason),
                     expected[reason]) == 0);
    }
    CHECK(strcmp(WLNC_ReasonString((WlncReason)UINT32_C(0xffffffff)),
                 "unknown") == 0);
    return 1;
}

static void RunTest(const char *name, int (*test)(void))
{
    if (test() == 0) {
        ++g_failures;
        (void)fprintf(stderr, "FAIL %s\n", name);
    } else {
        (void)fprintf(stdout, "PASS %s\n", name);
    }
}

int main(void)
{
    RunTest("reset_required", TestResetRequired);
    RunTest("happy_audit_only", TestHappyAuditOnly);
    RunTest("static_and_epoch_rejections", TestStaticAndEpochRejections);
    RunTest("guard_source_rejections", TestGuardSourceRejections);
    RunTest("replay_and_owner_rejections", TestReplayAndOwnerRejections);
    RunTest("fork_reset_clears_inherited_state",
            TestForkResetClearsInheritedState);
    RunTest("revocation_and_thread_owner", TestRevocationAndThreadOwner);
    RunTest("concurrent_init_gate", TestConcurrentInitGate);
    RunTest("terminal_reason_atomicity", TestTerminalReasonAtomicity);
    RunTest("stable_reason_names", TestStableReasonNames);
    if (g_failures != 0) {
        (void)fprintf(stderr, "FAIL total=%d\n", g_failures);
        return 1;
    }
    (void)fprintf(stdout, "PASS total=10 audit_only_no_load_permit=proven\n");
    return 0;
}
