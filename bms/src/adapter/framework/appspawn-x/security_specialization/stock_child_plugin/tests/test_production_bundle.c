#include "westlake_generation_identity_ops.h"
#include "westlake_generation_identity_producer.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define CHECK(expression) do { \
    if (!(expression)) { \
        fprintf(stderr, "FAIL:%d:%s\n", __LINE__, #expression); \
        return 1; \
    } \
} while (0)

static uint32_t GetLe32(const uint8_t *bytes)
{
    return (uint32_t)bytes[0] |
        ((uint32_t)bytes[1] << 8U) |
        ((uint32_t)bytes[2] << 16U) |
        ((uint32_t)bytes[3] << 24U);
}

static uint64_t GetLe64(const uint8_t *bytes)
{
    return (uint64_t)GetLe32(bytes) |
        ((uint64_t)GetLe32(bytes + 4) << 32U);
}

int main(void)
{
    const WlgrIfGenerationMetadata *generated;
    const WlscplManifestV2 *manifest;
    WlgrIfChildRequest request;
    WlascStageLedgerV1 ledger;
    WlascStockStageReceiptV1 stock_receipt;
    WlgrIfHookContract hook;
    WlgrIfGenerationMetadata sealed;
    WlgrIfProductionContext context;
    WlgrIfOps production_ops;
    WlgrIfReplayGuard replay_guard;
    WlgrIpSourceFacts facts;
    WlgrIpProducer producer;
    WlgrIpOps producer_ops;
    const westlake_generation_identity_v2 *identity;
    uint8_t stock_receipt_digest[WLGR_V2_SHA256_SIZE];
    uint8_t serialized_receipt[WLGR_IF_STOCK_RECEIPT_CANONICAL_SIZE];
    uint64_t child_pid;
    uint64_t process_start;
    const uint64_t client_cookie = UINT64_C(0x1020304050607080);

    generated = WlgrIfGetBuildGeneratedMetadata();
    manifest = WLSCPL_GetBuildGeneratedManifest();
    CHECK(generated != NULL);
    CHECK(manifest != NULL);
    CHECK(WlgrIfValidateMetadata(generated));
    CHECK(WlgrIfProductionReadProcess(NULL, &child_pid, &process_start) == 0);

    memset(&request, 0, sizeof(request));
    request.android_uid = (uint32_t)getuid();
    request.launch_generation = generated->launch_generation;
    request.child_pid = child_pid;
    request.child_proc_start_time_ticks = process_start;
    memcpy(request.android_package, "org.westlake.bundle",
           sizeof("org.westlake.bundle"));
    memcpy(request.android_process_name, "org.westlake.bundle:main",
           sizeof("org.westlake.bundle:main"));

    memset(&ledger, 0, sizeof(ledger));
    CHECK(WLASC_ReceiptParentTail(
              &ledger, request.launch_generation, client_cookie,
              UINT32_C(73)) == WLASC_REASON_NONE);
    CHECK(WLASC_ReceiptBypassGuard(
              &ledger, client_cookie, UINT32_C(1), UINT32_C(0),
              UINT32_C(0)) == WLASC_REASON_NONE);
    CHECK(WLASC_ReceiptChildTail(
              &ledger, client_cookie) == WLASC_REASON_NONE);
    CHECK(WLASC_ReceiptConsume(
              &ledger, client_cookie, &stock_receipt) == WLASC_REASON_NONE);
    CHECK(WlgrIfDigestStockReceipt(
              &stock_receipt, stock_receipt_digest) == 0);
    CHECK(WlgrIfSerializeStockReceipt(
              &stock_receipt, serialized_receipt,
              sizeof(serialized_receipt)) == 0);
    CHECK(GetLe32(serialized_receipt) == stock_receipt.abi_version);
    CHECK(GetLe32(serialized_receipt + 4) == stock_receipt.struct_size);
    CHECK(GetLe64(serialized_receipt + 8) ==
          stock_receipt.runtime_generation);
    CHECK(GetLe32(serialized_receipt + 16) == stock_receipt.message_id);
    CHECK(GetLe32(serialized_receipt + 48) == UINT32_C(0));

    memset(&hook, 0, sizeof(hook));
    hook.magic = WLGR_IF_HOOK_MAGIC;
    hook.abi_version = WLGR_IF_ABI_VERSION;
    hook.struct_size = sizeof(hook);
    hook.capability_bitmap = WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP;
    hook.data_pointer_size = (uint16_t)sizeof(void *);
    hook.data_pointer_alignment = (uint16_t)_Alignof(void *);
    hook.function_pointer_size = (uint16_t)sizeof(void (*)(void));
    hook.function_pointer_alignment =
        (uint16_t)_Alignof(void (*)(void));
    CHECK(WlgrIfProduceHookSchemaDigest(hook.schema_digest) == 0);
    CHECK(WlgrIfValidateHook(&hook));
    CHECK(wlgr_v2_bytes_equal(
              hook.schema_digest, generated->hook_schema_digest,
              WLGR_V2_SHA256_SIZE));
    CHECK(wlgr_v2_bytes_equal(
              manifest->manifest_digest,
              generated->artifact_manifest_digest,
              WLGR_V2_SHA256_SIZE));
    CHECK(WlgrIfParentSeal(generated, &sealed) == 0);

    memset(&context, 0, sizeof(context));
    CHECK(WlgrIfProductionContextInit(
              &context, &request, &stock_receipt, &sealed, &hook) == 0);
    memset(&production_ops, 0, sizeof(production_ops));
    CHECK(WlgrIfProductionOps(&context, &production_ops) == 0);
    CHECK(production_ops.read_boot_id == WlgrIfProductionReadBootId);
    CHECK(production_ops.read_process == WlgrIfProductionReadProcess);
    CHECK(production_ops.read_metadata == WlgrIfProductionReadMetadata);
    CHECK(production_ops.read_receipt == WlgrIfProductionReadReceipt);
    CHECK(production_ops.read_manifest == WlgrIfProductionReadManifest);
    CHECK(production_ops.read_hook == WlgrIfProductionReadHook);
    CHECK(production_ops.random_bytes == WlgrIfProductionRandom);

    memset(&replay_guard, 0, sizeof(replay_guard));
    memset(&facts, 0, sizeof(facts));
    CHECK(WlgrIfAcquire(
              &request, &production_ops, &facts, &replay_guard) ==
          WLGR_IF_OK);
    CHECK(wlgr_v2_bytes_equal(
              facts.specialization_receipt_digest,
              stock_receipt_digest, WLGR_V2_SHA256_SIZE));
    CHECK(facts.policy_epoch == generated->policy_epoch);
    CHECK(wlgr_v2_bytes_equal(
              facts.artifact_generation, generated->artifact_generation,
              WLGR_V2_SHA256_SIZE));

    memset(&producer, 0, sizeof(producer));
    memset(&producer_ops, 0, sizeof(producer_ops));
    producer_ops.read_current_process = WlgrIfProductionReadProcess;
    producer_ops.context = &context;
    CHECK(WlgrIpBuild(&producer, &facts, &producer_ops) == WLGR_IP_OK);
    CHECK(WlgrIpValidate(&producer, &facts, &producer_ops) == WLGR_IP_OK);
    identity = WlgrIpGetIdentity(&producer);
    CHECK(identity != NULL);
    CHECK(wlgr_v2_identity_valid(identity));
    CHECK(wlgr_v2_bytes_equal(
              identity->specialization_receipt_digest,
              stock_receipt_digest, WLGR_V2_SHA256_SIZE));
    CHECK(identity->child_pid == child_pid);
    CHECK(identity->child_proc_start_time_ticks == process_start);

    puts("PRODUCTION_BUNDLE_PASS acquire=1 build=1 live_proc=1 "
         "real_getrandom=1 generated_metadata=1 stock_receipt_le=1");
    return 0;
}
