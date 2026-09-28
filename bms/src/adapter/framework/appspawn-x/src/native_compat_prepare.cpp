#include "native_compat_prepare.h"

#include "westlake_thread_guard_registry.h"
#include "westlake_bionic_pthread_bridge.h"
#include "westlake_thread_template_publisher.h"

#include <atomic>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <pthread.h>
#include <sys/random.h>
#include <sys/types.h>
#include <unistd.h>

namespace {

constexpr uint32_t kStockTailReached = UINT32_C(1);
constexpr uint32_t kStockSecurityOwner = UINT32_C(1);
constexpr uint32_t kStockTailPriority = UINT32_C(6000);
constexpr uint32_t kParentEpochTag = UINT32_C(0x50415241);
constexpr uint64_t kPolicyDomain = UINT64_C(0x574c4e43504f4c31);
constexpr uint64_t kNonceDomain = UINT64_C(0x574c4e4342494e44);

static_assert(sizeof(uintptr_t) == 8U,
              "Route-A native compatibility requires AArch64");
static_assert(sizeof(WlncProcessIdentityV1) == 104U,
              "WLNC identity ABI drift");
static_assert(sizeof(WlncParentIdentityV1) == 80U,
              "WLNC parent identity ABI drift");
static_assert(sizeof(WlncAuditSnapshotV1) == 176U,
              "WLNC audit snapshot ABI drift");
static_assert(sizeof(WltgThreadTicketV1) <= WLPB_TICKET_STORAGE_SIZE,
              "pthread bridge ticket storage too small");
static_assert(sizeof(WltgThreadReceiptV1) <= WLPB_RECEIPT_STORAGE_SIZE,
              "pthread bridge receipt storage too small");
static_assert(sizeof(pthread_attr_t) <= WLPB_MUSL_ATTR_STORAGE_SIZE,
              "pthread bridge Musl attr storage too small");
static_assert(sizeof(pthread_t) <= sizeof(uint64_t),
              "pthread bridge thread scalar storage too small");

extern "C" uint8_t *WestLakeNativeCompatReservationBase();

enum class ProductState : uint32_t {
    COLD = 0,
    PARENT_PREPARING = 1,
    PARENT_READY = 2,
    CHILD_PREPARING = 3,
    READY = 4,
    FAILED = 5,
};

struct ProductContext {
    WlncParentIdentityV1 parent_identity;
    WlncProcessIdentityV1 child_identity;
    uint64_t runtime_generation;
    uint32_t owner_uid;
    uint32_t owner_gid;
    uint8_t runtime_provider_sha256[WLNC_SHA256_SIZE];
    WltgProcessBindingV1 binding;
    WltgThreadReceiptV1 main_receipt;
    std::atomic<uint64_t> audit_accepted_count;
    std::atomic<uint64_t> audit_sequence_xor;
    std::atomic<uint64_t> audit_payload_xor;
    std::atomic<uint64_t> audit_type_count[WLTG_EVENT_PROCESS_REJECTED + 1U];
};

ProductContext g_context{};
std::atomic<uint32_t> g_state{static_cast<uint32_t>(ProductState::COLD)};

bool BytesAllZero(const uint8_t *bytes, size_t size)
{
    uint8_t combined = UINT8_C(0);
    for (size_t index = 0; index < size; ++index) {
        combined = static_cast<uint8_t>(combined | bytes[index]);
    }
    return combined == UINT8_C(0);
}

bool WordsAllZero(const uint32_t *words, size_t count)
{
    uint32_t combined = UINT32_C(0);
    for (size_t index = 0; index < count; ++index) {
        combined |= words[index];
    }
    return combined == UINT32_C(0);
}

bool DigestMatchesGeneration(const uint8_t *digest, uint64_t generation)
{
    if (digest == nullptr || generation == UINT64_C(0) ||
        BytesAllZero(digest, WLNC_SHA256_SIZE)) {
        return false;
    }
    uint64_t digest_generation = UINT64_C(0);
    for (size_t index = 0; index < sizeof(digest_generation); ++index) {
        digest_generation =
            (digest_generation << UINT32_C(8)) | digest[index];
    }
    return digest_generation == generation;
}

bool ParentIdentityValid(const WlncParentIdentityV1 *identity)
{
    return identity != nullptr &&
           identity->abi_version == WLNC_ABI_VERSION &&
           identity->struct_size == sizeof(*identity) &&
           identity->runtime_generation != UINT64_C(0) &&
           identity->pid == static_cast<uint32_t>(getpid()) &&
           identity->uid == static_cast<uint32_t>(getuid()) &&
           identity->gid == static_cast<uint32_t>(getgid()) &&
           identity->reserved_zero == UINT32_C(0) &&
           DigestMatchesGeneration(identity->runtime_provider_sha256,
                                   identity->runtime_generation) &&
           WordsAllZero(identity->reserved_zero2,
                        sizeof(identity->reserved_zero2) /
                            sizeof(identity->reserved_zero2[0]));
}

bool ChildIdentityValid(const WlncProcessIdentityV1 *identity)
{
    if (identity == nullptr ||
        identity->abi_version != WLNC_ABI_VERSION ||
        identity->struct_size != sizeof(*identity) ||
        identity->runtime_generation == UINT64_C(0) ||
        identity->message_id == UINT64_C(0) ||
        identity->message_id > UINT32_MAX ||
        identity->parent_stage_tail_reached != kStockTailReached ||
        identity->child_stage_tail_reached != kStockTailReached ||
        identity->bypass_guard_passed != kStockTailReached ||
        identity->security_owner_stock_appspawn != kStockSecurityOwner ||
        identity->parent_tail_priority != kStockTailPriority ||
        identity->child_tail_priority != kStockTailPriority ||
        identity->uid != static_cast<uint32_t>(getuid()) ||
        identity->gid != static_cast<uint32_t>(getgid()) ||
        !DigestMatchesGeneration(identity->runtime_provider_sha256,
                                 identity->runtime_generation)) {
        return false;
    }
    return WordsAllZero(identity->reserved_zero,
                        sizeof(identity->reserved_zero) /
                            sizeof(identity->reserved_zero[0]));
}

bool ChildMatchesPreparedParent(const WlncProcessIdentityV1 &identity)
{
    return g_context.parent_identity.runtime_generation != UINT64_C(0) &&
           identity.runtime_generation ==
               g_context.parent_identity.runtime_generation &&
           std::memcmp(identity.runtime_provider_sha256,
                       g_context.parent_identity.runtime_provider_sha256,
                       WLNC_SHA256_SIZE) == 0 &&
           static_cast<uint32_t>(getpid()) !=
               g_context.parent_identity.pid;
}

bool MakeBinding(uint64_t runtime_generation, uint32_t epoch_tag,
                 uint32_t uid, uint32_t gid,
                 const uint8_t runtime_provider_sha256[WLNC_SHA256_SIZE],
                 WltgProcessBindingV1 *binding)
{
    const pid_t pid = getpid();
    if (pid <= 0 || epoch_tag == UINT32_C(0) || binding == nullptr ||
        !DigestMatchesGeneration(runtime_provider_sha256,
                                 runtime_generation)) {
        return false;
    }
    std::memset(binding, 0, sizeof(*binding));
    binding->abi_version = WLTG_ABI_VERSION;
    binding->struct_size = sizeof(*binding);
    binding->adapter_generation = runtime_generation;
    binding->process_epoch =
        (static_cast<uint64_t>(static_cast<uint32_t>(pid)) << UINT32_C(32)) |
        epoch_tag;
    binding->policy_epoch = runtime_generation ^ kPolicyDomain;
    binding->binding_nonce =
        runtime_generation ^ binding->process_epoch ^
        (static_cast<uint64_t>(uid) << UINT32_C(32)) ^ gid ^
        kNonceDomain;
    if (binding->process_epoch == UINT64_C(0) ||
        binding->policy_epoch == UINT64_C(0) ||
        binding->binding_nonce == UINT64_C(0)) {
        return false;
    }
    for (size_t index = 0; index < WLTG_DIGEST_SIZE; ++index) {
        binding->profile_digest[index] =
            runtime_provider_sha256[index];
        binding->target_digest[index] =
            runtime_provider_sha256[WLTG_DIGEST_SIZE - 1U - index];
    }
    binding->reservation_tp_start = WLTG_RESERVATION_TP_START;
    binding->reservation_size = WLTG_RESERVATION_SIZE;
    binding->stack_guard_tp_offset = WLTG_STACK_GUARD_TP_OFFSET;
    binding->stack_guard_width = WLTG_STACK_GUARD_WIDTH;
    binding->max_live_threads = WLTG_MAX_THREAD_RECORDS;
    return true;
}

int VerifyProcessBinding(void *opaque,
                         const WltgProcessBindingV1 *binding)
{
    const ProductContext *context = static_cast<ProductContext *>(opaque);
    return context != nullptr && binding != nullptr &&
                   getpid() == static_cast<pid_t>(
                   static_cast<uint32_t>(binding->process_epoch >> 32U)) &&
                   getuid() == static_cast<uid_t>(context->owner_uid) &&
                   getgid() == static_cast<gid_t>(context->owner_gid) &&
                   std::memcmp(binding, &context->binding,
                               sizeof(*binding)) == 0
               ? 1
               : 0;
}

uint64_t GetCurrentThreadId(void *opaque)
{
    (void)opaque;
    const pid_t tid = gettid();
    return tid > 0 ? static_cast<uint64_t>(static_cast<uint32_t>(tid))
                   : UINT64_C(0);
}

int ResolveCurrentThreadRegion(void *opaque,
                               const WltgProcessBindingV1 *binding,
                               const WltgThreadTicketV1 *ticket,
                               WltgOwnedRegion *out_region)
{
    (void)opaque;
    (void)ticket;
    if (binding == nullptr || out_region == nullptr) {
        return 0;
    }
    uint8_t *base = WestLakeNativeCompatReservationBase();
    const uint64_t thread_id = GetCurrentThreadId(nullptr);
    if (base == nullptr || thread_id == UINT64_C(0)) {
        return 0;
    }
    std::memset(out_region, 0, sizeof(*out_region));
    out_region->abi_version = WLTG_ABI_VERSION;
    out_region->owner_kind = WLTG_OWNER_MAIN_ELF_TLS_RESERVATION;
    out_region->tp_start_offset = WLTG_RESERVATION_TP_START;
    out_region->byte_size = WLTG_RESERVATION_SIZE;
    out_region->base = base;
    out_region->owner_cookie =
        static_cast<uint64_t>(reinterpret_cast<uintptr_t>(base)) ^
        binding->binding_nonce;
    if (out_region->owner_cookie == UINT64_C(0)) {
        out_region->owner_cookie = binding->binding_nonce;
    }
    out_region->current_thread_id = thread_id;
    out_region->adapter_generation = binding->adapter_generation;
    out_region->process_epoch = binding->process_epoch;
    out_region->policy_epoch = binding->policy_epoch;
    return 1;
}

int GetOsCsprng(void *opaque, uint64_t required_process_epoch,
                WltgGuardSample *out_sample)
{
    const ProductContext *context = static_cast<ProductContext *>(opaque);
    if (context == nullptr || out_sample == nullptr ||
        required_process_epoch != context->binding.process_epoch) {
        return 0;
    }
    std::memset(out_sample, 0, sizeof(*out_sample));
    uint64_t guard = UINT64_C(0);
    const ssize_t count = getrandom(&guard, sizeof(guard), 0);
    if (count != static_cast<ssize_t>(sizeof(guard))) {
        return 0;
    }
    out_sample->value = guard;
    out_sample->source_epoch = required_process_epoch;
    out_sample->quality = WLTG_GUARD_SOURCE_OS_CSPRNG;
    out_sample->reserved_zero = UINT32_C(0);
    return 1;
}

int EmitAuditEvent(void *opaque, const WltgAuditEvent *event)
{
    ProductContext *context = static_cast<ProductContext *>(opaque);
    if (context == nullptr || event == nullptr ||
        event->abi_version != WLTG_ABI_VERSION ||
        event->type < WLTG_EVENT_PROCESS_ARMED ||
        event->type > WLTG_EVENT_PROCESS_REJECTED ||
        event->sequence == UINT64_C(0)) {
        return 0;
    }
    const uint64_t payload =
        event->sequence ^
        (static_cast<uint64_t>(event->type) << UINT32_C(56)) ^
        (static_cast<uint64_t>(event->reason) << UINT32_C(32)) ^
        event->ticket_id ^ event->current_thread_id ^
        event->publication_sequence;
    context->audit_type_count[event->type].fetch_add(
        UINT64_C(1), std::memory_order_relaxed);
    context->audit_sequence_xor.fetch_xor(event->sequence,
                                          std::memory_order_relaxed);
    context->audit_payload_xor.fetch_xor(payload,
                                         std::memory_order_relaxed);
    context->audit_accepted_count.fetch_add(UINT64_C(1),
                                            std::memory_order_release);
    return 1;
}

bool ResultIsOk(const WltgResult &result);

WltgPlatformOpsV1 MakePlatformOps()
{
    WltgPlatformOpsV1 ops{};
    ops.abi_version = WLTG_ABI_VERSION;
    ops.struct_size = sizeof(ops);
    ops.context = &g_context;
    ops.verify_process_binding = VerifyProcessBinding;
    ops.get_current_thread_id = GetCurrentThreadId;
    ops.resolve_current_thread_region = ResolveCurrentThreadRegion;
    ops.get_os_csprng = GetOsCsprng;
    ops.emit_audit_event = EmitAuditEvent;
    return ops;
}

int BridgeIssueThreadTicket(void *opaque, WlpbTicketStorageV1 *storage)
{
    if (opaque != &g_context || storage == nullptr) return 0;
    auto *ticket = reinterpret_cast<WltgThreadTicketV1 *>(storage->bytes);
    std::memset(ticket, 0, sizeof(*ticket));
    const WltgResult result = WLTG_IssueThreadTicket(
        WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE,
        WLTG_THREAD_ROLE_GUEST_PTHREAD, ticket);
    return ResultIsOk(result) ? 1 : 0;
}

int BridgeCancelThreadTicket(void *opaque,
                             const WlpbTicketStorageV1 *storage)
{
    if (opaque != &g_context || storage == nullptr) return 0;
    const auto *ticket = reinterpret_cast<const WltgThreadTicketV1 *>(
        storage->bytes);
    return ResultIsOk(WLTG_CancelThreadTicket(ticket)) ? 1 : 0;
}

int BridgePrepareCurrentThread(void *opaque,
                               const WlpbTicketStorageV1 *ticket_storage,
                               WlpbReceiptStorageV1 *receipt_storage)
{
    if (opaque != &g_context || ticket_storage == nullptr ||
        receipt_storage == nullptr) return 0;
    const auto *ticket = reinterpret_cast<const WltgThreadTicketV1 *>(
        ticket_storage->bytes);
    auto *receipt = reinterpret_cast<WltgThreadReceiptV1 *>(
        receipt_storage->bytes);
    std::memset(receipt, 0, sizeof(*receipt));
    return ResultIsOk(WLTG_PrepareCurrentThread(ticket, receipt)) ? 1 : 0;
}

int BridgeVerifyCurrentThreadReady(void *opaque,
                                   const WlpbReceiptStorageV1 *storage)
{
    if (opaque != &g_context || storage == nullptr) return 0;
    const auto *expected = reinterpret_cast<const WltgThreadReceiptV1 *>(
        storage->bytes);
    WltgThreadReceiptV1 actual{};
    return ResultIsOk(WLTG_VerifyCurrentThreadReady(&actual)) &&
                   std::memcmp(expected, &actual, sizeof(actual)) == 0
               ? 1 : 0;
}

int BridgeRetireCurrentThread(void *opaque,
                              const WlpbReceiptStorageV1 *storage)
{
    if (opaque != &g_context || storage == nullptr) return 0;
    const auto *receipt = reinterpret_cast<const WltgThreadReceiptV1 *>(
        storage->bytes);
    return ResultIsOk(WLTG_RetireCurrentThread(receipt)) ? 1 : 0;
}

uint64_t BridgeGetCurrentThreadId(void *opaque)
{
    return opaque == &g_context ? GetCurrentThreadId(opaque) : UINT64_C(0);
}

int BridgeRealPthreadCreate(void *opaque, uint64_t *thread,
                            const WlpbMuslAttrStorageV1 *attribute,
                            WlpbStartRoutine start, void *argument)
{
    if (opaque != &g_context || thread == nullptr || start == nullptr) {
        return EINVAL;
    }
    pthread_t native_thread{};
    const auto *native_attribute = attribute == nullptr ? nullptr :
        reinterpret_cast<const pthread_attr_t *>(attribute->bytes);
    const int result = pthread_create(&native_thread, native_attribute,
                                      start, argument);
    if (result == 0) {
        std::memset(thread, 0, sizeof(*thread));
        std::memcpy(thread, &native_thread, sizeof(native_thread));
    }
    return result;
}

void BridgeRealPthreadExit(void *opaque, void *result)
{
    if (opaque != &g_context) _exit(126);
    pthread_exit(result);
}

int BridgeRealPthreadAttrInit(void *opaque,
                              WlpbMuslAttrStorageV1 *attribute)
{
    return opaque == &g_context && attribute != nullptr ?
        pthread_attr_init(reinterpret_cast<pthread_attr_t *>(attribute->bytes)) :
        EINVAL;
}

int BridgeRealPthreadAttrDestroy(void *opaque,
                                 WlpbMuslAttrStorageV1 *attribute)
{
    return opaque == &g_context && attribute != nullptr ?
        pthread_attr_destroy(
            reinterpret_cast<pthread_attr_t *>(attribute->bytes)) : EINVAL;
}

int BridgeRealPthreadAttrSetDetachState(void *opaque,
                                        WlpbMuslAttrStorageV1 *attribute,
                                        int state)
{
    return opaque == &g_context && attribute != nullptr ?
        pthread_attr_setdetachstate(
            reinterpret_cast<pthread_attr_t *>(attribute->bytes), state) :
        EINVAL;
}

int BridgeRealPthreadAttrSetStackSize(void *opaque,
                                      WlpbMuslAttrStorageV1 *attribute,
                                      size_t size)
{
    return opaque == &g_context && attribute != nullptr ?
        pthread_attr_setstacksize(
            reinterpret_cast<pthread_attr_t *>(attribute->bytes), size) :
        EINVAL;
}

int BridgeRealPthreadAttrGetStack(void *opaque,
                                  const WlpbMuslAttrStorageV1 *attribute,
                                  void **stack_base, size_t *stack_size)
{
    return opaque == &g_context && attribute != nullptr &&
                   stack_base != nullptr && stack_size != nullptr ?
        pthread_attr_getstack(
            reinterpret_cast<const pthread_attr_t *>(attribute->bytes),
            stack_base, stack_size) : EINVAL;
}

int BridgeRealPthreadGetAttr(void *opaque, uint64_t thread,
                             WlpbMuslAttrStorageV1 *attribute)
{
    if (opaque != &g_context || attribute == nullptr) return EINVAL;
    pthread_t native_thread{};
    std::memcpy(&native_thread, &thread, sizeof(native_thread));
    return pthread_getattr_np(
        native_thread, reinterpret_cast<pthread_attr_t *>(attribute->bytes));
}

void BridgeFatalProcess(void *opaque, uint32_t reason)
{
    (void)reason;
    if (opaque == &g_context) {
        (void)WLTG_Revoke();
    }
    _exit(126);
}

bool ResultIsOk(const WltgResult &result)
{
    return result.status == WLTG_STATUS_OK;
}

void ResetEpochContext(uint64_t runtime_generation, uint32_t uid,
                       uint32_t gid,
                       const uint8_t runtime_provider_sha256[
                           WLNC_SHA256_SIZE])
{
    g_context.runtime_generation = runtime_generation;
    g_context.owner_uid = uid;
    g_context.owner_gid = gid;
    std::memcpy(g_context.runtime_provider_sha256,
                runtime_provider_sha256, WLNC_SHA256_SIZE);
    std::memset(&g_context.binding, 0, sizeof(g_context.binding));
    std::memset(&g_context.main_receipt, 0,
                sizeof(g_context.main_receipt));
    g_context.audit_accepted_count.store(UINT64_C(0),
                                         std::memory_order_relaxed);
    g_context.audit_sequence_xor.store(UINT64_C(0),
                                       std::memory_order_relaxed);
    g_context.audit_payload_xor.store(UINT64_C(0),
                                      std::memory_order_relaxed);
    for (size_t index = 0;
         index < sizeof(g_context.audit_type_count) /
                     sizeof(g_context.audit_type_count[0]);
         ++index) {
        g_context.audit_type_count[index].store(UINT64_C(0),
                                                std::memory_order_relaxed);
    }
}

int PrepareParentEpoch()
{
    WltpProcessEpochSeedV1 publisher_seed{};
    publisher_seed.abi_version = WLTP_ABI_VERSION;
    publisher_seed.struct_size = sizeof(publisher_seed);
    publisher_seed.mode = WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP;
    publisher_seed.adapter_generation =
        g_context.binding.adapter_generation;
    publisher_seed.process_epoch = g_context.binding.process_epoch;
    if (WLTP_BeginProcessEpoch(
            &publisher_seed, WestLakeNativeCompatReservationBase()) !=
        WLTP_PROCESS_EPOCH_OK) {
        return WLNC_PREPARE_PROCESS_EPOCH_FAILED;
    }

    WltgForkSeed registry_seed{};
    registry_seed.abi_version = WLTG_ABI_VERSION;
    registry_seed.adapter_generation =
        g_context.binding.adapter_generation;
    registry_seed.process_epoch = g_context.binding.process_epoch;
    registry_seed.policy_epoch = g_context.binding.policy_epoch;
    WltgResult result = WLTG_AfterForkChildReset(&registry_seed);
    if (!ResultIsOk(result)) {
        return WLNC_PREPARE_FORK_RESET_FAILED;
    }

    const WltgPlatformOpsV1 ops = MakePlatformOps();
    result = WLTG_ProcessArm(&g_context.binding, &ops);
    if (!ResultIsOk(result)) {
        return WLNC_PREPARE_PROCESS_ARM_FAILED;
    }

    WltgThreadTicketV1 ticket{};
    result = WLTG_IssueThreadTicket(
        WLTG_ADMISSION_PARENT_PRELOAD,
        WLTG_THREAD_ROLE_PARENT_PRELOAD, &ticket);
    if (!ResultIsOk(result)) {
        return WLNC_PREPARE_MAIN_TICKET_FAILED;
    }
    result = WLTG_PrepareCurrentThread(&ticket, &g_context.main_receipt);
    if (!ResultIsOk(result)) {
        return WLNC_PREPARE_MAIN_PUBLICATION_FAILED;
    }
    WltgThreadReceiptV1 verified{};
    result = WLTG_VerifyCurrentThreadReady(&verified);
    if (!ResultIsOk(result) ||
        std::memcmp(&verified, &g_context.main_receipt,
                    sizeof(verified)) != 0) {
        (void)WLTG_Revoke();
        return WLNC_PREPARE_MAIN_VERIFY_FAILED;
    }
    if (WLTP_PublishMainThreadTemplate(
            WestLakeNativeCompatReservationBase()) != WLTP_PUBLISH_OK) {
        (void)WLTG_Revoke();
        return WLNC_PREPARE_THREAD_TEMPLATE_PUBLISH_FAILED;
    }
    return WLNC_PREPARE_OK;
}

void MarkFailed()
{
    g_state.store(static_cast<uint32_t>(ProductState::FAILED),
                  std::memory_order_release);
}

}  // namespace

