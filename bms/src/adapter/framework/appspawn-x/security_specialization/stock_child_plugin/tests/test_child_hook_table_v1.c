#include "westlake_child_hook_table_v1.h"
#include "sealed_child_provider_loader.h"
#include "westlake_generation_identity_facts.h"

#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sched.h>

#define WLASC_PROVIDER_ENTRY_TEST_ONLY 1
#include "../src/westlake_android_child_plugin.c"

#define TEST_THREAD_COUNT 8U
#define EXPECTED_CAPACITY 1024U

int32_t westlake_child_hook_table_v1_prepare_candidate(
    westlake_child_hook_table_v1 *candidate,
    const uint8_t generation_digest[
        WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE],
    uint64_t owner_cookie);

static unsigned int g_tests;
static int g_provider_entry_calls;
static int g_provider_install_calls;
static int g_provider_resolve_mode;
static int g_provider_install_symbol_exact;
static int g_provider_entry_symbol_exact;

#define CHECK(condition)                                                     \
    do {                                                                     \
        ++g_tests;                                                           \
        if (!(condition)) {                                                  \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,       \
                    #condition);                                             \
            return -1;                                                       \
        }                                                                    \
    } while (0)

static westlake_child_hook_result_v1 TestResult(uint64_t value)
{
    westlake_child_hook_result_v1 result = {
        WESTLAKE_CHILD_HOOK_OK, UINT32_C(0), { value }
    };
    return result;
}
static westlake_child_hook_result_v1 TestCreate(
    westlake_child_hook_token_v1 a, westlake_child_hook_token_v1 b,
    westlake_child_hook_token_v1 c) { return TestResult(a.opaque_id ^ b.opaque_id ^ c.opaque_id ^ UINT64_C(1)); }
static westlake_child_hook_result_v1 TestJoin(westlake_child_hook_token_v1 a) { return TestResult(a.opaque_id ^ UINT64_C(2)); }
static westlake_child_hook_result_v1 TestDetach(westlake_child_hook_token_v1 a) { return TestResult(a.opaque_id ^ UINT64_C(3)); }
static westlake_child_hook_result_v1 TestSelf(void) { return TestResult(UINT64_C(4)); }
static westlake_child_hook_result_v1 TestTlsKey(westlake_child_hook_token_v1 a) { return TestResult(a.opaque_id ^ UINT64_C(5)); }
static westlake_child_hook_result_v1 TestTls(westlake_child_hook_token_v1 a, westlake_child_hook_token_v1 b, uint32_t op) { return TestResult(a.opaque_id ^ b.opaque_id ^ op ^ UINT64_C(6)); }
static westlake_child_hook_result_v1 TestSignal(int32_t n, westlake_child_hook_token_v1 a, westlake_child_hook_token_v1 b) { return TestResult((uint64_t)n ^ a.opaque_id ^ b.opaque_id ^ UINT64_C(7)); }
static westlake_child_hook_result_v1 TestAlloc(westlake_child_hook_token_v1 a, westlake_child_hook_token_v1 b, uint64_t size, uint64_t align, uint32_t op) { return TestResult(a.opaque_id ^ b.opaque_id ^ size ^ align ^ op ^ UINT64_C(8)); }
static westlake_child_hook_result_v1 TestUnwind(uint32_t op, westlake_child_hook_token_v1 a, westlake_child_hook_token_v1 b) { return TestResult(a.opaque_id ^ b.opaque_id ^ op ^ UINT64_C(9)); }
static westlake_child_hook_result_v1 TestCpp(uint32_t op, westlake_child_hook_token_v1 a, westlake_child_hook_token_v1 b) { return TestResult(a.opaque_id ^ b.opaque_id ^ op ^ UINT64_C(10)); }

static void FillDigest(uint8_t digest[32], uint8_t seed)
{
    size_t index;

    for (index = 0; index < 32U; ++index) {
        digest[index] = (uint8_t)(seed + (uint8_t)index + UINT8_C(1));
    }
}

static int Prepare(westlake_child_hook_table_v1 *table, uint8_t seed,
                   uint64_t owner)
{
    uint8_t digest[32];
    static const westlake_child_hook_callbacks_v1 callbacks = {
        TestCreate, TestJoin, TestDetach, TestSelf, TestTlsKey, TestTls,
        TestSignal, TestAlloc, TestUnwind, TestCpp
    };

    FillDigest(digest, seed);
    return westlake_child_hook_table_v1_prepare_candidate_with_callbacks(
        table, digest, owner, &callbacks);
}

