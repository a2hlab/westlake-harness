#include "westlake_bionic_pthread_bridge.h"

#include <stdatomic.h>
#include <stdbool.h>

#define WLPB_EAGAIN 11
#define WLPB_EINVAL 22
#define WLPB_ENOSYS 38

enum RecordState {
    RECORD_FREE = 0,
    RECORD_ALLOCATING = 1,
    RECORD_ISSUED = 2,
    RECORD_READY = 3,
};

typedef struct AttrRecord {
    _Atomic uint32_t state;
    uintptr_t guest_address;
    WlpbMuslAttrStorageV1 musl_attribute;
} AttrRecord;

typedef struct StartRecord {
    _Atomic uint32_t state;
    WlpbTicketStorageV1 ticket;
    WlpbReceiptStorageV1 receipt;
    WlpbStartRoutine guest_start;
    void *guest_argument;
    uint64_t current_thread_id;
} StartRecord;

static _Atomic uint32_t g_install_state;
static WlpbHostOpsV1 g_ops;
static AttrRecord g_attributes[WLPB_MAX_RECORDS];
static StartRecord g_starts[WLPB_MAX_RECORDS];

static bool reserved_zero(const uint32_t values[4])
{
    return (values[0] | values[1] | values[2] | values[3]) == 0U;
}

static bool installed(void)
{
    return atomic_load_explicit(&g_install_state, memory_order_acquire) == 2U;
}

static _Noreturn void fatal(uint32_t reason)
{
    if (installed() && g_ops.fatal_process != NULL) {
        g_ops.fatal_process(g_ops.context, reason);
    }
    __builtin_trap();
}

static AttrRecord *find_attribute(const void *guest_attribute)
{
    const uintptr_t key = (uintptr_t)guest_attribute;
    for (size_t index = 0; index < WLPB_MAX_RECORDS; ++index) {
        if (atomic_load_explicit(&g_attributes[index].state,
                                 memory_order_acquire) == RECORD_READY &&
            g_attributes[index].guest_address == key) {
            return &g_attributes[index];
        }
    }
    return NULL;
}

static AttrRecord *allocate_attribute(void *guest_attribute)
{
    if (guest_attribute == NULL || find_attribute(guest_attribute) != NULL) {
        return NULL;
    }
    for (size_t index = 0; index < WLPB_MAX_RECORDS; ++index) {
        uint32_t expected = RECORD_FREE;
        if (atomic_compare_exchange_strong_explicit(
                &g_attributes[index].state, &expected, RECORD_ALLOCATING,
                memory_order_acq_rel, memory_order_acquire)) {
            g_attributes[index].guest_address = (uintptr_t)guest_attribute;
            return &g_attributes[index];
        }
    }
    return NULL;
}

static void release_attribute(AttrRecord *record)
{
    record->guest_address = 0U;
    atomic_store_explicit(&record->state, RECORD_FREE, memory_order_release);
}

static StartRecord *allocate_start(void)
{
    for (size_t index = 0; index < WLPB_MAX_RECORDS; ++index) {
        uint32_t expected = RECORD_FREE;
        if (atomic_compare_exchange_strong_explicit(
                &g_starts[index].state, &expected, RECORD_ALLOCATING,
                memory_order_acq_rel, memory_order_acquire)) {
            return &g_starts[index];
        }
    }
    return NULL;
}

static void release_start(StartRecord *record)
{
    record->guest_start = NULL;
    record->guest_argument = NULL;
    record->current_thread_id = 0U;
    atomic_store_explicit(&record->state, RECORD_FREE, memory_order_release);
}

static void *start_trampoline(void *opaque)
{
    StartRecord *record = (StartRecord *)opaque;
    if (record == NULL ||
        atomic_load_explicit(&record->state, memory_order_acquire) !=
            RECORD_ISSUED ||
        g_ops.prepare_current_thread(g_ops.context, &record->ticket,
                                     &record->receipt) != 1 ||
        g_ops.verify_current_thread_ready(g_ops.context, &record->receipt) != 1) {
        fatal(UINT32_C(1));
    }
    record->current_thread_id = g_ops.get_current_thread_id(g_ops.context);
    if (record->current_thread_id == 0U) {
        fatal(UINT32_C(2));
    }
    atomic_store_explicit(&record->state, RECORD_READY, memory_order_release);
    WlpbStartRoutine start = record->guest_start;
    void *argument = record->guest_argument;
    void *result = start(argument);
    if (g_ops.retire_current_thread(g_ops.context, &record->receipt) != 1) {
        fatal(UINT32_C(3));
    }
    release_start(record);
    return result;
}

