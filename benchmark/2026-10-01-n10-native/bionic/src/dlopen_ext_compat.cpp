// Android dlopen_ext for the Bionic/Musl boundary.
//
// Android's android_dlopen_ext extends dlopen with android_dlextinfo
// (namespace, library path, etc.).  musl's dlopen supports standard RTLD_*
// flags only.  This shim ignores extinfo (logs when non-NULL) and forwards
// to dlopen, covering the common case where extinfo is NULL or unused.

#include <dlfcn.h>
#include <stdio.h>

extern "C" void *android_dlopen_ext(const char *filename, int flags, const void *extinfo)
{
    if (extinfo != nullptr) {
        // Log when extinfo is provided but not handled (namespace, library path,
        // etc. are Android-specific and not implemented here).
        fprintf(stderr, "[bionic_compat] android_dlopen_ext: extinfo=%p ignored (namespace/library-path not implemented)\n", extinfo);
    }
    return dlopen(filename, flags);
}
