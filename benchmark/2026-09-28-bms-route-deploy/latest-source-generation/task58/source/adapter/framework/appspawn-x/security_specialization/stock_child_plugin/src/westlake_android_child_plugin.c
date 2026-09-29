#if defined(WLASC_PROVIDER_ENTRY_TEST_ONLY)
#include <stdint.h>

typedef struct WlascAndroidChildRequestV1 {
    uint8_t test_opaque;
} WlascAndroidChildRequestV1;
typedef struct WlascStockStageReceiptV1 {
    uint8_t test_opaque;
} WlascStockStageReceiptV1;
typedef struct WlascHostRuntimeServicesV1 {
    uint8_t test_opaque;
} WlascHostRuntimeServicesV1;
#else
#include "westlake_stock_host_services.h"
#include "westlake_child_hook_table_v1.h"
#include "sealed_child_provider_loader.h"
#endif

#include <dlfcn.h>
#include <stddef.h>
#include <string.h>
#if !defined(WLASC_PROVIDER_ENTRY_TEST_ONLY)
#include <unistd.h>

typedef int (*WlascHiLogPrintFn)(int type, int level, unsigned int domain,
                                 const char *tag, const char *fmt, ...);

static void WlascGateMarker(const char *text, size_t length)
{
    WlascHiLogPrintFn print_log = (WlascHiLogPrintFn)0;
    void *symbol;

    (void)write(STDERR_FILENO, text, length);
    (void)write(STDERR_FILENO, "\n", 1U);
    symbol = dlsym(RTLD_DEFAULT, "HiLogPrint");
    if (symbol == (void *)0 || sizeof(symbol) != sizeof(print_log)) {
        return;
    }
    memcpy(&print_log, &symbol, sizeof(print_log));
    if (print_log != (WlascHiLogPrintFn)0) {
        (void)print_log(3, 4, UINT32_C(0xD002C11), "APPSPAWN",
                        "%{public}s", text);
    }
}

static void WlascGateMarkerValue(const char *text, uint32_t value)
{
    WlascHiLogPrintFn print_log = (WlascHiLogPrintFn)0;
    void *symbol = dlsym(RTLD_DEFAULT, "HiLogPrint");

    if (symbol == (void *)0 || sizeof(symbol) != sizeof(print_log)) {
        return;
    }
    memcpy(&print_log, &symbol, sizeof(print_log));
    if (print_log != (WlascHiLogPrintFn)0) {
        (void)print_log(3, 4, UINT32_C(0xD002C11), "APPSPAWN",
                        "%{public}s:%{public}u", text, value);
    }
}

#define WLASC_GATE_MARKER(text) WlascGateMarker(text, sizeof(text) - 1U)
#endif

typedef int (*WlascProviderChildEntryV1)(
    const WlascAndroidChildRequestV1 *request,
    const WlascStockStageReceiptV1 *stock_receipt);
typedef int (*WlascProviderInstallServicesV1)(
    const WlascHostRuntimeServicesV1 *services);
typedef void *(*WlascProviderSymbolResolverV1)(
    void *handle, const char *symbol);

static int InvokeProviderChildEntryWithResolver(
    void *provider_handle,
    const WlascHostRuntimeServicesV1 *services,
    const WlascAndroidChildRequestV1 *request,
    const WlascStockStageReceiptV1 *receipt,
    WlascProviderSymbolResolverV1 resolver)
{
    WlascProviderInstallServicesV1 install =
        (WlascProviderInstallServicesV1)0;
    WlascProviderChildEntryV1 entry =
        (WlascProviderChildEntryV1)0;
    int install_result;
    int entry_result;
    void *install_symbol;
    void *entry_symbol;

    if (provider_handle == (void *)0 ||
        services == (const WlascHostRuntimeServicesV1 *)0 ||
        request == (const WlascAndroidChildRequestV1 *)0 ||
        receipt == (const WlascStockStageReceiptV1 *)0 || resolver == 0) {
        return -1;
    }
    install_symbol = resolver(provider_handle,
                              "WLAR_InstallHostRuntimeServices");
    entry_symbol = resolver(provider_handle,
                            "WLAR_EnterAndroidAfterStockSpecialization");
    if (install_symbol == (void *)0 || entry_symbol == (void *)0 ||
        sizeof(install_symbol) != sizeof(install) ||
        sizeof(entry_symbol) != sizeof(entry)) {
        return -1;
    }
    memcpy(&install, &install_symbol, sizeof(install));
    memcpy(&entry, &entry_symbol, sizeof(entry));
    if (install == (WlascProviderInstallServicesV1)0 ||
        entry == (WlascProviderChildEntryV1)0) {
        return -1;
    }
    install_result = install(services);
#if !defined(WLASC_PROVIDER_ENTRY_TEST_ONLY)
    WlascGateMarkerValue("WLCGATE:PROVIDER:INSTALL_RESULT",
                         (uint32_t)install_result);
#endif
    if (install_result != 0) {
        return -1;
    }
    entry_result = entry(request, receipt);
#if !defined(WLASC_PROVIDER_ENTRY_TEST_ONLY)
    WlascGateMarkerValue("WLCGATE:PROVIDER:ENTRY_RESULT",
                         (uint32_t)entry_result);
#endif
    return entry_result == 0 ? 0 : -1;
}

