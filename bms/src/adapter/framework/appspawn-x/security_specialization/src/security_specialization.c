#include "westlake_oh_security_specialization.h"

#include <stdbool.h>

#define WLSS_REQUIRED_SECURITY_BITMAP UINT32_C(0x000000ff)
#define WLSS_PARENT_PRE_FORK_STAGE UINT32_C(20)
#define WLSS_CHILD_EXECUTE_STAGE UINT32_C(31)
#define WLSS_HOOK_PRIORITY_FROM_START UINT32_C(0)
#define WLSS_FLAG_NO_SANDBOX UINT32_C(7)
#define WLSS_FLAG_IGNORE_SANDBOX UINT32_C(13)

_Static_assert(sizeof(WlssOhAppSpawnMsg) == 276,
               "OH AppSpawnMsg wire ABI drift");
_Static_assert(sizeof(WlssOhAppDacInfo) == 332,
               "OH AppDacInfo wire ABI drift");
_Static_assert(sizeof(_Atomic uint32_t) == sizeof(uint32_t),
               "record state ABI drift");

static uint16_t Load16(const uint8_t *bytes)
{
    return (uint16_t)((uint16_t)bytes[0] |
                      ((uint16_t)bytes[1] << 8));
}

static uint32_t Load32(const uint8_t *bytes)
{
    return (uint32_t)bytes[0] |
           ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) |
           ((uint32_t)bytes[3] << 24);
}

static uint64_t Load64(const uint8_t *bytes)
{
    return (uint64_t)Load32(bytes) |
           ((uint64_t)Load32(bytes + 4) << 32);
}

static bool BytesAllZero(const uint8_t *bytes, size_t size)
{
    uint8_t value = UINT8_C(0);
    size_t index;
    for (index = 0; index < size; ++index) {
        value = (uint8_t)(value | bytes[index]);
    }
    return value == UINT8_C(0);
}

static bool BytesEqual(const uint8_t *left, const uint8_t *right, size_t size)
{
    uint8_t difference = UINT8_C(0);
    size_t index;
    for (index = 0; index < size; ++index) {
        difference =
            (uint8_t)(difference | (uint8_t)(left[index] ^ right[index]));
    }
    return difference == UINT8_C(0);
}

static void CopyBytes(uint8_t *destination, const uint8_t *source, size_t size)
{
    size_t index;
    for (index = 0; index < size; ++index) {
        destination[index] = source[index];
    }
}

static void ZeroBytes(void *memory, size_t size)
{
    uint8_t *bytes = (uint8_t *)memory;
    size_t index;
    for (index = 0; index < size; ++index) {
        bytes[index] = UINT8_C(0);
    }
}

static bool HasNul(const uint8_t *bytes, uint32_t size,
                   uint32_t *out_string_length)
{
    uint32_t index;
    for (index = 0; index < size; ++index) {
        if (bytes[index] == UINT8_C(0)) {
            if (out_string_length != (uint32_t *)0) {
                *out_string_length = index;
            }
            return true;
        }
    }
    return false;
}

static WlssRecordState LoadState(const WlssSecurityRecordV1 *record)
{
    if (record == (const WlssSecurityRecordV1 *)0) {
        return WLSS_RECORD_EMPTY;
    }
    return (WlssRecordState)atomic_load_explicit(&record->state,
                                                 memory_order_acquire);
}

static WlssResult Result(WlssStatus status, WlssReason reason,
                         const WlssSecurityRecordV1 *record)
{
    WlssResult result;
    result.status = status;
    result.reason = reason;
    result.state = LoadState(record);
    result.reserved_zero = UINT32_C(0);
    return result;
}

static WlssResult FailRecord(WlssSecurityRecordV1 *record, WlssReason reason)
{
    if (record != (WlssSecurityRecordV1 *)0) {
        record->last_reason = (uint32_t)reason;
        atomic_store_explicit(&record->state, (uint32_t)WLSS_RECORD_FAILED,
                              memory_order_release);
    }
    return Result(WLSS_STATUS_TERMINAL, reason, record);
}

