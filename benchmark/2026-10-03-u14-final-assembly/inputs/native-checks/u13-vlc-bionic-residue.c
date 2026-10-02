#include <stddef.h>
#include <stdlib.h>

typedef struct AndroidCleanup {
    struct AndroidCleanup *previous;
    void (*routine)(void *);
    void *argument;
} AndroidCleanup;

typedef struct OhCleanup {
    void (*routine)(void *);
    void *argument;
    struct OhCleanup *next;
} OhCleanup;

typedef struct CleanupAdapter {
    OhCleanup host_record;
    AndroidCleanup *android_record;
    struct CleanupAdapter *previous;
} CleanupAdapter;

_Static_assert(sizeof(AndroidCleanup) == 24, "Android LP64 cleanup record");
_Static_assert(sizeof(OhCleanup) == 24, "OH LP64 cleanup record");
_Static_assert(offsetof(AndroidCleanup, routine) == 8, "Android cleanup routine offset");
_Static_assert(offsetof(OhCleanup, next) == 16, "OH cleanup previous offset");

extern void _pthread_cleanup_push(OhCleanup *, void (*)(void *), void *);
extern void _pthread_cleanup_pop(OhCleanup *, int);

static _Thread_local CleanupAdapter *cleanup_head;

long long strtoll_l(const char *text, char **end_pointer, int base, void *locale) {
    (void)locale;
    return strtoll(text, end_pointer, base);
}

unsigned long long strtoull_l(const char *text, char **end_pointer, int base, void *locale) {
    (void)locale;
    return strtoull(text, end_pointer, base);
}

static void cleanup_dispatch(void *opaque) {
    CleanupAdapter *adapter = opaque;
    AndroidCleanup *record = adapter->android_record;
    void (*routine)(void *) = record->routine;
    void *argument = record->argument;
    cleanup_head = adapter->previous;
    free(adapter);
    routine(argument);
}

void __pthread_cleanup_push(AndroidCleanup *record, void (*routine)(void *), void *argument) {
    CleanupAdapter *adapter = malloc(sizeof(*adapter));
    if (adapter == NULL) {
        abort();
    }
    adapter->android_record = record;
    adapter->previous = cleanup_head;
    record->previous = cleanup_head == NULL ? NULL : cleanup_head->android_record;
    record->routine = routine;
    record->argument = argument;
    cleanup_head = adapter;
    _pthread_cleanup_push(&adapter->host_record, cleanup_dispatch, adapter);
}

void __pthread_cleanup_pop(AndroidCleanup *record, int execute) {
    CleanupAdapter *adapter = cleanup_head;
    if (adapter == NULL || adapter->android_record != record) {
        abort();
    }
    _pthread_cleanup_pop(&adapter->host_record, 0);
    if (execute) {
        cleanup_dispatch(adapter);
    } else {
        cleanup_head = adapter->previous;
        free(adapter);
    }
}