#if !defined(WLASC_PROVIDER_ENTRY_TEST_ONLY)
static void *ResolveProviderChildSymbol(void *handle, const char *symbol)
{
    return dlsym(handle, symbol);
}

/* Exact, project-local OH v7 private ABI. Never replace with guessed fields. */
#include "appspawn_manager.h"

#define WLASC_GUARD_PRIORITY (HOOK_PRIO_SANDBOX - 1)
#define WLASC_REG_PRELOAD UINT32_C(0x01)
#define WLASC_REG_PARENT_TAIL UINT32_C(0x02)
#define WLASC_REG_CHILD_GUARD UINT32_C(0x04)
#define WLASC_REG_CHILD_TAIL UINT32_C(0x08)
#define WLASC_REG_ALL UINT32_C(0x0f)

#ifndef WLASC_PLUGIN_GENERATION_SHA_HEX
#error "WLASC_PLUGIN_GENERATION_SHA_HEX must bind the plugin input closure"
#endif
#ifndef WLASC_PLUGIN_BUILD_ID_HEX
#error "WLASC_PLUGIN_BUILD_ID_HEX must bind the plugin ELF Build-ID"
#endif
#ifndef WLAR_GENERATION_SHA_HEX
#error "WLAR_GENERATION_SHA_HEX must bind the runtime provider generation"
#endif

_Static_assert(offsetof(AppSpawnMgr, content) == 0,
               "OH AppSpawnMgr prefix ABI drift");
_Static_assert(offsetof(AppSpawningCtx, client) == 0,
               "OH AppSpawningCtx prefix ABI drift");
_Static_assert(sizeof(AppSpawnMsg) == 276,
               "OH AppSpawnMsg ABI drift");
_Static_assert(sizeof(AppDacInfo) == 332,
               "OH AppDacInfo ABI drift");
_Static_assert(sizeof(WlascHostRuntimeServicesV1) == 128,
               "host runtime services ABI drift");
_Static_assert(sizeof(WlascStockHostServicesV1) == 256,
               "stock host services ABI drift");

typedef enum WlascStockServicesState {
    WLASC_STOCK_SERVICES_EMPTY = 0,
    WLASC_STOCK_SERVICES_INSTALLING = 1,
    WLASC_STOCK_SERVICES_INSTALLED = 2,
    WLASC_STOCK_SERVICES_FAILED = 3
} WlascStockServicesState;

static uint32_t g_registration_mask;
static uint32_t g_stock_services_state;
static WlascStockHostServicesV1 g_stock_host_services;
static WlascStageLedgerV1 g_stage_ledger;
static westlake_child_hook_control_v1 g_child_hook_control;
static westlake_child_hook_table_v1 g_child_hook_table;
static WlscplLoaderV1 g_sealed_child_loader;

/* Private same-binary construction seam; never exported from the plugin. */
int32_t westlake_child_hook_table_v1_prepare_candidate(
    westlake_child_hook_table_v1 *candidate,
    const uint8_t generation_digest[
        WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE],
    uint64_t owner_cookie);

static const WlascContractV1 g_contract = {
    WLASC_ABI_VERSION,
    (uint32_t)sizeof(WlascContractV1),
    WLASC_PRELOAD_PRIORITY,
    WLASC_PARENT_STAGE,
    WLASC_CHILD_STAGE,
    WLASC_TAIL_PRIORITY,
    WLASC_FLAG_NO_SANDBOX,
    WLASC_FLAG_IGNORE_SANDBOX,
    UINT32_C(1),
    UINT32_C(1),
    (uint32_t)sizeof(WlascAndroidChildRequestV1),
    (uint32_t)sizeof(WlascStockStageReceiptV1),
};

static void ZeroBytes(void *memory, size_t size)
{
    uint8_t *bytes = (uint8_t *)memory;
    size_t index;
    for (index = 0; index < size; ++index) {
        bytes[index] = UINT8_C(0);
    }
}

