#include "sealed_child_provider_loader.h"

/* Test-only helper declaration intentionally kept out of the frozen public
 * loader header so its production hash and ABI remain stable. */
int WLSCPL_ComputeManifestDigestForTest(
    const WlscplManifestV2 *manifest,
    uint8_t digest[WLGR_V2_SHA256_SIZE]);

#include <dlfcn.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define TEST_ELF_MACHINE_AARCH64 UINT16_C(183)

typedef struct TestContext {
    uint64_t pid;
    int verify_fail_at;
    int premapped_at;
    int external_unmapped;
    int open_fail_at;
    int swap_at;
    int verify_calls;
    int mapping_calls;
    int open_calls;
    int mapped_match_calls;
    int verified_close_calls;
    int bad_flags;
    const char *opened[4];
} TestContext;

static int failures;
static int tests_run;

static uint64_t CurrentPid(void *opaque)
{
    return ((TestContext *)opaque)->pid;
}

static int Verify(void *opaque, const WlscplArtifactV2 *artifact,
                  uint16_t machine, WlscplVerifiedObjectV2 *verified)
{
    TestContext *context = (TestContext *)opaque;
    int call = context->verify_calls++;
    if (artifact == NULL || verified == NULL ||
        machine != TEST_ELF_MACHINE_AARCH64 ||
        call == context->verify_fail_at) return -1;
    verified->descriptor_token = (int64_t)(100 + call);
    verified->device = UINT64_C(7);
    verified->inode = (uint64_t)(900 + call);
    verified->size = UINT64_C(4096);
    return 0;
}

static int MappingState(void *opaque, const WlscplArtifactV2 *artifact,
                        const WlscplVerifiedObjectV2 *verified)
{
    TestContext *context = (TestContext *)opaque;
    int call = context->mapping_calls++;
    if (artifact == NULL || verified == NULL) return -1;
    if (artifact->artifact_kind == WLSCPL_ARTIFACT_OH_SYSTEM_ROOT)
        return context->external_unmapped ? 0 : 1;
    return call == context->premapped_at ? 1 : 0;
}

static void *OpenVerified(void *opaque, const WlscplArtifactV2 *artifact,
                          const WlscplVerifiedObjectV2 *verified, int flags)
{
    TestContext *context = (TestContext *)opaque;
    int call = context->open_calls++;
    if (artifact == NULL || verified == NULL ||
        verified->descriptor_token < 0 ||
        flags != (RTLD_NOW | RTLD_LOCAL)) context->bad_flags = 1;
    if (call < 4) context->opened[call] = artifact->absolute_path;
    return call == context->open_fail_at ? NULL :
        (void *)(uintptr_t)(UINT64_C(0x1000) + (uint64_t)call);
}

static int MappedIdentityMatches(
    void *opaque, const WlscplArtifactV2 *artifact,
    const WlscplVerifiedObjectV2 *verified, void *handle)
{
    TestContext *context = (TestContext *)opaque;
    int call = context->mapped_match_calls++;
    if (artifact == NULL || verified == NULL || handle == NULL) return -1;
    return call == context->swap_at ? -1 : 0;
}

static int CloseVerified(void *opaque, WlscplVerifiedObjectV2 *verified)
{
    TestContext *context = (TestContext *)opaque;
    if (verified == NULL || verified->descriptor_token < 0) return -1;
    verified->descriptor_token = -1;
    ++context->verified_close_calls;
    return 0;
}

static void FillHex(char *output, size_t digits, char digit)
{
    size_t index;
    for (index = 0U; index < digits; ++index) output[index] = digit;
    output[digits] = '\0';
}

static void FillBytes(uint8_t *output, size_t size, uint8_t value)
{
    (void)memset(output, value, size);
}

