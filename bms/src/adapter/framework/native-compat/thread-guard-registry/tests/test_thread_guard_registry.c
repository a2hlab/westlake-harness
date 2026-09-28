#include "westlake_thread_guard_registry.h"

#include <fcntl.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define FIXTURE_REGION_COUNT 64
#define CONCURRENT_THREAD_COUNT 24

#define CHECK(expression)                                                        \
    do {                                                                         \
        if (!(expression)) {                                                     \
            (void)fprintf(stderr, "CHECK failed %s:%d: %s\n", __FILE__,      \
                          __LINE__, #expression);                                \
            return 0;                                                            \
        }                                                                        \
    } while (0)

typedef enum RandomMode {
    RANDOM_REAL = 0,
    RANDOM_FAIL = 1,
    RANDOM_ZERO = 2,
    RANDOM_WRONG_EPOCH = 3,
    RANDOM_WRONG_QUALITY = 4,
    RANDOM_FIXED = 5
} RandomMode;

typedef struct FixtureRegion {
    _Alignas(16) uint8_t aperture[64];
    _Atomic uint64_t thread_id;
} FixtureRegion;

typedef struct FixtureContext {
    FixtureRegion regions[FIXTURE_REGION_COUNT];
    _Atomic int verify_binding_accept;
    _Atomic int audit_accept;
    _Atomic int random_mode;
    _Atomic uint32_t owner_start;
    _Atomic uint32_t owner_size;
    _Atomic uint64_t event_count;
    _Atomic uint64_t ready_event_count;
    _Atomic uint64_t ready_without_receipt;
    _Atomic uint64_t random_call_count;
} FixtureContext;

typedef struct Worker {
    FixtureContext *context;
    uint32_t region_index;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    WltgResult prepare_result;
    WltgResult verify_result;
    WltgResult retire_result;
    uint64_t guard_value;
    _Atomic int ready;
    _Atomic int release;
    int hold_ready;
    int retire;
} Worker;

static uint64_t CurrentThreadId(void *opaque)
{
    (void)opaque;
    return (uint64_t)(uintptr_t)pthread_self();
}

static void RegisterRegion(FixtureContext *context, uint32_t index)
{
    atomic_store_explicit(&context->regions[index].thread_id,
                          CurrentThreadId((void *)0), memory_order_release);
}

static void InitContext(FixtureContext *context)
{
    uint32_t index;
    (void)memset(context, 0, sizeof(*context));
    atomic_init(&context->verify_binding_accept, 1);
    atomic_init(&context->audit_accept, 1);
    atomic_init(&context->random_mode, RANDOM_REAL);
    atomic_init(&context->owner_start, WLTG_RESERVATION_TP_START);
    atomic_init(&context->owner_size, WLTG_RESERVATION_SIZE);
    atomic_init(&context->event_count, UINT64_C(0));
    atomic_init(&context->ready_event_count, UINT64_C(0));
    atomic_init(&context->ready_without_receipt, UINT64_C(0));
    atomic_init(&context->random_call_count, UINT64_C(0));
    for (index = 0; index < FIXTURE_REGION_COUNT; ++index) {
        atomic_init(&context->regions[index].thread_id, UINT64_C(0));
    }
    RegisterRegion(context, UINT32_C(0));
}

static WltgProcessBindingV1 MakeBinding(uint32_t max_live_threads)
{
    WltgProcessBindingV1 binding;
    uint32_t index;
    (void)memset(&binding, 0, sizeof(binding));
    binding.abi_version = WLTG_ABI_VERSION;
    binding.struct_size = (uint32_t)sizeof(binding);
    binding.adapter_generation = UINT64_C(0x202607120901);
    binding.process_epoch = UINT64_C(0x550011);
    binding.policy_epoch = UINT64_C(0x880022);
    binding.binding_nonce = UINT64_C(0xaacc3377551199ee);
    for (index = 0; index < WLTG_DIGEST_SIZE; ++index) {
        binding.profile_digest[index] =
            (uint8_t)(UINT8_C(0x31) + (uint8_t)(index * UINT32_C(7)));
        binding.target_digest[index] =
            (uint8_t)(UINT8_C(0x91) + (uint8_t)(index * UINT32_C(11)));
    }
    binding.reservation_tp_start = WLTG_RESERVATION_TP_START;
    binding.reservation_size = WLTG_RESERVATION_SIZE;
    binding.stack_guard_tp_offset = WLTG_STACK_GUARD_TP_OFFSET;
    binding.stack_guard_width = WLTG_STACK_GUARD_WIDTH;
    binding.max_live_threads = max_live_threads;
    return binding;
}

static int VerifyBinding(void *opaque, const WltgProcessBindingV1 *binding)
{
    FixtureContext *context = (FixtureContext *)opaque;
    return binding->binding_nonce != UINT64_C(0) &&
                   atomic_load_explicit(&context->verify_binding_accept,
                                        memory_order_relaxed) == 1
               ? 1
               : 0;
}

static int ResolveRegion(void *opaque,
                         const WltgProcessBindingV1 *binding,
                         const WltgThreadTicketV1 *ticket,
                         WltgOwnedRegion *out_region)
{
    FixtureContext *context = (FixtureContext *)opaque;
    uint64_t current = CurrentThreadId(opaque);
    uint32_t index;
    (void)ticket;
    for (index = 0; index < FIXTURE_REGION_COUNT; ++index) {
        if (atomic_load_explicit(&context->regions[index].thread_id,
                                 memory_order_acquire) != current) {
            continue;
        }
        (void)memset(out_region, 0, sizeof(*out_region));
        out_region->abi_version = WLTG_ABI_VERSION;
        out_region->owner_kind = WLTG_OWNER_MAIN_ELF_TLS_RESERVATION;
        out_region->tp_start_offset = atomic_load_explicit(
            &context->owner_start, memory_order_relaxed);
        out_region->byte_size = atomic_load_explicit(
            &context->owner_size, memory_order_relaxed);
        out_region->base = context->regions[index].aperture;
        out_region->owner_cookie = UINT64_C(0xc001000000000000) + index + 1U;
        out_region->current_thread_id = current;
        out_region->adapter_generation = binding->adapter_generation;
        out_region->process_epoch = binding->process_epoch;
        out_region->policy_epoch = binding->policy_epoch;
        return 1;
    }
    return 0;
}

static int ReadOsCsprng(void *opaque, uint64_t required_process_epoch,
                        WltgGuardSample *out_sample)
{
    FixtureContext *context = (FixtureContext *)opaque;
    RandomMode mode = (RandomMode)atomic_load_explicit(
        &context->random_mode, memory_order_relaxed);
    uint8_t *destination = (uint8_t *)(void *)&out_sample->value;
    size_t remaining = sizeof(out_sample->value);
    int descriptor;
    (void)atomic_fetch_add_explicit(&context->random_call_count,
                                    UINT64_C(1), memory_order_relaxed);
    (void)memset(out_sample, 0, sizeof(*out_sample));
    if (mode == RANDOM_FAIL) {
        return 0;
    }
    if (mode == RANDOM_ZERO) {
        out_sample->value = UINT64_C(0);
    } else if (mode == RANDOM_FIXED) {
        out_sample->value = UINT64_C(0x8a7731e5c9b2046d);
    } else {
        descriptor = open("/dev/urandom", O_RDONLY);
        if (descriptor < 0) {
            return 0;
        }
        while (remaining != 0U) {
            ssize_t count = read(descriptor, destination, remaining);
            if (count <= 0) {
                (void)close(descriptor);
                return 0;
            }
            destination += (size_t)count;
            remaining -= (size_t)count;
        }
        (void)close(descriptor);
    }
    out_sample->source_epoch = mode == RANDOM_WRONG_EPOCH
                                   ? required_process_epoch + UINT64_C(1)
                                   : required_process_epoch;
    out_sample->quality = mode == RANDOM_WRONG_QUALITY
                              ? WLTG_GUARD_SOURCE_INVALID
                              : WLTG_GUARD_SOURCE_OS_CSPRNG;
    out_sample->reserved_zero = UINT32_C(0);
    return 1;
}

static int OnEvent(void *opaque, const WltgAuditEvent *event)
{
    FixtureContext *context = (FixtureContext *)opaque;
    uint64_t event_count =
        atomic_fetch_add_explicit(&context->event_count, UINT64_C(1),
                                  memory_order_relaxed) + UINT64_C(1);
    if (event->type == WLTG_EVENT_THREAD_READY) {
        (void)atomic_fetch_add_explicit(&context->ready_event_count,
                                        UINT64_C(1), memory_order_relaxed);
        if (event->thread_state != WLTG_THREAD_READY ||
            event->ticket_id == UINT64_C(0) ||
            event->current_thread_id == UINT64_C(0) ||
            event->owner_cookie == UINT64_C(0) ||
            event->written_address == (uintptr_t)0 ||
            event->publication_sequence == UINT64_C(0)) {
            (void)atomic_fetch_add_explicit(&context->ready_without_receipt,
                                            UINT64_C(1),
                                            memory_order_relaxed);
        }
    }
#if defined(WLTG_MUTANT_AUDIT_CAP_512)
    if (event_count > UINT64_C(512)) {
        return 0;
    }
#else
    (void)event_count;
#endif
    return atomic_load_explicit(&context->audit_accept,
                                memory_order_relaxed) == 1
               ? 1
               : 0;
}

static WltgPlatformOpsV1 MakeOps(FixtureContext *context)
{
    WltgPlatformOpsV1 ops;
    (void)memset(&ops, 0, sizeof(ops));
    ops.abi_version = WLTG_ABI_VERSION;
    ops.struct_size = (uint32_t)sizeof(ops);
    ops.context = context;
    ops.verify_process_binding = VerifyBinding;
    ops.get_current_thread_id = CurrentThreadId;
    ops.resolve_current_thread_region = ResolveRegion;
    ops.get_os_csprng = ReadOsCsprng;
    ops.emit_audit_event = OnEvent;
    return ops;
}

static WltgResult ArmFixtureMode(FixtureContext *context,
                                 uint32_t max_live_threads,
                                 RandomMode random_mode)
{
    WltgForkSeed seed;
    WltgProcessBindingV1 binding;
    WltgPlatformOpsV1 ops;
    WltgResult result;
    InitContext(context);
    atomic_store_explicit(&context->random_mode, (int)random_mode,
                          memory_order_relaxed);
    binding = MakeBinding(max_live_threads);
    (void)memset(&seed, 0, sizeof(seed));
    seed.abi_version = WLTG_ABI_VERSION;
    seed.adapter_generation = binding.adapter_generation;
    seed.process_epoch = binding.process_epoch;
    seed.policy_epoch = binding.policy_epoch;
    result = WLTG_AfterForkChildReset(&seed);
    if (result.status != WLTG_STATUS_OK) {
        return result;
    }
    ops = MakeOps(context);
    return WLTG_ProcessArm(&binding, &ops);
}

static int ArmFixture(FixtureContext *context, uint32_t max_live_threads)
{
    return ArmFixtureMode(context, max_live_threads, RANDOM_REAL).status ==
                   WLTG_STATUS_OK
               ? 1
               : 0;
}

static uint64_t RegionGuard(const FixtureContext *context, uint32_t index)
{
    uint64_t value;
    (void)memcpy(&value,
                 context->regions[index].aperture +
                     (WLTG_STACK_GUARD_TP_OFFSET -
                      WLTG_RESERVATION_TP_START),
                 sizeof(value));
    return value;
}

static void *WorkerMain(void *opaque)
{
    Worker *worker = (Worker *)opaque;
    RegisterRegion(worker->context, worker->region_index);
    worker->prepare_result = WLTG_PrepareCurrentThread(
        &worker->ticket, &worker->receipt);
    if (worker->prepare_result.status == WLTG_STATUS_OK ||
        worker->prepare_result.status == WLTG_STATUS_OK_IDEMPOTENT) {
        WltgThreadReceiptV1 verified;
        worker->verify_result = WLTG_VerifyCurrentThreadReady(&verified);
        worker->guard_value = RegionGuard(worker->context,
                                          worker->region_index);
    }
    atomic_store_explicit(&worker->ready, 1, memory_order_release);
    if (worker->hold_ready) {
        while (atomic_load_explicit(&worker->release,
                                    memory_order_acquire) == 0) {
        }
    }
    if (worker->retire && worker->prepare_result.status == WLTG_STATUS_OK) {
        worker->retire_result = WLTG_RetireCurrentThread(&worker->receipt);
    }
    return (void *)0;
}

static void InitWorker(Worker *worker, FixtureContext *context,
                       uint32_t region_index,
                       const WltgThreadTicketV1 *ticket)
{
    (void)memset(worker, 0, sizeof(*worker));
    worker->context = context;
    worker->region_index = region_index;
    worker->ticket = *ticket;
    atomic_init(&worker->ready, 0);
    atomic_init(&worker->release, 0);
    worker->retire = 1;
}

static int TestForkResetAndBindingGate(void)
{
    FixtureContext context;
    WltgProcessBindingV1 binding;
    WltgPlatformOpsV1 ops;
    WltgResult result;
    InitContext(&context);
    binding = MakeBinding(UINT32_C(8));
    ops = MakeOps(&context);
    result = WLTG_ProcessArm(&binding, &ops);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_FORK_RESET_REQUIRED);

    InitContext(&context);
    atomic_store_explicit(&context.verify_binding_accept, 0,
                          memory_order_relaxed);
    {
        WltgForkSeed seed = {WLTG_ABI_VERSION, 0,
                             binding.adapter_generation,
                             binding.process_epoch, binding.policy_epoch};
        CHECK(WLTG_AfterForkChildReset(&seed).status == WLTG_STATUS_OK);
    }
    ops = MakeOps(&context);
    result = WLTG_ProcessArm(&binding, &ops);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_BINDING_REJECTED);
    return 1;
}