static int BytesAllZero(const uint8_t *bytes, size_t size)
{
    uint8_t value = UINT8_C(0);
    size_t index;
    for (index = 0; index < size; ++index) {
        value = (uint8_t)(value | bytes[index]);
    }
    return value == UINT8_C(0);
}

static int BytesEqual(const uint8_t *left, const uint8_t *right, size_t size)
{
    uint8_t difference = UINT8_C(0);
    size_t index;
    for (index = 0; index < size; ++index) {
        difference = (uint8_t)(difference | (left[index] ^ right[index]));
    }
    return difference == UINT8_C(0);
}

static uint8_t HexNibble(char value)
{
    if (value >= '0' && value <= '9') {
        return (uint8_t)(value - '0');
    }
    if (value >= 'a' && value <= 'f') {
        return (uint8_t)(value - 'a' + 10);
    }
    return UINT8_C(255);
}

static int BytesMatchHex(const uint8_t *bytes, size_t byte_count,
                         const char *hex, size_t hex_size)
{
    size_t index;
    if (bytes == (const uint8_t *)0 || hex == (const char *)0 ||
        hex_size != byte_count * 2U + 1U || hex[hex_size - 1U] != '\0') {
        return 0;
    }
    for (index = 0; index < byte_count; ++index) {
        uint8_t high = HexNibble(hex[index * 2U]);
        uint8_t low = HexNibble(hex[index * 2U + 1U]);
        if (high == UINT8_C(255) || low == UINT8_C(255) ||
            bytes[index] != (uint8_t)((high << 4U) | low)) {
            return 0;
        }
    }
    return 1;
}

static uint64_t GenerationFromHex(const char *hex)
{
    uint64_t generation = UINT64_C(0);
    size_t index;
    for (index = 0; index < 8U; ++index) {
        uint8_t high = HexNibble(hex[index * 2U]);
        uint8_t low = HexNibble(hex[index * 2U + 1U]);
        if (high == UINT8_C(255) || low == UINT8_C(255)) {
            return UINT64_C(0);
        }
        generation = (generation << 8U) |
            (uint64_t)((high << 4U) | low);
    }
    return generation;
}

static int StockServicesReady(void)
{
    return __atomic_load_n(&g_stock_services_state, __ATOMIC_ACQUIRE) ==
        WLASC_STOCK_SERVICES_INSTALLED;
}

static int FixedStringEquals(const char *left, const char *right,
                             size_t maximum)
{
    size_t index;
    for (index = 0; index < maximum; ++index) {
        if (left[index] != right[index]) {
            return 0;
        }
        if (left[index] == '\0') {
            return 1;
        }
    }
    return 0;
}

static int CopyFixedString(char *destination, size_t destination_size,
                           const char *source)
{
    size_t index;
    if (destination == (char *)0 || destination_size == 0U ||
        source == (const char *)0) {
        return -1;
    }
    for (index = 0; index + 1U < destination_size; ++index) {
        destination[index] = source[index];
        if (source[index] == '\0') {
            return index == 0U ? -1 : 0;
        }
    }
    destination[destination_size - 1U] = '\0';
    return -1;
}

static uint64_t ClientCookie(const AppSpawnClient *client)
{
    return (uint64_t)(uintptr_t)client;
}

static int ImmutableGenerationReady(void)
{
    return StockServicesReady() &&
           g_stock_host_services.runtime_generation != UINT64_C(0) &&
           !BytesAllZero(g_stock_host_services.runtime_provider_sha256,
                         WLASC_SHA256_SIZE);
}

static int StockServicesValid(const WlascStockHostServicesV1 *services)
{
    static const char plugin_generation_hex[] =
        WLASC_PLUGIN_GENERATION_SHA_HEX;
    static const char plugin_build_id_hex[] = WLASC_PLUGIN_BUILD_ID_HEX;
    static const char runtime_generation_hex[] = WLAR_GENERATION_SHA_HEX;
    return services != (const WlascStockHostServicesV1 *)0 &&
        services->abi_version == WLASC_STOCK_HOST_SERVICES_ABI_VERSION &&
        services->struct_size == sizeof(*services) &&
        services->runtime_generation ==
            GenerationFromHex(runtime_generation_hex) &&
        BytesMatchHex(services->runtime_provider_sha256,
                      WLASC_SHA256_SIZE, runtime_generation_hex,
                      sizeof(runtime_generation_hex)) &&
        BytesMatchHex(services->plugin_generation_sha256,
                      WLASC_SHA256_SIZE, plugin_generation_hex,
                      sizeof(plugin_generation_hex)) &&
        !BytesAllZero(services->plugin_elf_sha256,
                      sizeof(services->plugin_elf_sha256)) &&
        BytesMatchHex(services->plugin_build_id,
                      WLASC_BUILD_ID_SIZE, plugin_build_id_hex,
                      sizeof(plugin_build_id_hex)) &&
        services->reserved_identity_zero == UINT32_C(0) &&
        services->add_server_stage_hook != 0 &&
        services->add_app_spawn_hook != 0 &&
        services->get_app_spawn_msg_info != 0 &&
        services->check_app_spawn_msg_flag != 0 &&
        services->reg_child_looper != 0 &&
        services->clear_child_environment != 0 &&
        services->create_configured_namespaces != 0 &&
        services->open_namespace != 0;
}

