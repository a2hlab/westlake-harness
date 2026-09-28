#ifndef WESTLAKE_OH_SECURITY_SPECIALIZATION_H
#define WESTLAKE_OH_SECURITY_SPECIALIZATION_H

#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__) || defined(__clang__)
#define WLSS_EXPORT __attribute__((visibility("default")))
#else
#define WLSS_EXPORT
#endif

#define WLSS_ABI_VERSION UINT32_C(1)
#define WLSS_RAW_SHA256_SIZE UINT32_C(32)
#define WLSS_MAX_TLV_COUNT UINT32_C(128)
#define WLSS_MAX_FLAGS_WORDS UINT32_C(2)
#define WLSS_OH_MSG_MAGIC UINT32_C(0xef201234)
#define WLSS_OH_MSG_APP_SPAWN UINT32_C(0)
#define WLSS_OH_PROCESS_NAME_SIZE UINT32_C(256)
#define WLSS_OH_TLV_NAME_SIZE UINT32_C(32)
#define WLSS_OH_MAX_GIDS UINT32_C(64)
#define WLSS_OH_USER_NAME_SIZE UINT32_C(64)
#define WLSS_OH_APL_MAX_SIZE UINT32_C(32)
#define WLSS_OH_OWNER_MAX_SIZE UINT32_C(64)
#define WLSS_OH_BUNDLE_NAME_SIZE UINT32_C(256)
#define WLSS_OH_MAX_MESSAGE_SIZE UINT32_C(65536)

typedef enum WlssOhTlvType {
    WLSS_TLV_BUNDLE_INFO = 0,
    WLSS_TLV_MSG_FLAGS = 1,
    WLSS_TLV_DAC_INFO = 2,
    WLSS_TLV_DOMAIN_INFO = 3,
    WLSS_TLV_OWNER_INFO = 4,
    WLSS_TLV_ACCESS_TOKEN_INFO = 5,
    WLSS_TLV_PERMISSION = 6,
    WLSS_TLV_INTERNET_INFO = 7,
    WLSS_TLV_RENDER_TERMINATION_INFO = 8,
    WLSS_TLV_CHECK_POINT_INFO = 9,
    WLSS_TLV_EXT = 10
} WlssOhTlvType;

typedef enum WlssStatus {
    WLSS_STATUS_OK = 0,
    WLSS_STATUS_DENIED = 1,
    WLSS_STATUS_TERMINAL = 2,
    WLSS_STATUS_INVALID_ARGUMENT = 3
} WlssStatus;

typedef enum WlssReason {
    WLSS_REASON_NONE = 0,
    WLSS_REASON_INVALID_ARGUMENT = 1,
    WLSS_REASON_ABI_MISMATCH = 2,
    WLSS_REASON_CONFIG_REQUIRED = 3,
    WLSS_REASON_STOCK_BINDING_REQUIRED = 4,
    WLSS_REASON_RAW_IDENTITY_REJECTED = 5,
    WLSS_REASON_STOCK_IDENTITY_REJECTED = 6,
    WLSS_REASON_MESSAGE_HEADER_INVALID = 7,
    WLSS_REASON_PROCESS_NAME_INVALID = 8,
    WLSS_REASON_TLV_COUNT_INVALID = 9,
    WLSS_REASON_TLV_BOUNDS_INVALID = 10,
    WLSS_REASON_TLV_TYPE_UNSUPPORTED = 11,
    WLSS_REASON_TLV_DUPLICATE = 12,
    WLSS_REASON_REQUIRED_TLV_MISSING = 13,
    WLSS_REASON_BUNDLE_REQUIRED = 14,
    WLSS_REASON_BUNDLE_INVALID = 15,
    WLSS_REASON_FLAGS_INVALID = 16,
    WLSS_REASON_NO_SANDBOX_FORBIDDEN = 17,
    WLSS_REASON_IGNORE_SANDBOX_FORBIDDEN = 18,
    WLSS_REASON_DAC_REQUIRED = 19,
    WLSS_REASON_DAC_INVALID = 20,
    WLSS_REASON_APL_REQUIRED = 21,
    WLSS_REASON_APL_INVALID = 22,
    WLSS_REASON_TOKEN_REQUIRED = 23,
    WLSS_REASON_TOKEN_INVALID = 24,
    WLSS_REASON_OWNER_REQUIRED = 25,
    WLSS_REASON_OWNER_INVALID = 26,
    WLSS_REASON_PERMISSION_REQUIRED = 27,
    WLSS_REASON_PERMISSION_INVALID = 28,
    WLSS_REASON_INTERNET_REQUIRED = 29,
    WLSS_REASON_INTERNET_INVALID = 30,
    WLSS_REASON_EXT_INVALID = 31,
    WLSS_REASON_SEQUENCE_INVALID = 32,
    WLSS_REASON_PARENT_HOOK_FAILED = 33,
    WLSS_REASON_PARENT_RECEIPT_INVALID = 34,
    WLSS_REASON_CHILD_SANDBOX_FAILED = 35,
    WLSS_REASON_CHILD_RECEIPT_INVALID = 36,
    WLSS_REASON_RECORD_DRIFT = 37
} WlssReason;