static int TestMainThreadPublication(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    WltgThreadReceiptV1 verified;
    WltgProcessBindingV1 binding;
    WltgProcessSnapshotV1 snapshot;
    WltgPlatformOpsV1 ops;
    WltgResult result;
    uint64_t guard;
    CHECK(ArmFixture(&context, UINT32_C(8)));
    binding = MakeBinding(UINT32_C(8));
    ops = MakeOps(&context);
    result = WLTG_ProcessArm(&binding, &ops);
    CHECK(result.status == WLTG_STATUS_OK_IDEMPOTENT);
    CHECK(atomic_load_explicit(&context.random_call_count,
                               memory_order_relaxed) == UINT64_C(1));
    result = WLTG_IssueThreadTicket(
        WLTG_ADMISSION_MAIN_POST_SPECIALIZATION, WLTG_THREAD_ROLE_MAIN,
        &ticket);
    CHECK(result.status == WLTG_STATUS_OK);
    result = WLTG_PrepareCurrentThread(&ticket, &receipt);
    CHECK(result.status == WLTG_STATUS_OK);
    CHECK(WLTG_GetProcessSnapshot(&snapshot).status == WLTG_STATUS_OK);
    CHECK(snapshot.ready_count == UINT32_C(1));
    CHECK(snapshot.active_ticket_count == UINT32_C(0));
    CHECK(receipt.state == WLTG_THREAD_READY);
    CHECK(receipt.current_thread_id == CurrentThreadId((void *)0));
    CHECK(receipt.tp_offset == WLTG_STACK_GUARD_TP_OFFSET);
    CHECK(receipt.width == WLTG_STACK_GUARD_WIDTH);
    guard = RegionGuard(&context, UINT32_C(0));
    CHECK(guard != UINT64_C(0));
    result = WLTG_VerifyCurrentThreadReady(&verified);
    CHECK(result.status == WLTG_STATUS_OK);
    CHECK(verified.ticket_id == receipt.ticket_id);
    result = WLTG_PrepareCurrentThread(&ticket, &verified);
    CHECK(result.status == WLTG_STATUS_OK_IDEMPOTENT);
    CHECK(RegionGuard(&context, UINT32_C(0)) == guard);
    CHECK(atomic_load_explicit(&context.ready_event_count,
                               memory_order_relaxed) == UINT64_C(1));
    CHECK(atomic_load_explicit(&context.ready_without_receipt,
                               memory_order_relaxed) == UINT64_C(0));
    CHECK(atomic_load_explicit(&context.random_call_count,
                               memory_order_relaxed) == UINT64_C(1));
    return 1;
}