static int RequiredSecurityTlvsPresent(const AppSpawningCtx *property)
{
    uint32_t type;
    if (property == (const AppSpawningCtx *)0 ||
        property->message == (AppSpawnMsgNode *)0) {
        return 0;
    }
    for (type = (uint32_t)TLV_BUNDLE_INFO;
         type <= (uint32_t)TLV_INTERNET_INFO; ++type) {
        if (g_stock_host_services.get_app_spawn_msg_info(
                property->message, (int)type) == (void *)0) {
            return 0;
        }
    }
    return 1;
}

static int BuildAndroidRequest(const AppSpawningCtx *property,
                               WlascAndroidChildRequestV1 *request)
{
    AppSpawnMsgBundleInfo *bundle;
    AppSpawnMsgFlags *flags;
    AppSpawnMsgDacInfo *dac;
    AppSpawnMsgDomainInfo *domain;
    AppSpawnMsgOwnerId *owner;
    AppSpawnMsgAccessToken *token;
    AppSpawnMsgInternetInfo *internet;
    uint32_t index;
    if (!StockServicesReady() || property == (const AppSpawningCtx *)0 ||
        property->message == (AppSpawnMsgNode *)0 ||
        request == (WlascAndroidChildRequestV1 *)0) {
        return -1;
    }
    bundle = (AppSpawnMsgBundleInfo *)g_stock_host_services.get_app_spawn_msg_info(
        property->message, TLV_BUNDLE_INFO);
    flags = (AppSpawnMsgFlags *)g_stock_host_services.get_app_spawn_msg_info(
        property->message, TLV_MSG_FLAGS);
    dac = (AppSpawnMsgDacInfo *)g_stock_host_services.get_app_spawn_msg_info(
        property->message, TLV_DAC_INFO);
    domain = (AppSpawnMsgDomainInfo *)g_stock_host_services.get_app_spawn_msg_info(
        property->message, TLV_DOMAIN_INFO);
    owner = (AppSpawnMsgOwnerId *)g_stock_host_services.get_app_spawn_msg_info(
        property->message, TLV_OWNER_INFO);
    token = (AppSpawnMsgAccessToken *)g_stock_host_services.get_app_spawn_msg_info(
        property->message, TLV_ACCESS_TOKEN_INFO);
    internet = (AppSpawnMsgInternetInfo *)g_stock_host_services.get_app_spawn_msg_info(
        property->message, TLV_INTERNET_INFO);
    if (bundle == (AppSpawnMsgBundleInfo *)0 ||
        flags == (AppSpawnMsgFlags *)0 || dac == (AppSpawnMsgDacInfo *)0 ||
        domain == (AppSpawnMsgDomainInfo *)0 ||
        owner == (AppSpawnMsgOwnerId *)0 ||
        token == (AppSpawnMsgAccessToken *)0 ||
        internet == (AppSpawnMsgInternetInfo *)0 ||
        flags->count != WLASC_FLAGS_WORDS ||
        dac->gidCount > WLASC_MAX_GIDS ||
        token->accessTokenIdEx == UINT64_C(0) ||
        internet->setAllowInternet > UINT8_C(1) ||
        internet->allowInternet > UINT8_C(1)) {
        return -1;
    }

    ZeroBytes(request, sizeof(*request));
    request->abi_version = WLASC_ABI_VERSION;
    request->struct_size = (uint32_t)sizeof(*request);
    request->message_type = property->message->msgHeader.msgType;
    request->message_id = property->message->msgHeader.msgId;
    request->runtime_generation = g_stock_host_services.runtime_generation;
    request->uid = dac->uid;
    request->gid = dac->gid;
    request->gid_count = dac->gidCount;
    for (index = 0; index < dac->gidCount; ++index) {
        request->gids[index] = dac->gidTable[index];
    }
    request->access_token_id_ex = token->accessTokenIdEx;
    request->hap_flags = domain->hapFlags;
    request->flags_word_count = flags->count;
    for (index = 0; index < WLASC_FLAGS_WORDS; ++index) {
        request->flags_words[index] = flags->flags[index];
    }
    request->set_allow_internet = internet->setAllowInternet;
    request->allow_internet = internet->allowInternet;
    if (CopyFixedString(request->process_name,
                        sizeof(request->process_name),
                        property->message->msgHeader.processName) != 0 ||
        CopyFixedString(request->bundle_name, sizeof(request->bundle_name),
                        bundle->bundleName) != 0 ||
        CopyFixedString(request->apl, sizeof(request->apl), domain->apl) != 0 ||
        CopyFixedString(request->owner_id, sizeof(request->owner_id),
                        owner->ownerId) != 0) {
        return -1;
    }
    return 0;
}

