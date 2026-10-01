#ifndef WESTLAKE_MISSING_LIBRARY_ROUTE_H
#define WESTLAKE_MISSING_LIBRARY_ROUTE_H

#include "opensles-owner.h"

static bool MissingLibraryPackage(const char *paths, const char *package) {
    if (!paths) return false;
    const size_t length = strlen(package);
    const char *cursor = paths;
    while ((cursor = strstr(cursor, package)) != NULL) {
        if ((cursor == paths || cursor[-1] == '/') &&
            (cursor[length] == '/' || cursor[length] == ':' || cursor[length] == '\0')) return true;
        cursor += length;
    }
    return false;
}

static const char *MissingLibraryRoot(const char *search, const char *permitted) {
    if (MissingLibraryPackage(search, "io.anuke.mindustry") ||
        MissingLibraryPackage(permitted, "io.anuke.mindustry"))
        return "/system/android/lib64/westlake_audio";
    const char *packages[] = {"im.vector.app", "com.emn8.mobilem8.nativeapp.bk"};
    for (size_t index = 0; index < sizeof(packages) / sizeof(packages[0]); ++index)
        if (MissingLibraryPackage(search, packages[index]) ||
            MissingLibraryPackage(permitted, packages[index]))
            return "/system/android/lib64/westlake_native";
    return NULL;
}

static int MissingLibraryAudioOwner(Dl_namespace *app, const char *search, const char *permitted) {
    if (!MissingLibraryPackage(search, "io.anuke.mindustry") &&
        !MissingLibraryPackage(permitted, "io.anuke.mindustry")) return 0;
    Dl_namespace owner_namespace;
    if (dlns_get("default", &owner_namespace) != 0) return ENOENT;
    void *owner = dlopen_ns(&owner_namespace, "/system/lib64/libOpenSLES.so", RTLD_NOW | RTLD_LOCAL);
    if (!owner) return ENOENT;
    WlSlOwnerV1 binding = {.version = 1};
    void *create = dlsym(owner, "slCreateEngine");
    if (!create || sizeof(create) != sizeof(binding.create_engine)) return ENOEXEC;
    Dl_info owner_info;
    if (!dladdr(create, &owner_info) || !owner_info.dli_fname ||
        strcmp(owner_info.dli_fname, "/system/lib64/libOpenSLES.so") != 0) return ENOEXEC;
    memcpy(&binding.create_engine, &create, sizeof(create));
    const char *names[] = {"SL_IID_ENGINE", "SL_IID_VOLUME", "SL_IID_PLAY", "SL_IID_BUFFERQUEUE"};
    WlSlId *slots[] = {&binding.engine, &binding.volume, &binding.play, &binding.buffer_queue};
    for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); ++index) {
        WlSlId *symbol = (WlSlId *)dlsym(owner, names[index]);
        if (!symbol || !*symbol) return ENOEXEC;
        *slots[index] = *symbol;
    }
    void *facade = dlopen_ns(app, "/system/android/lib64/westlake_audio/libOpenSLES.so", RTLD_NOW | RTLD_LOCAL);
    if (!facade) return ENOENT;
    void *bind_symbol = dlsym(facade, "WestlakeBindOpenSlesOwnerV1");
    WlSlBindOwner bind = NULL;
    if (!bind_symbol || sizeof(bind_symbol) != sizeof(bind)) return ENOEXEC;
    Dl_info facade_info;
    if (!dladdr(bind_symbol, &facade_info) || !facade_info.dli_fname ||
        strcmp(facade_info.dli_fname, "/system/android/lib64/westlake_audio/libOpenSLES.so") != 0) return ENOEXEC;
    memcpy(&bind, &bind_symbol, sizeof(bind_symbol));
    int result = bind(&binding);
    if (result) return result;
    APPSPAWN_LOGI("[U9-SL-OWNER] ns=%{public}s owner=%{public}p engine=%{public}p facade=%{public}p queue=%{public}p",
                  app->name, owner, create, facade, (const void *)binding.buffer_queue);
    return 0;
}

#endif
