/*
 * Route A Android-runtime provider.
 *
 * This is the only owner of the six WLAR_* symbols.  It translates the
 * pointer-free stock receipt into the existing adapter runtime and enters the
 * Android child only after the OH stage-31 tail.  It performs no process
 * security operation.
 */

#include <cstddef>
#include <cstdint>

namespace wlar_child_sequence {

enum class Stage : uint32_t {
    UNENTERED = 0,
    CONSTRUCTING = 1,
    CONSTRUCTORS_READY = 2,
    VM_READY = 3,
    JNI_READY = 4,
    MAIN_ENTERED = 5,
    FAILED_TERMINAL = 6,
};

enum Failure : int32_t {
    OK = 0,
    INVALID_ARGUMENT = -2001,
    STALE_GENERATION = -2002,
    WRONG_CHILD_PID = -2003,
    EVENT_CONFLICT = -2004,
    CONSTRUCTOR_FAILED = -2005,
    VM_FAILED = -2006,
    JNI_FAILED = -2007,
    MAIN_FAILED = -2008,
};

struct Admission {
    uint64_t generation;
    uint64_t expected_child_pid;
    uint64_t observed_child_pid;
    uint64_t event_token;
    uint64_t request_digest;
};

struct Operations {
    void *context;
    int (*constructors)(void *context);
    int (*vm)(void *context);
    int (*jni)(void *context);
    int (*main)(void *context);
    void (*revoke)(void *context);
    void (*drain)(void *context);
    void (*invalidate)(void *context);
};

struct Ledger {
    Stage stage;
    uint32_t admission_open;
    uint64_t inflight_count;
    int32_t first_cause;
    uint32_t reserved_zero;
    Admission admitted;
};

bool SameRequest(const Admission &left, const Admission &right)
{
    return left.generation == right.generation &&
        left.expected_child_pid == right.expected_child_pid &&
        left.observed_child_pid == right.observed_child_pid &&
        left.event_token == right.event_token &&
        left.request_digest == right.request_digest;
}

int32_t Fail(Ledger *ledger, const Operations &operations, int32_t cause)
{
    if (ledger->first_cause == OK) {
        ledger->first_cause = cause;
    }
    ledger->admission_open = 0;
    if (operations.revoke != nullptr) {
        operations.revoke(operations.context);
    }
    if (operations.drain != nullptr) {
        operations.drain(operations.context);
    }
    ledger->inflight_count = 0;
    if (operations.invalidate != nullptr) {
        operations.invalidate(operations.context);
    }
    ledger->stage = Stage::FAILED_TERMINAL;
    return ledger->first_cause;
}

int32_t Run(Ledger *ledger, const Admission &admission,
            uint64_t sealed_generation, const Operations &operations)
{
    if (ledger == nullptr || admission.generation == 0 ||
        admission.event_token == 0 || admission.request_digest == 0 ||
        operations.constructors == nullptr || operations.vm == nullptr ||
        operations.jni == nullptr || operations.main == nullptr) {
        return INVALID_ARGUMENT;
    }
    if (ledger->stage == Stage::FAILED_TERMINAL ||
        ledger->stage == Stage::MAIN_ENTERED) {
        return SameRequest(ledger->admitted, admission) ?
            ledger->first_cause : EVENT_CONFLICT;
    }
    if (ledger->stage != Stage::UNENTERED) {
        return EVENT_CONFLICT;
    }
    if (admission.generation != sealed_generation) {
        ledger->admitted = admission;
        return Fail(ledger, operations, STALE_GENERATION);
    }
    if (admission.expected_child_pid == 0 ||
        admission.observed_child_pid != admission.expected_child_pid) {
        ledger->admitted = admission;
        return Fail(ledger, operations, WRONG_CHILD_PID);
    }

    ledger->admitted = admission;
    ledger->admission_open = 1;
    ledger->inflight_count = 1;
    ledger->stage = Stage::CONSTRUCTING;
    if (operations.constructors(operations.context) != 0) {
        return Fail(ledger, operations, CONSTRUCTOR_FAILED);
    }
    ledger->stage = Stage::CONSTRUCTORS_READY;
    if (operations.vm(operations.context) != 0) {
        return Fail(ledger, operations, VM_FAILED);
    }
    ledger->stage = Stage::VM_READY;
    if (operations.jni(operations.context) != 0) {
        return Fail(ledger, operations, JNI_FAILED);
    }
    ledger->stage = Stage::JNI_READY;
    if (operations.main(operations.context) != 0) {
        return Fail(ledger, operations, MAIN_FAILED);
    }
    ledger->inflight_count = 0;
    ledger->stage = Stage::MAIN_ENTERED;
    return OK;
}

} // namespace wlar_child_sequence

