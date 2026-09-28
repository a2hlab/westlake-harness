/*
 * Android system-property exports for native guests in the app namespace.
 *
 * OpenHarmony's linker namespace inheritance exposes the explicitly shared
 * pthread bridge to the guest, but not the bridge's transitive providers.
 * libbionic_compat already owns the Android-to-OH property implementation, so
 * keep one semantic implementation and publish only narrow forwarding entry
 * points from the DSO that is visible to the guest.
 */

#include <dlfcn.h>
#include <stdatomic.h>
#include <stddef.h>
#include <string.h>

typedef struct prop_info prop_info;

static _Atomic(void *) g_bionic_compat_handle;

static void *GetBionicCompatHandle(void)
{
    void *handle = atomic_load_explicit(&g_bionic_compat_handle,
                                        memory_order_acquire);
    if (handle != NULL) return handle;

    void *opened = dlopen("libbionic_compat.so", RTLD_NOW | RTLD_LOCAL);
    if (opened == NULL) return NULL;

    void *expected = NULL;
    if (!atomic_compare_exchange_strong_explicit(
            &g_bionic_compat_handle, &expected, opened,
            memory_order_release, memory_order_acquire)) {
        (void)dlclose(opened);
        handle = expected;
    } else {
        handle = opened;
    }
    return handle;
}

static int ResolveCompatSymbol(const char *name, void *output,
                               size_t output_size)
{
    void *handle = GetBionicCompatHandle();
    if (handle == NULL || output == NULL || output_size != sizeof(void *)) {
        return 0;
    }
    (void)dlerror();
    void *symbol = dlsym(handle, name);
    if (symbol == NULL || dlerror() != NULL) return 0;
    memcpy(output, &symbol, sizeof(symbol));
    return 1;
}

const prop_info *__system_property_find(const char *name)
{
    typedef const prop_info *(*Function)(const char *);
    Function function = NULL;
    if (!ResolveCompatSymbol("__system_property_find", &function,
                             sizeof(function))) {
        return NULL;
    }
    return function(name);
}

int __system_property_get(const char *name, char *value)
{
    typedef int (*Function)(const char *, char *);
    Function function = NULL;
    if (!ResolveCompatSymbol("__system_property_get", &function,
                             sizeof(function))) {
        if (value != NULL) value[0] = '\0';
        return 0;
    }
    return function(name, value);
}

int __system_property_read(const prop_info *info, char *name, char *value)
{
    typedef int (*Function)(const prop_info *, char *, char *);
    Function function = NULL;
    if (!ResolveCompatSymbol("__system_property_read", &function,
                             sizeof(function))) {
        return -1;
    }
    return function(info, name, value);
}