uint32_t WLPB_GetAbiVersion(void)
{
    return WLPB_ABI_VERSION;
}

int WLPB_InstallHostOps(const WlpbHostOpsV1 *ops)
{
    if (ops == NULL || ops->abi_version != WLPB_ABI_VERSION ||
        ops->struct_size != sizeof(*ops) || ops->generation == 0U ||
        !reserved_zero(ops->reserved_zero) ||
        ops->issue_thread_ticket == NULL ||
        ops->cancel_thread_ticket == NULL ||
        ops->prepare_current_thread == NULL ||
        ops->verify_current_thread_ready == NULL ||
        ops->retire_current_thread == NULL ||
        ops->get_current_thread_id == NULL ||
        ops->real_pthread_create == NULL || ops->real_pthread_exit == NULL ||
        ops->real_pthread_attr_init == NULL ||
        ops->real_pthread_attr_destroy == NULL ||
        ops->real_pthread_attr_setdetachstate == NULL ||
        ops->real_pthread_attr_setstacksize == NULL ||
        ops->real_pthread_attr_getstack == NULL ||
        ops->real_pthread_getattr_np == NULL || ops->fatal_process == NULL) {
        return WLPB_EINVAL;
    }
    uint32_t expected = 0U;
    if (!atomic_compare_exchange_strong_explicit(
            &g_install_state, &expected, 1U,
            memory_order_acq_rel, memory_order_acquire)) {
        return WLPB_EINVAL;
    }
    g_ops.abi_version = ops->abi_version;
    g_ops.struct_size = ops->struct_size;
    g_ops.context = ops->context;
    g_ops.issue_thread_ticket = ops->issue_thread_ticket;
    g_ops.cancel_thread_ticket = ops->cancel_thread_ticket;
    g_ops.prepare_current_thread = ops->prepare_current_thread;
    g_ops.verify_current_thread_ready = ops->verify_current_thread_ready;
    g_ops.retire_current_thread = ops->retire_current_thread;
    g_ops.get_current_thread_id = ops->get_current_thread_id;
    g_ops.real_pthread_create = ops->real_pthread_create;
    g_ops.real_pthread_exit = ops->real_pthread_exit;
    g_ops.real_pthread_attr_init = ops->real_pthread_attr_init;
    g_ops.real_pthread_attr_destroy = ops->real_pthread_attr_destroy;
    g_ops.real_pthread_attr_setdetachstate =
        ops->real_pthread_attr_setdetachstate;
    g_ops.real_pthread_attr_setstacksize =
        ops->real_pthread_attr_setstacksize;
    g_ops.real_pthread_attr_getstack = ops->real_pthread_attr_getstack;
    g_ops.real_pthread_getattr_np = ops->real_pthread_getattr_np;
    g_ops.fatal_process = ops->fatal_process;
    g_ops.generation = ops->generation;
    g_ops.reserved_zero[0] = 0U;
    g_ops.reserved_zero[1] = 0U;
    g_ops.reserved_zero[2] = 0U;
    g_ops.reserved_zero[3] = 0U;
    atomic_store_explicit(&g_install_state, 2U, memory_order_release);
    return 0;
}

WLPB_EXPORT int pthread_attr_init(void *guest_attribute)
{
    if (!installed()) return WLPB_ENOSYS;
    AttrRecord *record = allocate_attribute(guest_attribute);
    if (record == NULL) return WLPB_EINVAL;
    const int result = g_ops.real_pthread_attr_init(
        g_ops.context, &record->musl_attribute);
    if (result != 0) {
        release_attribute(record);
        return result;
    }
    atomic_store_explicit(&record->state, RECORD_READY, memory_order_release);
    return 0;
}