typedef enum WlssRecordState {
    WLSS_RECORD_EMPTY = 0,
    WLSS_RECORD_PARENT_PREPARED = 1,
    WLSS_RECORD_PARENT_HOOK_RUNNING = 2,
    WLSS_RECORD_PARENT_HOOK_READY = 3,
    WLSS_RECORD_CHILD_HOOK_RUNNING = 4,
    WLSS_RECORD_CHILD_SANDBOX_READY = 5,
    WLSS_RECORD_FAILED = 6
} WlssRecordState;

typedef enum WlssStockBindingKind {
    WLSS_STOCK_BINDING_INVALID = 0,
    /* Exact OH normal-sandbox ABI owned by a same-generation OH GN wrapper. */
    WLSS_STOCK_BINDING_OH_GN_NORMAL_V7 = 1,
    /* The installed libappspawn_stub_empty alias is explicitly non-capable. */
    WLSS_STOCK_BINDING_EMPTY_STUB = 2
} WlssStockBindingKind;

typedef struct WlssTlvSpan {
    uint32_t raw_offset;
    uint32_t raw_length;
    uint32_t payload_offset;
    uint32_t payload_length;
    uint16_t type;
    uint16_t ext_data_type;
    uint32_t ext_data_length;
    char ext_name[WLSS_OH_TLV_NAME_SIZE];
} WlssTlvSpan;

/* Exact wire shapes copied from the frozen OH v7 headers. */
#pragma pack(push, 4)
typedef struct WlssOhAppSpawnMsg {
    uint32_t magic;
    uint32_t msg_type;
    uint32_t msg_len;
    uint32_t msg_id;
    uint32_t tlv_count;
    char process_name[WLSS_OH_PROCESS_NAME_SIZE];
} WlssOhAppSpawnMsg;

typedef struct WlssOhAppDacInfo {
    uint32_t uid;
    uint32_t gid;
    uint32_t gid_count;
    uint32_t gid_table[WLSS_OH_MAX_GIDS];
    char user_name[WLSS_OH_USER_NAME_SIZE];
} WlssOhAppDacInfo;
#pragma pack(pop)

typedef struct WlssParentInputs {
    uint32_t abi_version;
    uint32_t config_loaded;
    WlssStockBindingKind stock_binding_kind;
    uint32_t full_module_engine_present;
    uint64_t adapter_generation;
    uint64_t config_generation;
    const uint8_t *raw_message;
    uint32_t raw_message_size;
    uint32_t reserved_zero;
    uint8_t raw_message_sha256[WLSS_RAW_SHA256_SIZE];
    uint8_t config_sha256[WLSS_RAW_SHA256_SIZE];
    uint8_t sandbox_dso_sha256[WLSS_RAW_SHA256_SIZE];
    uint8_t module_engine_sha256[WLSS_RAW_SHA256_SIZE];
} WlssParentInputs;