static bool FlagSet(const WlssSecurityRecordV1 *record, uint32_t index)
{
    uint32_t word = index / UINT32_C(32);
    uint32_t bit = index % UINT32_C(32);
    if (word >= record->flags_word_count || word >= WLSS_MAX_FLAGS_WORDS) {
        return false;
    }
    return (record->flags_words[word] & (UINT32_C(1) << bit)) != 0U;
}

static WlssReason ValidateStringTlv(const WlssSecurityRecordV1 *record,
                                    uint32_t span_index,
                                    uint32_t prefix_size,
                                    uint32_t maximum_size,
                                    WlssReason missing_reason,
                                    WlssReason invalid_reason)
{
    const WlssTlvSpan *span;
    uint32_t string_length = 0;
    if (span_index >= record->tlv_count) {
        return missing_reason;
    }
    span = &record->spans[span_index];
    if (span->payload_length <= prefix_size ||
        !HasNul(record->raw_message + span->payload_offset + prefix_size,
                span->payload_length - prefix_size, &string_length) ||
        string_length == UINT32_C(0) || string_length >= maximum_size) {
        return invalid_reason;
    }
    return WLSS_REASON_NONE;
}

static WlssReason ValidateSecurityTlvs(WlssSecurityRecordV1 *record)
{
    const WlssTlvSpan *span;
    const uint8_t *payload;
    uint32_t count;
    uint32_t index;
    WlssReason reason;

    if ((record->standard_presence_bitmap & WLSS_REQUIRED_SECURITY_BITMAP) !=
        WLSS_REQUIRED_SECURITY_BITMAP) {
        return WLSS_REASON_REQUIRED_TLV_MISSING;
    }

    reason = ValidateStringTlv(
        record, record->required_span_index[WLSS_TLV_BUNDLE_INFO], 4,
        WLSS_OH_BUNDLE_NAME_SIZE, WLSS_REASON_BUNDLE_REQUIRED,
        WLSS_REASON_BUNDLE_INVALID);
    if (reason != WLSS_REASON_NONE) {
        return reason;
    }

    /* TLV_MSG_FLAGS: count + complete 64-bit OH flag bitmap. */
    span = &record->spans[record->required_span_index[WLSS_TLV_MSG_FLAGS]];
    payload = record->raw_message + span->payload_offset;
    if (span->payload_length < UINT32_C(8)) {
        return WLSS_REASON_FLAGS_INVALID;
    }
    count = Load32(payload);
    if (count != WLSS_MAX_FLAGS_WORDS ||
        UINT32_C(4) + count * UINT32_C(4) > span->payload_length) {
        return WLSS_REASON_FLAGS_INVALID;
    }
    record->flags_word_count = count;
    for (index = 0; index < count; ++index) {
        record->flags_words[index] = Load32(payload + 4 + index * 4);
    }
#if !defined(WLSS_MUTANT_ALLOW_NO_SANDBOX)
    if (FlagSet(record, WLSS_FLAG_NO_SANDBOX)) {
        return WLSS_REASON_NO_SANDBOX_FORBIDDEN;
    }
#endif
    if (FlagSet(record, WLSS_FLAG_IGNORE_SANDBOX)) {
        return WLSS_REASON_IGNORE_SANDBOX_FORBIDDEN;
    }

    /* Full packed AppDacInfo must remain available to the stock decoder. */
    span = &record->spans[record->required_span_index[WLSS_TLV_DAC_INFO]];
    if (span->payload_length < sizeof(WlssOhAppDacInfo)) {
#if defined(WLSS_MUTANT_ALLOW_MISSING_DAC)
        (void)span;
#else
        return WLSS_REASON_DAC_REQUIRED;
#endif
    } else {
        payload = record->raw_message + span->payload_offset;
        if (Load32(payload + 8) > WLSS_OH_MAX_GIDS ||
            !HasNul(payload + 12 + WLSS_OH_MAX_GIDS * 4,
                    WLSS_OH_USER_NAME_SIZE, (uint32_t *)0)) {
            return WLSS_REASON_DAC_INVALID;
        }
    }

    reason = ValidateStringTlv(
        record, record->required_span_index[WLSS_TLV_DOMAIN_INFO], 4,
        WLSS_OH_APL_MAX_SIZE, WLSS_REASON_APL_REQUIRED,
        WLSS_REASON_APL_INVALID);
    if (reason != WLSS_REASON_NONE) {
        return reason;
    }

    span = &record->spans[
        record->required_span_index[WLSS_TLV_ACCESS_TOKEN_INFO]];
    if (span->payload_length < UINT32_C(8)) {
#if !defined(WLSS_MUTANT_ALLOW_MISSING_TOKEN)
        return WLSS_REASON_TOKEN_REQUIRED;
#endif
    } else if (Load64(record->raw_message + span->payload_offset) ==
               UINT64_C(0)) {
        return WLSS_REASON_TOKEN_INVALID;
    }

    reason = ValidateStringTlv(
        record, record->required_span_index[WLSS_TLV_OWNER_INFO], 0,
        WLSS_OH_OWNER_MAX_SIZE, WLSS_REASON_OWNER_REQUIRED,
        WLSS_REASON_OWNER_INVALID);
    if (reason != WLSS_REASON_NONE) {
        return reason;
    }

    span = &record->spans[record->required_span_index[WLSS_TLV_PERMISSION]];
    payload = record->raw_message + span->payload_offset;
    if (span->payload_length < UINT32_C(8)) {
        return WLSS_REASON_PERMISSION_REQUIRED;
    }
    count = Load32(payload);
    if (count == UINT32_C(0) ||
        count > (span->payload_length - UINT32_C(4)) / UINT32_C(4)) {
        return WLSS_REASON_PERMISSION_INVALID;
    }

    span = &record->spans[record->required_span_index[WLSS_TLV_INTERNET_INFO]];
    payload = record->raw_message + span->payload_offset;
    if (span->payload_length < UINT32_C(4)) {
        return WLSS_REASON_INTERNET_REQUIRED;
    }
    if (payload[0] > UINT8_C(1) || payload[1] > UINT8_C(1) ||
        payload[2] != UINT8_C(0) || payload[3] != UINT8_C(0)) {
        return WLSS_REASON_INTERNET_INVALID;
    }
    return WLSS_REASON_NONE;
}

