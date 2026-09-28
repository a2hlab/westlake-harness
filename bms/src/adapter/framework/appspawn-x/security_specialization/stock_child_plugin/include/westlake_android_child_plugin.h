#ifndef WESTLAKE_ANDROID_CHILD_PLUGIN_H
#define WESTLAKE_ANDROID_CHILD_PLUGIN_H

#include <stddef.h>
#include <stdint.h>

#include "native_compat_prepare.h"

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__) || defined(__clang__)
#define WLASC_EXPORT __attribute__((visibility("default")))
#else
#define WLASC_EXPORT
#endif

#define WLASC_ABI_VERSION UINT32_C(1)
#define WLASC_SHA256_SIZE UINT32_C(32)
#define WLASC_PROCESS_NAME_SIZE UINT32_C(256)
#define WLASC_BUNDLE_NAME_SIZE UINT32_C(256)
#define WLASC_APL_SIZE UINT32_C(32)
#define WLASC_OWNER_SIZE UINT32_C(64)
#define WLASC_MAX_GIDS UINT32_C(64)
#define WLASC_FLAGS_WORDS UINT32_C(2)
#define WLASC_PARENT_STAGE UINT32_C(20)
#define WLASC_CHILD_STAGE UINT32_C(31)
#define WLASC_TAIL_PRIORITY UINT32_C(6000)
#define WLASC_PRELOAD_PRIORITY UINT32_C(3001)
#define WLASC_FLAG_NO_SANDBOX UINT32_C(7)
#define WLASC_FLAG_IGNORE_SANDBOX UINT32_C(13)
#define WLASC_HOST_SERVICES_ABI_VERSION UINT32_C(1)

typedef int (*WlascCreateConfiguredNamespacesV1)(
    void *bridge_namespace, const char *bridge_name,
    const char *bridge_search_paths, const char *bridge_permitted_paths,
    const char *bridge_shared_sonames, const char *bridge_bootstrap_soname,
    const WlpbHostOpsV1 *pthread_bridge_ops,
    void **out_bridge_bootstrap_handle, void *app_namespace,
    const char *app_name, const char *app_search_paths,
    const char *app_permitted_paths);

typedef void *(*WlascOpenNamespaceV1)(void *app_namespace,
                                      const char *path, int mode);

typedef enum WlascReceiptState {
    WLASC_RECEIPT_EMPTY = 0,
    WLASC_RECEIPT_PARENT_TAIL = 1,
    WLASC_RECEIPT_BYPASS_GUARD = 2,
    WLASC_RECEIPT_CHILD_TAIL = 3,
    WLASC_RECEIPT_CONSUMED = 4,
    WLASC_RECEIPT_FAILED = 5
} WlascReceiptState;

typedef enum WlascReason {
    WLASC_REASON_NONE = 0,
    WLASC_REASON_INVALID_ARGUMENT = 1,
    WLASC_REASON_RUNTIME_NOT_READY = 2,
    WLASC_REASON_SEQUENCE_INVALID = 3,
    WLASC_REASON_CLIENT_MISMATCH = 4,
    WLASC_REASON_REQUIRED_SECURITY_TLV_MISSING = 5,
    WLASC_REASON_NO_SANDBOX_FORBIDDEN = 6,
    WLASC_REASON_IGNORE_SANDBOX_FORBIDDEN = 7,
    WLASC_REASON_REPLAY = 8,
    WLASC_REASON_REQUEST_INVALID = 9,
    WLASC_REASON_RUNTIME_FAILED = 10,
    WLASC_REASON_STOCK_REGISTRATION_FAILED = 11,
    WLASC_REASON_SERVICE_IDENTITY_REJECTED = 12,
    WLASC_REASON_RUNTIME_RECEIPT_INVALID = 13,
    WLASC_REASON_ZYGOTE_PREFORK_FAILED = 14,
    WLASC_REASON_ZYGOTE_PARENT_RECOVERY_FAILED = 15
} WlascReason;

/*
 * Internal COW ledger. client_cookie is used only inside the OH-owned plugin
 * to bind the parent and child callbacks to one inherited AppSpawnClient.
 * It is never passed to the Android runtime provider.
 */
typedef struct WlascStageLedgerV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    WlascReceiptState state;
    WlascReason last_reason;
    uint64_t runtime_generation;
    uint64_t client_cookie;
    uint32_t message_id;
    uint32_t parent_stage;
    uint32_t parent_tail_priority;
    uint32_t child_stage;
    uint32_t child_tail_priority;
    uint32_t bypass_guard_passed;
    uint32_t reserved_zero;
} WlascStageLedgerV1;

