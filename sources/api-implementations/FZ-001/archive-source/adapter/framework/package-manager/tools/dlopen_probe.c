// dlopen_probe.c — minimal on-device dlopen()/dlsym() verifier.
//
// Cross-compile for aarch64-linux-ohos the same way as install_plan (see
// ../install_plan/DEVICE_VERIFICATION.md and ../ARM64_PRODUCER_REBUILD_RESULT.md
// for the exact clang invocation) and push to a D600 board via hdc. Confirms
// a freshly built .so actually loads and exports a given symbol on real
// hardware, rather than trusting a host-side `nm`/`readelf` check alone.
//
// Usage: dlopen_probe <path-to-so> <symbol-name>

#include <dlfcn.h>
#include <stdio.h>

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <path-to-so> <symbol-name>\n", argv[0]);
        return 2;
    }
    void* h = dlopen(argv[1], RTLD_NOW);
    if (!h) {
        fprintf(stderr, "dlopen FAILED: %s\n", dlerror());
        return 1;
    }
    printf("dlopen OK\n");
    void* sym = dlsym(h, argv[2]);
    if (!sym) {
        fprintf(stderr, "dlsym FAILED: %s\n", dlerror());
        return 1;
    }
    printf("dlsym OK: %s @ %p\n", argv[2], sym);
    dlclose(h);
    return 0;
}
