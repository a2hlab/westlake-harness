#include "android_dlext_abi.h"

#include <dlfcn.h>
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>

extern void* __loader_android_dlopen_ext(const char*, int,
    const android_dlextinfo*, const void*)
#if defined(__APPLE__)
    __attribute__((weak_import));
#else
    __attribute__((weak));
#endif

void* android_dlopen_ext(const char* filename, int flags,
    const android_dlextinfo* extinfo) {
    const void* caller_addr = __builtin_return_address(0);
    if (__loader_android_dlopen_ext != NULL) {
        return __loader_android_dlopen_ext(filename, flags, extinfo, caller_addr);
    }
    if (extinfo != NULL && extinfo->flags != 0) {
        fprintf(stderr, "[U10-DLEXT] backend absent; refusing extension flags=0x%" PRIx64
            " file=%s\n", extinfo->flags, filename == NULL ? "(null)" : filename);
        errno = ENOTSUP;
        return NULL;
    }
    return dlopen(filename, flags);
}
