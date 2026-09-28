#include "westlake_oh_security_specialization.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define TEST_BUFFER_SIZE 4096U
#define TEST_STAGE_PARENT 20U
#define TEST_STAGE_CHILD 31U

typedef struct BuildOptions {
    uint32_t flags_word_zero;
    bool short_dac;
    bool short_token;
} BuildOptions;

typedef struct BuiltMessage {
    uint8_t bytes[TEST_BUFFER_SIZE];
    uint32_t size;
    uint32_t tlv_count;
    uint32_t flags_payload_offset;
    uint32_t apl_offset;
    uint32_t owner_payload_offset;
    uint32_t permission_payload_offset;
    uint32_t internet_payload_offset;
    uint32_t first_ext_header_offset;
    uint32_t first_ext_payload_offset;
    uint32_t second_ext_payload_offset;
} BuiltMessage;

typedef struct TestContext {
    uint8_t snapshot[TEST_BUFFER_SIZE];
    uint32_t snapshot_size;
    uint8_t expected_digest[WLSS_RAW_SHA256_SIZE];
    int verify_raw_result;
    int verify_raw_without_snapshot;
    int verify_binding_result;
    int parent_callback_result;
    int parent_stock_result;
    int parent_bad_receipt;
    int child_callback_result;
    int child_stock_result;
    int child_bad_receipt;
} TestContext;

typedef struct TestCase {
    BuiltMessage message;
    WlssParentInputs inputs;
    WlssStockOps ops;
    TestContext context;
    WlssSecurityRecordV1 record;
} TestCase;

static int failures;
static int tests_run;

static void Store16(uint8_t *bytes, uint16_t value)
{
    bytes[0] = (uint8_t)value;
    bytes[1] = (uint8_t)(value >> 8);
}

static void Store32(uint8_t *bytes, uint32_t value)
{
    bytes[0] = (uint8_t)value;
    bytes[1] = (uint8_t)(value >> 8);
    bytes[2] = (uint8_t)(value >> 16);
    bytes[3] = (uint8_t)(value >> 24);
}

static void Store64(uint8_t *bytes, uint64_t value)
{
    Store32(bytes, (uint32_t)value);
    Store32(bytes + 4, (uint32_t)(value >> 32));
}

static uint32_t Align4(uint32_t value)
{
    return (value + 3U) & ~UINT32_C(3);
}

static uint32_t TlvHeaderAt(const BuiltMessage *message, uint32_t ordinal)
{
    uint32_t offset = (uint32_t)sizeof(WlssOhAppSpawnMsg);
    uint32_t index;
    for (index = 0; index < ordinal; ++index) {
        uint32_t length = (uint32_t)message->bytes[offset] |
                          ((uint32_t)message->bytes[offset + 1] << 8);
        offset += length;
    }
    return offset;
}

static uint32_t AddTlv(BuiltMessage *message, uint16_t type,
                       const void *payload, uint32_t payload_size)
{
    uint32_t offset = message->size;
    uint32_t tlv_size = Align4(UINT32_C(4) + payload_size);
    if (offset + tlv_size > TEST_BUFFER_SIZE) {
        return UINT32_MAX;
    }
    Store16(message->bytes + offset, (uint16_t)tlv_size);
    Store16(message->bytes + offset + 2, type);
    if (payload_size != 0U) {
        memcpy(message->bytes + offset + 4, payload, payload_size);
    }
    message->size += tlv_size;
    message->tlv_count += UINT32_C(1);
    return offset + UINT32_C(4);
}

static uint32_t AddExt(BuiltMessage *message, const char *name,
                       uint16_t data_type, const void *payload,
                       uint16_t payload_size, uint32_t *out_header_offset)
{
    uint32_t offset = message->size;
    uint32_t tlv_size = Align4(UINT32_C(40) + payload_size);
    size_t name_length = strlen(name);
    if (offset + tlv_size > TEST_BUFFER_SIZE || name_length >= 32U) {
        return UINT32_MAX;
    }
    Store16(message->bytes + offset, (uint16_t)tlv_size);
    Store16(message->bytes + offset + 2, (uint16_t)WLSS_TLV_EXT);
    Store16(message->bytes + offset + 4, payload_size);
    Store16(message->bytes + offset + 6, data_type);
    memcpy(message->bytes + offset + 8, name, name_length + 1U);
    if (payload_size != 0U) {
        memcpy(message->bytes + offset + 40, payload, payload_size);
    }
    message->size += tlv_size;
    message->tlv_count += UINT32_C(1);
    *out_header_offset = offset;
    return offset + UINT32_C(40);
}