static int TestParentPreloadPublication(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadTicketV1 replay;
    WltgThreadReceiptV1 receipt;
    WltgThreadReceiptV1 verified;
    CHECK(ArmFixture(&context, UINT32_C(8)));
    CHECK(WLTG_IssueThreadTicket(
              WLTG_ADMISSION_PARENT_PRELOAD,
              WLTG_THREAD_ROLE_PARENT_PRELOAD, &ticket).status ==
          WLTG_STATUS_OK);
    CHECK(WLTG_PrepareCurrentThread(&ticket, &receipt).status ==
          WLTG_STATUS_OK);
    CHECK(receipt.admission_kind == WLTG_ADMISSION_PARENT_PRELOAD);
    CHECK(receipt.role == WLTG_THREAD_ROLE_PARENT_PRELOAD);
    CHECK(WLTG_VerifyCurrentThreadReady(&verified).status ==
          WLTG_STATUS_OK);
    CHECK(verified.ticket_id == receipt.ticket_id);
    CHECK(RegionGuard(&context, UINT32_C(0)) != UINT64_C(0));
    CHECK(WLTG_IssueThreadTicket(
              WLTG_ADMISSION_PARENT_PRELOAD,
              WLTG_THREAD_ROLE_PARENT_PRELOAD, &replay).reason ==
          WLTG_REASON_MAIN_TICKET_ALREADY_ISSUED);
    return 1;
}