static WlssReason ParseRawMessage(const WlssParentInputs *inputs,
                                  WlssSecurityRecordV1 *record)
{
    const uint8_t *raw = inputs->raw_message;
    uint32_t raw_size = inputs->raw_message_size;
    uint32_t tlv_count;
    uint32_t offset;
    uint32_t index;
    uint32_t process_name_length = 0;

    if (raw == (const uint8_t *)0 ||
        raw_size < sizeof(WlssOhAppSpawnMsg) ||
        raw_size > WLSS_OH_MAX_MESSAGE_SIZE ||
        Load32(raw) != WLSS_OH_MSG_MAGIC ||
        Load32(raw + 4) != WLSS_OH_MSG_APP_SPAWN ||
        Load32(raw + 8) != raw_size) {
        return WLSS_REASON_MESSAGE_HEADER_INVALID;
    }
    if (!HasNul(raw + 20, WLSS_OH_PROCESS_NAME_SIZE,
                &process_name_length) ||
        process_name_length == UINT32_C(0)) {
        return WLSS_REASON_PROCESS_NAME_INVALID;
    }
    tlv_count = Load32(raw + 16);
    if (tlv_count == UINT32_C(0) || tlv_count > WLSS_MAX_TLV_COUNT) {
        return WLSS_REASON_TLV_COUNT_INVALID;
    }

    record->raw_message = raw;
    record->raw_message_size = raw_size;
    record->tlv_count = tlv_count;
    for (index = 0; index < 8; ++index) {
        record->required_span_index[index] = UINT32_MAX;
    }

    offset = (uint32_t)sizeof(WlssOhAppSpawnMsg);
    for (index = 0; index < tlv_count; ++index) {
        WlssTlvSpan *span = &record->spans[index];
        uint32_t tlv_length;
        uint16_t type;
        if (offset > raw_size - UINT32_C(4)) {
            return WLSS_REASON_TLV_BOUNDS_INVALID;
        }
        tlv_length = (uint32_t)Load16(raw + offset);
        type = Load16(raw + offset + 2);
        if (tlv_length < UINT32_C(4) || (tlv_length & UINT32_C(3)) != 0U ||
            tlv_length > raw_size - offset) {
            return WLSS_REASON_TLV_BOUNDS_INVALID;
        }
        span->raw_offset = offset;
        span->raw_length = tlv_length;
        span->type = type;
        span->payload_offset = offset + UINT32_C(4);
        span->payload_length = tlv_length - UINT32_C(4);

        if (type < WLSS_TLV_EXT) {
            uint32_t bit = UINT32_C(1) << type;
            if ((record->standard_presence_bitmap & bit) != 0U) {
                return WLSS_REASON_TLV_DUPLICATE;
            }
            record->standard_presence_bitmap |= bit;
            if (type < 8) {
                record->required_span_index[type] = index;
            }
        } else if (type == WLSS_TLV_EXT) {
            uint32_t name_length = 0;
            uint32_t ext_data_length;
            uint32_t name_index;
            if (tlv_length < UINT32_C(40)) {
                return WLSS_REASON_EXT_INVALID;
            }
            ext_data_length = (uint32_t)Load16(raw + offset + 4);
            if (ext_data_length > tlv_length - UINT32_C(40) ||
                !HasNul(raw + offset + 8, WLSS_OH_TLV_NAME_SIZE,
                        &name_length) || name_length == UINT32_C(0)) {
                return WLSS_REASON_EXT_INVALID;
            }
            span->payload_offset = offset + UINT32_C(40);
            span->payload_length = ext_data_length;
            span->ext_data_length = ext_data_length;
            span->ext_data_type = Load16(raw + offset + 6);
            for (name_index = 0; name_index < WLSS_OH_TLV_NAME_SIZE;
                 ++name_index) {
                span->ext_name[name_index] =
                    (char)raw[offset + 8 + name_index];
            }
            record->extension_count += UINT32_C(1);
        } else {
            return WLSS_REASON_TLV_TYPE_UNSUPPORTED;
        }
        offset += tlv_length;
    }
    if (offset != raw_size) {
        return WLSS_REASON_TLV_BOUNDS_INVALID;
    }
    return ValidateSecurityTlvs(record);
}