static bool BuildMessage(BuiltMessage *message, BuildOptions options)
{
    uint8_t payload[sizeof(WlssOhAppDacInfo)];
    const char bundle[] = "com.westlake.unity";
    const char apl[] = "normal";
    const char owner[] = "westlake-owner";
    const char ext_one[] = "100";
    const uint8_t ext_two[] = {0xdeU, 0xadU, 0xbeU, 0xefU, 0x00U};

    memset(message, 0, sizeof(*message));
    message->size = (uint32_t)sizeof(WlssOhAppSpawnMsg);
    Store32(message->bytes, WLSS_OH_MSG_MAGIC);
    Store32(message->bytes + 4, WLSS_OH_MSG_APP_SPAWN);
    Store32(message->bytes + 12, UINT32_C(0x1234));
    memcpy(message->bytes + 20, "com.westlake.unity:main", 24U);

    memset(payload, 0, sizeof(payload));
    Store32(payload, UINT32_C(0));
    memcpy(payload + 4, bundle, sizeof(bundle));
    if (AddTlv(message, (uint16_t)WLSS_TLV_BUNDLE_INFO, payload,
               UINT32_C(4) + (uint32_t)sizeof(bundle)) == UINT32_MAX) {
        return false;
    }

    memset(payload, 0, sizeof(payload));
    Store32(payload, WLSS_MAX_FLAGS_WORDS);
    Store32(payload + 4, options.flags_word_zero);
    Store32(payload + 8, UINT32_C(0x80000000));
    message->flags_payload_offset = AddTlv(
        message, (uint16_t)WLSS_TLV_MSG_FLAGS, payload, UINT32_C(12));

    memset(payload, 0, sizeof(payload));
    Store32(payload, UINT32_C(20010042));
    Store32(payload + 4, UINT32_C(20010042));
    Store32(payload + 8, UINT32_C(2));
    Store32(payload + 12, UINT32_C(1006));
    Store32(payload + 16, UINT32_C(1008));
    memcpy(payload + 12 + WLSS_OH_MAX_GIDS * 4, "u0_a42", 7U);
    if (AddTlv(message, (uint16_t)WLSS_TLV_DAC_INFO, payload,
               options.short_dac ? UINT32_C(4) :
               (uint32_t)sizeof(WlssOhAppDacInfo)) == UINT32_MAX) {
        return false;
    }

    memset(payload, 0, sizeof(payload));
    Store32(payload, UINT32_C(0x55aa));
    memcpy(payload + 4, apl, sizeof(apl));
    {
        uint32_t domain_payload = AddTlv(
            message, (uint16_t)WLSS_TLV_DOMAIN_INFO, payload,
            UINT32_C(4) + (uint32_t)sizeof(apl));
        if (domain_payload == UINT32_MAX) {
            return false;
        }
        message->apl_offset = domain_payload + UINT32_C(4);
    }

    message->owner_payload_offset = AddTlv(
        message, (uint16_t)WLSS_TLV_OWNER_INFO, owner,
        (uint32_t)sizeof(owner));

    memset(payload, 0, sizeof(payload));
    Store64(payload, UINT64_C(0x1122334455667788));
    if (AddTlv(message, (uint16_t)WLSS_TLV_ACCESS_TOKEN_INFO, payload,
               options.short_token ? UINT32_C(4) : UINT32_C(8)) ==
        UINT32_MAX) {
        return false;
    }

    memset(payload, 0, sizeof(payload));
    Store32(payload, UINT32_C(2));
    Store32(payload + 4, UINT32_C(0x01020304));
    Store32(payload + 8, UINT32_C(0x80000001));
    message->permission_payload_offset = AddTlv(
        message, (uint16_t)WLSS_TLV_PERMISSION, payload, UINT32_C(12));

    payload[0] = UINT8_C(1);
    payload[1] = UINT8_C(1);
    payload[2] = UINT8_C(0);
    payload[3] = UINT8_C(0);
    message->internet_payload_offset = AddTlv(
        message, (uint16_t)WLSS_TLV_INTERNET_INFO, payload, UINT32_C(4));

    message->first_ext_payload_offset = AddExt(
        message, "UserId", UINT16_C(1), ext_one,
        (uint16_t)sizeof(ext_one), &message->first_ext_header_offset);
    {
        uint32_t ignored_header = 0;
        message->second_ext_payload_offset = AddExt(
            message, "westlake.raw", UINT16_C(7), ext_two,
            (uint16_t)sizeof(ext_two), &ignored_header);
    }

    if (message->flags_payload_offset == UINT32_MAX ||
        message->owner_payload_offset == UINT32_MAX ||
        message->permission_payload_offset == UINT32_MAX ||
        message->internet_payload_offset == UINT32_MAX ||
        message->first_ext_payload_offset == UINT32_MAX ||
        message->second_ext_payload_offset == UINT32_MAX) {
        return false;
    }
    Store32(message->bytes + 8, message->size);
    Store32(message->bytes + 16, message->tlv_count);
    return true;
}