#if !defined(WLAR_RUNTIME_PROVIDER_SEQUENCE_TEST)

#include "westlake_android_child_plugin.h"

#include "app_native_loader.h"
#include "appspawnx_runtime.h"
#include "child_main.h"
#include "host_runtime_services.h"
#include "runtime_loader_phase.h"
extern "C" int WLNL_InstallSealedOpenV1(WlascOpenSealedExactV1);
#include "spawn_msg.h"

#include <cstdlib>
#include <cstring>
#include <new>
#include <sys/resource.h>
#include <unistd.h>

static void ProviderGateMarker(const char *text)
{
    (void)HiLogPrint(LOG_CORE, LOG_INFO, UINT32_C(0xD002C11), "APPSPAWN",
                     "%{public}s", text);
}

static void ProviderGateMarkerValue(const char *text, uint64_t value)
{
    (void)HiLogPrint(LOG_CORE, LOG_INFO, UINT32_C(0xD002C11), "APPSPAWN",
                     "%{public}s:%{public}llu", text,
                     static_cast<unsigned long long>(value));
}

#ifndef WLAR_GENERATION_SHA_HEX
#error "WLAR_GENERATION_SHA_HEX must bind the frozen provider input closure"
#endif

namespace {

using appspawnx::AppSpawnXRuntime;
using appspawnx::ChildMain;
using appspawnx::SpawnMsg;

constexpr char kGenerationShaHex[] = WLAR_GENERATION_SHA_HEX;
static_assert(sizeof(kGenerationShaHex) == 65,
              "provider generation identity must be SHA-256 hex");
static_assert(sizeof(WlascHostRuntimeServicesV1) == 128U,
              "host runtime services ABI drift");
static_assert(sizeof(WlncParentIdentityV1) == 80U,
              "parent runtime identity ABI drift");

constexpr uint8_t HexNibble(char value)
{
    return value >= '0' && value <= '9' ?
        static_cast<uint8_t>(value - '0') :
        value >= 'a' && value <= 'f' ?
            static_cast<uint8_t>(value - 'a' + 10) : UINT8_C(255);
}

constexpr uint8_t HexByte(size_t index)
{
    return static_cast<uint8_t>(
        (HexNibble(kGenerationShaHex[index * 2U]) << 4U) |
        HexNibble(kGenerationShaHex[index * 2U + 1U]));
}

constexpr uint64_t ProviderGeneration()
{
    uint64_t result = 0;
    for (size_t index = 0; index < 8U; ++index) {
        result = (result << 8U) | HexByte(index);
    }
    return result;
}

static_assert(HexNibble(kGenerationShaHex[0]) != UINT8_C(255),
              "provider generation SHA must use lower-case hex");
static_assert(ProviderGeneration() != UINT64_C(0),
              "provider generation must be nonzero");

__attribute__((used, retain, section(".rodata.wlar_generation")))
const uint8_t kProviderGenerationSha[WLASC_SHA256_SIZE] = {
    HexByte(0), HexByte(1), HexByte(2), HexByte(3),
    HexByte(4), HexByte(5), HexByte(6), HexByte(7),
    HexByte(8), HexByte(9), HexByte(10), HexByte(11),
    HexByte(12), HexByte(13), HexByte(14), HexByte(15),
    HexByte(16), HexByte(17), HexByte(18), HexByte(19),
    HexByte(20), HexByte(21), HexByte(22), HexByte(23),
    HexByte(24), HexByte(25), HexByte(26), HexByte(27),
    HexByte(28), HexByte(29), HexByte(30), HexByte(31),
};

enum ProviderAdmissionState : uint32_t {
    PROVIDER_ADMISSION_EMPTY = 0,
    PROVIDER_ADMISSION_INSTALLING = 1,
    PROVIDER_ADMISSION_READY = 2,
    PROVIDER_ADMISSION_FAILED = 3,
};

uint32_t gAdmissionState = PROVIDER_ADMISSION_EMPTY;
WlarHostServicesRegistryV1 gHostServicesRegistry{};
WlarLoaderPhaseRegistryV1 gLoaderPhaseRegistry{};
wlar_child_sequence::Ledger gChildLedger{};
uint32_t gChildOwnerState;

constexpr char kBootClasspath[] =
    "/system/android/framework/core-oj.jar:"
    "/system/android/framework/core-libart.jar:"
    "/system/android/framework/core-icu4j.jar:"
    "/system/android/framework/okhttp.jar:"
    "/system/android/framework/bouncycastle.jar:"
    "/system/android/framework/apache-xml.jar:"
    "/system/android/framework/adapter-mainline-stubs.jar:"
    "/system/android/framework/framework.jar:"
    "/system/android/framework/oh-adapter-framework.jar";

constexpr char kDex2oatBootClasspath[] =
    "/system/android/framework/core-oj.jar:"
    "/system/android/framework/core-libart.jar:"
    "/system/android/framework/core-icu4j.jar:"
    "/system/android/framework/adapter-mainline-stubs.jar:"
    "/system/android/framework/framework.jar";

bool SetRequiredEnvironment()
{
    return setenv("BOOTCLASSPATH", kBootClasspath, 1) == 0 &&
           setenv("DEX2OATBOOTCLASSPATH", kDex2oatBootClasspath, 1) == 0 &&
           setenv("ANDROID_ROOT", "/system/android", 1) == 0 &&
           setenv("ANDROID_DATA", "/data", 1) == 0 &&
           setenv("ANDROID_BOOT_IMAGE",
                  "/system/android/framework/boot.art", 1) == 0 &&
           setenv("ANDROID_I18N_ROOT", "/system/android", 1) == 0 &&
           setenv("ANDROID_TZDATA_ROOT", "/system/android", 1) == 0 &&
           setenv("ICU_DATA", "/system/android/etc/icu", 1) == 0;
}

bool FixedStringValid(const char *value, size_t capacity)
{
    if (value == nullptr || capacity < 2U || value[0] == '\0') {
        return false;
    }
    return std::memchr(value, '\0', capacity) != nullptr;
}

bool AllZero(const uint32_t *values, size_t count)
{
    uint32_t combined = 0;
    for (size_t index = 0; index < count; ++index) {
        combined |= values[index];
    }
    return combined == 0U;
}

void FillGenerationSha(uint8_t output[WLASC_SHA256_SIZE])
{
    const volatile uint8_t *source = kProviderGenerationSha;
    for (size_t index = 0; index < WLASC_SHA256_SIZE; ++index) {
        output[index] = source[index];
    }
}

int VerifyLoaderThreadReady(void *context)
{
    if (context != &gLoaderPhaseRegistry) {
        return 0;
    }
    const pid_t processId = getpid();
    if (processId <= 0) {
        return 0;
    }
    return WLAR_LoaderPhaseIsChildReady(
               &gLoaderPhaseRegistry,
               static_cast<uint64_t>(processId)) == 1 &&
           WLAR_HostServicesVerifyCurrentThreadReady(
               &gHostServicesRegistry) == 0
               ? 1 : 0;
}

WlascCreateConfiguredNamespacesV1 gCreateConfiguredNamespaces = nullptr;
WlascOpenNamespaceV1 gOpenNamespace = nullptr;
int CreateConfiguredNamespacesFromStock(
    Dl_namespace *bridge, const char *name, const char *search, const char *permitted,
    const char *shared, const char *bootstrap, const WlpbHostOpsV1 *ops,
    void **handle, Dl_namespace *app, const char *appName, const char *appSearch,
    const char *appPermitted)
{
    return gCreateConfiguredNamespaces == nullptr ? -1 :
        gCreateConfiguredNamespaces(bridge, name, search, permitted, shared,
                                   bootstrap, ops, handle, app, appName, appSearch, appPermitted);
}
void *OpenNamespaceFromStock(Dl_namespace *app, const char *path, int mode)
{
    return gOpenNamespace == nullptr ? nullptr : gOpenNamespace(app, path, mode);
}

bool InstallLoaderReadyGate()
{
    AnlRuntimeGateV1 gate{};
    gate.abi_version = ANL_RUNTIME_GATE_ABI_VERSION;
    gate.struct_size = sizeof(gate);
    gate.context = &gLoaderPhaseRegistry;
    gate.verify_current_thread_ready = VerifyLoaderThreadReady;
    if (WLAR_HostServicesGetNamespaceCallbacks(
            &gHostServicesRegistry, &gCreateConfiguredNamespaces, &gOpenNamespace) != 0) return false;
    gate.namespace_host_ops.abi_version = ANL_NAMESPACE_HOST_OPS_ABI_VERSION;
    gate.namespace_host_ops.struct_size = sizeof(gate.namespace_host_ops);
    gate.namespace_host_ops.runtime_generation = ProviderGeneration();
    gate.namespace_host_ops.create_configured_namespaces =
        CreateConfiguredNamespacesFromStock;
    gate.namespace_host_ops.open_namespace = OpenNamespaceFromStock;
    return WLAR_HostServicesGetPthreadBridgeOps(
               &gHostServicesRegistry, &gate.pthread_bridge_ops) == 0 &&
           ANL_InstallRuntimeGate(&gate) == 0;
}

bool AuditSnapshotValid(const WlncAuditSnapshotV1 &snapshot,
                        uint64_t runtimeGeneration)
{
    if (snapshot.abi_version != WLNC_ABI_VERSION ||
        snapshot.struct_size != sizeof(snapshot) ||
        snapshot.event_type_slots != WLNC_AUDIT_EVENT_TYPE_SLOTS ||
        snapshot.runtime_generation != runtimeGeneration ||
        snapshot.process_epoch == UINT64_C(0) ||
        snapshot.accepted_event_count == UINT64_C(0) ||
        snapshot.accepted_event_count != snapshot.registry_audit_sequence ||
        snapshot.registry_audit_drop_count != UINT64_C(0) ||
        snapshot.registry_ready_count != UINT32_C(1) ||
        snapshot.registry_active_ticket_count != UINT32_C(0) ||
        !AllZero(snapshot.reserved_zero,
                 sizeof(snapshot.reserved_zero) /
                     sizeof(snapshot.reserved_zero[0]))) {
        return false;
    }
    uint64_t typeCount = UINT64_C(0);
    for (size_t index = 0; index < WLNC_AUDIT_EVENT_TYPE_SLOTS; ++index) {
        if (UINT64_MAX - typeCount < snapshot.event_type_count[index]) {
            return false;
        }
        typeCount += snapshot.event_type_count[index];
    }
    return typeCount == snapshot.accepted_event_count;
}

bool RequestValid(const WlascAndroidChildRequestV1 *request,
                  const WlascStockStageReceiptV1 *receipt)
{
    constexpr uint32_t noSandboxMask = UINT32_C(1) << 7U;
    constexpr uint32_t ignoreSandboxMask = UINT32_C(1) << 13U;
    return request != nullptr && receipt != nullptr &&
           request->abi_version == WLASC_ABI_VERSION &&
           request->struct_size == sizeof(*request) &&
           request->message_type == UINT32_C(0) &&
           request->runtime_generation == ProviderGeneration() &&
           request->runtime_generation == receipt->runtime_generation &&
           request->message_id == receipt->message_id &&
           request->gid_count <= WLASC_MAX_GIDS &&
           request->access_token_id_ex != UINT64_C(0) &&
           request->flags_word_count == WLASC_FLAGS_WORDS &&
           (request->flags_words[0] &
            (noSandboxMask | ignoreSandboxMask)) == UINT32_C(0) &&
           request->set_allow_internet <= UINT8_C(1) &&
           request->allow_internet <= UINT8_C(1) &&
           request->reserved_bytes[0] == UINT8_C(0) &&
           request->reserved_bytes[1] == UINT8_C(0) &&
           FixedStringValid(request->process_name,
                            sizeof(request->process_name)) &&
           FixedStringValid(request->bundle_name,
                            sizeof(request->bundle_name)) &&
           FixedStringValid(request->apl, sizeof(request->apl)) &&
           FixedStringValid(request->owner_id,
                            sizeof(request->owner_id)) &&
           receipt->abi_version == WLASC_ABI_VERSION &&
           receipt->struct_size == sizeof(*receipt) &&
           receipt->parent_stage_tail_reached == UINT32_C(1) &&
           receipt->child_stage_tail_reached == UINT32_C(1) &&
           receipt->bypass_guard_passed == UINT32_C(1) &&
           receipt->security_owner_stock_appspawn == UINT32_C(1) &&
           receipt->parent_tail_priority == WLASC_TAIL_PRIORITY &&
           receipt->child_tail_priority == WLASC_TAIL_PRIORITY &&
           AllZero(receipt->reserved_zero,
                   sizeof(receipt->reserved_zero) /
                       sizeof(receipt->reserved_zero[0]));
}

SpawnMsg TranslateRequest(const WlascAndroidChildRequestV1 &request)
{
    SpawnMsg message;
    message.code = static_cast<int32_t>(request.message_type);
    message.procName.assign(request.process_name);
    message.bundleName.assign(request.bundle_name);
    message.uid = static_cast<int32_t>(request.uid);
    message.gid = static_cast<int32_t>(request.gid);
    message.gids.reserve(request.gid_count);
    for (uint32_t index = 0; index < request.gid_count; ++index) {
        message.gids.push_back(static_cast<int32_t>(request.gids[index]));
    }
    message.accessTokenIdEx = request.access_token_id_ex;
    message.hapFlags = request.hap_flags;
    message.apl.assign(request.apl);
    message.flags = static_cast<uint64_t>(request.flags_words[0]) |
        (static_cast<uint64_t>(request.flags_words[1]) << 32U);
    message.targetClass = "android.app.ActivityThread";
    message.targetSdkVersion = 0;
    message.isOhBinary = true;
    message.ohMsgId = request.message_id;
    return message;
}

struct ProductionSequenceContext {
    alignas(AppSpawnXRuntime) uint8_t runtime_storage[sizeof(AppSpawnXRuntime)];
    AppSpawnXRuntime *runtime;
    SpawnMsg message;
};

int ConstructChildRuntime(void *opaque)
{
    auto *context = static_cast<ProductionSequenceContext *>(opaque);
    struct rlimit stackLimit = {
        16U * 1024U * 1024U,
        16U * 1024U * 1024U,
    };
    struct rlimit previousStack{};
    if (context == nullptr || getrlimit(RLIMIT_STACK, &previousStack) != 0 || !SetRequiredEnvironment() ||
        setrlimit(RLIMIT_STACK, &stackLimit) != 0) {
        return -1;
    }
    context->runtime = new (context->runtime_storage) AppSpawnXRuntime();
    return InstallLoaderReadyGate() ? 0 : -1;
}

int CreateChildVm(void *opaque)
{
    auto *context = static_cast<ProductionSequenceContext *>(opaque);
    return context != nullptr && context->runtime != nullptr ?
        context->runtime->startVm(false) : -1;
}

int CompleteChildJni(void *opaque)
{
    auto *context = static_cast<ProductionSequenceContext *>(opaque);
    return context != nullptr && context->runtime != nullptr &&
        context->runtime->getJNIEnv() != nullptr &&
        context->runtime->preload() == 0 ? 0 : -1;
}

int EnterChildMain(void *opaque)
{
    auto *context = static_cast<ProductionSequenceContext *>(opaque);
    if (context == nullptr || context->runtime == nullptr) {
        return -1;
    }
    ChildMain::runAfterStockSpecialization(context->message,
                                            context->runtime);
}

void RevokeChildAdmission(void *)
{
    WLAR_LoaderPhaseFail(&gLoaderPhaseRegistry);
}

void DrainChildCalls(void *)
{
    /* The sequence owner is the sole in-flight caller in this child. */
}

void InvalidateChildAdmission(void *)
{
    /* The caller returns a typed first cause; appspawn then fail-stops child. */
}

} // namespace