static void BuildIdentity(westlake_generation_identity_v2 *identity,
                          const uint8_t manifest_digest[WLGR_V2_SHA256_SIZE])
{
    (void)memset(identity, 0, sizeof(*identity));
    identity->magic = WLGR_V2_IDENTITY_MAGIC;
    identity->abi_version = WLGR_V2_ABI_VERSION;
    identity->struct_size = WLGR_V2_IDENTITY_SIZE;
    identity->struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    identity->runtime_key.magic = WLGR_V2_RUNTIME_KEY_MAGIC;
    identity->runtime_key.abi_version = WLGR_V2_ABI_VERSION;
    identity->runtime_key.struct_size = WLGR_V2_RUNTIME_KEY_SIZE;
    identity->runtime_key.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    identity->runtime_key.android_uid = UINT32_C(20000123);
    identity->runtime_key.launch_generation = UINT64_C(9);
    strcpy(identity->runtime_key.android_package, "com.example.test");
    strcpy(identity->runtime_key.android_process_name, "com.example.test");
    FillBytes(identity->boot_id, sizeof(identity->boot_id), UINT8_C(1));
    FillBytes(identity->artifact_generation,
              sizeof(identity->artifact_generation), UINT8_C(2));
    identity->policy_epoch = UINT64_C(3);
    identity->child_pid = UINT64_C(101);
    identity->child_proc_start_time_ticks = UINT64_C(555);
    FillBytes(identity->specialization_receipt_digest,
              sizeof(identity->specialization_receipt_digest), UINT8_C(4));
    (void)memcpy(identity->artifact_manifest_digest, manifest_digest,
                 WLGR_V2_SHA256_SIZE);
    FillBytes(identity->hook_schema_digest,
              sizeof(identity->hook_schema_digest), UINT8_C(5));
    FillBytes(identity->request_nonce,
              sizeof(identity->request_nonce), UINT8_C(6));
}

static bool ResealManifest(
    WlscplManifestV2 *manifest, westlake_generation_identity_v2 *identity)
{
    if (WLSCPL_ComputeManifestDigestForTest(
            manifest, manifest->manifest_digest) != 0)
        return false;
    (void)memcpy(identity->artifact_manifest_digest,
                 manifest->manifest_digest, WLGR_V2_SHA256_SIZE);
    return true;
}

static void BuildValid(WlscplArtifactV2 artifacts[4],
                       WlscplManifestV2 *manifest,
                       westlake_generation_identity_v2 *identity,
                       WlscplLoadRequestV2 *request,
                       TestContext *context)
{
    (void)memset(artifacts, 0, 4U * sizeof(*artifacts));
    artifacts[0].absolute_path = "/system/lib64/libc.so";
    strcpy(artifacts[0].soname, "libc.so");
    artifacts[0].artifact_kind = WLSCPL_ARTIFACT_OH_SYSTEM_ROOT;
    artifacts[1].absolute_path = "/sealed/libdep2.so";
    strcpy(artifacts[1].soname, "libdep2.so");
    artifacts[1].artifact_kind = WLSCPL_ARTIFACT_SEALED_LOAD;
    artifacts[1].needed_count = 1U;
    artifacts[1].needed_indices[0] = 0U;
    artifacts[2].absolute_path = "/sealed/libdep1.so";
    strcpy(artifacts[2].soname, "libdep1.so");
    artifacts[2].artifact_kind = WLSCPL_ARTIFACT_SEALED_LOAD;
    artifacts[2].needed_count = 1U;
    artifacts[2].needed_indices[0] = 1U;
    artifacts[3].absolute_path =
        "/sealed/libwestlake_android_runtime_provider.so";
    strcpy(artifacts[3].soname, WLSCPL_PROVIDER_SONAME);
    artifacts[3].artifact_kind = WLSCPL_ARTIFACT_SEALED_LOAD;
    artifacts[3].needed_count = 1U;
    artifacts[3].needed_indices[0] = 2U;
    FillHex(artifacts[0].sha256_hex, 64U, '1');
    FillHex(artifacts[0].build_id_hex, 32U, '8');
    FillHex(artifacts[1].sha256_hex, 64U, '2');
    FillHex(artifacts[2].sha256_hex, 64U, '3');
    FillHex(artifacts[3].sha256_hex, 64U, '4');
    FillHex(artifacts[1].build_id_hex, 40U, '5');
    FillHex(artifacts[2].build_id_hex, 40U, '6');
    FillHex(artifacts[3].build_id_hex, 40U, '7');
    (void)memset(manifest, 0, sizeof(*manifest));
    manifest->abi_version = WLSCPL_ABI_VERSION;
    manifest->struct_size = sizeof(*manifest);
    manifest->elf_machine = TEST_ELF_MACHINE_AARCH64;
    manifest->artifact_count = 4U;
    manifest->root_index = 3U;
    manifest->external_root_count = 1U;
    manifest->artifacts = artifacts;
    if (WLSCPL_ComputeManifestDigestForTest(
            manifest, manifest->manifest_digest) != 0)
        FillBytes(manifest->manifest_digest,
                  sizeof(manifest->manifest_digest), UINT8_C(0));
    BuildIdentity(identity, manifest->manifest_digest);
    (void)memset(request, 0, sizeof(*request));
    request->abi_version = WLSCPL_ABI_VERSION;
    request->struct_size = sizeof(*request);
    request->specialization_complete = 1U;
    request->hook_table_ready = 1U;
    request->generation_seal_verified = 1U;
    request->parent_pid = UINT64_C(100);
    request->generation_identity = identity;
    request->manifest = manifest;
    (void)memset(context, 0, sizeof(*context));
    context->pid = identity->child_pid;
    context->verify_fail_at = -1;
    context->premapped_at = -1;
    context->open_fail_at = -1;
    context->swap_at = -1;
}

