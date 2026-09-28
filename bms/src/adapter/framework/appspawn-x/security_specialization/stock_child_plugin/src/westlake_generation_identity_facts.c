#include "westlake_generation_identity_facts.h"
#include "westlake_sha256.h"

#include <string.h>

#define WLGR_IF_METADATA_CANONICAL_SIZE ((size_t)176)

static int Nonzero(const uint8_t *bytes, size_t size)
{
    size_t index;

    for (index = 0; index < size; ++index) {
        if (bytes[index] != UINT8_C(0)) {
            return 1;
        }
    }
    return 0;
}

static int HexValue(char value)
{
    if (value >= '0' && value <= '9') {
        return value - '0';
    }
    if (value >= 'a' && value <= 'f') {
        return value - 'a' + 10;
    }
    if (value >= 'A' && value <= 'F') {
        return value - 'A' + 10;
    }
    return -1;
}

static void PutLe32(uint8_t *out, uint32_t value)
{
    out[0] = (uint8_t)value;
    out[1] = (uint8_t)(value >> 8U);
    out[2] = (uint8_t)(value >> 16U);
    out[3] = (uint8_t)(value >> 24U);
}

static void PutLe64(uint8_t *out, uint64_t value)
{
    PutLe32(out, (uint32_t)value);
    PutLe32(out + 4, (uint32_t)(value >> 32U));
}

int WlgrIfParseBootId(const char *text,
                      uint8_t out[WLGR_V2_BOOT_ID_SIZE])
{
    size_t text_index;
    size_t out_index;
    int high;
    int low;

    if (text == NULL || out == NULL) {
        return 0;
    }
    for (text_index = 0; text_index < 36; ++text_index) {
        if (text_index == 8 || text_index == 13 || text_index == 18 ||
            text_index == 23) {
            if (text[text_index] != '-') {
                return 0;
            }
        } else if (HexValue(text[text_index]) < 0) {
            return 0;
        }
    }
    if (text[36] != '\0') {
        return 0;
    }
    text_index = 0;
    for (out_index = 0; out_index < WLGR_V2_BOOT_ID_SIZE; ++out_index) {
        while (text[text_index] == '-') {
            ++text_index;
        }
        high = HexValue(text[text_index++]);
        low = HexValue(text[text_index++]);
        if (high < 0 || low < 0) {
            return 0;
        }
        out[out_index] = (uint8_t)((high << 4) | low);
    }
    return Nonzero(out, WLGR_V2_BOOT_ID_SIZE);
}

int WlgrIfDigestMetadata(const WlgrIfGenerationMetadata *metadata,
                         uint8_t out[WLGR_V2_SHA256_SIZE])
{
    uint8_t canonical[WLGR_IF_METADATA_CANONICAL_SIZE];
    size_t offset = 0;
    WlSha256Context sha;

    if (metadata == NULL || out == NULL) {
        return -1;
    }
    PutLe64(canonical + offset, metadata->magic);
    offset += 8;
    PutLe32(canonical + offset, metadata->abi_version);
    offset += 4;
    PutLe32(canonical + offset, metadata->struct_size);
    offset += 4;
    memcpy(canonical + offset, metadata->boot_id, WLGR_V2_BOOT_ID_SIZE);
    offset += WLGR_V2_BOOT_ID_SIZE;
    memcpy(canonical + offset, metadata->artifact_generation,
           WLGR_V2_SHA256_SIZE);
    offset += WLGR_V2_SHA256_SIZE;
    PutLe64(canonical + offset, metadata->policy_epoch);
    offset += 8;
    PutLe64(canonical + offset, metadata->launch_generation);
    offset += 8;
    memcpy(canonical + offset, metadata->artifact_manifest_digest,
           WLGR_V2_SHA256_SIZE);
    offset += WLGR_V2_SHA256_SIZE;
    memcpy(canonical + offset, metadata->hook_schema_digest,
           WLGR_V2_SHA256_SIZE);
    offset += WLGR_V2_SHA256_SIZE;
    memcpy(canonical + offset, metadata->policy_provenance_digest,
           WLGR_V2_SHA256_SIZE);
    offset += WLGR_V2_SHA256_SIZE;
    if (offset != sizeof(canonical)) {
        return -1;
    }
    WLSha256Init(&sha);
    WLSha256Update(&sha, canonical, sizeof(canonical));
    return WLSha256Final(&sha, out);
}