extern "C" __attribute__((visibility("default")))
int WLAR_GetRuntimeIdentity(WlascRuntimeIdentityV1 *outIdentity)
{
    if (outIdentity == nullptr) {
        return -1;
    }
    std::memset(outIdentity, 0, sizeof(*outIdentity));
    outIdentity->abi_version = WLASC_ABI_VERSION;
    outIdentity->struct_size = sizeof(*outIdentity);
    outIdentity->runtime_generation = ProviderGeneration();
    FillGenerationSha(outIdentity->runtime_provider_sha256);
    return 0;
}

extern "C" __attribute__((visibility("default")))
int WLAR_InstallHostRuntimeServices(
    const WlascHostRuntimeServicesV1 *services)
{
    uint32_t expected = PROVIDER_ADMISSION_EMPTY;
    if (!__atomic_compare_exchange_n(
            &gAdmissionState, &expected, PROVIDER_ADMISSION_INSTALLING,
            false, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        return -1;
    }
    if (WLAR_HostServicesInstall(&gHostServicesRegistry,
            ProviderGeneration(), kProviderGenerationSha, services) != 0 ||
        WLNL_InstallSealedOpenV1(services->open_sealed_exact) != 0) {
        __atomic_store_n(&gAdmissionState, PROVIDER_ADMISSION_FAILED,
                         __ATOMIC_RELEASE);
        return -1;
    }
    __atomic_store_n(&gAdmissionState, PROVIDER_ADMISSION_READY,
                     __ATOMIC_RELEASE);
    return 0;
}

extern "C" __attribute__((visibility("default")))
int WLAR_EnterAndroidAfterStockSpecialization(
    const WlascAndroidChildRequestV1 *request,
    const WlascStockStageReceiptV1 *stockReceipt)
{
    const pid_t childPid = getpid();
    if (__atomic_load_n(&gAdmissionState, __ATOMIC_ACQUIRE) !=
            PROVIDER_ADMISSION_READY ||
        !WLAR_HostServicesIsInstalled(&gHostServicesRegistry) ||
        !RequestValid(request, stockReceipt) ||
        childPid <= 1 || childPid == getppid() ||
        getuid() != static_cast<uid_t>(request->uid) ||
        getgid() != static_cast<gid_t>(request->gid)) {
        return wlar_child_sequence::WRONG_CHILD_PID;
    }
    if (WLAR_LoaderPhaseBeginChildOnly(
            &gLoaderPhaseRegistry, request->runtime_generation,
            kProviderGenerationSha,
            static_cast<uint64_t>(childPid)) != 0) {
        ProviderGateMarker("WLCGATE:PROVIDER:FAIL_PHASE_BEGIN");
        return wlar_child_sequence::STALE_GENERATION;
    }
    ProviderGateMarker("WLCGATE:PROVIDER:PASS_PHASE_BEGIN");
    if (WLAR_HostServicesBeginChildOnly(&gHostServicesRegistry) != 0) {
        WLAR_LoaderPhaseFail(&gLoaderPhaseRegistry);
        return wlar_child_sequence::EVENT_CONFLICT;
    }

    WlncProcessIdentityV1 identity{};
    identity.abi_version = WLNC_ABI_VERSION;
    identity.struct_size = sizeof(identity);
    identity.runtime_generation = request->runtime_generation;
    identity.message_id = request->message_id;
    identity.uid = request->uid;
    identity.gid = request->gid;
    identity.parent_stage_tail_reached =
        stockReceipt->parent_stage_tail_reached;
    identity.child_stage_tail_reached =
        stockReceipt->child_stage_tail_reached;
    identity.bypass_guard_passed = stockReceipt->bypass_guard_passed;
    identity.security_owner_stock_appspawn =
        stockReceipt->security_owner_stock_appspawn;
    identity.parent_tail_priority = stockReceipt->parent_tail_priority;
    identity.child_tail_priority = stockReceipt->child_tail_priority;
    FillGenerationSha(identity.runtime_provider_sha256);
    if (WLAR_HostServicesPrepareMain(
            &gHostServicesRegistry, &identity) != 0) {
        WLAR_LoaderPhaseFail(&gLoaderPhaseRegistry);
        return wlar_child_sequence::WRONG_CHILD_PID;
    }
    WlncAuditSnapshotV1 auditSnapshot{};
    const int auditResult = WLAR_HostServicesGetAuditSnapshot(
        &gHostServicesRegistry, &auditSnapshot);
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_CALL_RESULT",
                            static_cast<uint32_t>(auditResult));
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_GENERATION",
                            auditSnapshot.runtime_generation);
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_PROCESS_EPOCH",
                            auditSnapshot.process_epoch);
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_ACCEPTED",
                            auditSnapshot.accepted_event_count);
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_SEQUENCE",
                            auditSnapshot.registry_audit_sequence);
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_DROPS",
                            auditSnapshot.registry_audit_drop_count);
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_READY",
                            auditSnapshot.registry_ready_count);
    ProviderGateMarkerValue("WLCGATE:PROVIDER:AUDIT_ACTIVE_TICKETS",
                            auditSnapshot.registry_active_ticket_count);
    if (auditResult != 0 ||
        !AuditSnapshotValid(auditSnapshot, request->runtime_generation)) {
        ProviderGateMarker("WLCGATE:PROVIDER:FAIL_AUDIT_SNAPSHOT");
        WLAR_LoaderPhaseFail(&gLoaderPhaseRegistry);
        return wlar_child_sequence::STALE_GENERATION;
    }
    ProviderGateMarker("WLCGATE:PROVIDER:PASS_AUDIT_SNAPSHOT");
    if (WLAR_HostServicesMarkChildConsumed(
            &gHostServicesRegistry) != 0) {
        WLAR_LoaderPhaseFail(&gLoaderPhaseRegistry);
        return wlar_child_sequence::EVENT_CONFLICT;
    }
    if (WLAR_LoaderPhaseMarkChildReady(
            &gLoaderPhaseRegistry,
            static_cast<uint64_t>(childPid)) != 0) {
        ProviderGateMarker("WLCGATE:PROVIDER:FAIL_PHASE_READY");
        return wlar_child_sequence::STALE_GENERATION;
    }
    ProviderGateMarker("WLCGATE:PROVIDER:PASS_PHASE_READY");

    uint32_t expectedOwner = 0;
    if (!__atomic_compare_exchange_n(
            &gChildOwnerState, &expectedOwner, UINT32_C(1), false,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        wlar_child_sequence::Admission replay{
            request->runtime_generation,
            static_cast<uint64_t>(childPid),
            static_cast<uint64_t>(childPid),
            static_cast<uint64_t>(request->message_id) + UINT64_C(1),
            request->runtime_generation ^
                (static_cast<uint64_t>(request->message_id) << 32U) ^
                (static_cast<uint64_t>(request->uid) << 1U) ^
                static_cast<uint64_t>(request->gid),
        };
        return wlar_child_sequence::SameRequest(
            gChildLedger.admitted, replay) ? gChildLedger.first_cause :
            wlar_child_sequence::EVENT_CONFLICT;
    }

    ProductionSequenceContext context{};
    context.message = TranslateRequest(*request);
    wlar_child_sequence::Admission admission{
        request->runtime_generation,
        static_cast<uint64_t>(childPid),
        static_cast<uint64_t>(childPid),
        static_cast<uint64_t>(request->message_id) + UINT64_C(1),
        request->runtime_generation ^
            (static_cast<uint64_t>(request->message_id) << 32U) ^
            (static_cast<uint64_t>(request->uid) << 1U) ^
            static_cast<uint64_t>(request->gid),
    };
    if (admission.request_digest == 0) {
        admission.request_digest = UINT64_C(1);
    }
    const wlar_child_sequence::Operations operations{
        &context,
        ConstructChildRuntime,
        CreateChildVm,
        CompleteChildJni,
        EnterChildMain,
        RevokeChildAdmission,
        DrainChildCalls,
        InvalidateChildAdmission,
    };
    const int32_t result = wlar_child_sequence::Run(
        &gChildLedger, admission, ProviderGeneration(), operations);
    __atomic_store_n(&gChildOwnerState, UINT32_C(2), __ATOMIC_RELEASE);
    return result;
}

#endif /* !WLAR_RUNTIME_PROVIDER_SEQUENCE_TEST */
