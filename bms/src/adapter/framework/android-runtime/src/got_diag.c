// got_diag.c — read GOT.PLT[HiLogPrint] slot in liboh_android_runtime.so after dlopen
#include <dlfcn.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char** argv) {
    const char* lib = argc > 1 ? argv[1] : "liboh_android_runtime.so";
    printf("=== loading %s ===\n", lib);
    fflush(stdout);

    void* h = dlopen(lib, RTLD_NOW);
    if (!h) {
        printf("dlopen FAIL: %s\n", dlerror());
        return 1;
    }
    printf("dlopen OK\n");

    void* hilog_addr = dlsym(RTLD_DEFAULT, "HiLogPrint");
    printf("HiLogPrint via dlsym = %p\n", hilog_addr);

    /* Find lib base via /proc/self/maps */
    FILE* f = fopen("/proc/self/maps", "r");
    if (!f) { perror("maps"); return 2; }
    char line[1024];
    uintptr_t lib_base = 0;
    const char* basename = strrchr(lib, '/');
    basename = basename ? basename + 1 : lib;
    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, basename)) {
            uintptr_t a, b;
            if (sscanf(line, "%lx-%lx", &a, &b) == 2) {
                lib_base = a;
                printf("lib base = %p (line: %s", (void*)lib_base, line);
                break;
            }
        }
    }
    fclose(f);
    if (!lib_base) { printf("lib_base not found\n"); return 3; }

    /* GOT.PLT[HiLogPrint] is at lib_base + 0x26800 (per readelf -r) */
    uintptr_t got_slot_addr = lib_base + 0x26800;
    uintptr_t got_slot_value = *(uintptr_t*)got_slot_addr;
    printf("GOT.PLT[HiLogPrint] @ %p = 0x%lx\n", (void*)got_slot_addr, got_slot_value);

    if (got_slot_value == 0x00023770UL) {
        printf("RESULT: file-value (BIND_NOW SKIPPED)\n");
    } else if (got_slot_value == lib_base + 0x23770) {
        printf("RESULT: lazy-relocation (load_bias added but symbol NOT eagerly resolved)\n");
    } else {
        printf("RESULT: eagerly resolved (BIND_NOW worked, points to actual symbol)\n");
    }

    /* Also dump several other GOT.PLT slots */
    printf("\n=== first 16 GOT.PLT slots ===\n");
    for (int i = 0; i < 16; i++) {
        uintptr_t v = *(uintptr_t*)(lib_base + 0x267d0 + i*4);
        printf("  +0x%x = 0x%lx\n", 0x267d0 + i*4, v);
    }

    return 0;
}