static bool SameRecordShape(const WlssSecurityRecordV1 *left,
                            const WlssSecurityRecordV1 *right)
{
    uint32_t index;
    if (left->raw_message != right->raw_message ||
        left->raw_message_size != right->raw_message_size ||
        left->tlv_count != right->tlv_count ||
        left->standard_presence_bitmap != right->standard_presence_bitmap ||
        left->extension_count != right->extension_count ||
        left->flags_word_count != right->flags_word_count ||
        !BytesEqual(left->raw_message_sha256, right->raw_message_sha256,
                    WLSS_RAW_SHA256_SIZE)) {
        return false;
    }
    for (index = 0; index < left->flags_word_count; ++index) {
        if (left->flags_words[index] != right->flags_words[index]) {
            return false;
        }
    }
    for (index = 0; index < left->tlv_count; ++index) {
        if (left->spans[index].raw_offset != right->spans[index].raw_offset ||
            left->spans[index].raw_length != right->spans[index].raw_length ||
            left->spans[index].payload_offset !=
                right->spans[index].payload_offset ||
            left->spans[index].payload_length !=
                right->spans[index].payload_length ||
            left->spans[index].type != right->spans[index].type ||
            left->spans[index].ext_data_type !=
                right->spans[index].ext_data_type ||
            left->spans[index].ext_data_length !=
                right->spans[index].ext_data_length ||
            !BytesEqual((const uint8_t *)left->spans[index].ext_name,
                        (const uint8_t *)right->spans[index].ext_name,
                        WLSS_OH_TLV_NAME_SIZE)) {
            return false;
        }
    }
    for (index = 0; index < 8; ++index) {
        if (left->required_span_index[index] !=
            right->required_span_index[index]) {
            return false;
        }
    }
    return true;
}