static int VerifyRaw(void *opaque, const uint8_t *raw, uint32_t raw_size,
                     const uint8_t expected_sha256[32])
{
    TestContext *context = (TestContext *)opaque;
    if (context->verify_raw_result != 1 ||
        memcmp(expected_sha256, context->expected_digest,
               WLSS_RAW_SHA256_SIZE) != 0) {
        return 0;
    }
    if (context->verify_raw_without_snapshot == 1) {
        return 1;
    }
    return raw_size == context->snapshot_size &&
           memcmp(raw, context->snapshot, raw_size) == 0;
}

static int VerifyBinding(void *opaque, const WlssParentInputs *inputs)
{
    TestContext *context = (TestContext *)opaque;
    return context->verify_binding_result == 1 &&
           inputs->stock_binding_kind == WLSS_STOCK_BINDING_OH_GN_NORMAL_V7;
}

static int ExecuteParent(void *opaque, const WlssSecurityRecordV1 *record,
                         WlssStockParentReceipt *receipt)
{
    TestContext *context = (TestContext *)opaque;
    memset(receipt, 0, sizeof(*receipt));
    receipt->abi_version = WLSS_ABI_VERSION;
    receipt->stage = context->parent_bad_receipt ? 19U : TEST_STAGE_PARENT;
    receipt->hook_priority_start = UINT32_C(0);
    receipt->stock_result = context->parent_stock_result;
    receipt->config_preloaded = UINT32_C(1);
    receipt->all_parent_hooks_completed = UINT32_C(1);
    receipt->shared_mount_completed = UINT32_C(1);
    receipt->bypass_used = UINT32_C(0);
    receipt->adapter_generation = record->adapter_generation;
    receipt->config_generation = record->config_generation;
    return context->parent_callback_result;
}

static int ExecuteChild(void *opaque, const WlssSecurityRecordV1 *record,
                        WlssStockChildReceipt *receipt)
{
    TestContext *context = (TestContext *)opaque;
    memset(receipt, 0, sizeof(*receipt));
    receipt->abi_version = WLSS_ABI_VERSION;
    receipt->stage = context->child_bad_receipt ? 30U : TEST_STAGE_CHILD;
    receipt->hook_priority_start = UINT32_C(0);
    receipt->stock_result = context->child_stock_result;
    receipt->sandbox_applied = UINT32_C(1);
    receipt->no_sandbox_used = UINT32_C(0);
    receipt->ignore_sandbox_result_used = UINT32_C(0);
    receipt->adapter_generation = record->adapter_generation;
    receipt->config_generation = record->config_generation;
    return context->child_callback_result;
}