static int WestlakeParentPreForkTail(AppSpawnMgr *content,
                                     AppSpawningCtx *property)
{
    (void)content;
    if (!ImmutableGenerationReady() || property == (AppSpawningCtx *)0 ||
        property->message == (AppSpawnMsgNode *)0) {
        return -1;
    }
    return WLASC_ReceiptParentTail(
        &g_stage_ledger, g_stock_host_services.runtime_generation,
        ClientCookie(&property->client), property->client.id) ==
        WLASC_REASON_NONE ? 0 : -1;
}

static int WestlakeChildBypassGuard(AppSpawnMgr *content,
                                    AppSpawningCtx *property)
{
    int no_sandbox;
    int ignore_sandbox;
    (void)content;
    if (!StockServicesReady() || property == (AppSpawningCtx *)0 ||
        property->message == (AppSpawnMsgNode *)0) {
        return -1;
    }
    no_sandbox = g_stock_host_services.check_app_spawn_msg_flag(
        property->message, TLV_MSG_FLAGS, WLASC_FLAG_NO_SANDBOX);
    ignore_sandbox = g_stock_host_services.check_app_spawn_msg_flag(
        property->message, TLV_MSG_FLAGS, WLASC_FLAG_IGNORE_SANDBOX);
    return WLASC_ReceiptBypassGuard(
        &g_stage_ledger, ClientCookie(&property->client),
        (uint32_t)RequiredSecurityTlvsPresent(property),
        no_sandbox ? UINT32_C(1) : UINT32_C(0),
        ignore_sandbox ? UINT32_C(1) : UINT32_C(0)) ==
        WLASC_REASON_NONE ? 0 : -1;
}

static int WestlakeChildStageTail(AppSpawnMgr *content,
                                  AppSpawningCtx *property)
{
    (void)content;
    if (property == (AppSpawningCtx *)0) {
        return -1;
    }
    return WLASC_ReceiptChildTail(
        &g_stage_ledger, ClientCookie(&property->client)) ==
        WLASC_REASON_NONE ? 0 : -1;
}

static uint64_t ChildHookOwnerCookie(
    const WlascAndroidChildRequestV1 *request)
{
    uint64_t cookie = request->runtime_generation ^
        ((uint64_t)request->message_id << 32U) ^
        UINT64_C(0x574c484f4f4b4f57);

    return cookie == UINT64_C(0) ? UINT64_C(1) : cookie;
}

static uint64_t ChildHookEpoch(const WlascAndroidChildRequestV1 *request)
{
    uint64_t epoch = (uint64_t)request->message_id + UINT64_C(1);

    return epoch == UINT64_C(0) ? UINT64_C(1) : epoch;
}

static int PublishChildHookTable(const WlascAndroidChildRequestV1 *request)
{
    int32_t status;

    if (request == (const WlascAndroidChildRequestV1 *)0 ||
        request->runtime_generation !=
            g_stock_host_services.runtime_generation ||
        BytesAllZero(g_stock_host_services.runtime_provider_sha256,
                     WLASC_SHA256_SIZE)) {
        return -1;
    }
    status = westlake_child_hook_table_v1_prepare_candidate(
        &g_child_hook_table,
        g_stock_host_services.runtime_provider_sha256,
        ChildHookOwnerCookie(request));
    if (status != WESTLAKE_CHILD_HOOK_OK) {
        return -1;
    }
    status = westlake_child_hook_table_v1_begin_install(
        &g_child_hook_control, &g_child_hook_table,
        ChildHookEpoch(request));
    if (status != WESTLAKE_CHILD_HOOK_OK) {
        return -1;
    }
    status = westlake_child_hook_table_v1_publish(
        &g_child_hook_control, &g_child_hook_table);
    return status == WESTLAKE_CHILD_HOOK_OK &&
        __atomic_load_n(&g_child_hook_control.atomic_lifecycle_state,
                        __ATOMIC_ACQUIRE) ==
            WESTLAKE_CHILD_HOOK_READY &&
        __atomic_load_n(&g_child_hook_control.atomic_admission_open,
                        __ATOMIC_ACQUIRE) == UINT64_C(1) &&
        BytesEqual(g_child_hook_control.generation_digest,
                   g_stock_host_services.runtime_provider_sha256,
                   WLASC_SHA256_SIZE) ? 0 : -1;
}