static int TestConcurrentThreadsCopyProcessGuard(void)
{
    FixtureContext context;
    WltgThreadTicketV1 main_ticket;
    WltgThreadReceiptV1 main_receipt;
    WltgThreadTicketV1 tickets[CONCURRENT_THREAD_COUNT];
    Worker workers[CONCURRENT_THREAD_COUNT];
    pthread_t threads[CONCURRENT_THREAD_COUNT];
    uint64_t process_guard;
    uint32_t index;
    CHECK(ArmFixture(&context, UINT32_C(48)));
    CHECK(WLTG_IssueThreadTicket(
              WLTG_ADMISSION_MAIN_POST_SPECIALIZATION,
              WLTG_THREAD_ROLE_MAIN, &main_ticket).status == WLTG_STATUS_OK);
    CHECK(WLTG_PrepareCurrentThread(&main_ticket, &main_receipt).status ==
          WLTG_STATUS_OK);
    process_guard = RegionGuard(&context, UINT32_C(0));
    CHECK(process_guard != UINT64_C(0));
    for (index = 0; index < CONCURRENT_THREAD_COUNT; ++index) {
        CHECK(WLTG_IssueThreadTicket(
                  WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                  WLTG_THREAD_ROLE_GUEST_PTHREAD, &tickets[index])
                  .status == WLTG_STATUS_OK);
        InitWorker(&workers[index], &context, index + UINT32_C(1),
                   &tickets[index]);
        CHECK(pthread_create(&threads[index], (const pthread_attr_t *)0,
                             WorkerMain, &workers[index]) == 0);
    }
    for (index = 0; index < CONCURRENT_THREAD_COUNT; ++index) {
        CHECK(pthread_join(threads[index], (void **)0) == 0);
        CHECK(workers[index].prepare_result.status == WLTG_STATUS_OK);
        CHECK(workers[index].verify_result.status == WLTG_STATUS_OK);
        CHECK(workers[index].retire_result.status == WLTG_STATUS_OK);
        CHECK(workers[index].guard_value == process_guard);
    }
    CHECK(WLTG_RetireCurrentThread(&main_receipt).status == WLTG_STATUS_OK);
    CHECK(atomic_load_explicit(&context.ready_event_count,
                               memory_order_relaxed) ==
          CONCURRENT_THREAD_COUNT + UINT64_C(1));
    CHECK(atomic_load_explicit(&context.ready_without_receipt,
                               memory_order_relaxed) == UINT64_C(0));
    CHECK(atomic_load_explicit(&context.random_call_count,
                               memory_order_relaxed) == UINT64_C(1));
    return 1;
}