static bool InitCase(TestCase *test_case, BuildOptions options)
{
    uint32_t index;
    memset(test_case, 0, sizeof(*test_case));
    if (!BuildMessage(&test_case->message, options)) {
        return false;
    }
    test_case->context.snapshot_size = test_case->message.size;
    memcpy(test_case->context.snapshot, test_case->message.bytes,
           test_case->message.size);
    test_case->context.verify_raw_result = 1;
    test_case->context.verify_binding_result = 1;
    test_case->context.parent_callback_result = 1;
    test_case->context.child_callback_result = 1;
    for (index = 0; index < WLSS_RAW_SHA256_SIZE; ++index) {
        test_case->context.expected_digest[index] = (uint8_t)(index + 1U);
    }
    test_case->inputs.abi_version = WLSS_ABI_VERSION;
    test_case->inputs.config_loaded = UINT32_C(1);
    test_case->inputs.stock_binding_kind =
        WLSS_STOCK_BINDING_OH_GN_NORMAL_V7;
    test_case->inputs.full_module_engine_present = UINT32_C(1);
    test_case->inputs.adapter_generation = UINT64_C(101);
    test_case->inputs.config_generation = UINT64_C(202);
    test_case->inputs.raw_message = test_case->message.bytes;
    test_case->inputs.raw_message_size = test_case->message.size;
    memcpy(test_case->inputs.raw_message_sha256,
           test_case->context.expected_digest, WLSS_RAW_SHA256_SIZE);
    memset(test_case->inputs.config_sha256, 0x31,
           WLSS_RAW_SHA256_SIZE);
    memset(test_case->inputs.sandbox_dso_sha256, 0x32,
           WLSS_RAW_SHA256_SIZE);
    memset(test_case->inputs.module_engine_sha256, 0x33,
           WLSS_RAW_SHA256_SIZE);
    test_case->ops.abi_version = WLSS_ABI_VERSION;
    test_case->ops.context = &test_case->context;
    test_case->ops.verify_raw_identity = VerifyRaw;
    test_case->ops.verify_stock_binding = VerifyBinding;
    test_case->ops.execute_parent_pre_fork = ExecuteParent;
    test_case->ops.execute_child_sandbox = ExecuteChild;
    return true;
}

static bool Prepare(TestCase *test_case, WlssReason reason)
{
    WlssResult result = WLSS_ParentPrepare(
        &test_case->inputs, &test_case->ops, &test_case->record);
    return result.reason == reason &&
           (reason == WLSS_REASON_NONE ?
                result.status == WLSS_STATUS_OK :
                result.status == WLSS_STATUS_TERMINAL);
}

static bool ParentReady(TestCase *test_case)
{
    WlssStockParentReceipt receipt;
    WlssResult result;
    if (!Prepare(test_case, WLSS_REASON_NONE)) {
        return false;
    }
    result = WLSS_ParentPreFork(&test_case->record, &test_case->ops,
                                &receipt);
    return result.status == WLSS_STATUS_OK &&
           result.state == WLSS_RECORD_PARENT_HOOK_READY &&
           receipt.stage == TEST_STAGE_PARENT;
}

static bool TestHappyPathAndRawPreservation(void)
{
    TestCase test_case;
    WlssStockParentReceipt parent_receipt;
    WlssStockChildReceipt child_receipt;
    WlssResult result;
    const WlssTlvSpan *owner;
    const WlssTlvSpan *permission;
    const WlssTlvSpan *internet;
    const WlssTlvSpan *ext_one;
    const WlssTlvSpan *ext_two;
    const char expected_owner[] = "westlake-owner";
    const char expected_ext_one[] = "100";
    const uint8_t expected_ext_two[] = {0xdeU, 0xadU, 0xbeU, 0xefU, 0x00U};
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !Prepare(&test_case, WLSS_REASON_NONE)) {
        return false;
    }
    if (test_case.record.raw_message != test_case.message.bytes ||
        test_case.record.tlv_count != 10U ||
        test_case.record.extension_count != 2U ||
        test_case.record.flags_word_count != 2U ||
        test_case.record.flags_words[1] != UINT32_C(0x80000000)) {
        return false;
    }
    owner = WLSS_GetTlvSpan(
        &test_case.record,
        test_case.record.required_span_index[WLSS_TLV_OWNER_INFO]);
    permission = WLSS_GetTlvSpan(
        &test_case.record,
        test_case.record.required_span_index[WLSS_TLV_PERMISSION]);
    internet = WLSS_GetTlvSpan(
        &test_case.record,
        test_case.record.required_span_index[WLSS_TLV_INTERNET_INFO]);
    ext_one = WLSS_GetTlvSpan(&test_case.record, 8U);
    ext_two = WLSS_GetTlvSpan(&test_case.record, 9U);
    if (owner == NULL || permission == NULL || internet == NULL ||
        ext_one == NULL || ext_two == NULL ||
        owner->payload_offset != test_case.message.owner_payload_offset ||
        memcmp(test_case.message.bytes + owner->payload_offset,
               expected_owner, sizeof(expected_owner)) != 0 ||
        permission->payload_offset !=
            test_case.message.permission_payload_offset ||
        memcmp(test_case.message.bytes + permission->payload_offset,
               test_case.context.snapshot + permission->payload_offset,
               permission->payload_length) != 0 ||
        internet->payload_offset != test_case.message.internet_payload_offset ||
        memcmp(test_case.message.bytes + internet->payload_offset,
               "\x01\x01\x00\x00", 4U) != 0 ||
        strcmp(ext_one->ext_name, "UserId") != 0 ||
        ext_one->payload_offset != test_case.message.first_ext_payload_offset ||
        ext_one->ext_data_type != 1U ||
        ext_one->ext_data_length != sizeof(expected_ext_one) ||
        memcmp(test_case.message.bytes + ext_one->payload_offset,
               expected_ext_one, sizeof(expected_ext_one)) != 0 ||
        strcmp(ext_two->ext_name, "westlake.raw") != 0 ||
        ext_two->payload_offset != test_case.message.second_ext_payload_offset ||
        ext_two->ext_data_type != 7U ||
        ext_two->ext_data_length != sizeof(expected_ext_two) ||
        memcmp(test_case.message.bytes + ext_two->payload_offset,
               expected_ext_two, sizeof(expected_ext_two)) != 0) {
        return false;
    }
    result = WLSS_ParentPreFork(&test_case.record, &test_case.ops,
                                &parent_receipt);
    if (result.status != WLSS_STATUS_OK ||
        result.state != WLSS_RECORD_PARENT_HOOK_READY) {
        return false;
    }
    result = WLSS_ChildExecute(&test_case.record, &test_case.ops,
                               &child_receipt);
    return result.status == WLSS_STATUS_OK &&
           result.state == WLSS_RECORD_CHILD_SANDBOX_READY &&
           child_receipt.sandbox_applied == 1U;
}

