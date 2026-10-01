#include_next <dlfcn.h>

typedef struct {
    char name[256];
} Dl_namespace;

int dlns_get(const char*, Dl_namespace*);
int dlns_inherit(Dl_namespace*, Dl_namespace*, const char*);
void* dlopen_ns(Dl_namespace*, const char*, int);