/* Pointer-free proof passed to the Android runtime provider. */
typedef struct WlascStockStageReceiptV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t runtime_generation;
    uint32_t message_id;
    uint32_t parent_stage_tail_reached;
    uint32_t child_stage_tail_reached;
    uint32_t bypass_guard_passed;
    uint32_t security_owner_stock_appspawn;
    uint32_t parent_tail_priority;
    uint32_t child_tail_priority;
    uint32_t reserved_zero[2];
} WlascStockStageReceiptV1;

/*
 * Only fixed C values cross from OH appspawn into the Android runtime owner.
 * Security objects and raw OH pointers do not cross this ABI.
 */
typedef struct WlascAndroidChildRequestV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t message_type;
    uint32_t message_id;
    uint64_t runtime_generation;
    uint32_t uid;
    uint32_t gid;
    uint32_t gid_count;
    uint32_t gids[WLASC_MAX_GIDS];
    uint64_t access_token_id_ex;
    uint32_t hap_flags;
    uint32_t flags_word_count;
    uint32_t flags_words[WLASC_FLAGS_WORDS];
    uint8_t set_allow_internet;
    uint8_t allow_internet;
    uint8_t reserved_bytes[2];
    char process_name[WLASC_PROCESS_NAME_SIZE];
    char bundle_name[WLASC_BUNDLE_NAME_SIZE];
    char apl[WLASC_APL_SIZE];
    char owner_id[WLASC_OWNER_SIZE];
} WlascAndroidChildRequestV1;

/* The runtime provider must explicitly declare that it performed no security. */
typedef struct WlascRuntimePreloadReceiptV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t runtime_ready;
    uint32_t security_operations_mask;
    uint64_t runtime_generation;
    uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE];
} WlascRuntimePreloadReceiptV1;

/* Read-only provider identity available before any ART preload side effect. */
typedef struct WlascRuntimeIdentityV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t runtime_generation;
    uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE];
    uint32_t reserved_zero[4];
} WlascRuntimeIdentityV1;

/*
 * MAIN-owned native-compat services installed once after a provider preload
 * receipt is validated. The provider copies this fixed table by value; it
 * never retains the caller's table pointer or any opaque object pointer.
 */
typedef struct WlascHostRuntimeServicesV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t runtime_generation;
    uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE];
    uint64_t (*current_thread_token)(void);
    int (*prepare_parent_runtime)(const WlncParentIdentityV1 *identity);
    int (*verify_parent_preload_thread_ready)(uint64_t runtime_generation);
    int (*prepare_main_thread)(const WlncProcessIdentityV1 *identity);
    int (*verify_current_thread_ready)(void);
    int (*get_audit_snapshot)(WlncAuditSnapshotV1 *out_snapshot);
    int (*get_pthread_bridge_ops)(WlpbHostOpsV1 *out_ops);
    void *(*open_sealed_exact)(const char *absolute_path, int flags);
    WlascCreateConfiguredNamespacesV1 create_configured_namespaces;
    WlascOpenNamespaceV1 open_namespace;
} WlascHostRuntimeServicesV1;

typedef struct WlascContractV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t preload_priority;
    uint32_t parent_stage;
    uint32_t child_stage;
    uint32_t tail_priority;
    uint32_t no_sandbox_flag_index;
    uint32_t ignore_sandbox_flag_index;
    uint32_t stock_security_owner_required;
    uint32_t runtime_security_operations_required_zero;
    uint32_t request_size;
    uint32_t receipt_size;
} WlascContractV1;

WLASC_EXPORT const WlascContractV1 *WLASC_GetContractV1(void);

WlascReason WLASC_ReceiptParentTail(
    WlascStageLedgerV1 *ledger, uint64_t runtime_generation,
    uint64_t client_cookie, uint32_t message_id);

WlascReason WLASC_ReceiptBypassGuard(
    WlascStageLedgerV1 *ledger, uint64_t client_cookie,
    uint32_t required_security_tlvs_present, uint32_t no_sandbox,
    uint32_t ignore_sandbox);

WlascReason WLASC_ReceiptChildTail(
    WlascStageLedgerV1 *ledger, uint64_t client_cookie);

WlascReason WLASC_ReceiptConsume(
    WlascStageLedgerV1 *ledger, uint64_t client_cookie,
    WlascStockStageReceiptV1 *out_receipt);

/* Exact missing runtime-provider edge for the production stock host. */
int WLAR_GetRuntimeIdentity(WlascRuntimeIdentityV1 *out_identity);
int WLAR_ServerPreload(WlascRuntimePreloadReceiptV1 *out_receipt);
int WLAR_InstallHostRuntimeServices(
    const WlascHostRuntimeServicesV1 *services);
int WLAR_ZygotePreFork(uint64_t runtime_generation);
int WLAR_ZygotePostForkParent(uint64_t runtime_generation);
int WLAR_EnterAndroidAfterStockSpecialization(
    const WlascAndroidChildRequestV1 *request,
    const WlascStockStageReceiptV1 *stock_receipt);

#ifdef __cplusplus
}
#endif

#endif