static bool TestMissingConfig(void)
{
    TestCase test_case;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    test_case.inputs.config_loaded = 0U;
    return Prepare(&test_case, WLSS_REASON_CONFIG_REQUIRED);
}

static bool TestEmptyModuleEngine(void)
{
    TestCase test_case;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    test_case.inputs.stock_binding_kind = WLSS_STOCK_BINDING_EMPTY_STUB;
    test_case.inputs.full_module_engine_present = 0U;
    return Prepare(&test_case, WLSS_REASON_STOCK_BINDING_REQUIRED);
}

static bool TestStockIdentityFailure(void)
{
    TestCase test_case;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    test_case.context.verify_binding_result = 0;
    return Prepare(&test_case, WLSS_REASON_STOCK_IDENTITY_REJECTED);
}

static bool TestNoSandboxForbidden(void)
{
    TestCase test_case;
    BuildOptions options = {UINT32_C(1) << 7, false, false};
    if (!InitCase(&test_case, options)) return false;
    return Prepare(&test_case, WLSS_REASON_NO_SANDBOX_FORBIDDEN);
}

static bool TestIgnoreSandboxForbidden(void)
{
    TestCase test_case;
    BuildOptions options = {UINT32_C(1) << 13, false, false};
    if (!InitCase(&test_case, options)) return false;
    return Prepare(&test_case, WLSS_REASON_IGNORE_SANDBOX_FORBIDDEN);
}

static bool TestBundleRequired(void)
{
    TestCase test_case;
    uint32_t bundle_payload;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    bundle_payload = TlvHeaderAt(&test_case.message, 0U) + 4U;
    test_case.message.bytes[bundle_payload + 4U] = 0U;
    memcpy(test_case.context.snapshot, test_case.message.bytes,
           test_case.message.size);
    return Prepare(&test_case, WLSS_REASON_BUNDLE_INVALID);
}

static bool TestFullFlagsRequired(void)
{
    TestCase test_case;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    Store32(test_case.message.bytes + test_case.message.flags_payload_offset,
            UINT32_C(1));
    memcpy(test_case.context.snapshot, test_case.message.bytes,
           test_case.message.size);
    return Prepare(&test_case, WLSS_REASON_FLAGS_INVALID);
}

static bool TestShortDacForbidden(void)
{
    TestCase test_case;
    BuildOptions options = {0, true, false};
    if (!InitCase(&test_case, options)) return false;
    return Prepare(&test_case, WLSS_REASON_DAC_REQUIRED);
}

