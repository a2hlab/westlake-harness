#include "westlake_generation_identity_facts.h"
#include "westlake_sha256.h"

#include <stdio.h>
#include <string.h>

#define CHECK(expression) do { \
    if (!(expression)) { \
        fprintf(stderr, "FAIL:%d:%s\n", __LINE__, #expression); \
        return 1; \
    } \
} while (0)

int main(void)
{
    uint8_t boot_id[WLGR_V2_BOOT_ID_SIZE];
    uint8_t digest[WLGR_V2_SHA256_SIZE];
    WlgrIfGenerationMetadata metadata;
    WlgrIfHookContract hook;

    memset(boot_id, 0, sizeof(boot_id));
    CHECK(WlgrIfParseBootId(
              "01234567-89ab-cdef-0123-456789abcdef", boot_id));
    CHECK(boot_id[0] == UINT8_C(0x01) &&
          boot_id[15] == UINT8_C(0xef));
    CHECK(!WlgrIfParseBootId(
              "0123456789ab-cdef-0123-456789abcdef", boot_id));

    memset(&metadata, 0, sizeof(metadata));
    metadata.magic = WLGR_IF_METADATA_MAGIC;
    metadata.abi_version = WLGR_IF_ABI_VERSION;
    metadata.struct_size = sizeof(metadata);
    memset(metadata.boot_id, 1, sizeof(metadata.boot_id));
    memset(metadata.artifact_generation, 2,
           sizeof(metadata.artifact_generation));
    metadata.policy_epoch = UINT64_C(7);
    metadata.launch_generation = UINT64_C(11);
    memset(metadata.artifact_manifest_digest, 3,
           sizeof(metadata.artifact_manifest_digest));
    memset(metadata.hook_schema_digest, 4,
           sizeof(metadata.hook_schema_digest));
    memset(metadata.policy_provenance_digest, 5,
           sizeof(metadata.policy_provenance_digest));
    CHECK(WlgrIfDigestMetadata(&metadata, digest) == 0);
    memcpy(metadata.metadata_digest, digest,
           sizeof(metadata.metadata_digest));
    CHECK(WlgrIfValidateMetadata(&metadata));
    metadata.launch_generation = UINT64_C(12);
    CHECK(!WlgrIfValidateMetadata(&metadata));
    metadata.launch_generation = UINT64_C(11);
    memcpy(metadata.artifact_generation,
           metadata.artifact_manifest_digest,
           sizeof(metadata.artifact_generation));
    CHECK(WlgrIfDigestMetadata(&metadata, metadata.metadata_digest) == 0);
    CHECK(!WlgrIfValidateMetadata(&metadata));

    memset(&hook, 0, sizeof(hook));
    hook.magic = WLGR_IF_HOOK_MAGIC;
    hook.abi_version = WLGR_IF_ABI_VERSION;
    hook.struct_size = sizeof(hook);
    hook.capability_bitmap = WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP;
    hook.data_pointer_size = (uint16_t)sizeof(void *);
    hook.function_pointer_size = (uint16_t)sizeof(void (*)(void));
    hook.data_pointer_alignment = (uint16_t)_Alignof(void *);
    hook.function_pointer_alignment =
        (uint16_t)_Alignof(void (*)(void));
    memset(hook.schema_digest, 5, sizeof(hook.schema_digest));
    CHECK(WlgrIfValidateHook(&hook));
    hook.capability_bitmap = UINT64_C(0);
    CHECK(!WlgrIfValidateHook(&hook));

    puts("RESULT PASS tests=9");
    return 0;
}
