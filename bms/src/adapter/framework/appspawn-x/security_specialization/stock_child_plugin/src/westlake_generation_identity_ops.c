#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "westlake_generation_identity_ops.h"
#include "westlake_sha256.h"

#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <unistd.h>

extern ssize_t getrandom(void *, size_t, unsigned int);

static int BytesNonzero(const uint8_t *bytes, size_t size)
{
    size_t index;

    for (index = 0; index < size; ++index) {
        if (bytes[index] != UINT8_C(0)) {
            return 1;
        }
    }
    return 0;
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

static int StockReceiptValid(const WlascStockStageReceiptV1 *receipt)
{
    return receipt != NULL &&
        receipt->abi_version == WLASC_ABI_VERSION &&
        receipt->struct_size == sizeof(*receipt) &&
        receipt->runtime_generation != UINT64_C(0) &&
        receipt->parent_stage_tail_reached == UINT32_C(1) &&
        receipt->child_stage_tail_reached == UINT32_C(1) &&
        receipt->bypass_guard_passed == UINT32_C(1) &&
        receipt->security_owner_stock_appspawn == UINT32_C(1) &&
        receipt->parent_tail_priority == WLASC_TAIL_PRIORITY &&
        receipt->child_tail_priority == WLASC_TAIL_PRIORITY &&
        wlgr_v2_bytes_zero((const uint8_t *)receipt->reserved_zero,
                           sizeof(receipt->reserved_zero));
}

static int RequestKey(const WlgrIfChildRequest *request,
                      westlake_runtime_instance_key_v2 *key)
{
    if (request == NULL || key == NULL) {
        return 0;
    }
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

int WlgrIfProductionReadBootId(void *context, char *out, size_t capacity)
{
    int descriptor;
    ssize_t count;

    (void)context;
    if (out == NULL || capacity < 37) {
        return -1;
    }
    descriptor = open("/proc/sys/kernel/random/boot_id",
                      O_RDONLY | O_CLOEXEC);
    if (descriptor < 0) {
        return -1;
    }
    count = read(descriptor, out, capacity - 1);
    (void)close(descriptor);
    if (count < 0 || (size_t)count >= capacity - 1) {
        return -1;
    }
    while (count > 0 && (out[count - 1] == '\n' || out[count - 1] == '\r')) {
        --count;
    }
    out[count] = '\0';
    return count == 36 ? 0 : -1;
}

int WlgrIfProductionReadProcess(void *context, uint64_t *pid,
                                uint64_t *start_time_ticks)
{
    char buffer[4096];
    char *cursor;
    char *end;
    int descriptor;
    ssize_t count;
    unsigned long long value;
    unsigned int field;

    (void)context;
    if (pid == NULL || start_time_ticks == NULL) {
        return -1;
    }
    descriptor = open("/proc/self/stat", O_RDONLY | O_CLOEXEC);
    if (descriptor < 0) {
        return -1;
    }
    count = read(descriptor, buffer, sizeof(buffer) - 1);
    (void)close(descriptor);
    if (count <= 0) {
        return -1;
    }
    buffer[count] = '\0';
    cursor = strrchr(buffer, ')');
    if (cursor == NULL) {
        return -1;
    }
    ++cursor;
    while (*cursor == ' ') {
        ++cursor;
    }
    if (*cursor == '\0') {
        return -1;
    }
    while (*cursor != '\0' && *cursor != ' ') {
        ++cursor;
    }
    while (*cursor == ' ') {
        ++cursor;
    }
    for (field = 4; field <= 22; ++field) {
        errno = 0;
        value = strtoull(cursor, &end, 10);
        if (errno != 0 || end == cursor) {
            return -1;
        }
        cursor = end;
        while (*cursor == ' ') {
            ++cursor;
        }
        if (field == 22) {
            *pid = (uint64_t)getpid();
            *start_time_ticks = (uint64_t)value;
            return 0;
        }
    }
    return -1;
}

int WlgrIfProductionRandom(void *context, uint8_t *out, size_t size)
{
    size_t offset = 0;

    (void)context;
    if (out == NULL || size == 0) {
        return -1;
    }
    while (offset < size) {
        ssize_t count = getrandom(out + offset, size - offset, 0);

        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (count == 0) {
            return -1;
        }
        offset += (size_t)count;
    }
    return 0;
}

int WlgrIfProductionReadManifest(void *context,
                                 const WlscplManifestV2 **manifest)
{
    WlgrIfProductionContext *production =
        (WlgrIfProductionContext *)context;

    if (production == NULL || manifest == NULL ||
        production->build_manifest == NULL) {
        return -1;
    }
    *manifest = production->build_manifest;
    return 0;
}

int WlgrIfProductionReadMetadata(void *context,
                                 WlgrIfGenerationMetadata *metadata)
{
    WlgrIfProductionContext *production =
        (WlgrIfProductionContext *)context;

    if (production == NULL || production->sealed_metadata == NULL ||
        metadata == NULL) {
        return -1;
    }
    return WlgrIfChildReadSeal(production->sealed_metadata, metadata);
}

int WlgrIfSerializeStockReceipt(const WlascStockStageReceiptV1 *receipt,
                                uint8_t *out, size_t capacity)
{
    size_t offset = 0;
    size_t index;

    if (!StockReceiptValid(receipt) || out == NULL ||
        capacity < WLGR_IF_STOCK_RECEIPT_CANONICAL_SIZE) {
        return -1;
    }
#define PUT32(value) do { PutLe32(out + offset, (value)); offset += 4; } while (0)
#define PUT64(value) do { PutLe64(out + offset, (value)); offset += 8; } while (0)
    PUT32(receipt->abi_version);
    PUT32(receipt->struct_size);
    PUT64(receipt->runtime_generation);
    PUT32(receipt->message_id);
    PUT32(receipt->parent_stage_tail_reached);
    PUT32(receipt->child_stage_tail_reached);
    PUT32(receipt->bypass_guard_passed);
    PUT32(receipt->security_owner_stock_appspawn);
    PUT32(receipt->parent_tail_priority);
    PUT32(receipt->child_tail_priority);
    for (index = 0; index < 2; ++index) {
        PUT32(receipt->reserved_zero[index]);
    }
#undef PUT64
#undef PUT32
    return offset == WLGR_IF_STOCK_RECEIPT_CANONICAL_SIZE ? 0 : -1;
}

int WlgrIfDigestStockReceipt(const WlascStockStageReceiptV1 *receipt,
                             uint8_t out[WLGR_V2_SHA256_SIZE])
{
    uint8_t canonical[WLGR_IF_STOCK_RECEIPT_CANONICAL_SIZE];
    WlSha256Context sha;

    if (out == NULL ||
        WlgrIfSerializeStockReceipt(receipt, canonical,
                                    sizeof(canonical)) != 0) {
        return -1;
    }
    WLSha256Init(&sha);
    WLSha256Update(&sha, canonical, sizeof(canonical));
    return WLSha256Final(&sha, out);
}

int WlgrIfProductionReadReceipt(void *context,
                                WlgrIfSpecializationReceipt *out)
{
    WlgrIfProductionContext *production =
        (WlgrIfProductionContext *)context;
    westlake_runtime_instance_key_v2 key;

    if (production == NULL || out == NULL ||
        production->child_request == NULL ||
        production->stock_receipt == NULL ||
        production->sealed_metadata == NULL ||
        !StockReceiptValid(production->stock_receipt) ||
        !WlgrIfValidateMetadata(production->sealed_metadata) ||
        production->stock_receipt->runtime_generation !=
            production->child_request->launch_generation ||
        production->sealed_metadata->launch_generation !=
            production->child_request->launch_generation ||
        !RequestKey(production->child_request, &key)) {
        return -1;
    }
    memset(out, 0, sizeof(*out));
    out->magic = WLGR_IF_RECEIPT_MAGIC;
    out->abi_version = WLGR_IF_ABI_VERSION;
    out->struct_size = sizeof(*out);
    out->runtime_key = key;
    memcpy(out->boot_id, production->sealed_metadata->boot_id,
           sizeof(out->boot_id));
    memcpy(out->artifact_generation,
           production->sealed_metadata->artifact_generation,
           sizeof(out->artifact_generation));
    out->policy_epoch = production->sealed_metadata->policy_epoch;
    out->child_pid = production->child_request->child_pid;
    out->child_proc_start_time_ticks =
        production->child_request->child_proc_start_time_ticks;
    return WlgrIfDigestStockReceipt(production->stock_receipt,
                                    out->stock_receipt_digest);
}

int WlgrIfProductionReadHook(void *context, WlgrIfHookContract *out)
{
    WlgrIfProductionContext *production =
        (WlgrIfProductionContext *)context;

    if (production == NULL || production->published_hook == NULL ||
        out == NULL ||
        !WlgrIfValidateHook(production->published_hook)) {
        return -1;
    }
    *out = *production->published_hook;
    return 0;
}

int WlgrIfProduceHookSchemaDigest(uint8_t out[WLGR_V2_SHA256_SIZE])
{
    static const uint8_t descriptor[] = "WL-HOOK-V1-CANONICAL";
    uint8_t canonical[64];
    WlSha256Context sha;

    if (out == NULL) {
        return -1;
    }
    memset(canonical, 0, sizeof(canonical));
    memcpy(canonical, descriptor, sizeof(descriptor) - 1);
    memcpy(canonical + 32, "cap=0x3ff;ptr=8;align=8", 24);
    WLSha256Init(&sha);
    WLSha256Update(&sha, canonical, sizeof(canonical));
    return WLSha256Final(&sha, out);
}

int WlgrIfParentSeal(const WlgrIfGenerationMetadata *input,
                     WlgrIfGenerationMetadata *sealed)
{
    if (!WlgrIfValidateMetadata(input) || sealed == NULL) {
        return -1;
    }
    memcpy(sealed, input, sizeof(*sealed));
    return 0;
}

int WlgrIfChildReadSeal(const WlgrIfGenerationMetadata *sealed,
                        WlgrIfGenerationMetadata *out)
{
    if (!WlgrIfValidateMetadata(sealed) || out == NULL) {
        return -1;
    }
    memcpy(out, sealed, sizeof(*out));
    return 0;
}

int WlgrIfProductionContextInit(
    WlgrIfProductionContext *context,
    const WlgrIfChildRequest *request,
    const WlascStockStageReceiptV1 *stock_receipt,
    const WlgrIfGenerationMetadata *sealed_metadata,
    const WlgrIfHookContract *published_hook)
{
    const WlscplManifestV2 *manifest;
    westlake_runtime_instance_key_v2 key;

    if (context == NULL || request == NULL ||
        !RequestKey(request, &key) ||
        !StockReceiptValid(stock_receipt) ||
        !WlgrIfValidateMetadata(sealed_metadata) ||
        !WlgrIfValidateHook(published_hook) ||
        stock_receipt->runtime_generation != request->launch_generation ||
        sealed_metadata->launch_generation != request->launch_generation) {
        return -1;
    }
    manifest = WLSCPL_GetBuildGeneratedManifest();
    if (manifest == NULL || manifest->abi_version != WLSCPL_ABI_VERSION ||
        manifest->struct_size != sizeof(*manifest) ||
        !BytesNonzero(manifest->manifest_digest, WLGR_V2_SHA256_SIZE) ||
        !wlgr_v2_bytes_equal(manifest->manifest_digest,
                             sealed_metadata->artifact_manifest_digest,
                             WLGR_V2_SHA256_SIZE) ||
        !wlgr_v2_bytes_equal(published_hook->schema_digest,
                             sealed_metadata->hook_schema_digest,
                             WLGR_V2_SHA256_SIZE)) {
        return -1;
    }
    memset(context, 0, sizeof(*context));
    context->child_request = request;
    context->stock_receipt = stock_receipt;
    context->sealed_metadata = sealed_metadata;
    context->published_hook = published_hook;
    context->build_manifest = manifest;
    return 0;
}

int WlgrIfProductionOps(WlgrIfProductionContext *context, WlgrIfOps *ops)
{
    if (context == NULL || ops == NULL ||
        context->child_request == NULL ||
        context->stock_receipt == NULL ||
        context->sealed_metadata == NULL ||
        context->published_hook == NULL ||
        context->build_manifest == NULL) {
        return -1;
    }
    memset(ops, 0, sizeof(*ops));
    ops->context = context;
    ops->read_boot_id = WlgrIfProductionReadBootId;
    ops->read_process = WlgrIfProductionReadProcess;
    ops->read_metadata = WlgrIfProductionReadMetadata;
    ops->read_receipt = WlgrIfProductionReadReceipt;
    ops->read_manifest = WlgrIfProductionReadManifest;
    ops->read_hook = WlgrIfProductionReadHook;
    ops->random_bytes = WlgrIfProductionRandom;
    return 0;
}