static int TestGuestTicketCannotRunOnCreator(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    WltgResult result;
    CHECK(ArmFixture(&context, UINT32_C(4)));
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                 WLTG_THREAD_ROLE_GUEST_PTHREAD, &ticket)
              .status == WLTG_STATUS_OK);
    result = WLTG_PrepareCurrentThread(&ticket, &receipt);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_TICKET_CREATOR_MISMATCH);
    CHECK(RegionGuard(&context, UINT32_C(0)) == UINT64_C(0));
    return 1;
}

static int TestJniAttachSameThreadBoundary(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    CHECK(ArmFixture(&context, UINT32_C(4)));
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_ADAPTER_JNI_ATTACH,
                                 WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH,
                                 &ticket)
              .status == WLTG_STATUS_OK);
    CHECK(WLTG_PrepareCurrentThread(&ticket, &receipt).status ==
          WLTG_STATUS_OK);
    CHECK(receipt.current_thread_id == ticket.issuer_thread_id);
    CHECK(RegionGuard(&context, UINT32_C(0)) != UINT64_C(0));
    return 1;
}

static int TestOwnerBoundsFailClosed(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    WltgResult result;
    CHECK(ArmFixture(&context, UINT32_C(4)));
    CHECK(WLTG_IssueThreadTicket(
              WLTG_ADMISSION_MAIN_POST_SPECIALIZATION,
              WLTG_THREAD_ROLE_MAIN, &ticket).status == WLTG_STATUS_OK);
    atomic_store_explicit(&context.owner_start, UINT32_C(0x18),
                          memory_order_relaxed);
    result = WLTG_PrepareCurrentThread(&ticket, &receipt);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_OWNER_BOUNDS);
    CHECK(RegionGuard(&context, UINT32_C(0)) == UINT64_C(0));
    return 1;
}