static WlscplError Load(WlscplLoaderV2 *loader,
                        WlscplLoadRequestV2 *request,
                        WlscplLoadResultV2 *result,
                        TestContext *context)
{
    WlscplTestOpsV2 ops = {
        CurrentPid, Verify, MappingState, OpenVerified,
        MappedIdentityMatches, CloseVerified, context
    };
    return WLSCPL_LoadSealedProviderForTest(loader, request, result, &ops);
}

#define DECLARE_FIXTURE() \
    WlscplArtifactV2 a[4]; WlscplManifestV2 m; \
    westlake_generation_identity_v2 i; WlscplLoadRequestV2 r; \
    WlscplLoaderV2 l = {0}; WlscplLoadResultV2 result; TestContext c; \
    BuildValid(a, &m, &i, &r, &c)

static bool Positive(void)
{
    DECLARE_FIXTURE();
    return Load(&l, &r, &result, &c) == WLSCPL_OK &&
        l.state == WLSCPL_STATE_LOADED &&
        result.validated_artifact_count == 4U &&
        result.mapped_artifact_count == 3U &&
        result.constructor_completed_count == 3U &&
        result.constructor_timing ==
            WLSCPL_CONSTRUCTORS_COMPLETE_BEFORE_DLOPEN_RETURN &&
        result.provider_handle == l.handles[2] &&
        wlgr_v2_identity_equal(&result.generation_identity, &i) &&
        c.verify_calls == 4 && c.mapping_calls == 4 &&
        c.open_calls == 3 && c.mapped_match_calls == 3 &&
        c.verified_close_calls == 4 && c.bad_flags == 0;
}

static bool ParentRejected(void)
{ DECLARE_FIXTURE(); c.pid = r.parent_pid;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_NOT_SPECIALIZED_CHILD && c.open_calls==0; }
static bool SpecializationRejected(void)
{ DECLARE_FIXTURE(); r.specialization_complete=0;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_NOT_SPECIALIZED_CHILD && c.verify_calls==0; }
static bool HookRejected(void)
{ DECLARE_FIXTURE(); r.hook_table_ready=0;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_HOOK_TABLE_NOT_READY && c.verify_calls==0; }
static bool SealRejected(void)
{ DECLARE_FIXTURE(); r.generation_seal_verified=0;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_SEAL_NOT_VERIFIED && c.verify_calls==0; }
static bool FullGenerationRejected(void)
{ DECLARE_FIXTURE(); i.artifact_manifest_digest[0]^=UINT8_C(1);
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY && c.verify_calls==0; }
static bool TruncatedGenerationRejected(void)
{ DECLARE_FIXTURE(); i.artifact_generation[8]=UINT8_C(0); i.artifact_generation[9]=UINT8_C(0);
  return Load(&l,&r,&result,&c)==WLSCPL_OK &&
    result.generation_identity.artifact_generation[31]==UINT8_C(2); }
