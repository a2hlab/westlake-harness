#include <dlfcn.h>
#include <stddef.h>

typedef int (*AnlNestedLeafValue)(void);

__attribute__((visibility("default"))) int anl_probe_nested_root_value(void) {
    void* handle = dlopen("libanl_probe_nested_leaf.so", RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) return 0xe2;

    AnlNestedLeafValue leaf_value =
        (AnlNestedLeafValue)dlsym(handle, "anl_probe_nested_leaf_value");
    if (leaf_value == NULL) {
        dlclose(handle);
        return 0xe3;
    }

    int value = leaf_value();
    if (dlclose(handle) != 0) return 0xe4;
    return value;
}
