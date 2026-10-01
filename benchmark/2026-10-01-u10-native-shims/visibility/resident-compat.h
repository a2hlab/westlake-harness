#ifndef WESTLAKE_U10_RESIDENT_COMPAT_H
#define WESTLAKE_U10_RESIDENT_COMPAT_H

#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>

static int U10ShareResidentCompat(Dl_namespace* application) {
    Dl_namespace resident_namespace;
    if (dlns_get("westlake.sealed.child", &resident_namespace) != 0) {
        fprintf(stderr, "[U10-COMPAT-VISIBLE] rejected missing resident namespace; no loading fallback\n");
        return ENOENT;
    }
    void* resident = dlopen_ns(&resident_namespace, "libbionic_compat.so", RTLD_NOW | RTLD_NOLOAD);
    if (resident == NULL) {
        fprintf(stderr, "[U10-COMPAT-VISIBLE] rejected unmapped resident compat; no loading fallback\n");
        return ENOENT;
    }
    const char* names[] = {"android_set_abort_message", "android_get_abort_message", "__gnu_strerror_r"};
    void* symbols[3];
    int result = 0;
    for (size_t index = 0; index < 3; ++index) {
        symbols[index] = dlsym(resident, names[index]);
        if (symbols[index] == NULL) result = ENOEXEC;
    }
    Dl_namespace direct_namespace;
    Dl_namespace* owner_namespace = &resident_namespace;
    void* direct = NULL;
    if (result == 0 && dlns_get("default", &direct_namespace) == 0) {
        direct = dlopen_ns(&direct_namespace, "libbionic_compat.so", RTLD_NOW | RTLD_NOLOAD);
        if (direct != NULL) {
            for (size_t index = 0; index < 3; ++index) {
                if (dlsym(direct, names[index]) != symbols[index]) result = ENOEXEC;
            }
            if (result == 0) owner_namespace = &direct_namespace;
        }
    }
    if (result == 0) result = dlns_inherit(application, owner_namespace, "libbionic_compat.so");
    void* application_view = result == 0
        ? dlopen_ns(application, "libbionic_compat.so", RTLD_NOW | RTLD_NOLOAD) : NULL;
    if (result == 0 && application_view == NULL) result = ENOENT;
    if (application_view != NULL) {
        for (size_t index = 0; index < 3; ++index) {
            if (dlsym(application_view, names[index]) != symbols[index]) result = ENOEXEC;
        }
        (void)dlclose(application_view);
    }
    if (result == 0) {
        fprintf(stderr, "[U10-COMPAT-VISIBLE] inherited_view=%s resident_view=westlake.sealed.child abort=%p getter=%p gnu=%p\n",
                owner_namespace->name, symbols[0], symbols[1], symbols[2]);
    } else {
        fprintf(stderr, "[U10-COMPAT-VISIBLE] rejected result=%d; no loading fallback\n", result);
    }
    if (direct != NULL) (void)dlclose(direct);
    (void)dlclose(resident);
    return result;
}

#endif
