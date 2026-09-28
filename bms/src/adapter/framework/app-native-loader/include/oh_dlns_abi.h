#ifndef WESTLAKE_OH_DLNS_ABI_H
#define WESTLAKE_OH_DLNS_ABI_H

#include <dlfcn.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* OpenHarmony third_party_musl/include/dlfcn.h ABI. */
#ifndef CREATE_INHERIT_DEFAULT
#define CREATE_INHERIT_DEFAULT 0x1
#endif
#ifndef CREATE_INHERIT_CURRENT
#define CREATE_INHERIT_CURRENT 0x2
#endif
#ifndef LOCAL_NS_PREFERED
#define LOCAL_NS_PREFERED 0x4
#endif

void dlns_init(Dl_namespace* ns, const char* name);
int dlns_get(const char* name, Dl_namespace* ns);
int dlns_create2(Dl_namespace* ns, const char* lib_path, int flags);
int dlns_inherit(Dl_namespace* ns, Dl_namespace* inherited, const char* shared_libs);
int dlns_set_namespace_separated(const char* name, bool separated);
int dlns_set_namespace_permitted_paths(const char* name, const char* permitted_paths);
int dlns_set_namespace_allowed_libs(const char* name, const char* allowed_libs);
void* dlopen_ns(Dl_namespace* ns, const char* file, int mode);

#ifdef __cplusplus
}
#endif

#endif