static void RevokeChildHookTable(int32_t cause)
{
    if (__atomic_load_n(&g_child_hook_control.atomic_lifecycle_state,
                        __ATOMIC_ACQUIRE) !=
            WESTLAKE_CHILD_HOOK_READY) {
        return;
    }
    if (westlake_child_hook_table_v1_revoke(
            &g_child_hook_control, cause) != WESTLAKE_CHILD_HOOK_OK) {
        return;
    }
    (void)westlake_child_hook_table_v1_drain(&g_child_hook_control);
    (void)westlake_child_hook_table_v1_invalidate(
        &g_child_hook_control, UINT32_C(1));
}

static int LoadSealedProviderAfterHooks(
    const WlascAndroidChildRequestV1 *request,
    const WlascStockStageReceiptV1 *receipt)
{
    const WlscplManifestV1 *manifest;
    WlscplLoadRequestV1 load_request;
    WlscplLoadResultV1 load_result;
    WlscplError loader_error;
    WlascHostRuntimeServicesV1 child_services;
    uint64_t child_pid;
    uint64_t parent_pid;

    WLASC_GATE_MARKER("WLCGATE:LSP:ENTER");
    if (request == (const WlascAndroidChildRequestV1 *)0 ||
        receipt == (const WlascStockStageReceiptV1 *)0 ||
        receipt->runtime_generation != request->runtime_generation ||
        receipt->child_stage_tail_reached != UINT32_C(1) ||
        receipt->bypass_guard_passed != UINT32_C(1) ||
        __atomic_load_n(&g_child_hook_control.atomic_lifecycle_state,
                        __ATOMIC_ACQUIRE) !=
            WESTLAKE_CHILD_HOOK_READY ||
        g_stock_host_services.current_thread_token == 0 ||
        g_stock_host_services.prepare_parent_runtime == 0 ||
        g_stock_host_services.verify_parent_preload_thread_ready == 0 ||
        g_stock_host_services.prepare_main_thread == 0 ||
        g_stock_host_services.verify_current_thread_ready == 0 ||
        g_stock_host_services.get_audit_snapshot == 0 ||
        g_stock_host_services.get_pthread_bridge_ops == 0) {
        WLASC_GATE_MARKER("WLCGATE:LSP:FAIL_PRECONDITION");
        return -1;
    }
    WLASC_GATE_MARKER("WLCGATE:LSP:PASS_PRECONDITION");
    manifest = WLSCPL_GetBuildGeneratedManifest();
    if (manifest == (const WlscplManifestV1 *)0 ||
        manifest->abi_version != WLSCPL_ABI_VERSION ||
        manifest->struct_size != sizeof(*manifest) ||
        manifest->artifact_generation != request->runtime_generation) {
        WLASC_GATE_MARKER("WLCGATE:LSP:FAIL_MANIFEST");
        return -1;
    }
    WLASC_GATE_MARKER("WLCGATE:LSP:PASS_MANIFEST");
    child_pid = (uint64_t)getpid();
    parent_pid = (uint64_t)getppid();
    if (child_pid == UINT64_C(0) || parent_pid == UINT64_C(0) ||
        child_pid == parent_pid) {
        WLASC_GATE_MARKER("WLCGATE:LSP:FAIL_PID");
        return -1;
    }
    WLASC_GATE_MARKER("WLCGATE:LSP:PASS_PID");

    ZeroBytes(&load_request, sizeof(load_request));
    ZeroBytes(&load_result, sizeof(load_result));
    load_request.abi_version = WLSCPL_ABI_VERSION;
    load_request.struct_size = (uint32_t)sizeof(load_request);
    load_request.specialization_complete = UINT32_C(1);
    load_request.hook_table_ready = UINT32_C(1);
    load_request.generation_seal_verified = UINT32_C(1);
    load_request.parent_pid = parent_pid;
    load_request.child_pid = child_pid;
    load_request.manifest = manifest;
    loader_error = WLSCPL_LoadSealedProvider(
        &g_sealed_child_loader, &load_request, &load_result);
    if (loader_error != WLSCPL_OK ||
        load_result.abi_version != WLSCPL_ABI_VERSION ||
        load_result.struct_size != sizeof(load_result) ||
        load_result.error != WLSCPL_OK ||
        load_result.validated_artifact_count != manifest->artifact_count ||
        load_result.child_pid != child_pid ||
        load_result.artifact_generation != request->runtime_generation ||
        load_result.provider_handle == (void *)0) {
        WlascGateMarkerValue("WLCGATE:LSP:LOAD_ERROR",
                             (uint32_t)loader_error);
        WlascGateMarkerValue("WLCGATE:LSP:RESULT_ERROR",
                             (uint32_t)load_result.error);
        WlascGateMarkerValue("WLCGATE:LSP:VALIDATED_COUNT",
                             load_result.validated_artifact_count);
        WLASC_GATE_MARKER("WLCGATE:LSP:FAIL_LOAD_RESULT");
        return -1;
    }
    WLASC_GATE_MARKER("WLCGATE:LSP:PASS_LOAD_RESULT");
    ZeroBytes(&child_services, sizeof(child_services));
    child_services.abi_version = WLASC_HOST_SERVICES_ABI_VERSION;
    child_services.struct_size = (uint32_t)sizeof(child_services);
    child_services.runtime_generation = request->runtime_generation;
    memcpy(child_services.runtime_provider_sha256,
           g_stock_host_services.runtime_provider_sha256,
           WLASC_SHA256_SIZE);
    child_services.current_thread_token =
        g_stock_host_services.current_thread_token;
    child_services.prepare_parent_runtime =
        g_stock_host_services.prepare_parent_runtime;
    child_services.verify_parent_preload_thread_ready =
        g_stock_host_services.verify_parent_preload_thread_ready;
    child_services.prepare_main_thread =
        g_stock_host_services.prepare_main_thread;
    child_services.verify_current_thread_ready =
        g_stock_host_services.verify_current_thread_ready;
    child_services.get_audit_snapshot =
        g_stock_host_services.get_audit_snapshot;
    child_services.get_pthread_bridge_ops =
        g_stock_host_services.get_pthread_bridge_ops;
    child_services.open_sealed_exact = WLSCPL_OpenPreparedNamespace;
    child_services.create_configured_namespaces = g_stock_host_services.create_configured_namespaces;
    child_services.open_namespace = g_stock_host_services.open_namespace;
    WLASC_GATE_MARKER("WLCGATE:LSP:INVOKE_PROVIDER");
    {
        int result = InvokeProviderChildEntryWithResolver(
            load_result.provider_handle, &child_services, request, receipt,
            ResolveProviderChildSymbol);
        WLASC_GATE_MARKER(result == 0 ?
            "WLCGATE:LSP:PASS_PROVIDER" : "WLCGATE:LSP:FAIL_PROVIDER");
        return result;
    }
}

