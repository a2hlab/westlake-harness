#ifndef WESTLAKE_U10_RESIDENT_COMPAT_H
#define WESTLAKE_U10_RESIDENT_COMPAT_H

#include <dlfcn.h>
#include <errno.h>

static int U10ShareResidentCompat(Dl_namespace* output_owner) {
    Dl_namespace resident_namespace;
    if (dlns_get("westlake.sealed.child", &resident_namespace) != 0) {
        APPSPAWN_LOGE("[U10-COMPAT-VISIBLE] unavailable missing resident namespace; no loading fallback; namespace continues");
        return ENOENT;
    }
    void* resident = dlopen_ns(&resident_namespace, "libbionic_compat.so", RTLD_NOW | RTLD_NOLOAD | RTLD_GLOBAL);
    if (resident == NULL) {
        APPSPAWN_LOGE("[U10-COMPAT-VISIBLE] unavailable unmapped resident compat; no loading fallback; namespace continues");
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
    if (result == 0) {
        *output_owner = *owner_namespace;
        APPSPAWN_LOGI("[U10-COMPAT-VISIBLE] owner_verified view=%{public}s resident_view=westlake.sealed.child abort=%{public}p getter=%{public}p gnu=%{public}p inheritance=caller_owned",
                owner_namespace->name, symbols[0], symbols[1], symbols[2]);
    } else {
        APPSPAWN_LOGE("[U10-COMPAT-VISIBLE] unavailable result=%{public}d; no loading fallback; namespace continues", result);
    }
    if (direct != NULL) (void)dlclose(direct);
    (void)dlclose(resident);
    return result;
}

#endif
