#ifndef WESTLAKE_STOCK_HOST_SERVICES_H
#define WESTLAKE_STOCK_HOST_SERVICES_H

#include "westlake_android_child_plugin.h"

/* Exact project-local OH appspawn hook/message types. */
#include "appspawn_hook.h"
#include "appspawn_manager.h"

#ifdef __cplusplus
extern "C" {
#endif

#define WLASC_STOCK_HOST_SERVICES_ABI_VERSION UINT32_C(1)
#define WLASC_BUILD_ID_SIZE UINT32_C(20)

typedef struct WlascStockHostServicesV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t runtime_generation;
    uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE];
    uint8_t plugin_generation_sha256[WLASC_SHA256_SIZE];
    uint8_t plugin_elf_sha256[WLASC_SHA256_SIZE];
    uint8_t plugin_build_id[WLASC_BUILD_ID_SIZE];
    uint32_t reserved_identity_zero;

    int (*add_server_stage_hook)(AppSpawnHookStage stage, int priority,
                                 ServerStageHook hook);
    int (*add_app_spawn_hook)(AppSpawnHookStage stage, int priority,
                              AppSpawnHook hook);
    void *(*get_app_spawn_msg_info)(const AppSpawnMsgNode *message,
                                    int type);
    int (*check_app_spawn_msg_flag)(const AppSpawnMsgNode *message,
                                    uint32_t type, uint32_t index);
    void (*reg_child_looper)(AppSpawnContent *content, ChildLoop loop);
    void (*clear_child_environment)(AppSpawnContent *content,
                                    AppSpawnClient *client);

    uint64_t (*current_thread_token)(void);
    int (*prepare_parent_runtime)(const WlncParentIdentityV1 *identity);
    int (*verify_parent_preload_thread_ready)(uint64_t runtime_generation);
    int (*prepare_main_thread)(const WlncProcessIdentityV1 *identity);
    int (*verify_current_thread_ready)(void);
    int (*get_audit_snapshot)(WlncAuditSnapshotV1 *out_snapshot);
    int (*get_pthread_bridge_ops)(WlpbHostOpsV1 *out_ops);
    WlascCreateConfiguredNamespacesV1 create_configured_namespaces;
    WlascOpenNamespaceV1 open_namespace;
} WlascStockHostServicesV1;

/* MAIN calls this exactly once after stock ModuleMgr loads the inert DSO. */
WLASC_EXPORT int WLASC_InstallStockHostServicesV1(
    const WlascStockHostServicesV1 *services);

#ifdef __cplusplus
}
#endif

#endif