static int CompleteStockChildReply(AppSpawnContent *content,
                                   AppSpawnClient *client)
{
    AppSpawningCtx *property = (AppSpawningCtx *)client;
    int reply_fd;
    const int result = 0;
    ssize_t written;

    if (content == (AppSpawnContent *)0 ||
        property == (AppSpawningCtx *)0) {
        return -1;
    }
    reply_fd = property->forkCtx.fd[1];
    if (reply_fd < 0) {
        return -1;
    }

    property->forkCtx.fd[1] = -1;
    g_stock_host_services.clear_child_environment(content, client);
    do {
        written = write(reply_fd, &result, sizeof(result));
    } while (written < 0 && errno == EINTR);
    if (close(reply_fd) != 0 || written != (ssize_t)sizeof(result)) {
        WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_STOCK_REPLY_WRITE");
        _exit(124);
    }
    WLASC_GATE_MARKER("WLCGATE:RAC:PASS_STOCK_REPLY");
    return 0;
}

static int WestlakeRunAndroidChild(AppSpawnContent *content,
                                   AppSpawnClient *client)
{
    AppSpawningCtx *property = (AppSpawningCtx *)client;
    WlascAndroidChildRequestV1 request;
    WlascStockStageReceiptV1 receipt;
    WLASC_GATE_MARKER("WLCGATE:RAC:ENTER");
    if (!ImmutableGenerationReady() || content == (AppSpawnContent *)0 ||
        client == (AppSpawnClient *)0 ||
        content->mode != MODE_FOR_APP_SPAWN ||
        content->runChildProcessor != WestlakeRunAndroidChild ||
        BuildAndroidRequest(property, &request) != 0 ||
        WLASC_ReceiptConsume(&g_stage_ledger, ClientCookie(client),
                             &receipt) != WLASC_REASON_NONE) {
        WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_REQUEST_RECEIPT");
        return -1;
    }
    WLASC_GATE_MARKER("WLCGATE:RAC:PASS_REQUEST_RECEIPT");
    if (receipt.runtime_generation != request.runtime_generation ||
        PublishChildHookTable(&request) != 0) {
        WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_HOOK_PUBLICATION");
        RevokeChildHookTable(WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
        return -1;
    }
    WLASC_GATE_MARKER("WLCGATE:RAC:PASS_HOOK_PUBLICATION");

    if (CompleteStockChildReply(content, client) != 0) {
        WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_STOCK_REPLY_PRECONDITION");
        RevokeChildHookTable(WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
        return -1;
    }

    if (LoadSealedProviderAfterHooks(&request, &receipt) != 0) {
        WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_SEALED_PROVIDER");
        RevokeChildHookTable(WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
        _exit(123);
    }
    WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_PROVIDER_RETURNED");
    _exit(122);
}

static int WestlakeServerPrepareInert(AppSpawnMgr *content)
{
    static const char service_name[] = "appspawn-x";
    if (!ImmutableGenerationReady() || content == (AppSpawnMgr *)0 ||
        g_registration_mask != WLASC_REG_ALL ||
        content->content.mode != MODE_FOR_APP_SPAWN ||
        content->content.longProcName == (char *)0 ||
        !FixedStringEquals(content->content.longProcName, service_name,
                           sizeof(service_name)) ||
        content->content.runChildProcessor != (ChildLoop)0) {
        return -1;
    }
    g_stock_host_services.reg_child_looper(
        &content->content, WestlakeRunAndroidChild);
    if (content->content.runChildProcessor != WestlakeRunAndroidChild) {
        return -1;
    }
    return 0;
}

int WLASC_InstallStockHostServicesV1(
    const WlascStockHostServicesV1 *services)
{
    uint32_t expected = WLASC_STOCK_SERVICES_EMPTY;
    if (!__atomic_compare_exchange_n(
            &g_stock_services_state, &expected,
            WLASC_STOCK_SERVICES_INSTALLING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE) ||
        g_registration_mask != UINT32_C(0) ||
        !StockServicesValid(services)) {
        __atomic_store_n(&g_stock_services_state,
                         WLASC_STOCK_SERVICES_FAILED,
                         __ATOMIC_RELEASE);
        return -1;
    }
    g_stock_host_services = *services;
    if (g_stock_host_services.add_server_stage_hook(
            STAGE_SERVER_PRELOAD, (int)WLASC_PRELOAD_PRIORITY,
            WestlakeServerPrepareInert) != 0 ||
        __atomic_load_n(&g_stock_services_state, __ATOMIC_ACQUIRE) !=
            WLASC_STOCK_SERVICES_INSTALLING) {
        goto fail;
    }
    g_registration_mask |= WLASC_REG_PRELOAD;
    if (g_stock_host_services.add_app_spawn_hook(
            STAGE_PARENT_PRE_FORK, (int)WLASC_TAIL_PRIORITY,
            WestlakeParentPreForkTail) != 0 ||
        __atomic_load_n(&g_stock_services_state, __ATOMIC_ACQUIRE) !=
            WLASC_STOCK_SERVICES_INSTALLING) {
        goto fail;
    }
    g_registration_mask |= WLASC_REG_PARENT_TAIL;
    if (g_stock_host_services.add_app_spawn_hook(
            STAGE_CHILD_EXECUTE, (int)WLASC_GUARD_PRIORITY,
            WestlakeChildBypassGuard) != 0 ||
        __atomic_load_n(&g_stock_services_state, __ATOMIC_ACQUIRE) !=
            WLASC_STOCK_SERVICES_INSTALLING) {
        goto fail;
    }
    g_registration_mask |= WLASC_REG_CHILD_GUARD;
    if (g_stock_host_services.add_app_spawn_hook(
            STAGE_CHILD_EXECUTE, (int)WLASC_TAIL_PRIORITY,
            WestlakeChildStageTail) != 0 ||
        __atomic_load_n(&g_stock_services_state, __ATOMIC_ACQUIRE) !=
            WLASC_STOCK_SERVICES_INSTALLING) {
        goto fail;
    }
    g_registration_mask |= WLASC_REG_CHILD_TAIL;
    __atomic_store_n(&g_stock_services_state,
                     WLASC_STOCK_SERVICES_INSTALLED,
                     __ATOMIC_RELEASE);
    return 0;

fail:
    __atomic_store_n(&g_stock_services_state,
                     WLASC_STOCK_SERVICES_FAILED,
                     __ATOMIC_RELEASE);
    return -1;
}

const WlascContractV1 *WLASC_GetContractV1(void)
{
    return &g_contract;
}
#endif /* !WLASC_PROVIDER_ENTRY_TEST_ONLY */
