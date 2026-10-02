#define _pthread_cleanup_push test_oh_push
#define _pthread_cleanup_pop test_oh_pop
#define strtoll_l test_strtoll_l
#define strtoull_l test_strtoull_l
#include "vlc_bionic_residue.c"
#undef _pthread_cleanup_push
#undef _pthread_cleanup_pop
#undef strtoll_l
#undef strtoull_l

#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stdint.h>

static _Thread_local OhCleanup *host_head;
static _Thread_local unsigned callback_order;

void test_oh_push(OhCleanup *record, void (*routine)(void *), void *argument) {
    record->routine = routine;
    record->argument = argument;
    record->next = host_head;
    host_head = record;
}

void test_oh_pop(OhCleanup *record, int execute) {
    host_head = record->next;
    if (execute) {
        record->routine(record->argument);
    }
}

static void record_callback(void *value) {
    callback_order = callback_order * 10 + (unsigned)(uintptr_t)value;
}

static void drain_host(void *unused) {
    (void)unused;
    while (host_head != NULL) {
        OhCleanup *record = host_head;
        host_head = record->next;
        record->routine(record->argument);
    }
}

static void check_thread_exit(void *result) {
    drain_host(NULL);
    if (callback_order != 4321 || cleanup_head != NULL) {
        abort();
    }
    (void)result;
}

static void *exit_worker(void *argument) {
    (void)argument;
    AndroidCleanup first, second, popped;
    OhCleanup native_record, last_native;
    pthread_cleanup_push(check_thread_exit, NULL);
    __pthread_cleanup_push(&first, record_callback, (void *)(uintptr_t)1);
    test_oh_push(&native_record, record_callback, (void *)(uintptr_t)2);
    __pthread_cleanup_push(&second, record_callback, (void *)(uintptr_t)3);
    __pthread_cleanup_push(&popped, record_callback, (void *)(uintptr_t)9);
    __pthread_cleanup_pop(&popped, 0);
    test_oh_push(&last_native, record_callback, (void *)(uintptr_t)4);
    pthread_exit((void *)(uintptr_t)17);
    pthread_cleanup_pop(0);
    return NULL;
}

int main(void) {
    char *end_pointer = NULL;
    if (test_strtoll_l("-0x2az", &end_pointer, 0, NULL) != -42 || *end_pointer != 'z') return 1;
    errno = 0;
    if (test_strtoull_l("18446744073709551616", &end_pointer, 10, NULL) != ULLONG_MAX || errno != ERANGE) return 2;
    AndroidCleanup first, second;
    __pthread_cleanup_push(&first, record_callback, (void *)(uintptr_t)1);
    __pthread_cleanup_push(&second, record_callback, (void *)(uintptr_t)2);
    if (second.previous != &first || first.previous != NULL) return 3;
    __pthread_cleanup_pop(&second, 1);
    __pthread_cleanup_pop(&first, 0);
    if (callback_order != 2 || cleanup_head != NULL || host_head != NULL) return 4;
    pthread_t thread;
    void *result = NULL;
    if (pthread_create(&thread, NULL, exit_worker, NULL) != 0 || pthread_join(thread, &result) != 0) return 5;
    if (result != (void *)(uintptr_t)17 || callback_order != 2) return 6;
    return 0;
}