namespace appspawnx {

int WestLakeNativeCompatPrepareParentRuntime(
    const WlncParentIdentityV1 *identity)
{
    if (!ParentIdentityValid(identity)) {
        MarkFailed();
        return WLNC_PREPARE_INVALID_IDENTITY;
    }
    uint32_t expected = static_cast<uint32_t>(ProductState::COLD);
    if (!g_state.compare_exchange_strong(
            expected,
            static_cast<uint32_t>(ProductState::PARENT_PREPARING),
            std::memory_order_acq_rel, std::memory_order_acquire)) {
        MarkFailed();
        return WLNC_PREPARE_REPLAY;
    }

    std::memset(&g_context.parent_identity, 0,
                sizeof(g_context.parent_identity));
    std::memset(&g_context.child_identity, 0,
                sizeof(g_context.child_identity));
    g_context.parent_identity = *identity;
    ResetEpochContext(identity->runtime_generation, identity->uid,
                      identity->gid,
                      identity->runtime_provider_sha256);
    if (!MakeBinding(identity->runtime_generation, kParentEpochTag,
                     identity->uid, identity->gid,
                     identity->runtime_provider_sha256,
                     &g_context.binding)) {
        MarkFailed();
        return WLNC_PREPARE_INVALID_IDENTITY;
    }
    const int result = PrepareParentEpoch();
    if (result != WLNC_PREPARE_OK) {
        MarkFailed();
        return result;
    }
    g_state.store(static_cast<uint32_t>(ProductState::PARENT_READY),
                  std::memory_order_release);
    return WLNC_PREPARE_OK;
}

int WestLakeNativeCompatVerifyParentPreloadThreadReady(
    uint64_t runtime_generation)
{
    if (runtime_generation == UINT64_C(0) ||
        g_state.load(std::memory_order_acquire) !=
            static_cast<uint32_t>(ProductState::PARENT_READY) ||
        runtime_generation != g_context.runtime_generation ||
        getpid() != static_cast<pid_t>(g_context.parent_identity.pid)) {
        return WLNC_PREPARE_PROCESS_NOT_READY;
    }
    WltgThreadReceiptV1 receipt{};
    const WltgResult result = WLTG_VerifyCurrentThreadReady(&receipt);
    return ResultIsOk(result) &&
                   std::memcmp(&receipt, &g_context.main_receipt,
                               sizeof(receipt)) == 0 &&
                   g_state.load(std::memory_order_acquire) ==
                       static_cast<uint32_t>(ProductState::PARENT_READY)
               ? WLNC_PREPARE_OK
               : WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
}

int WestLakeNativeCompatPrepareMainThread(
    const WlncProcessIdentityV1 *identity)
{
    if (!ChildIdentityValid(identity)) {
        MarkFailed();
        return WLNC_PREPARE_INVALID_IDENTITY;
    }
    if (!ChildMatchesPreparedParent(*identity)) {
        MarkFailed();
        return WLNC_PREPARE_GENERATION_MISMATCH;
    }
    uint32_t expected = static_cast<uint32_t>(ProductState::PARENT_READY);
    if (!g_state.compare_exchange_strong(
            expected,
            static_cast<uint32_t>(ProductState::CHILD_PREPARING),
            std::memory_order_acq_rel, std::memory_order_acquire)) {
        MarkFailed();
        return WLNC_PREPARE_REPLAY;
    }

    g_context.child_identity = *identity;
    ResetEpochContext(identity->runtime_generation, identity->uid,
                      identity->gid,
                      identity->runtime_provider_sha256);
    if (!MakeBinding(identity->runtime_generation,
                     static_cast<uint32_t>(identity->message_id),
                     identity->uid, identity->gid,
                     identity->runtime_provider_sha256,
                     &g_context.binding)) {
        MarkFailed();
        return WLNC_PREPARE_INVALID_IDENTITY;
    }
    WltpProcessEpochSeedV1 publisher_seed{};
    publisher_seed.abi_version = WLTP_ABI_VERSION;
    publisher_seed.struct_size = sizeof(publisher_seed);
    publisher_seed.mode = WLTP_PROCESS_EPOCH_AFTER_FORK_CHILD;
    publisher_seed.adapter_generation =
        g_context.binding.adapter_generation;
    publisher_seed.process_epoch = g_context.binding.process_epoch;
    if (WLTP_BeginProcessEpoch(
            &publisher_seed, WestLakeNativeCompatReservationBase()) !=
        WLTP_PROCESS_EPOCH_OK) {
        MarkFailed();
        return WLNC_PREPARE_PROCESS_EPOCH_FAILED;
    }

    WltgForkSeed registry_seed{};
    registry_seed.abi_version = WLTG_ABI_VERSION;
    registry_seed.adapter_generation =
        g_context.binding.adapter_generation;
    registry_seed.process_epoch = g_context.binding.process_epoch;
    registry_seed.policy_epoch = g_context.binding.policy_epoch;
    WltgResult registry_result = WLTG_AfterForkChildReset(&registry_seed);
    if (!ResultIsOk(registry_result)) {
        MarkFailed();
        return WLNC_PREPARE_FORK_RESET_FAILED;
    }

    const WltgPlatformOpsV1 ops = MakePlatformOps();
    registry_result = WLTG_ProcessArm(&g_context.binding, &ops);
    if (!ResultIsOk(registry_result)) {
        MarkFailed();
        return WLNC_PREPARE_PROCESS_ARM_FAILED;
    }

    WltgThreadTicketV1 ticket{};
    registry_result = WLTG_IssueThreadTicket(
        WLTG_ADMISSION_MAIN_POST_SPECIALIZATION,
        WLTG_THREAD_ROLE_MAIN, &ticket);
    if (!ResultIsOk(registry_result)) {
        MarkFailed();
        return WLNC_PREPARE_MAIN_TICKET_FAILED;
    }
    registry_result = WLTG_PrepareCurrentThread(
        &ticket, &g_context.main_receipt);
    if (!ResultIsOk(registry_result)) {
        MarkFailed();
        return WLNC_PREPARE_MAIN_PUBLICATION_FAILED;
    }
    WltgThreadReceiptV1 verified{};
    registry_result = WLTG_VerifyCurrentThreadReady(&verified);
    if (!ResultIsOk(registry_result) ||
        std::memcmp(&verified, &g_context.main_receipt,
                    sizeof(verified)) != 0) {
        (void)WLTG_Revoke();
        MarkFailed();
        return WLNC_PREPARE_MAIN_VERIFY_FAILED;
    }
    if (WLTP_PublishMainThreadTemplate(
            WestLakeNativeCompatReservationBase()) != WLTP_PUBLISH_OK) {
        (void)WLTG_Revoke();
        MarkFailed();
        _exit(126);
    }
    g_state.store(static_cast<uint32_t>(ProductState::READY),
                  std::memory_order_release);
    return WLNC_PREPARE_OK;
}

int WestLakeNativeCompatVerifyCurrentThreadReady()
{
    if (g_state.load(std::memory_order_acquire) !=
        static_cast<uint32_t>(ProductState::READY)) {
        return WLNC_PREPARE_PROCESS_NOT_READY;
    }
    WltgThreadReceiptV1 receipt{};
    const WltgResult result = WLTG_VerifyCurrentThreadReady(&receipt);
    return ResultIsOk(result) ? WLNC_PREPARE_OK
                              : WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
}

int WestLakeNativeCompatGetAuditSnapshot(WlncAuditSnapshotV1 *out_snapshot)
{
    if (out_snapshot == nullptr) {
        return WLNC_PREPARE_AUDIT_SNAPSHOT_INVALID;
    }
    std::memset(out_snapshot, 0, sizeof(*out_snapshot));
    if (g_state.load(std::memory_order_acquire) !=
        static_cast<uint32_t>(ProductState::READY)) {
        return WLNC_PREPARE_PROCESS_NOT_READY;
    }

    const uint64_t accepted_before =
        g_context.audit_accepted_count.load(std::memory_order_acquire);
    WltgProcessSnapshotV1 registry{};
    const WltgResult result = WLTG_GetProcessSnapshot(&registry);
    if (!ResultIsOk(result)) {
        return WLNC_PREPARE_AUDIT_SNAPSHOT_INVALID;
    }

    WlncAuditSnapshotV1 snapshot{};
    snapshot.abi_version = WLNC_ABI_VERSION;
    snapshot.struct_size = sizeof(snapshot);
    snapshot.product_state = static_cast<uint32_t>(ProductState::READY);
    snapshot.event_type_slots = WLNC_AUDIT_EVENT_TYPE_SLOTS;
    snapshot.runtime_generation = g_context.runtime_generation;
    snapshot.process_epoch = g_context.binding.process_epoch;
    snapshot.sequence_xor_digest =
        g_context.audit_sequence_xor.load(std::memory_order_relaxed);
    snapshot.payload_xor_digest =
        g_context.audit_payload_xor.load(std::memory_order_relaxed);
    for (size_t index = 0; index < WLNC_AUDIT_EVENT_TYPE_SLOTS; ++index) {
        snapshot.event_type_count[index] =
            g_context.audit_type_count[index].load(std::memory_order_relaxed);
    }
    const uint64_t accepted_after =
        g_context.audit_accepted_count.load(std::memory_order_acquire);
    if (accepted_before != accepted_after ||
        accepted_after != registry.audit_sequence ||
        registry.audit_drop_count != UINT64_C(0) ||
        g_state.load(std::memory_order_acquire) !=
            static_cast<uint32_t>(ProductState::READY)) {
        return WLNC_PREPARE_AUDIT_SNAPSHOT_RACE;
    }
    snapshot.accepted_event_count = accepted_after;
    snapshot.registry_audit_sequence = registry.audit_sequence;
    snapshot.registry_audit_drop_count = registry.audit_drop_count;
    snapshot.registry_ready_count = registry.ready_count;
    snapshot.registry_active_ticket_count = registry.active_ticket_count;
    *out_snapshot = snapshot;
    return WLNC_PREPARE_OK;
}

int WestLakeNativeCompatGetPthreadBridgeOps(WlpbHostOpsV1 *out_ops)
{
    const uint32_t state = g_state.load(std::memory_order_acquire);
    if (out_ops == nullptr ||
        (state != static_cast<uint32_t>(ProductState::PARENT_READY) &&
         state != static_cast<uint32_t>(ProductState::READY))) {
        return WLNC_PREPARE_PROCESS_NOT_READY;
    }
    WlpbHostOpsV1 ops{};
    ops.abi_version = WLPB_ABI_VERSION;
    ops.struct_size = sizeof(ops);
    ops.context = &g_context;
    ops.issue_thread_ticket = BridgeIssueThreadTicket;
    ops.cancel_thread_ticket = BridgeCancelThreadTicket;
    ops.prepare_current_thread = BridgePrepareCurrentThread;
    ops.verify_current_thread_ready = BridgeVerifyCurrentThreadReady;
    ops.retire_current_thread = BridgeRetireCurrentThread;
    ops.get_current_thread_id = BridgeGetCurrentThreadId;
    ops.real_pthread_create = BridgeRealPthreadCreate;
    ops.real_pthread_exit = BridgeRealPthreadExit;
    ops.real_pthread_attr_init = BridgeRealPthreadAttrInit;
    ops.real_pthread_attr_destroy = BridgeRealPthreadAttrDestroy;
    ops.real_pthread_attr_setdetachstate = BridgeRealPthreadAttrSetDetachState;
    ops.real_pthread_attr_setstacksize = BridgeRealPthreadAttrSetStackSize;
    ops.real_pthread_attr_getstack = BridgeRealPthreadAttrGetStack;
    ops.real_pthread_getattr_np = BridgeRealPthreadGetAttr;
    ops.fatal_process = BridgeFatalProcess;
    ops.generation = g_context.binding.adapter_generation;
    *out_ops = ops;
    return WLNC_PREPARE_OK;
}

}  // namespace appspawnx

extern "C" int westlake_native_compat_prepare_parent_runtime(
    const WlncParentIdentityV1 *identity)
{
    return appspawnx::WestLakeNativeCompatPrepareParentRuntime(identity);
}

extern "C" int westlake_native_compat_verify_parent_preload_thread_ready(
    uint64_t runtime_generation)
{
    return appspawnx::WestLakeNativeCompatVerifyParentPreloadThreadReady(
        runtime_generation);
}

extern "C" int westlake_native_compat_prepare_main_thread(
    const WlncProcessIdentityV1 *identity)
{
    return appspawnx::WestLakeNativeCompatPrepareMainThread(identity);
}

extern "C" int westlake_native_compat_verify_current_thread_ready(void)
{
    return appspawnx::WestLakeNativeCompatVerifyCurrentThreadReady();
}

extern "C" int westlake_native_compat_get_audit_snapshot(
    WlncAuditSnapshotV1 *out_snapshot)
{
    return appspawnx::WestLakeNativeCompatGetAuditSnapshot(out_snapshot);
}

extern "C" int westlake_native_compat_get_pthread_bridge_ops(
    WlpbHostOpsV1 *out_ops)
{
    return appspawnx::WestLakeNativeCompatGetPthreadBridgeOps(out_ops);
}