static int TestCsprngFailureNoFallback(void)
{
    FixtureContext context;
    WltgResult result;
    result = ArmFixtureMode(&context, UINT32_C(4), RANDOM_FAIL);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_CSPRNG_FAILED);
    CHECK(RegionGuard(&context, UINT32_C(0)) == UINT64_C(0));
    CHECK(atomic_load_explicit(&context.random_call_count,
                               memory_order_relaxed) == UINT64_C(1));
    return 1;
}

static int TestZeroAndWrongQualityRejected(void)
{
    FixtureContext context;
    WltgResult result;
    result = ArmFixtureMode(&context, UINT32_C(4), RANDOM_ZERO);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_GUARD_VALUE_INVALID);
    CHECK(RegionGuard(&context, UINT32_C(0)) == UINT64_C(0));

    result = ArmFixtureMode(&context, UINT32_C(4), RANDOM_WRONG_QUALITY);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_CSPRNG_QUALITY);

    result = ArmFixtureMode(&context, UINT32_C(4), RANDOM_WRONG_EPOCH);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_CSPRNG_QUALITY);
    return 1;
}

static int TestCancelAndCapacityReuse(void)
{
    FixtureContext context;
    WltgThreadTicketV1 first;
    WltgThreadTicketV1 second;
    WltgThreadTicketV1 third;
    WltgResult result;
    WltgProcessSnapshotV1 snapshot;
    CHECK(ArmFixture(&context, UINT32_C(2)));
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                 WLTG_THREAD_ROLE_GUEST_PTHREAD, &first)
              .status == WLTG_STATUS_OK);
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                 WLTG_THREAD_ROLE_GUEST_PTHREAD, &second)
              .status == WLTG_STATUS_OK);
    result = WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                    WLTG_THREAD_ROLE_GUEST_PTHREAD, &third);
    CHECK(result.status == WLTG_STATUS_DENIED_TRANSIENT);
    CHECK(result.reason == WLTG_REASON_REGISTRY_FULL);
    CHECK(WLTG_CancelThreadTicket(&first).status == WLTG_STATUS_OK);
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                 WLTG_THREAD_ROLE_GUEST_PTHREAD, &third)
              .status == WLTG_STATUS_OK);
    CHECK(WLTG_CancelThreadTicket(&second).status == WLTG_STATUS_OK);
    CHECK(WLTG_CancelThreadTicket(&third).status == WLTG_STATUS_OK);
    CHECK(WLTG_GetProcessSnapshot(&snapshot).status == WLTG_STATUS_OK);
    CHECK(snapshot.active_ticket_count == UINT32_C(0));
    CHECK(snapshot.cancelled_count >= UINT32_C(2));
    return 1;
}