int WlgrIfValidateMetadata(const WlgrIfGenerationMetadata *metadata)
{
    uint8_t digest[WLGR_V2_SHA256_SIZE];

    if (metadata == NULL || metadata->magic != WLGR_IF_METADATA_MAGIC ||
        metadata->abi_version != WLGR_IF_ABI_VERSION ||
        metadata->struct_size != sizeof(*metadata) ||
        !Nonzero(metadata->boot_id, WLGR_V2_BOOT_ID_SIZE) ||
        !Nonzero(metadata->artifact_generation, WLGR_V2_SHA256_SIZE) ||
        metadata->policy_epoch == UINT64_C(0) ||
        metadata->launch_generation == UINT64_C(0) ||
        !Nonzero(metadata->artifact_manifest_digest, WLGR_V2_SHA256_SIZE) ||
        !Nonzero(metadata->hook_schema_digest, WLGR_V2_SHA256_SIZE) ||
        !Nonzero(metadata->policy_provenance_digest, WLGR_V2_SHA256_SIZE) ||
        !Nonzero(metadata->metadata_digest, WLGR_V2_SHA256_SIZE) ||
        wlgr_v2_bytes_equal(metadata->artifact_generation,
                            metadata->artifact_manifest_digest,
                            WLGR_V2_SHA256_SIZE) ||
        wlgr_v2_bytes_equal(metadata->artifact_generation,
                            metadata->hook_schema_digest,
                            WLGR_V2_SHA256_SIZE) ||
        !wlgr_v2_bytes_zero((const uint8_t *)metadata->reserved_zero,
                            sizeof(metadata->reserved_zero)) ||
        WlgrIfDigestMetadata(metadata, digest) != 0) {
        return 0;
    }
    return wlgr_v2_bytes_equal(digest, metadata->metadata_digest,
                               WLGR_V2_SHA256_SIZE);
}

int WlgrIfValidateHook(const WlgrIfHookContract *hook)
{
    return hook != NULL &&
        hook->magic == WLGR_IF_HOOK_MAGIC &&
        hook->abi_version == WLGR_IF_ABI_VERSION &&
        hook->struct_size == sizeof(*hook) &&
        hook->capability_bitmap == WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP &&
        hook->data_pointer_size == sizeof(void *) &&
        hook->function_pointer_size == sizeof(void (*)(void)) &&
        hook->data_pointer_alignment != UINT16_C(0) &&
        hook->function_pointer_alignment != UINT16_C(0) &&
        Nonzero(hook->schema_digest, WLGR_V2_SHA256_SIZE) &&
        wlgr_v2_bytes_zero((const uint8_t *)hook->reserved_zero,
                           sizeof(hook->reserved_zero));
}

static int BuildRequestKey(const WlgrIfChildRequest *request,
                           westlake_runtime_instance_key_v2 *key)
{
    memset(key, 0, sizeof(*key));
    key->magic = WLGR_V2_RUNTIME_KEY_MAGIC;
    key->abi_version = WLGR_V2_ABI_VERSION;
    key->struct_size = WLGR_V2_RUNTIME_KEY_SIZE;
    key->struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    key->android_uid = request->android_uid;
    key->launch_generation = request->launch_generation;
    memcpy(key->android_package, request->android_package,
           sizeof(key->android_package));
    memcpy(key->android_process_name, request->android_process_name,
           sizeof(key->android_process_name));
    return wlgr_v2_runtime_key_valid(key);
}