static bool TestShortTokenForbidden(void)
{
    TestCase test_case;
    BuildOptions options = {0, false, true};
    if (!InitCase(&test_case, options)) return false;
    return Prepare(&test_case, WLSS_REASON_TOKEN_REQUIRED);
}

static bool TestZeroTokenForbidden(void)
{
    TestCase test_case;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    /* Access-token TLV is the sixth TLV; payload begins after its header. */
    {
        uint32_t offset = TlvHeaderAt(&test_case.message, 5U);
        memset(test_case.message.bytes + offset + 4, 0, 8U);
        memcpy(test_case.context.snapshot, test_case.message.bytes,
               test_case.message.size);
    }
    return Prepare(&test_case, WLSS_REASON_TOKEN_INVALID);
}

static bool MissingRequiredOrdinal(uint32_t ordinal)
{
    TestCase test_case;
    uint32_t header;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    header = TlvHeaderAt(&test_case.message, ordinal);
    Store16(test_case.message.bytes + header + 2,
            (uint16_t)WLSS_TLV_RENDER_TERMINATION_INFO);
    memcpy(test_case.context.snapshot, test_case.message.bytes,
           test_case.message.size);
    return Prepare(&test_case, WLSS_REASON_REQUIRED_TLV_MISSING);
}

static bool TestMissingDac(void)
{
    return MissingRequiredOrdinal(2U);
}

static bool TestMissingApl(void)
{
    return MissingRequiredOrdinal(3U);
}

static bool TestMissingToken(void)
{
    return MissingRequiredOrdinal(5U);
}

static bool TestMissingOwner(void)
{
    return MissingRequiredOrdinal(4U);
}

static bool TestMissingPermission(void)
{
    return MissingRequiredOrdinal(6U);
}

static bool TestMissingInternet(void)
{
    return MissingRequiredOrdinal(7U);
}

static bool TestEmptyAplForbidden(void)
{
    TestCase test_case;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    test_case.message.bytes[test_case.message.apl_offset] = 0U;
    memcpy(test_case.context.snapshot, test_case.message.bytes,
           test_case.message.size);
    return Prepare(&test_case, WLSS_REASON_APL_INVALID);
}

static bool TestMissingRequiredTlv(void)
{
    TestCase test_case;
    uint32_t owner_header;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    owner_header = test_case.message.owner_payload_offset - 4U;
    Store16(test_case.message.bytes + owner_header + 2,
            (uint16_t)WLSS_TLV_RENDER_TERMINATION_INFO);
    memcpy(test_case.context.snapshot, test_case.message.bytes,
           test_case.message.size);
    return Prepare(&test_case, WLSS_REASON_REQUIRED_TLV_MISSING);
}

static bool TestDuplicateTlv(void)
{
    TestCase test_case;
    uint32_t owner_header;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    owner_header = test_case.message.owner_payload_offset - 4U;
    Store16(test_case.message.bytes + owner_header + 2,
            (uint16_t)WLSS_TLV_BUNDLE_INFO);
    memcpy(test_case.context.snapshot, test_case.message.bytes,
           test_case.message.size);
    return Prepare(&test_case, WLSS_REASON_TLV_DUPLICATE);
}

static bool TestMalformedExt(void)
{
    TestCase test_case;
    if (!InitCase(&test_case, (BuildOptions){0})) return false;
    Store16(test_case.message.bytes + test_case.message.first_ext_header_offset + 4,
            UINT16_C(200));
    memcpy(test_case.context.snapshot, test_case.message.bytes,
           test_case.message.size);
    return Prepare(&test_case, WLSS_REASON_EXT_INVALID);
}

static bool TestRawDriftRejected(void)
{
    TestCase test_case;
    WlssStockChildReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !ParentReady(&test_case)) return false;
    test_case.message.bytes[test_case.message.owner_payload_offset] ^= 1U;
    result = WLSS_ChildExecute(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_RAW_IDENTITY_REJECTED &&
           result.state == WLSS_RECORD_FAILED;
}

static bool TestShapeDriftRejected(void)
{
    TestCase test_case;
    WlssStockChildReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !ParentReady(&test_case)) return false;
    test_case.context.verify_raw_without_snapshot = 1;
    Store16(test_case.message.bytes + test_case.message.first_ext_header_offset + 4,
            UINT16_C(200));
    result = WLSS_ChildExecute(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_RECORD_DRIFT &&
           result.state == WLSS_RECORD_FAILED;
}