static int TestAuditSinkBeyondOneRegistryWave(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgProcessSnapshotV1 snapshot;
    uint32_t index;
    CHECK(ArmFixture(&context, UINT32_C(1)));
    for (index = 0; index < UINT32_C(700); ++index) {
        CHECK(WLTG_IssueThreadTicket(
                  WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                  WLTG_THREAD_ROLE_GUEST_PTHREAD, &ticket).status ==
              WLTG_STATUS_OK);
        CHECK(WLTG_CancelThreadTicket(&ticket).status == WLTG_STATUS_OK);
    }
    CHECK(WLTG_GetProcessSnapshot(&snapshot).status == WLTG_STATUS_OK);
    CHECK(snapshot.process_state == WLTG_PROCESS_ARMED);
    CHECK(snapshot.active_ticket_count == UINT32_C(0));
    CHECK(atomic_load_explicit(&context.event_count,
                               memory_order_relaxed) == UINT64_C(1401));
    CHECK(atomic_load_explicit(&context.random_call_count,
                               memory_order_relaxed) == UINT64_C(1));
    return 1;
}

static int TestCrossThreadReplayRejected(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    Worker first;
    Worker replay;
    pthread_t first_thread;
    pthread_t replay_thread;
    CHECK(ArmFixture(&context, UINT32_C(4)));
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                 WLTG_THREAD_ROLE_GUEST_PTHREAD, &ticket)
              .status == WLTG_STATUS_OK);
    InitWorker(&first, &context, UINT32_C(1), &ticket);
    first.hold_ready = 1;
    CHECK(pthread_create(&first_thread, (const pthread_attr_t *)0,
                         WorkerMain, &first) == 0);
    while (atomic_load_explicit(&first.ready, memory_order_acquire) == 0) {
    }
    CHECK(first.prepare_result.status == WLTG_STATUS_OK);

    InitWorker(&replay, &context, UINT32_C(2), &ticket);
    replay.retire = 0;
    CHECK(pthread_create(&replay_thread, (const pthread_attr_t *)0,
                         WorkerMain, &replay) == 0);
    CHECK(pthread_join(replay_thread, (void **)0) == 0);
    CHECK(replay.prepare_result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(replay.prepare_result.reason == WLTG_REASON_TICKET_REPLAY);
    CHECK(RegionGuard(&context, UINT32_C(2)) == UINT64_C(0));
    atomic_store_explicit(&first.release, 1, memory_order_release);
    CHECK(pthread_join(first_thread, (void **)0) == 0);
    return 1;
}

static int TestFixedProcessGuardCopiedToEveryThread(void)
{
    FixtureContext context;
    WltgThreadTicketV1 first_ticket;
    WltgThreadTicketV1 second_ticket;
    Worker first;
    Worker second;
    pthread_t first_thread;
    pthread_t second_thread;
    CHECK(ArmFixtureMode(&context, UINT32_C(4), RANDOM_FIXED).status ==
          WLTG_STATUS_OK);
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                 WLTG_THREAD_ROLE_GUEST_PTHREAD,
                                 &first_ticket).status == WLTG_STATUS_OK);
    CHECK(WLTG_IssueThreadTicket(WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
                                 WLTG_THREAD_ROLE_GUEST_PTHREAD,
                                 &second_ticket).status == WLTG_STATUS_OK);
    InitWorker(&first, &context, UINT32_C(1), &first_ticket);
    first.hold_ready = 1;
    CHECK(pthread_create(&first_thread, (const pthread_attr_t *)0,
                         WorkerMain, &first) == 0);
    while (atomic_load_explicit(&first.ready, memory_order_acquire) == 0) {
    }
    CHECK(first.prepare_result.status == WLTG_STATUS_OK);
    InitWorker(&second, &context, UINT32_C(2), &second_ticket);
    second.retire = 0;
    CHECK(pthread_create(&second_thread, (const pthread_attr_t *)0,
                         WorkerMain, &second) == 0);
    CHECK(pthread_join(second_thread, (void **)0) == 0);
    CHECK(second.prepare_result.status == WLTG_STATUS_OK);
    CHECK(first.guard_value == UINT64_C(0x8a7731e5c9b2046d));
    CHECK(second.guard_value == first.guard_value);
    CHECK(atomic_load_explicit(&context.random_call_count,
                               memory_order_relaxed) == UINT64_C(1));
    atomic_store_explicit(&first.release, 1, memory_order_release);
    CHECK(pthread_join(first_thread, (void **)0) == 0);
    return 1;
}