static bool OpsValid(const WlssStockOps *ops)
{
    return ops != (const WlssStockOps *)0 &&
           ops->abi_version == WLSS_ABI_VERSION &&
           ops->reserved_zero == UINT32_C(0) &&
           ops->verify_raw_identity != (WlssVerifyRawIdentity)0 &&
           ops->verify_stock_binding != (WlssVerifyStockBinding)0 &&
           ops->execute_parent_pre_fork != (WlssExecuteParentPreFork)0 &&
           ops->execute_child_sandbox != (WlssExecuteChildSandbox)0;
}

static WlssReason RevalidateRecord(const WlssSecurityRecordV1 *record,
                                   const WlssStockOps *ops)
{
    WlssParentInputs inputs;
    WlssSecurityRecordV1 reparsed;
    WlssReason parse_reason;
    if (ops->verify_raw_identity(ops->context, record->raw_message,
                                 record->raw_message_size,
                                 record->raw_message_sha256) != 1) {
        return WLSS_REASON_RAW_IDENTITY_REJECTED;
    }
    ZeroBytes(&inputs, sizeof(inputs));
    inputs.abi_version = WLSS_ABI_VERSION;
    inputs.config_loaded = UINT32_C(1);
    inputs.stock_binding_kind = record->stock_binding_kind;
    inputs.full_module_engine_present = UINT32_C(1);
    inputs.adapter_generation = record->adapter_generation;
    inputs.config_generation = record->config_generation;
    inputs.raw_message = record->raw_message;
    inputs.raw_message_size = record->raw_message_size;
    CopyBytes(inputs.raw_message_sha256, record->raw_message_sha256,
              WLSS_RAW_SHA256_SIZE);
    CopyBytes(inputs.config_sha256, record->config_sha256,
              WLSS_RAW_SHA256_SIZE);
    CopyBytes(inputs.sandbox_dso_sha256, record->sandbox_dso_sha256,
              WLSS_RAW_SHA256_SIZE);
    CopyBytes(inputs.module_engine_sha256, record->module_engine_sha256,
              WLSS_RAW_SHA256_SIZE);
    if (ops->verify_stock_binding(ops->context, &inputs) != 1) {
        return WLSS_REASON_STOCK_IDENTITY_REJECTED;
    }
    ZeroBytes(&reparsed, sizeof(reparsed));
    CopyBytes(reparsed.raw_message_sha256, record->raw_message_sha256,
              WLSS_RAW_SHA256_SIZE);
    parse_reason = ParseRawMessage(&inputs, &reparsed);
    if (parse_reason != WLSS_REASON_NONE ||
        !SameRecordShape(record, &reparsed)) {
        return WLSS_REASON_RECORD_DRIFT;
    }
    return WLSS_REASON_NONE;
}