static int TestExactTenWiring(void)
{
    westlake_child_hook_table_v1 table;
    westlake_child_hook_table_v1 production_candidate;
    westlake_child_hook_result_v1 result;
    westlake_child_hook_token_v1 zero = { UINT64_C(0) };

#if defined(WLASC_P0_TYPED_REJECT_CAPABILITIES)
    CHECK(westlake_child_hook_table_v1_prepare_candidate(
              &production_candidate,
              (const uint8_t *)"01234567890123456789012345678901",
              UINT64_C(0x1234)) == WESTLAKE_CHILD_HOOK_OK);
    result = production_candidate.thread_create(zero, zero, zero);
    CHECK(result.status == WESTLAKE_CHILD_HOOK_TABLE_REJECTED &&
          result.value.opaque_id == UINT64_C(0));
    CHECK(production_candidate.thread_join(zero).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.thread_detach(zero).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.thread_self().status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.tls_key_create(zero).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.tls_get_set(zero, zero, UINT32_C(0)).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.signal_route(0, zero, zero).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.allocator_domain(
              zero, zero, UINT64_C(16), UINT64_C(8),
              WESTLAKE_CHILD_HOOK_ALLOCATE).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.unwind_domain(
              UINT32_C(0), zero, zero).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
    CHECK(production_candidate.cpp_runtime_domain(
              UINT32_C(0), zero, zero).status ==
          WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
#else
    CHECK(westlake_child_hook_table_v1_prepare_candidate(
              &production_candidate,
              (const uint8_t *)"01234567890123456789012345678901",
              UINT64_C(0x1234)) == WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
#endif
    CHECK(Prepare(&table, UINT8_C(1), UINT64_C(0xa14a15a16)) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(table.capability_bitmap == WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP);
    CHECK((table.capability_bitmap &
           WESTLAKE_CHILD_HOOK_THREAD_TLS_SIGNAL_BITMAP) == UINT64_C(0x7f));
    CHECK((table.capability_bitmap & WESTLAKE_CHILD_HOOK_ALLOCATOR_BITMAP) ==
          UINT64_C(0x80));
    CHECK((table.capability_bitmap & WESTLAKE_CHILD_HOOK_UNWIND_CPP_BITMAP) ==
          UINT64_C(0x300));
    CHECK(table.thread_create != 0 && table.thread_join != 0 &&
          table.thread_detach != 0 && table.thread_self != 0 &&
          table.tls_key_create != 0 && table.tls_get_set != 0 &&
          table.signal_route != 0 && table.allocator_domain != 0 &&
          table.unwind_domain != 0 && table.cpp_runtime_domain != 0);
    result = table.thread_create(zero, zero, zero);
    CHECK(result.status == WESTLAKE_CHILD_HOOK_OK && result.value.opaque_id == UINT64_C(1));
    result = table.allocator_domain(zero, zero, UINT64_C(16), UINT64_C(8),
                                    WESTLAKE_CHILD_HOOK_ALLOCATE);
    CHECK(result.status == WESTLAKE_CHILD_HOOK_OK);
    result = table.unwind_domain(UINT32_C(0), zero, zero);
    CHECK(result.status == WESTLAKE_CHILD_HOOK_OK);
    result = table.cpp_runtime_domain(UINT32_C(0), zero, zero);
    CHECK(result.status == WESTLAKE_CHILD_HOOK_OK);
    return 0;
}

static int ProviderInstall(
    const WlascHostRuntimeServicesV1 *services)
{
    if (services == (const WlascHostRuntimeServicesV1 *)0) {
        return -1;
    }
    ++g_provider_install_calls;
    return g_provider_resolve_mode == 2 ? -66 : 0;
}

static int ProviderEntry(
    const WlascAndroidChildRequestV1 *request,
    const WlascStockStageReceiptV1 *receipt)
{
    if (request == (const WlascAndroidChildRequestV1 *)0 ||
        receipt == (const WlascStockStageReceiptV1 *)0) {
        return -1;
    }
    ++g_provider_entry_calls;
    return g_provider_resolve_mode == 3 ? -77 : 0;
}

static void *ProviderResolver(void *handle, const char *symbol)
{
    void *resolved = (void *)0;

    if (handle != (void *)(uintptr_t)UINT64_C(0x1234) ||
        symbol == (const char *)0) {
        return (void *)0;
    }
    if (strcmp(symbol, "WLAR_InstallHostRuntimeServices") == 0) {
        WlascProviderInstallServicesV1 install = ProviderInstall;
        g_provider_install_symbol_exact = 1;
        if (g_provider_resolve_mode == 0 ||
            sizeof(resolved) != sizeof(install)) {
            return (void *)0;
        }
        memcpy(&resolved, &install, sizeof(resolved));
        return resolved;
    }
    if (strcmp(symbol, "WLAR_EnterAndroidAfterStockSpecialization") == 0) {
        WlascProviderChildEntryV1 entry = ProviderEntry;
        g_provider_entry_symbol_exact = 1;
        if (g_provider_resolve_mode == 1 ||
            sizeof(resolved) != sizeof(entry)) {
            return (void *)0;
        }
        memcpy(&resolved, &entry, sizeof(resolved));
        return resolved;
    }
    return (void *)0;
}

static int TestSealedProviderEntryPNF(void)
{
    WlascAndroidChildRequestV1 request = {0};
    WlascStockStageReceiptV1 receipt = {0};
    WlascHostRuntimeServicesV1 services = {0};
    void *handle = (void *)(uintptr_t)UINT64_C(0x1234);

    g_provider_entry_calls = 0;
    g_provider_install_calls = 0;
    g_provider_resolve_mode = 0;
    g_provider_install_symbol_exact = 0;
    g_provider_entry_symbol_exact = 0;
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, &services, &request, &receipt,
              ProviderResolver) == -1);
    CHECK(g_provider_install_symbol_exact == 1 &&
          g_provider_entry_symbol_exact == 1 &&
          g_provider_install_calls == 0 && g_provider_entry_calls == 0);

    g_provider_resolve_mode = 1;
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, &services, &request, &receipt,
              ProviderResolver) == -1);
    CHECK(g_provider_install_calls == 0 && g_provider_entry_calls == 0);

    g_provider_resolve_mode = 2;
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, &services, &request, &receipt,
              ProviderResolver) == -1);
    CHECK(g_provider_install_calls == 1 && g_provider_entry_calls == 0);

    g_provider_resolve_mode = 3;
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, &services, &request, &receipt,
              ProviderResolver) == -1);
    CHECK(g_provider_install_calls == 2 && g_provider_entry_calls == 1);

    g_provider_resolve_mode = 4;
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, &services, &request, &receipt,
              ProviderResolver) == 0);
    CHECK(g_provider_install_calls == 3 && g_provider_entry_calls == 2);

    CHECK(InvokeProviderChildEntryWithResolver(
              (void *)0, &services, &request, &receipt,
              ProviderResolver) == -1);
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, (const WlascHostRuntimeServicesV1 *)0,
              &request, &receipt, ProviderResolver) == -1);
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, &services,
              (const WlascAndroidChildRequestV1 *)0,
              &receipt, ProviderResolver) == -1);
    CHECK(InvokeProviderChildEntryWithResolver(
              handle, &services, &request,
              (const WlascStockStageReceiptV1 *)0,
              ProviderResolver) == -1);
    return 0;
}