static int TestAuditSinkFailureIsTerminal(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    WltgResult result;
    CHECK(ArmFixture(&context, UINT32_C(4)));
    CHECK(WLTG_IssueThreadTicket(
              WLTG_ADMISSION_MAIN_POST_SPECIALIZATION,
              WLTG_THREAD_ROLE_MAIN, &ticket).status == WLTG_STATUS_OK);
    atomic_store_explicit(&context.audit_accept, 0, memory_order_relaxed);
    result = WLTG_PrepareCurrentThread(&ticket, &receipt);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_AUDIT_SINK_REJECTED);
    CHECK(result.process_state == WLTG_PROCESS_REJECTED);
    CHECK(RegionGuard(&context, UINT32_C(0)) == UINT64_C(0));
    return 1;
}

static int TestRevokeBlocksOutstandingTicket(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    WltgResult result;
    CHECK(ArmFixture(&context, UINT32_C(4)));
    CHECK(WLTG_IssueThreadTicket(
              WLTG_ADMISSION_MAIN_POST_SPECIALIZATION,
              WLTG_THREAD_ROLE_MAIN, &ticket).status == WLTG_STATUS_OK);
    CHECK(WLTG_Revoke().status == WLTG_STATUS_OK);
    result = WLTG_PrepareCurrentThread(&ticket, &receipt);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_PROCESS_TERMINAL);
    CHECK(RegionGuard(&context, UINT32_C(0)) == UINT64_C(0));
    return 1;
}

static int TestReceiptTamperAndRetire(void)
{
    FixtureContext context;
    WltgThreadTicketV1 ticket;
    WltgThreadReceiptV1 receipt;
    WltgThreadReceiptV1 tampered;
    WltgResult result;
    uint64_t guard;
    CHECK(ArmFixture(&context, UINT32_C(4)));
    CHECK(WLTG_IssueThreadTicket(
              WLTG_ADMISSION_MAIN_POST_SPECIALIZATION,
              WLTG_THREAD_ROLE_MAIN, &ticket).status == WLTG_STATUS_OK);
    CHECK(WLTG_PrepareCurrentThread(&ticket, &receipt).status ==
          WLTG_STATUS_OK);
    guard = RegionGuard(&context, UINT32_C(0));
    tampered = receipt;
    tampered.owner_cookie ^= UINT64_C(1);
    result = WLTG_RetireCurrentThread(&tampered);
    CHECK(result.status == WLTG_STATUS_DENIED_TERMINAL);
    CHECK(result.reason == WLTG_REASON_RECEIPT_MISMATCH);
    CHECK(WLTG_RetireCurrentThread(&receipt).status == WLTG_STATUS_OK);
    CHECK(RegionGuard(&context, UINT32_C(0)) == guard);
    CHECK(guard != UINT64_C(0));
    return 1;
}

int main(void)
{
    int passed = 0;
    passed += TestForkResetAndBindingGate();
    passed += TestMainThreadPublication();
    passed += TestParentPreloadPublication();
    passed += TestConcurrentThreadsCopyProcessGuard();
    passed += TestGuestTicketCannotRunOnCreator();
    passed += TestJniAttachSameThreadBoundary();
    passed += TestOwnerBoundsFailClosed();
    passed += TestCsprngFailureNoFallback();
    passed += TestZeroAndWrongQualityRejected();
    passed += TestCancelAndCapacityReuse();
    passed += TestAuditSinkBeyondOneRegistryWave();
    passed += TestCrossThreadReplayRejected();
    passed += TestFixedProcessGuardCopiedToEveryThread();
    passed += TestAuditSinkFailureIsTerminal();
    passed += TestRevokeBlocksOutstandingTicket();
    passed += TestReceiptTamperAndRetire();
    if (passed != 16) {
        (void)fprintf(stderr,
                      "FAIL thread guard registry host tests passed=%d/16\n",
                      passed);
        return 1;
    }
    (void)printf("PASS thread guard registry host tests=16 threads=%d\n",
                 CONCURRENT_THREAD_COUNT);
    return 0;
}
