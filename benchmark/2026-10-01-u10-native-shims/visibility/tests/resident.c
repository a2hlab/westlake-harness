#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "../resident-compat.h"

static int failure;
static int opens;
static int inheritance;
static int closes;

int dlns_get(const char* name, Dl_namespace* output) {
    assert(strcmp(name, "westlake.sealed.child") == 0 || strcmp(name, "default") == 0);
    if ((failure == 1 && strcmp(name, "westlake.sealed.child") == 0) ||
        (failure == 9 && strcmp(name, "default") == 0)) return 2;
    strcpy(output->name, name);
    return 0;
}

void* dlopen_ns(Dl_namespace* domain, const char* name, int flags) {
    assert(strcmp(name, "libbionic_compat.so") == 0);
    assert((flags & RTLD_NOLOAD) != 0);
    ++opens;
    if (strcmp(domain->name, "westlake.sealed.child") == 0) {
        return failure == 2 ? NULL : (void*)(uintptr_t)10;
    }
    if (strcmp(domain->name, "default") == 0) {
        return failure == 7 ? NULL : (void*)(uintptr_t)30;
    }
    assert(strcmp(domain->name, "application") == 0);
    return failure == 4 ? NULL : (void*)(uintptr_t)20;
}

int dlns_inherit(Dl_namespace* application, Dl_namespace* resident, const char* names) {
    assert(strcmp(application->name, "application") == 0);
    assert(strcmp(resident->name, failure == 7 || failure == 9 ? "westlake.sealed.child" : "default") == 0);
    assert(strcmp(names, "libbionic_compat.so") == 0);
    ++inheritance;
    return failure == 3 ? EACCES : 0;
}

void* dlsym(void* handle, const char* name) {
    uintptr_t value = strcmp(name, "android_set_abort_message") == 0 ? 100
        : strcmp(name, "android_get_abort_message") == 0 ? 200 : 300;
    if (failure == 5 && handle == (void*)(uintptr_t)20) ++value;
    if (failure == 8 && handle == (void*)(uintptr_t)30) ++value;
    if (failure == 6 && value == 300) return NULL;
    return (void*)value;
}

int dlclose(void* handle) {
    assert(handle == (void*)(uintptr_t)10 || handle == (void*)(uintptr_t)20 || handle == (void*)(uintptr_t)30);
    ++closes;
    return 0;
}

int main(void) {
    Dl_namespace application;
    strcpy(application.name, "application");
    for (failure = 0; failure <= 9; ++failure) {
        opens = 0;
        inheritance = 0;
        closes = 0;
        int result = U10ShareResidentCompat(&application);
        if (failure == 0 || failure == 7 || failure == 9) {
            assert(result == 0 && inheritance == 1);
            assert(opens == (failure == 9 ? 2 : 3));
            assert(closes == (failure == 0 ? 3 : 2));
        } else {
            assert(result != 0);
            if (failure == 1) assert(opens == 0);
            if (failure == 2) assert(opens == 1 && inheritance == 0);
            if (failure == 6) assert(inheritance == 0);
            if (failure == 8) assert(inheritance == 0 && closes == 2);
        }
    }
    return 0;
}