WLPB_EXPORT int pthread_attr_destroy(void *guest_attribute)
{
    if (!installed()) return WLPB_ENOSYS;
    AttrRecord *record = find_attribute(guest_attribute);
    if (record == NULL) return WLPB_EINVAL;
    const int result = g_ops.real_pthread_attr_destroy(
        g_ops.context, &record->musl_attribute);
    if (result == 0) release_attribute(record);
    return result;
}

WLPB_EXPORT int pthread_attr_setdetachstate(void *guest_attribute, int state)
{
    AttrRecord *record = installed() ? find_attribute(guest_attribute) : NULL;
    return record == NULL ? WLPB_EINVAL :
        g_ops.real_pthread_attr_setdetachstate(
            g_ops.context, &record->musl_attribute, state);
}

WLPB_EXPORT int pthread_attr_setstacksize(void *guest_attribute, size_t size)
{
    AttrRecord *record = installed() ? find_attribute(guest_attribute) : NULL;
    return record == NULL ? WLPB_EINVAL :
        g_ops.real_pthread_attr_setstacksize(
            g_ops.context, &record->musl_attribute, size);
}

WLPB_EXPORT int pthread_attr_getstack(const void *guest_attribute,
                                      void **stack_base, size_t *stack_size)
{
    AttrRecord *record = installed() ? find_attribute(guest_attribute) : NULL;
    return record == NULL ? WLPB_EINVAL :
        g_ops.real_pthread_attr_getstack(
            g_ops.context, &record->musl_attribute, stack_base, stack_size);
}

WLPB_EXPORT int pthread_getattr_np(uint64_t thread, void *guest_attribute)
{
    if (!installed()) return WLPB_ENOSYS;
    AttrRecord *record = allocate_attribute(guest_attribute);
    if (record == NULL) return WLPB_EINVAL;
    const int result = g_ops.real_pthread_getattr_np(
        g_ops.context, thread, &record->musl_attribute);
    if (result != 0) {
        release_attribute(record);
        return result;
    }
    atomic_store_explicit(&record->state, RECORD_READY, memory_order_release);
    return 0;
}

WLPB_EXPORT int pthread_create(uint64_t *thread, const void *guest_attribute,
                               WlpbStartRoutine start, void *argument)
{
    if (!installed()) return WLPB_ENOSYS;
    if (thread == NULL || start == NULL) return WLPB_EINVAL;
    AttrRecord *attribute = guest_attribute == NULL ? NULL :
        find_attribute(guest_attribute);
    if (guest_attribute != NULL && attribute == NULL) return WLPB_EINVAL;
    StartRecord *record = allocate_start();
    if (record == NULL) return WLPB_EAGAIN;
    record->guest_start = start;
    record->guest_argument = argument;
    if (g_ops.issue_thread_ticket(g_ops.context, &record->ticket) != 1) {
        release_start(record);
        return WLPB_EAGAIN;
    }
    atomic_store_explicit(&record->state, RECORD_ISSUED, memory_order_release);
    const int result = g_ops.real_pthread_create(
        g_ops.context, thread,
        attribute == NULL ? NULL : &attribute->musl_attribute,
        start_trampoline, record);
    if (result != 0) {
        if (g_ops.cancel_thread_ticket(g_ops.context, &record->ticket) != 1) {
            fatal(UINT32_C(4));
        }
        release_start(record);
    }
    return result;
}

WLPB_EXPORT _Noreturn void pthread_exit(void *result)
{
    if (!installed()) fatal(UINT32_C(5));
    const uint64_t current = g_ops.get_current_thread_id(g_ops.context);
    for (size_t index = 0; index < WLPB_MAX_RECORDS; ++index) {
        StartRecord *record = &g_starts[index];
        if (atomic_load_explicit(&record->state, memory_order_acquire) ==
                RECORD_READY &&
            record->current_thread_id == current) {
            if (g_ops.retire_current_thread(g_ops.context,
                                            &record->receipt) != 1) {
                fatal(UINT32_C(6));
            }
            release_start(record);
            g_ops.real_pthread_exit(g_ops.context, result);
            __builtin_trap();
        }
    }
    fatal(UINT32_C(7));
}