WlssResult WLSS_ParentPrepare(const WlssParentInputs *inputs,
                              const WlssStockOps *ops,
                              WlssSecurityRecordV1 *out_record)
{
    WlssReason reason;
    if (inputs == (const WlssParentInputs *)0 ||
        out_record == (WlssSecurityRecordV1 *)0 || !OpsValid(ops)) {
        return Result(WLSS_STATUS_INVALID_ARGUMENT,
                      WLSS_REASON_INVALID_ARGUMENT,
                      (const WlssSecurityRecordV1 *)0);
    }
    ZeroBytes(out_record, sizeof(*out_record));
    atomic_init(&out_record->state, (uint32_t)WLSS_RECORD_EMPTY);
    if (inputs->abi_version != WLSS_ABI_VERSION ||
        inputs->reserved_zero != UINT32_C(0)) {
        return FailRecord(out_record, WLSS_REASON_ABI_MISMATCH);
    }
    if (inputs->config_loaded != UINT32_C(1) ||
        inputs->adapter_generation == UINT64_C(0) ||
        inputs->config_generation == UINT64_C(0) ||
        BytesAllZero(inputs->config_sha256, WLSS_RAW_SHA256_SIZE)) {
        return FailRecord(out_record, WLSS_REASON_CONFIG_REQUIRED);
    }
    if (inputs->stock_binding_kind !=
            WLSS_STOCK_BINDING_OH_GN_NORMAL_V7 ||
        inputs->full_module_engine_present != UINT32_C(1) ||
        BytesAllZero(inputs->sandbox_dso_sha256, WLSS_RAW_SHA256_SIZE) ||
        BytesAllZero(inputs->module_engine_sha256, WLSS_RAW_SHA256_SIZE)) {
        return FailRecord(out_record, WLSS_REASON_STOCK_BINDING_REQUIRED);
    }
    if (BytesAllZero(inputs->raw_message_sha256, WLSS_RAW_SHA256_SIZE) ||
        ops->verify_raw_identity(ops->context, inputs->raw_message,
                                 inputs->raw_message_size,
                                 inputs->raw_message_sha256) != 1) {
        return FailRecord(out_record, WLSS_REASON_RAW_IDENTITY_REJECTED);
    }
    if (ops->verify_stock_binding(ops->context, inputs) != 1) {
        return FailRecord(out_record, WLSS_REASON_STOCK_IDENTITY_REJECTED);
    }
    out_record->abi_version = WLSS_ABI_VERSION;
    out_record->stock_binding_kind = inputs->stock_binding_kind;
    out_record->adapter_generation = inputs->adapter_generation;
    out_record->config_generation = inputs->config_generation;
    CopyBytes(out_record->raw_message_sha256, inputs->raw_message_sha256,
              WLSS_RAW_SHA256_SIZE);
    CopyBytes(out_record->config_sha256, inputs->config_sha256,
              WLSS_RAW_SHA256_SIZE);
    CopyBytes(out_record->sandbox_dso_sha256, inputs->sandbox_dso_sha256,
              WLSS_RAW_SHA256_SIZE);
    CopyBytes(out_record->module_engine_sha256,
              inputs->module_engine_sha256, WLSS_RAW_SHA256_SIZE);

    reason = ParseRawMessage(inputs, out_record);
    if (reason != WLSS_REASON_NONE) {
        return FailRecord(out_record, reason);
    }
    out_record->last_reason = (uint32_t)WLSS_REASON_NONE;
    atomic_store_explicit(&out_record->state,
                          (uint32_t)WLSS_RECORD_PARENT_PREPARED,
                          memory_order_release);
    return Result(WLSS_STATUS_OK, WLSS_REASON_NONE, out_record);
}

WlssResult WLSS_ParentPreFork(WlssSecurityRecordV1 *record,
                              const WlssStockOps *ops,
                              WlssStockParentReceipt *out_receipt)
{
    uint32_t expected = (uint32_t)WLSS_RECORD_PARENT_PREPARED;
    WlssStockParentReceipt receipt;
    WlssReason revalidate_reason;
    if (record == (WlssSecurityRecordV1 *)0 ||
        out_receipt == (WlssStockParentReceipt *)0 || !OpsValid(ops)) {
        return Result(WLSS_STATUS_INVALID_ARGUMENT,
                      WLSS_REASON_INVALID_ARGUMENT, record);
    }
    ZeroBytes(out_receipt, sizeof(*out_receipt));
    if (!atomic_compare_exchange_strong_explicit(
            &record->state, &expected,
            (uint32_t)WLSS_RECORD_PARENT_HOOK_RUNNING,
            memory_order_acq_rel, memory_order_acquire)) {
        return FailRecord(record, WLSS_REASON_SEQUENCE_INVALID);
    }
    revalidate_reason = RevalidateRecord(record, ops);
    if (revalidate_reason != WLSS_REASON_NONE) {
        return FailRecord(record, revalidate_reason);
    }
    ZeroBytes(&receipt, sizeof(receipt));
    if (ops->execute_parent_pre_fork(ops->context, record, &receipt) != 1 ||
        receipt.stock_result != 0) {
        return FailRecord(record, WLSS_REASON_PARENT_HOOK_FAILED);
    }
    if (receipt.abi_version != WLSS_ABI_VERSION ||
        receipt.stage != WLSS_PARENT_PRE_FORK_STAGE ||
        receipt.hook_priority_start != WLSS_HOOK_PRIORITY_FROM_START ||
        receipt.config_preloaded != UINT32_C(1) ||
        receipt.all_parent_hooks_completed != UINT32_C(1) ||
        receipt.shared_mount_completed != UINT32_C(1) ||
        receipt.bypass_used != UINT32_C(0) ||
        receipt.adapter_generation != record->adapter_generation ||
        receipt.config_generation != record->config_generation) {
        return FailRecord(record, WLSS_REASON_PARENT_RECEIPT_INVALID);
    }
    *out_receipt = receipt;
    atomic_store_explicit(&record->state,
                          (uint32_t)WLSS_RECORD_PARENT_HOOK_READY,
                          memory_order_release);
    return Result(WLSS_STATUS_OK, WLSS_REASON_NONE, record);
}

