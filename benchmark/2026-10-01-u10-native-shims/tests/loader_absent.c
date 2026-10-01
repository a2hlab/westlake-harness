#include "../overlay/android_dlext_abi.h"

#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <string.h>

extern void* android_dlopen_ext(const char*, int, const android_dlextinfo*);

static int calls;

void* dlopen(const char* filename, int flags) {
    assert(strcmp(filename, "ordinary") == 0);
    assert(flags == RTLD_NOW);
    ++calls;
    return (void*)(uintptr_t)123;
}

int main(void) {
    android_dlextinfo info = {0};
    assert(android_dlopen_ext("ordinary", RTLD_NOW, NULL) == (void*)(uintptr_t)123);
    assert(android_dlopen_ext("ordinary", RTLD_NOW, &info) == (void*)(uintptr_t)123);
    assert(calls == 2);
    uint64_t flags[] = {0x200, 0x210, 1, UINT64_MAX};
    for (size_t index = 0; index < sizeof(flags) / sizeof(flags[0]); ++index) {
        info.flags = flags[index];
        errno = 0;
        assert(android_dlopen_ext("unsupported", RTLD_NOW, &info) == NULL);
        assert(errno == ENOTSUP);
        assert(calls == 2);
    }
    return 0;
}
