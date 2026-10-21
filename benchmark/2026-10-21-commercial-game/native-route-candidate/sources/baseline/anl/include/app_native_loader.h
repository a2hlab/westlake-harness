#ifndef WESTLAKE_APP_NATIVE_LOADER_H
#define WESTLAKE_APP_NATIVE_LOADER_H

#include "oh_dlns_abi.h"
#include "westlake_bionic_pthread_bridge.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__)
#define ANL_API __attribute__((visibility("default")))
#else
#define ANL_API
#endif

typedef struct AnlDomain AnlDomain;

#define ANL_RUNTIME_GATE_ABI_VERSION 1U
#define ANL_NAMESPACE_HOST_OPS_ABI_VERSION 1U

typedef int (*AnlVerifyCurrentThreadReady)(void* context);

/*
 * Target OH musl authorizes dlns_* by the direct caller address.  Route-A
 * providers execute in westlake.sealed.child, which is intentionally not a
 * privileged namespace owner.  These two callbacks therefore remain owned by
 * the stock appspawn-x executable in the default namespace and are inherited
 * across fork as a generation-bound function table.
 */
typedef int (*AnlCreateConfiguredNamespacesV1)(
    Dl_namespace* bridge_namespace, const char* bridge_name,
    const char* bridge_search_paths, const char* bridge_permitted_paths,
    const char* bridge_shared_sonames, const char* bridge_bootstrap_soname,
    const WlpbHostOpsV1* pthread_bridge_ops,
    void** out_bridge_bootstrap_handle, Dl_namespace* app_namespace,
    const char* app_name, const char* app_search_paths,
    const char* app_permitted_paths);

typedef void* (*AnlOpenNamespaceV1)(Dl_namespace* app_namespace,
                                    const char* path, int mode);

typedef struct AnlNamespaceHostOpsV1 {
    unsigned int abi_version;
    unsigned int struct_size;
    uint64_t runtime_generation;
    AnlCreateConfiguredNamespacesV1 create_configured_namespaces;
    AnlOpenNamespaceV1 open_namespace;
    unsigned int reserved_zero[4];
} AnlNamespaceHostOpsV1;

typedef struct AnlRuntimeGateV1 {
    unsigned int abi_version;
    unsigned int struct_size;
    void* context;
    AnlVerifyCurrentThreadReady verify_current_thread_ready;
    WlpbHostOpsV1 pthread_bridge_ops;
    AnlNamespaceHostOpsV1 namespace_host_ops;
    unsigned int reserved_zero[4];
} AnlRuntimeGateV1;

typedef struct AnlDomainConfig {
    const char* app_search_paths;
    const char* app_permitted_paths;
    const char* bridge_search_paths;
    const char* bridge_permitted_paths;
    const char* bridge_shared_sonames;
    const char* bridge_bootstrap_soname;
} AnlDomainConfig;

/* One-shot parent injection inherited by children before any domain exists. */
ANL_API int ANL_InstallRuntimeGate(const AnlRuntimeGateV1* gate);
ANL_API int ANL_CreateDomain(const AnlDomainConfig* config, AnlDomain** out_domain);
ANL_API void* ANL_Dlopen(AnlDomain* domain, const char* path, int mode);
ANL_API void* ANL_Dlsym(void* handle, const char* symbol);
ANL_API int ANL_Dlclose(void* handle);
ANL_API const char* ANL_Dlerror(void);

/* CORE-006 typed load-error codes.  Every ANL_Dlopen failure diagnostic
 * returned by ANL_Dlerror() starts with exactly one of these tokens followed
 * by the target path and the raw linker text (which carries the failing
 * SONAME, ELF machine or symbol), so callers classify without re-parsing
 * free-form linker output.  The returned pointer borrows a thread-local
 * buffer: callers must read it immediately and must not hold it across
 * further loader calls. */
#define ANL_LOAD_ERROR_MISSING_DEPENDENCY "F02-A12-MISSING-DEPENDENCY"
#define ANL_LOAD_ERROR_ABI_MISMATCH "F02-A12-ABI-MISMATCH"
#define ANL_LOAD_ERROR_UNSUPPORTED_SYMBOL "F02-A12-UNSUPPORTED-SYMBOL"
#define ANL_LOAD_ERROR_UNCLASSIFIED "F02-A12-UNCLASSIFIED"
ANL_API const char* ANL_GetNamespaceName(const AnlDomain* domain);

/* OH exposes no namespace destruction API. Use only during process teardown. */
ANL_API void ANL_ReleaseDomainHandle(AnlDomain* domain);

#ifdef __cplusplus
}
#endif

#endif