WlssResult WLSS_ChildExecute(WlssSecurityRecordV1 *record,
                             const WlssStockOps *ops,
                             WlssStockChildReceipt *out_receipt)
{
    uint32_t expected = (uint32_t)WLSS_RECORD_PARENT_HOOK_READY;
    WlssStockChildReceipt receipt;
    WlssReason revalidate_reason;
    if (record == (WlssSecurityRecordV1 *)0 ||
        out_receipt == (WlssStockChildReceipt *)0 || !OpsValid(ops)) {
        return Result(WLSS_STATUS_INVALID_ARGUMENT,
                      WLSS_REASON_INVALID_ARGUMENT, record);
    }
    ZeroBytes(out_receipt, sizeof(*out_receipt));
    if (!atomic_compare_exchange_strong_explicit(
            &record->state, &expected,
            (uint32_t)WLSS_RECORD_CHILD_HOOK_RUNNING,
            memory_order_acq_rel, memory_order_acquire)) {
        return FailRecord(record, WLSS_REASON_SEQUENCE_INVALID);
    }
    revalidate_reason = RevalidateRecord(record, ops);
    if (revalidate_reason != WLSS_REASON_NONE) {
        return FailRecord(record, revalidate_reason);
    }
    if (FlagSet(record, WLSS_FLAG_NO_SANDBOX)) {
        return FailRecord(record, WLSS_REASON_NO_SANDBOX_FORBIDDEN);
    }
    if (FlagSet(record, WLSS_FLAG_IGNORE_SANDBOX)) {
        return FailRecord(record, WLSS_REASON_IGNORE_SANDBOX_FORBIDDEN);
    }

    ZeroBytes(&receipt, sizeof(receipt));
    if (ops->execute_child_sandbox(ops->context, record, &receipt) != 1 ||
#if defined(WLSS_MUTANT_IGNORE_SANDBOX_RESULT)
        false) {
#else
        receipt.stock_result != 0) {
#endif
        return FailRecord(record, WLSS_REASON_CHILD_SANDBOX_FAILED);
    }
    if (receipt.abi_version != WLSS_ABI_VERSION ||
        receipt.stage != WLSS_CHILD_EXECUTE_STAGE ||
        receipt.hook_priority_start != WLSS_HOOK_PRIORITY_FROM_START ||
        receipt.sandbox_applied != UINT32_C(1) ||
        receipt.no_sandbox_used != UINT32_C(0) ||
        receipt.ignore_sandbox_result_used != UINT32_C(0) ||
        receipt.reserved_zero != UINT32_C(0) ||
        receipt.adapter_generation != record->adapter_generation ||
        receipt.config_generation != record->config_generation) {
        return FailRecord(record, WLSS_REASON_CHILD_RECEIPT_INVALID);
    }
    *out_receipt = receipt;
    atomic_store_explicit(&record->state,
                          (uint32_t)WLSS_RECORD_CHILD_SANDBOX_READY,
                          memory_order_release);
    return Result(WLSS_STATUS_OK, WLSS_REASON_NONE, record);
}

