#ifndef WESTLAKE_GENERATION_IDENTITY_FACTS_H
#define WESTLAKE_GENERATION_IDENTITY_FACTS_H

#include "sealed_child_provider_loader.h"
#include "westlake_generation_identity_producer.h"
#include "westlake_child_hook_table_v1.h"

#include <stddef.h>
#include <stdint.h>

#define WLGR_IF_ABI_VERSION UINT32_C(1)
#define WLGR_IF_METADATA_MAGIC UINT64_C(0x574c474d45544131)
#define WLGR_IF_RECEIPT_MAGIC UINT64_C(0x574c475245435031)
#define WLGR_IF_HOOK_MAGIC UINT64_C(0x574c474853434831)

typedef enum WlgrIfError {
    WLGR_IF_OK = 0,
    WLGR_IF_INVALID_ARGUMENT = 1,
    WLGR_IF_BOOT_UNAVAILABLE = 2,
    WLGR_IF_BOOT_MALFORMED = 3,
    WLGR_IF_PROCESS_MISMATCH = 4,
    WLGR_IF_METADATA_INVALID = 5,
    WLGR_IF_METADATA_MISMATCH = 6,
    WLGR_IF_RECEIPT_INVALID = 7,
    WLGR_IF_MANIFEST_INVALID = 8,
    WLGR_IF_HOOK_INVALID = 9,
    WLGR_IF_NONCE_UNAVAILABLE = 10,
    WLGR_IF_NONCE_REPLAY = 11
} WlgrIfError;

typedef struct WlgrIfChildRequest {
    uint32_t android_uid;
    uint64_t launch_generation;
    uint64_t child_pid;
    uint64_t child_proc_start_time_ticks;
    char android_package[WLGR_V2_PACKAGE_NAME_SIZE];
    char android_process_name[WLGR_V2_PROCESS_NAME_SIZE];
} WlgrIfChildRequest;

/* Immutable parent seal inherited by the specialized child. */
typedef struct WlgrIfGenerationMetadata {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    uint8_t boot_id[WLGR_V2_BOOT_ID_SIZE];
    uint8_t artifact_generation[WLGR_V2_SHA256_SIZE];
    uint64_t policy_epoch;
    uint64_t launch_generation;
    uint8_t artifact_manifest_digest[WLGR_V2_SHA256_SIZE];
    uint8_t hook_schema_digest[WLGR_V2_SHA256_SIZE];
    uint8_t policy_provenance_digest[WLGR_V2_SHA256_SIZE];
    uint8_t metadata_digest[WLGR_V2_SHA256_SIZE];
    uint32_t reserved_zero[8];
} WlgrIfGenerationMetadata;

/* Canonical fixed-width consumed specialization receipt; no pointers/padding. */
typedef struct WlgrIfSpecializationReceipt {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    westlake_runtime_instance_key_v2 runtime_key;
    uint8_t boot_id[WLGR_V2_BOOT_ID_SIZE];
    uint8_t artifact_generation[WLGR_V2_SHA256_SIZE];
    uint64_t policy_epoch;
    uint64_t child_pid;
    uint64_t child_proc_start_time_ticks;
    uint8_t stock_receipt_digest[WLGR_V2_SHA256_SIZE];
    uint32_t reserved_zero[8];
} WlgrIfSpecializationReceipt;

typedef struct WlgrIfHookContract {
    uint64_t magic;
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t capability_bitmap;
    uint16_t data_pointer_size;
    uint16_t data_pointer_alignment;
    uint16_t function_pointer_size;
    uint16_t function_pointer_alignment;
    uint8_t schema_digest[WLGR_V2_SHA256_SIZE];
    uint32_t reserved_zero[8];
} WlgrIfHookContract;

typedef int (*WlgrIfReadBootIdFn)(void *, char *, size_t);
typedef int (*WlgrIfReadProcessFn)(void *, uint64_t *, uint64_t *);
typedef int (*WlgrIfReadMetadataFn)(void *, WlgrIfGenerationMetadata *);
typedef int (*WlgrIfReadReceiptFn)(void *, WlgrIfSpecializationReceipt *);
typedef int (*WlgrIfReadManifestFn)(void *, const WlscplManifestV2 **);
typedef int (*WlgrIfReadHookFn)(void *, WlgrIfHookContract *);
typedef int (*WlgrIfRandomFn)(void *, uint8_t *, size_t);
typedef struct WlgrIfOps {
    WlgrIfReadBootIdFn read_boot_id;
    WlgrIfReadProcessFn read_process;
    WlgrIfReadMetadataFn read_metadata;
    WlgrIfReadReceiptFn read_receipt;
    WlgrIfReadManifestFn read_manifest;
    WlgrIfReadHookFn read_hook;
    WlgrIfRandomFn random_bytes;
    void *context;
} WlgrIfOps;

typedef struct WlgrIfReplayGuard {
    uint8_t nonce[WLGR_V2_NONCE_SIZE];
    uint8_t identity_digest[WLGR_V2_SHA256_SIZE];
    uint32_t consumed;
} WlgrIfReplayGuard;

WlgrIfError WlgrIfAcquire(const WlgrIfChildRequest *, const WlgrIfOps *,
                          WlgrIpSourceFacts *, WlgrIfReplayGuard *);
int WlgrIfParseBootId(const char *, uint8_t[WLGR_V2_BOOT_ID_SIZE]);
int WlgrIfDigestMetadata(const WlgrIfGenerationMetadata *,
                         uint8_t[WLGR_V2_SHA256_SIZE]);
int WlgrIfValidateMetadata(const WlgrIfGenerationMetadata *);
int WlgrIfValidateHook(const WlgrIfHookContract *);
const WlgrIfGenerationMetadata *WlgrIfGetBuildGeneratedMetadata(void);

#endif