WlgrIfError WlgrIfAcquire(const WlgrIfChildRequest *request,
                          const WlgrIfOps *ops,
                          WlgrIpSourceFacts *out,
                          WlgrIfReplayGuard *guard)
{
    uint8_t nonce[WLGR_V2_NONCE_SIZE];
    uint8_t parsed_boot_id[WLGR_V2_BOOT_ID_SIZE];
    char boot_text[64];
    uint64_t child_pid;
    uint64_t process_start;
    WlgrIfGenerationMetadata metadata;
    WlgrIfSpecializationReceipt receipt;
    WlgrIfHookContract hook;
    const WlscplManifestV2 *manifest = NULL;
    westlake_runtime_instance_key_v2 key;

    if (request == NULL || ops == NULL || out == NULL || guard == NULL ||
        ops->read_boot_id == NULL || ops->read_process == NULL ||
        ops->read_metadata == NULL || ops->read_receipt == NULL ||
        ops->read_manifest == NULL || ops->read_hook == NULL ||
        ops->random_bytes == NULL || !BuildRequestKey(request, &key)) {
        return WLGR_IF_INVALID_ARGUMENT;
    }
    memset(out, 0, sizeof(*out));
    memset(&metadata, 0, sizeof(metadata));
    memset(&receipt, 0, sizeof(receipt));
    memset(&hook, 0, sizeof(hook));
    memset(boot_text, 0, sizeof(boot_text));

    if (ops->read_boot_id(ops->context, boot_text, sizeof(boot_text)) != 0) {
        return WLGR_IF_BOOT_UNAVAILABLE;
    }
    if (!WlgrIfParseBootId(boot_text, parsed_boot_id)) {
        return WLGR_IF_BOOT_MALFORMED;
    }
    if (ops->read_process(ops->context, &child_pid, &process_start) != 0 ||
        child_pid != request->child_pid ||
        process_start != request->child_proc_start_time_ticks ||
        child_pid <= UINT64_C(1) || process_start == UINT64_C(0)) {
        return WLGR_IF_PROCESS_MISMATCH;
    }
    if (ops->read_metadata(ops->context, &metadata) != 0 ||
        !WlgrIfValidateMetadata(&metadata) ||
        !wlgr_v2_bytes_equal(parsed_boot_id, metadata.boot_id,
                             WLGR_V2_BOOT_ID_SIZE) ||
        metadata.launch_generation != request->launch_generation) {
        return WLGR_IF_METADATA_MISMATCH;
    }
    if (ops->read_receipt(ops->context, &receipt) != 0 ||
        receipt.magic != WLGR_IF_RECEIPT_MAGIC ||
        receipt.abi_version != WLGR_IF_ABI_VERSION ||
        receipt.struct_size != sizeof(receipt) ||
        !wlgr_v2_runtime_key_equal(&receipt.runtime_key, &key) ||
        !wlgr_v2_bytes_equal(receipt.boot_id, parsed_boot_id,
                             WLGR_V2_BOOT_ID_SIZE) ||
        !wlgr_v2_bytes_equal(receipt.artifact_generation,
                             metadata.artifact_generation,
                             WLGR_V2_SHA256_SIZE) ||
        receipt.policy_epoch != metadata.policy_epoch ||
        receipt.child_pid != child_pid ||
        receipt.child_proc_start_time_ticks != process_start ||
        !Nonzero(receipt.stock_receipt_digest, WLGR_V2_SHA256_SIZE) ||
        !wlgr_v2_bytes_zero((const uint8_t *)receipt.reserved_zero,
                            sizeof(receipt.reserved_zero))) {
        return WLGR_IF_RECEIPT_INVALID;
    }
    if (ops->read_manifest(ops->context, &manifest) != 0 ||
        manifest == NULL ||
        manifest->abi_version != WLSCPL_ABI_VERSION ||
        manifest->struct_size != sizeof(*manifest) ||
        !Nonzero(manifest->manifest_digest, WLGR_V2_SHA256_SIZE) ||
        !wlgr_v2_bytes_equal(manifest->manifest_digest,
                             metadata.artifact_manifest_digest,
                             WLGR_V2_SHA256_SIZE)) {
        return WLGR_IF_MANIFEST_INVALID;
    }
    if (ops->read_hook(ops->context, &hook) != 0 ||
        !WlgrIfValidateHook(&hook) ||
        !wlgr_v2_bytes_equal(hook.schema_digest,
                             metadata.hook_schema_digest,
                             WLGR_V2_SHA256_SIZE)) {
        return WLGR_IF_HOOK_INVALID;
    }
    if (ops->random_bytes(ops->context, nonce, sizeof(nonce)) != 0 ||
        !Nonzero(nonce, sizeof(nonce))) {
        return WLGR_IF_NONCE_UNAVAILABLE;
    }
    if (guard->consumed != UINT32_C(0) &&
        wlgr_v2_bytes_equal(guard->nonce, nonce, sizeof(nonce))) {
        return WLGR_IF_NONCE_REPLAY;
    }

    out->runtime_key = key;
    memcpy(out->boot_id, parsed_boot_id, sizeof(out->boot_id));
    memcpy(out->artifact_generation, metadata.artifact_generation,
           sizeof(out->artifact_generation));
    out->policy_epoch = metadata.policy_epoch;
    memcpy(out->specialization_receipt_digest,
           receipt.stock_receipt_digest,
           sizeof(out->specialization_receipt_digest));
    memcpy(out->artifact_manifest_digest,
           metadata.artifact_manifest_digest,
           sizeof(out->artifact_manifest_digest));
    memcpy(out->hook_schema_digest, metadata.hook_schema_digest,
           sizeof(out->hook_schema_digest));
    memcpy(out->request_nonce, nonce, sizeof(out->request_nonce));
    memcpy(guard->nonce, nonce, sizeof(guard->nonce));
    memcpy(guard->identity_digest, receipt.stock_receipt_digest,
           sizeof(guard->identity_digest));
    guard->consumed = UINT32_C(1);
    return WLGR_IF_OK;
}
