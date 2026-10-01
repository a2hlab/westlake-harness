#include "../overlay/android_dlext_abi.h"

#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>

extern void* android_dlopen_ext(const char*, int, const android_dlextinfo*);

static const char* expected_filename;
static const android_dlextinfo* expected_info;
static const void* observed_caller;

void* __loader_android_dlopen_ext(const char* filename, int flags,
    const android_dlextinfo* info, const void* caller_addr) {
    assert(filename == expected_filename);
    assert(flags == RTLD_NOW);
    assert(info == expected_info);
    assert(info->library_namespace == (struct android_namespace_t*)(uintptr_t)0x12345678);
    observed_caller = caller_addr;
    return (void*)(uintptr_t)567;
}

__attribute__((noinline)) static void test_backend(uint64_t flags) {
    android_dlextinfo info = {0};
    info.flags = flags;
    info.library_namespace = (struct android_namespace_t*)(uintptr_t)0x12345678;
    expected_filename = "opaque-namespace-consumer";
    expected_info = &info;
    const void* before = &&call_begin;
    const void* after = &&call_end;
call_begin:
    assert(android_dlopen_ext(expected_filename, RTLD_NOW, &info) == (void*)(uintptr_t)567);
call_end:
    assert((uintptr_t)observed_caller >= (uintptr_t)before);
    assert((uintptr_t)observed_caller <= (uintptr_t)after);
}

int main(void) {
    test_backend(0x200);
    test_backend(0x210);
    return 0;
}
