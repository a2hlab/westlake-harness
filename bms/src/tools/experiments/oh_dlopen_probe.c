#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: %s <absolute-so-path> <required-symbol>\n", argv[0]);
        return 2;
    }

    dlerror();
    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
        const char *error = dlerror();
        fprintf(stderr, "DLOPEN_FAIL path=%s error=%s\n",
                argv[1], error != NULL ? error : "<none>");
        return 1;
    }

    dlerror();
    void *symbol = dlsym(handle, argv[2]);
    const char *error = dlerror();
    if (error != NULL || symbol == NULL) {
        fprintf(stderr, "DLSYM_FAIL symbol=%s error=%s\n",
                argv[2], error != NULL ? error : "<none>");
        dlclose(handle);
        return 1;
    }

    printf("DLOPEN_PASS path=%s symbol=%s address=%p\n",
           argv[1], argv[2], symbol);
    /*
     * liboh_adapter_bridge is a process-lifetime DSO in appspawn-x.  Do not
     * call dlclose here: its global OH client singletons are not specified as
     * unload-safe, and unload behavior is outside this preflight contract.
     */
    fflush(stdout);
    _Exit(0);
}