static bool TestParentCallbackFailure(void)
{
    TestCase test_case;
    WlssStockParentReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !Prepare(&test_case, WLSS_REASON_NONE)) return false;
    test_case.context.parent_callback_result = 0;
    result = WLSS_ParentPreFork(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_PARENT_HOOK_FAILED;
}

static bool TestParentNonzeroFailure(void)
{
    TestCase test_case;
    WlssStockParentReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !Prepare(&test_case, WLSS_REASON_NONE)) return false;
    test_case.context.parent_stock_result = -9;
    result = WLSS_ParentPreFork(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_PARENT_HOOK_FAILED;
}

static bool TestParentReceiptFailure(void)
{
    TestCase test_case;
    WlssStockParentReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !Prepare(&test_case, WLSS_REASON_NONE)) return false;
    test_case.context.parent_bad_receipt = 1;
    result = WLSS_ParentPreFork(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_PARENT_RECEIPT_INVALID;
}

static bool TestChildBeforeParentFailure(void)
{
    TestCase test_case;
    WlssStockChildReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !Prepare(&test_case, WLSS_REASON_NONE)) return false;
    result = WLSS_ChildExecute(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_SEQUENCE_INVALID;
}

static bool TestChildSandboxNonzeroFailure(void)
{
    TestCase test_case;
    WlssStockChildReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !ParentReady(&test_case)) return false;
    test_case.context.child_stock_result = -7;
    result = WLSS_ChildExecute(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_CHILD_SANDBOX_FAILED;
}

static bool TestChildReceiptFailure(void)
{
    TestCase test_case;
    WlssStockChildReceipt receipt;
    WlssResult result;
    if (!InitCase(&test_case, (BuildOptions){0}) ||
        !ParentReady(&test_case)) return false;
    test_case.context.child_bad_receipt = 1;
    result = WLSS_ChildExecute(&test_case.record, &test_case.ops, &receipt);
    return result.reason == WLSS_REASON_CHILD_RECEIPT_INVALID;
}

static void Run(const char *name, bool (*test)(void))
{
    ++tests_run;
    if (!test()) {
        ++failures;
        fprintf(stderr, "FAIL %s\n", name);
    }
}

int main(void)
{
    Run("happy_path_and_raw_preservation", TestHappyPathAndRawPreservation);
    Run("missing_config", TestMissingConfig);
    Run("empty_module_engine", TestEmptyModuleEngine);
    Run("stock_identity_failure", TestStockIdentityFailure);
    Run("no_sandbox_forbidden", TestNoSandboxForbidden);
    Run("ignore_sandbox_forbidden", TestIgnoreSandboxForbidden);
    Run("bundle_required", TestBundleRequired);
    Run("full_flags_required", TestFullFlagsRequired);
    Run("short_dac_forbidden", TestShortDacForbidden);
    Run("short_token_forbidden", TestShortTokenForbidden);
    Run("zero_token_forbidden", TestZeroTokenForbidden);
    Run("empty_apl_forbidden", TestEmptyAplForbidden);
    Run("missing_dac", TestMissingDac);
    Run("missing_apl", TestMissingApl);
    Run("missing_token", TestMissingToken);
    Run("missing_owner", TestMissingOwner);
    Run("missing_permission", TestMissingPermission);
    Run("missing_internet", TestMissingInternet);
    Run("missing_required_tlv", TestMissingRequiredTlv);
    Run("duplicate_tlv", TestDuplicateTlv);
    Run("malformed_ext", TestMalformedExt);
    Run("raw_drift_rejected", TestRawDriftRejected);
    Run("shape_drift_rejected", TestShapeDriftRejected);
    Run("parent_callback_failure", TestParentCallbackFailure);
    Run("parent_nonzero_failure", TestParentNonzeroFailure);
    Run("parent_receipt_failure", TestParentReceiptFailure);
    Run("child_before_parent_failure", TestChildBeforeParentFailure);
    Run("child_sandbox_nonzero_failure", TestChildSandboxNonzeroFailure);
    Run("child_receipt_failure", TestChildReceiptFailure);
    if (failures != 0) {
        fprintf(stderr, "RESULT FAIL tests=%d failures=%d\n", tests_run,
                failures);
        return 1;
    }
    printf("RESULT PASS tests=%d\n", tests_run);
    return 0;
}