static bool RelativePathRejected(void)
{ DECLARE_FIXTURE(); a[1].absolute_path="libdep2.so";
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY && c.open_calls==0; }
static bool BadHashRejected(void)
{ DECLARE_FIXTURE(); a[1].sha256_hex[0]='A';
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY; }
static bool ManifestContentMutationRejected(void)
{ DECLARE_FIXTURE(); a[1].absolute_path="/sealed/other-libdep2.so";
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool ExternalBuildIdRejected(void)
{ DECLARE_FIXTURE(); a[0].build_id_hex[0]='\0';
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool BuildId32AllZeroRejected(void)
{ DECLARE_FIXTURE(); FillHex(a[0].build_id_hex,32U,'0');
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool BuildId40AllZeroRejected(void)
{ DECLARE_FIXTURE(); FillHex(a[1].build_id_hex,40U,'0');
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool BuildId31Rejected(void)
{ DECLARE_FIXTURE(); FillHex(a[0].build_id_hex,31U,'8');
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool BuildId33Rejected(void)
{ DECLARE_FIXTURE(); FillHex(a[0].build_id_hex,33U,'8');
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool BuildId39Rejected(void)
{ DECLARE_FIXTURE(); FillHex(a[1].build_id_hex,39U,'5');
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool BuildId41Rejected(void)
{ DECLARE_FIXTURE(); FillHex(a[1].build_id_hex,41U,'5');
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool BuildIdUppercaseRejected(void)
{ DECLARE_FIXTURE(); a[1].build_id_hex[0]='A';
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY &&
    c.verify_calls==0; }
static bool DuplicateSonameRejected(void)
{ DECLARE_FIXTURE(); strcpy(a[2].soname,a[1].soname);
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY; }
static bool WrongRootRejected(void)
{ DECLARE_FIXTURE(); m.root_index=2;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_GENERATION_IDENTITY; }
static bool OrphanRejected(void)
{ DECLARE_FIXTURE(); a[3].needed_indices[0]=1; if (!ResealManifest(&m,&i)) return false;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_CLOSURE_INVALID; }
static bool CycleRejected(void)
{ DECLARE_FIXTURE(); a[0].needed_count=1; a[0].needed_indices[0]=3;
  if (!ResealManifest(&m,&i)) return false;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_CLOSURE_INVALID; }
static bool IdentityRejectedBeforeOpen(void)
{ DECLARE_FIXTURE(); c.verify_fail_at=2;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_ARTIFACT_IDENTITY && c.open_calls==0; }
static bool PremappedRejectedBeforeOpen(void)
{ DECLARE_FIXTURE(); c.premapped_at=2;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_PREMATURE_MAPPING && c.open_calls==0; }
static bool InheritedRegistryAccepted(void)
{ DECLARE_FIXTURE();
  a[1].absolute_path="/system/lib64/libwestlake_thread_guard_registry.so";
  strcpy(a[1].soname,"libwestlake_thread_guard_registry.so");
  c.premapped_at=1; if (!ResealManifest(&m,&i)) return false;
  return Load(&l,&r,&result,&c)==WLSCPL_OK &&
    result.validated_artifact_count==4U && result.mapped_artifact_count==2U &&
    c.open_calls==2 && c.mapped_match_calls==2; }
static bool InheritedRegistryMissingRejected(void)
{ DECLARE_FIXTURE();
  a[1].absolute_path="/system/lib64/libwestlake_thread_guard_registry.so";
  strcpy(a[1].soname,"libwestlake_thread_guard_registry.so");
  if (!ResealManifest(&m,&i)) return false;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_EXTERNAL_ROOT && c.open_calls==0; }
static bool ExternalRootRejected(void)
{ DECLARE_FIXTURE(); c.external_unmapped=1;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_EXTERNAL_ROOT && c.open_calls==0; }
static bool SwapBetweenVerifyAndMapRejected(void)
{ DECLARE_FIXTURE(); c.swap_at=1;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_MAPPED_IDENTITY &&
    c.open_calls==2 && l.handle_count==2 &&
    l.constructor_completed_count==2 &&
    l.state==WLSCPL_STATE_FAILED_AFTER_CONSTRUCTORS; }
static bool PartialOpenNeverDlcloses(void)
{ DECLARE_FIXTURE(); c.open_fail_at=2;
  return Load(&l,&r,&result,&c)==WLSCPL_ERROR_DLOPEN &&
    l.handle_count==2 && l.constructor_completed_count==2 &&
    result.mapped_artifact_count==2 &&
    result.constructor_timing==WLSCPL_CONSTRUCTORS_COMPLETE_BEFORE_DLOPEN_RETURN &&
    l.state==WLSCPL_STATE_FAILED_AFTER_CONSTRUCTORS; }
static bool ReplayRejected(void)
{ DECLARE_FIXTURE();
  return Load(&l,&r,&result,&c)==WLSCPL_OK &&
    Load(&l,&r,&result,&c)==WLSCPL_ERROR_ALREADY_ATTEMPTED && c.open_calls==3; }

static void Run(const char *name, bool (*test)(void))
{
    ++tests_run;
    if (!test()) { ++failures; fprintf(stderr, "FAIL %s\n", name); }
}

int main(void)
{
    Run("positive_bound_inode_local_now", Positive);
    Run("parent_rejected", ParentRejected);
    Run("specialization_rejected", SpecializationRejected);
    Run("hook_not_ready", HookRejected);
    Run("seal_not_verified", SealRejected);
    Run("full_manifest_generation_mismatch", FullGenerationRejected);
    Run("full_32_byte_generation_preserved", TruncatedGenerationRejected);
    Run("relative_path", RelativePathRejected);
    Run("bad_hash", BadHashRejected);
    Run("manifest_content_digest_mutation", ManifestContentMutationRejected);
    Run("external_build_id_policy", ExternalBuildIdRejected);
    Run("build_id_32_all_zero", BuildId32AllZeroRejected);
    Run("build_id_40_all_zero", BuildId40AllZeroRejected);
    Run("build_id_31_invalid_length", BuildId31Rejected);
    Run("build_id_33_invalid_length", BuildId33Rejected);
    Run("build_id_39_invalid_length", BuildId39Rejected);
    Run("build_id_41_invalid_length", BuildId41Rejected);
    Run("build_id_uppercase", BuildIdUppercaseRejected);
    Run("duplicate_soname", DuplicateSonameRejected);
    Run("wrong_root", WrongRootRejected);
    Run("orphan_closure", OrphanRejected);
    Run("cycle_closure", CycleRejected);
    Run("identity_before_open", IdentityRejectedBeforeOpen);
    Run("premapped_before_open", PremappedRejectedBeforeOpen);
    Run("inherited_registry_exact_inode", InheritedRegistryAccepted);
    Run("inherited_registry_missing", InheritedRegistryMissingRejected);
    Run("external_root_must_be_premapped_bound", ExternalRootRejected);
    Run("swap_between_verify_and_map", SwapBetweenVerifyAndMapRejected);
    Run("partial_open_no_dlclose_after_constructors", PartialOpenNeverDlcloses);
    Run("replay", ReplayRejected);
    if (failures != 0) return 1;
    printf("RESULT PASS tests=%d\n", tests_run);
    return 0;
}