const WlssTlvSpan *WLSS_GetTlvSpan(const WlssSecurityRecordV1 *record,
                                   uint32_t index)
{
    if (record == (const WlssSecurityRecordV1 *)0 ||
        record->abi_version != WLSS_ABI_VERSION || index >= record->tlv_count ||
        index >= WLSS_MAX_TLV_COUNT) {
        return (const WlssTlvSpan *)0;
    }
    return &record->spans[index];
}

const char *WLSS_ReasonString(WlssReason reason)
{
    switch (reason) {
        case WLSS_REASON_NONE: return "none";
        case WLSS_REASON_INVALID_ARGUMENT: return "invalid_argument";
        case WLSS_REASON_ABI_MISMATCH: return "abi_mismatch";
        case WLSS_REASON_CONFIG_REQUIRED: return "config_required";
        case WLSS_REASON_STOCK_BINDING_REQUIRED: return "stock_binding_required";
        case WLSS_REASON_RAW_IDENTITY_REJECTED: return "raw_identity_rejected";
        case WLSS_REASON_STOCK_IDENTITY_REJECTED: return "stock_identity_rejected";
        case WLSS_REASON_MESSAGE_HEADER_INVALID: return "message_header_invalid";
        case WLSS_REASON_PROCESS_NAME_INVALID: return "process_name_invalid";
        case WLSS_REASON_TLV_COUNT_INVALID: return "tlv_count_invalid";
        case WLSS_REASON_TLV_BOUNDS_INVALID: return "tlv_bounds_invalid";
        case WLSS_REASON_TLV_TYPE_UNSUPPORTED: return "tlv_type_unsupported";
        case WLSS_REASON_TLV_DUPLICATE: return "tlv_duplicate";
        case WLSS_REASON_REQUIRED_TLV_MISSING: return "required_tlv_missing";
        case WLSS_REASON_BUNDLE_REQUIRED: return "bundle_required";
        case WLSS_REASON_BUNDLE_INVALID: return "bundle_invalid";
        case WLSS_REASON_FLAGS_INVALID: return "flags_invalid";
        case WLSS_REASON_NO_SANDBOX_FORBIDDEN: return "no_sandbox_forbidden";
        case WLSS_REASON_IGNORE_SANDBOX_FORBIDDEN: return "ignore_sandbox_forbidden";
        case WLSS_REASON_DAC_REQUIRED: return "dac_required";
        case WLSS_REASON_DAC_INVALID: return "dac_invalid";
        case WLSS_REASON_APL_REQUIRED: return "apl_required";
        case WLSS_REASON_APL_INVALID: return "apl_invalid";
        case WLSS_REASON_TOKEN_REQUIRED: return "token_required";
        case WLSS_REASON_TOKEN_INVALID: return "token_invalid";
        case WLSS_REASON_OWNER_REQUIRED: return "owner_required";
        case WLSS_REASON_OWNER_INVALID: return "owner_invalid";
        case WLSS_REASON_PERMISSION_REQUIRED: return "permission_required";
        case WLSS_REASON_PERMISSION_INVALID: return "permission_invalid";
        case WLSS_REASON_INTERNET_REQUIRED: return "internet_required";
        case WLSS_REASON_INTERNET_INVALID: return "internet_invalid";
        case WLSS_REASON_EXT_INVALID: return "ext_invalid";
        case WLSS_REASON_SEQUENCE_INVALID: return "sequence_invalid";
        case WLSS_REASON_PARENT_HOOK_FAILED: return "parent_hook_failed";
        case WLSS_REASON_PARENT_RECEIPT_INVALID: return "parent_receipt_invalid";
        case WLSS_REASON_CHILD_SANDBOX_FAILED: return "child_sandbox_failed";
        case WLSS_REASON_CHILD_RECEIPT_INVALID: return "child_receipt_invalid";
        case WLSS_REASON_RECORD_DRIFT: return "record_drift";
        default: return "unknown";
    }
}
