#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <dlfcn.h>
#include "opensles-owner.h"
typedef struct Dl_namespace { const char *name; } Dl_namespace;
static int missing_symbol;
static unsigned owner_opens, facade_opens;
static WlSlInterfaceId ids[4];
static WlSlId exported_ids[] = {&ids[0], &ids[1], &ids[2], &ids[3]};
static unsigned bind_calls;
static int bind_result;
static int open_failure;
static bool wrong_owner;
static uint32_t backend(WlSlObject *object, uint32_t option_count,
    const WlSlEngineOption *options, uint32_t interface_count,
    const WlSlId *interfaces, const uint32_t *required) {
    (void)object; (void)option_count; (void)options; (void)interface_count;
    (void)interfaces; (void)required;
    return 0;
}
static int bind_owner(const WlSlOwnerV1 *owner) {
    assert(owner->version == 1 && owner->create_engine == backend);
    assert(owner->engine == &ids[0] && owner->buffer_queue == &ids[3]);
    ++bind_calls;
    return bind_result;
}
static int dlns_get(const char *name, Dl_namespace *result) {
    assert(!strcmp(name, "default"));
    result->name = name;
    return 0;
}
static void *dlopen_ns(Dl_namespace *namespace, const char *path, int mode) {
    assert((mode & RTLD_NOW) && !(mode & RTLD_NOLOAD));
    if (!strcmp(namespace->name, "default")) {
        assert(!strcmp(path, "/system/lib64/libOpenSLES.so"));
        ++owner_opens;
        return open_failure == 1 ? NULL : (void *)(uintptr_t)1;
    }
    assert(!strcmp(path, "/system/android/lib64/westlake_audio/libOpenSLES.so"));
    ++facade_opens;
    return open_failure == 2 ? NULL : (void *)(uintptr_t)2;
}
static void *fake_symbol(void *handle, const char *name) {
    if (!strcmp(name, "WestlakeBindOpenSlesOwnerV1")) {
        assert(handle == (void *)(uintptr_t)2);
        WlSlBindOwner bind = bind_owner;
        void *result;
        memcpy(&result, &bind, sizeof(result));
        return missing_symbol == 5 ? NULL : result;
    }
    assert(handle == (void *)(uintptr_t)1);
    if (!strcmp(name, "slCreateEngine")) {
        WlSlCreateEngine engine = backend;
        void *result;
        memcpy(&result, &engine, sizeof(result));
        return missing_symbol == 1 ? NULL : result;
    }
    const char *names[] = {"SL_IID_ENGINE", "SL_IID_VOLUME", "SL_IID_PLAY", "SL_IID_BUFFERQUEUE"};
    for (size_t index = 0; index < 4; ++index)
        if (!strcmp(name, names[index]))
            return missing_symbol == (int)index + 6 ? NULL : &exported_ids[index];
    assert(false);
    return NULL;
}
#define dlsym fake_symbol
static int fake_address(const void *symbol, Dl_info *result) {
    WlSlBindOwner bind = bind_owner;
    void *bind_symbol;
    memcpy(&bind_symbol, &bind, sizeof(bind_symbol));
    result->dli_fname = symbol == bind_symbol
        ? "/system/android/lib64/westlake_audio/libOpenSLES.so"
        : wrong_owner ? "/system/android/lib64/libOpenSLES.so" : "/system/lib64/libOpenSLES.so";
    return 1;
}
#define dladdr fake_address
#define APPSPAWN_LOGI(...) ((void)0)
#include "missing-library-route.h"

int main(int argc, char **argv) {
    assert(argc == 2);
    assert(MissingLibraryPackage("/data/app/im.vector.app/lib", "im.vector.app"));
    assert(!MissingLibraryPackage("/data/app/notim.vector.app/lib", "im.vector.app"));
    assert(!MissingLibraryPackage("/data/app/im.vector.app.extra/lib", "im.vector.app"));
    assert(!MissingLibraryRoot("/data/app/ooniprobe/lib", "/data/app/ooniprobe"));
    assert(!strcmp(MissingLibraryRoot("/data/app/im.vector.app/lib", ""), "/system/android/lib64/westlake_native"));
    assert(!strcmp(MissingLibraryRoot("/data/app/com.emn8.mobilem8.nativeapp.bk/lib", ""), "/system/android/lib64/westlake_native"));
    assert(!strcmp(MissingLibraryRoot("", "/data/app/io.anuke.mindustry/lib"), "/system/android/lib64/westlake_audio"));
    Dl_namespace app = {"westlake.anl.app.100.3"};
    assert(MissingLibraryAudioOwner(&app, "/data/app/control/lib", "") == 0 && !owner_opens);
    if (!strcmp(argv[1], "missing")) missing_symbol = 1;
    if (!strcmp(argv[1], "iid-missing")) missing_symbol = 6;
    if (!strcmp(argv[1], "bind-missing")) missing_symbol = 5;
    if (!strcmp(argv[1], "bind-failed")) bind_result = 17;
    if (!strcmp(argv[1], "owner-failed")) open_failure = 1;
    if (!strcmp(argv[1], "facade-failed")) open_failure = 2;
    if (!strcmp(argv[1], "wrong-owner")) wrong_owner = true;
    int result = MissingLibraryAudioOwner(&app, "/data/app/io.anuke.mindustry/lib", "");
    if (missing_symbol || wrong_owner) assert(result == ENOEXEC);
    else if (open_failure) assert(result == ENOENT);
    else if (bind_result) assert(result == bind_result && bind_calls == 1);
    else assert(result == 0 && owner_opens == 1 && facade_opens == 1 && bind_calls == 1);
    return 0;
}
