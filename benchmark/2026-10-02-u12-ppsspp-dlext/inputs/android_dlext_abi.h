#ifndef WESTLAKE_ANDROID_DLEXT_ABI_H
#define WESTLAKE_ANDROID_DLEXT_ABI_H

#include <stddef.h>
#include <stdint.h>

struct android_namespace_t;

typedef struct {
    uint64_t flags;
    void* reserved_addr;
    size_t reserved_size;
    int relro_fd;
    int library_fd;
    int64_t library_fd_offset;
    struct android_namespace_t* library_namespace;
} android_dlextinfo;

#if __SIZEOF_POINTER__ == 8
_Static_assert(sizeof(android_dlextinfo) == 48, "Android LP64 dlextinfo size");
_Static_assert(offsetof(android_dlextinfo, library_namespace) == 40,
    "Android LP64 namespace offset");
#endif

#endif