typedef struct WlssSecurityRecordV1 {
    uint32_t abi_version;
    _Atomic uint32_t state;
    uint32_t last_reason;
    WlssStockBindingKind stock_binding_kind;
    uint64_t adapter_generation;
    uint64_t config_generation;
    const uint8_t *raw_message;
    uint32_t raw_message_size;
    uint32_t tlv_count;
    uint32_t standard_presence_bitmap;
    uint32_t extension_count;
    uint32_t flags_word_count;
    uint32_t flags_words[WLSS_MAX_FLAGS_WORDS];
    uint32_t required_span_index[8];
    uint8_t raw_message_sha256[WLSS_RAW_SHA256_SIZE];
    uint8_t config_sha256[WLSS_RAW_SHA256_SIZE];
    uint8_t sandbox_dso_sha256[WLSS_RAW_SHA256_SIZE];
    uint8_t module_engine_sha256[WLSS_RAW_SHA256_SIZE];
    WlssTlvSpan spans[WLSS_MAX_TLV_COUNT];
} WlssSecurityRecordV1;

typedef struct WlssStockParentReceipt {
    uint32_t abi_version;
    uint32_t stage;
    uint32_t hook_priority_start;
    int32_t stock_result;
    uint32_t config_preloaded;
    uint32_t all_parent_hooks_completed;
    uint32_t shared_mount_completed;
    uint32_t bypass_used;
    uint64_t adapter_generation;
    uint64_t config_generation;
} WlssStockParentReceipt;

typedef struct WlssStockChildReceipt {
    uint32_t abi_version;
    uint32_t stage;
    uint32_t hook_priority_start;
    int32_t stock_result;
    uint32_t sandbox_applied;
    uint32_t no_sandbox_used;
    uint32_t ignore_sandbox_result_used;
    uint32_t reserved_zero;
    uint64_t adapter_generation;
    uint64_t config_generation;
} WlssStockChildReceipt;

typedef int (*WlssVerifyRawIdentity)(void *context, const uint8_t *raw,
                                    uint32_t raw_size,
                                    const uint8_t expected_sha256[32]);
typedef int (*WlssVerifyStockBinding)(void *context,
                                     const WlssParentInputs *inputs);
typedef int (*WlssExecuteParentPreFork)(
    void *context, const WlssSecurityRecordV1 *record,
    WlssStockParentReceipt *out_receipt);
typedef int (*WlssExecuteChildSandbox)(
    void *context, const WlssSecurityRecordV1 *record,
    WlssStockChildReceipt *out_receipt);

typedef struct WlssStockOps {
    uint32_t abi_version;
    uint32_t reserved_zero;
    void *context;
    WlssVerifyRawIdentity verify_raw_identity;
    WlssVerifyStockBinding verify_stock_binding;
    WlssExecuteParentPreFork execute_parent_pre_fork;
    WlssExecuteChildSandbox execute_child_sandbox;
} WlssStockOps;

typedef struct WlssResult {
    WlssStatus status;
    WlssReason reason;
    WlssRecordState state;
    uint32_t reserved_zero;
} WlssResult;

WLSS_EXPORT WlssResult WLSS_ParentPrepare(
    const WlssParentInputs *inputs, const WlssStockOps *ops,
    WlssSecurityRecordV1 *out_record);

WLSS_EXPORT WlssResult WLSS_ParentPreFork(
    WlssSecurityRecordV1 *record, const WlssStockOps *ops,
    WlssStockParentReceipt *out_receipt);

WLSS_EXPORT WlssResult WLSS_ChildExecute(
    WlssSecurityRecordV1 *record, const WlssStockOps *ops,
    WlssStockChildReceipt *out_receipt);

WLSS_EXPORT const WlssTlvSpan *WLSS_GetTlvSpan(
    const WlssSecurityRecordV1 *record, uint32_t index);

WLSS_EXPORT const char *WLSS_ReasonString(WlssReason reason);

#ifdef __cplusplus
}
#endif

#endif