static int TestPositiveLifecycle(void)
{
    westlake_child_hook_control_v1 control = {0};
    westlake_child_hook_table_v1 table;
    westlake_child_hook_lease_v1 lease;
    westlake_child_hook_lease_v1 copied_lease;
    uint8_t wrong_digest[32];

    CHECK(Prepare(&table, UINT8_C(10), UINT64_C(0x600d)) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_begin_install(
              &control, &table, UINT64_C(41)) == WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_lifecycle_state == WESTLAKE_CHILD_HOOK_INSTALLING);
    CHECK(westlake_child_hook_table_v1_publish(&control, &table) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_lifecycle_state == WESTLAKE_CHILD_HOOK_READY &&
          control.atomic_admission_open == UINT64_C(1));

    /* Exact duplicate observes the recorded success without republishing. */
    CHECK(westlake_child_hook_table_v1_begin_install(
              &control, &table, UINT64_C(41)) == WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_publish(&control, &table) ==
          WESTLAKE_CHILD_HOOK_OK);

    FillDigest(wrong_digest, UINT8_C(99));
    CHECK(westlake_child_hook_table_v1_admit(
              &control, wrong_digest, &lease) ==
          WESTLAKE_CHILD_HOOK_GENERATION_STALE);
    CHECK(westlake_child_hook_table_v1_admit(
              &control, table.generation_digest, &lease) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(lease.table == &table && lease.child_epoch == UINT64_C(41) &&
          lease.lease_token.opaque_id != UINT64_C(0));
    CHECK(control.atomic_inflight_count == UINT64_C(1));
    copied_lease = lease;
    CHECK(westlake_child_hook_table_v1_release(&control, &lease) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_inflight_count == UINT64_C(0));
    CHECK(westlake_child_hook_table_v1_release(&control, &copied_lease) ==
          WESTLAKE_CHILD_HOOK_TOKEN_INVALID);
    CHECK(westlake_child_hook_table_v1_release(&control, &lease) ==
          WESTLAKE_CHILD_HOOK_TOKEN_INVALID);

    CHECK(westlake_child_hook_table_v1_revoke(
              &control, WESTLAKE_CHILD_HOOK_TABLE_REJECTED) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_admission_open == UINT64_C(0) &&
          control.atomic_lifecycle_state == WESTLAKE_CHILD_HOOK_REVOKING);
    CHECK(westlake_child_hook_table_v1_admit(
              &control, table.generation_digest, &lease) ==
          WESTLAKE_CHILD_HOOK_REVOKED);
    CHECK(westlake_child_hook_table_v1_drain(&control) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_lifecycle_state == WESTLAKE_CHILD_HOOK_DRAINING);
    CHECK(westlake_child_hook_table_v1_invalidate(&control, UINT32_C(0)) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_lifecycle_state == WESTLAKE_CHILD_HOOK_INVALID &&
          control.atomic_published_table_address == UINT64_C(0));
    return 0;
}

static int PublishRejects(westlake_child_hook_table_v1 *mutant)
{
    westlake_child_hook_control_v1 control = {0};

    return westlake_child_hook_table_v1_begin_install(
               &control, mutant, UINT64_C(1)) != WESTLAKE_CHILD_HOOK_OK;
}

static int TestValidationMutants(void)
{
    westlake_child_hook_table_v1 base;
    westlake_child_hook_table_v1 mutant;

    CHECK(Prepare(&base, UINT8_C(20), UINT64_C(0xcafe)) ==
          WESTLAKE_CHILD_HOOK_OK);

#define REJECT_MUTATION(statement)                                           \
    do {                                                                     \
        mutant = base;                                                       \
        statement;                                                           \
        CHECK(PublishRejects(&mutant));                                      \
    } while (0)

    REJECT_MUTATION(mutant.magic ^= UINT64_C(1));
    REJECT_MUTATION(mutant.abi_major += UINT16_C(1));
    REJECT_MUTATION(mutant.abi_minor += UINT16_C(1));
    REJECT_MUTATION(mutant.struct_size -= UINT32_C(8));
    REJECT_MUTATION(mutant.struct_alignment = UINT32_C(4));
    REJECT_MUTATION(mutant.capability_bitmap &= ~UINT64_C(1));
    REJECT_MUTATION(mutant.capability_bitmap |= UINT64_C(1) << 63U);
    REJECT_MUTATION(memset(mutant.generation_digest, 0,
                           sizeof(mutant.generation_digest)));
    REJECT_MUTATION(mutant.owner_cookie = UINT64_C(0));
    REJECT_MUTATION(mutant.data_pointer_size = UINT16_C(4));
    REJECT_MUTATION(mutant.data_pointer_alignment = UINT16_C(4));
    REJECT_MUTATION(mutant.function_pointer_size = UINT16_C(4));
    REJECT_MUTATION(mutant.function_pointer_alignment = UINT16_C(4));
    REJECT_MUTATION(mutant.thread_create = 0);
    REJECT_MUTATION(mutant.thread_join = 0);
    REJECT_MUTATION(mutant.thread_detach = 0);
    REJECT_MUTATION(mutant.thread_join = base.thread_detach);
    REJECT_MUTATION(mutant.thread_detach = base.thread_join);
    REJECT_MUTATION(mutant.thread_self = 0);
    REJECT_MUTATION(mutant.tls_key_create = 0);
    REJECT_MUTATION(mutant.tls_get_set = 0);
    REJECT_MUTATION(mutant.signal_route = 0);
    REJECT_MUTATION(mutant.allocator_domain = 0);
    REJECT_MUTATION(mutant.unwind_domain = 0);
    REJECT_MUTATION(mutant.cpp_runtime_domain = 0);
#undef REJECT_MUTATION
    return 0;
}

typedef struct InstallRaceContext {
    westlake_child_hook_control_v1 *control;
    westlake_child_hook_table_v1 table;
    uint64_t epoch;
    uint64_t *start;
    int32_t result;
} InstallRaceContext;

static void *RunInstallRace(void *opaque)
{
    InstallRaceContext *context = (InstallRaceContext *)opaque;

    while (__atomic_load_n(context->start, __ATOMIC_ACQUIRE) == UINT64_C(0)) {
        sched_yield();
    }
    context->result = westlake_child_hook_table_v1_begin_install(
        context->control, &context->table, context->epoch);
    return (void *)0;
}

static int TestInstallRace(void)
{
    westlake_child_hook_control_v1 control = {0};
    InstallRaceContext contexts[TEST_THREAD_COUNT];
    pthread_t threads[TEST_THREAD_COUNT];
    uint64_t start = UINT64_C(0);
    unsigned int index;
    unsigned int winners = 0U;

    for (index = 0; index < TEST_THREAD_COUNT; ++index) {
        contexts[index].control = &control;
        contexts[index].epoch = UINT64_C(100) + (uint64_t)index;
        contexts[index].start = &start;
        contexts[index].result = WESTLAKE_CHILD_HOOK_INVALID_ARGUMENT;
        CHECK(Prepare(&contexts[index].table, (uint8_t)(40U + index),
                      UINT64_C(0x1000) + (uint64_t)index) ==
              WESTLAKE_CHILD_HOOK_OK);
        CHECK(pthread_create(&threads[index], (const pthread_attr_t *)0,
                             RunInstallRace, &contexts[index]) == 0);
    }
    __atomic_store_n(&start, UINT64_C(1), __ATOMIC_RELEASE);
    for (index = 0; index < TEST_THREAD_COUNT; ++index) {
        CHECK(pthread_join(threads[index], (void **)0) == 0);
        if (contexts[index].result == WESTLAKE_CHILD_HOOK_OK) {
            ++winners;
        } else {
            CHECK(contexts[index].result ==
                  WESTLAKE_CHILD_HOOK_INSTALL_RACE);
        }
    }
    CHECK(winners == 1U);
    return 0;
}

typedef struct RevokeRaceContext {
    westlake_child_hook_control_v1 *control;
    const westlake_child_hook_table_v1 *table;
    uint64_t *start;
    uint64_t *holding;
    uint64_t *release;
    int32_t admit_result;
    int32_t late_result;
    int32_t release_result;
} RevokeRaceContext;

static void *RunRevokeRace(void *opaque)
{
    RevokeRaceContext *context = (RevokeRaceContext *)opaque;
    westlake_child_hook_lease_v1 lease;

    while (__atomic_load_n(context->start, __ATOMIC_ACQUIRE) == UINT64_C(0)) {
        sched_yield();
    }
    context->admit_result = westlake_child_hook_table_v1_admit(
        context->control, context->table->generation_digest, &lease);
    (void)__atomic_fetch_add(context->holding, UINT64_C(1), __ATOMIC_ACQ_REL);
    while (__atomic_load_n(context->release, __ATOMIC_ACQUIRE) == UINT64_C(0)) {
        sched_yield();
    }
    context->late_result = westlake_child_hook_table_v1_admit(
        context->control, context->table->generation_digest,
        &(westlake_child_hook_lease_v1){0});
    context->release_result = westlake_child_hook_table_v1_release(
        context->control, &lease);
    return (void *)0;
}

static int TestRevokeDrainRace(void)
{
    westlake_child_hook_control_v1 control = {0};
    westlake_child_hook_table_v1 table;
    RevokeRaceContext contexts[TEST_THREAD_COUNT];
    pthread_t threads[TEST_THREAD_COUNT];
    uint64_t start = UINT64_C(0);
    uint64_t holding = UINT64_C(0);
    uint64_t release = UINT64_C(0);
    unsigned int index;

    CHECK(Prepare(&table, UINT8_C(70), UINT64_C(0xbeef)) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_begin_install(
              &control, &table, UINT64_C(77)) == WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_publish(&control, &table) ==
          WESTLAKE_CHILD_HOOK_OK);
    for (index = 0; index < TEST_THREAD_COUNT; ++index) {
        contexts[index].control = &control;
        contexts[index].table = &table;
        contexts[index].start = &start;
        contexts[index].holding = &holding;
        contexts[index].release = &release;
        CHECK(pthread_create(&threads[index], (const pthread_attr_t *)0,
                             RunRevokeRace, &contexts[index]) == 0);
    }
    __atomic_store_n(&start, UINT64_C(1), __ATOMIC_RELEASE);
    while (__atomic_load_n(&holding, __ATOMIC_ACQUIRE) !=
           TEST_THREAD_COUNT) {
        sched_yield();
    }
    CHECK(control.atomic_inflight_count == TEST_THREAD_COUNT);
    CHECK(westlake_child_hook_table_v1_revoke(
              &control, WESTLAKE_CHILD_HOOK_OWNER_MISMATCH) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_drain(&control) ==
          WESTLAKE_CHILD_HOOK_DRAIN_TIMEOUT);
    CHECK(westlake_child_hook_table_v1_invalidate(&control, UINT32_C(0)) ==
          WESTLAKE_CHILD_HOOK_INVALIDATE_TIMEOUT);
    __atomic_store_n(&release, UINT64_C(1), __ATOMIC_RELEASE);
    for (index = 0; index < TEST_THREAD_COUNT; ++index) {
        CHECK(pthread_join(threads[index], (void **)0) == 0);
        CHECK(contexts[index].admit_result == WESTLAKE_CHILD_HOOK_OK);
        CHECK(contexts[index].late_result == WESTLAKE_CHILD_HOOK_REVOKED);
        CHECK(contexts[index].release_result == WESTLAKE_CHILD_HOOK_OK);
    }
    CHECK(control.atomic_inflight_count == UINT64_C(0));
    CHECK(westlake_child_hook_table_v1_drain(&control) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_invalidate(&control, UINT32_C(0)) ==
          WESTLAKE_CHILD_HOOK_OK);
    return 0;
}

static int TestCapacityAndFirstCause(void)
{
    westlake_child_hook_control_v1 control = {0};
    westlake_child_hook_table_v1 table;
    westlake_child_hook_lease_v1 *leases;
    westlake_child_hook_lease_v1 extra;
    unsigned int index;

    leases = calloc(EXPECTED_CAPACITY, sizeof(*leases));
    CHECK(leases != (westlake_child_hook_lease_v1 *)0);
    CHECK(Prepare(&table, UINT8_C(90), UINT64_C(0xf00d)) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_begin_install(
              &control, &table, UINT64_C(99)) == WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_publish(&control, &table) ==
          WESTLAKE_CHILD_HOOK_OK);
    for (index = 0; index < EXPECTED_CAPACITY; ++index) {
        CHECK(westlake_child_hook_table_v1_admit(
                  &control, table.generation_digest, &leases[index]) ==
              WESTLAKE_CHILD_HOOK_OK);
    }
    CHECK(westlake_child_hook_table_v1_admit(
              &control, table.generation_digest, &extra) ==
          WESTLAKE_CHILD_HOOK_CAPACITY_EXHAUSTED);
    CHECK(westlake_child_hook_table_v1_record_first_cause(
              &control, WESTLAKE_CHILD_HOOK_OWNER_MISMATCH) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_record_first_cause(
              &control, WESTLAKE_CHILD_HOOK_GENERATION_STALE) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_first_cause == WESTLAKE_CHILD_HOOK_OWNER_MISMATCH);
    for (index = 0; index < EXPECTED_CAPACITY; ++index) {
        CHECK(westlake_child_hook_table_v1_release(
                  &control, &leases[index]) == WESTLAKE_CHILD_HOOK_OK);
    }
    free(leases);
    return 0;
}

static int TestFailStopInvalidation(void)
{
    westlake_child_hook_control_v1 control = {0};
    westlake_child_hook_table_v1 table;
    westlake_child_hook_lease_v1 lease;

    CHECK(Prepare(&table, UINT8_C(110), UINT64_C(0xdead)) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_begin_install(
              &control, &table, UINT64_C(111)) == WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_publish(&control, &table) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_admit(
              &control, table.generation_digest, &lease) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_revoke(
              &control, WESTLAKE_CHILD_HOOK_DRAIN_TIMEOUT) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_drain(&control) ==
          WESTLAKE_CHILD_HOOK_DRAIN_TIMEOUT);
    CHECK(westlake_child_hook_table_v1_invalidate(&control, UINT32_C(0)) ==
          WESTLAKE_CHILD_HOOK_INVALIDATE_TIMEOUT);
    CHECK(westlake_child_hook_table_v1_invalidate(&control, UINT32_C(1)) ==
          WESTLAKE_CHILD_HOOK_INVALIDATE_TIMEOUT);
    CHECK(westlake_child_hook_table_v1_release(&control, &lease) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_drain(&control) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(westlake_child_hook_table_v1_invalidate(&control, UINT32_C(1)) ==
          WESTLAKE_CHILD_HOOK_OK);
    CHECK(control.atomic_lifecycle_state == WESTLAKE_CHILD_HOOK_INVALID);
    return 0;
}

static int TestP0ChildExitStatus(void)
{
    CHECK(WlascP0ChildExitFromFailure(0) == WLASC_P0_EXIT_UNCLASSIFIED);
    CHECK(WlascP0ChildExitFromFailure(1) == WLASC_P0_EXIT_UNCLASSIFIED);
    CHECK(WlascP0ChildExitFromFailure(-256) == WLASC_P0_EXIT_UNCLASSIFIED);
    CHECK(WlascP0ChildExitFromFailure(-WLASC_P0_EXIT_ARGUMENT) ==
          WLASC_P0_EXIT_ARGUMENT);
    CHECK(WlascP0ChildExitFromFailure(
              -(WLASC_P0_EXIT_ACQUIRE_BASE + WLGR_IF_NONCE_REPLAY)) ==
          WLASC_P0_EXIT_ACQUIRE_BASE + WLGR_IF_NONCE_REPLAY);
    CHECK(WlascP0ChildExitFromFailure(
              -(WLASC_P0_EXIT_BUILD_BASE + WLGR_IP_TAMPERED)) ==
          WLASC_P0_EXIT_BUILD_BASE + WLGR_IP_TAMPERED);
    CHECK(WlascP0ChildExitFromFailure(
              -(WLASC_P0_EXIT_VALIDATE_BASE + WLGR_IP_TAMPERED)) ==
          WLASC_P0_EXIT_VALIDATE_BASE + WLGR_IP_TAMPERED);
    CHECK(WlascP0ChildExitFromFailure(
              -(WLASC_P0_EXIT_LOADER_BASE + WLSCPL_ERROR_EXTERNAL_ROOT)) ==
          WLASC_P0_EXIT_LOADER_BASE + WLSCPL_ERROR_EXTERNAL_ROOT);
    CHECK(WlascP0ChildExitFromFailure(-WLASC_P0_EXIT_PROVIDER_ENTRY) ==
          WLASC_P0_EXIT_PROVIDER_ENTRY);
    return 0;
}

int main(void)
{
    if (TestExactTenWiring() != 0 ||
        TestSealedProviderEntryPNF() != 0 ||
        TestPositiveLifecycle() != 0 ||
        TestValidationMutants() != 0 ||
        TestInstallRace() != 0 ||
        TestRevokeDrainRace() != 0 ||
        TestCapacityAndFirstCause() != 0 ||
        TestFailStopInvalidation() != 0 ||
        TestP0ChildExitStatus() != 0) {
        return EXIT_FAILURE;
    }
    printf("child-hook-v1 PNF PASS checks=%u partitions=7/1/2 capacity=%u\n",
           g_tests, EXPECTED_CAPACITY);
    return EXIT_SUCCESS;
}
