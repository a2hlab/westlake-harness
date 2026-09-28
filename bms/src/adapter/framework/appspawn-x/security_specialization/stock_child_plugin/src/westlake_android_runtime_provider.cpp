/* Route-A specialized-child runtime provider. A06 stops at T11. */

#include "../include/westlake_generation_receipt_v2.h"

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace wlar_child_sequence {

constexpr uint32_t AUDIT_ABI_VERSION = UINT32_C(1);
constexpr uint32_t AUDIT_PRODUCT_READY = UINT32_C(4);
constexpr uint32_t AUDIT_EVENT_TYPE_SLOTS = UINT32_C(10);
constexpr uint32_t AUDIT_SNAPSHOT_SIZE = UINT32_C(176);

struct LosslessAuditSnapshot {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t product_state;
    uint32_t event_type_slots;
    uint64_t runtime_generation;
    uint64_t process_epoch;
    uint64_t accepted_event_count;
    uint64_t sequence_xor_digest;
    uint64_t payload_xor_digest;
    uint64_t registry_audit_sequence;
    uint64_t registry_audit_drop_count;
    uint64_t event_type_count[AUDIT_EVENT_TYPE_SLOTS];
    uint32_t registry_ready_count;
    uint32_t registry_active_ticket_count;
    uint32_t reserved_zero[4];
};

static_assert(sizeof(LosslessAuditSnapshot) == AUDIT_SNAPSHOT_SIZE,
              "lossless WLTG audit snapshot layout drift");
static_assert(alignof(LosslessAuditSnapshot) == alignof(uint64_t),
              "lossless WLTG audit snapshot alignment drift");

enum LedgerState : uint32_t {
    EMPTY = 0,
    CLAIMING = 1,
    IN_PROGRESS = 2,
    SUCCEEDED = 3,
    STOPPING = 4,
    RECONCILE_REQUIRED = 5,
    TERMINAL = 6,
};

struct Operations {
    void *context;
    uint64_t expected_runtime_generation;
    int (*audit_snapshot)(void *, LosslessAuditSnapshot *);
    int (*commit_audit)(void *);
    int (*constructors)(void *);
    int (*vm)(void *);
    int (*jni)(void *);
    int (*revoke)(void *);
    int (*drain)(void *);
    int (*invalidate)(void *);
    uint64_t (*thread_id)(void *);
    uint64_t (*monotonic_ns)(void *);
    int (*digest)(void *, const void *, size_t,
                  uint8_t[WLGR_V2_SHA256_SIZE]);
};

struct Ledger {
    uint32_t state;
    uint32_t inflight;
    int32_t first_cause;
    uint32_t reserved_zero;
    uint64_t last_sequence;
    uint64_t last_timestamp_ns;
    westlake_generation_identity_v2 identity;
    uint8_t request_digest[WLGR_V2_SHA256_SIZE];
    westlake_a02_prerequisite_bundle_v2 bundle;
    westlake_runtime_stage_receipt_v2 failure;
};

static bool OpsValid(const Operations &ops)
{
    return ops.expected_runtime_generation != 0U &&
        ops.audit_snapshot != nullptr && ops.commit_audit != nullptr &&
        ops.constructors != nullptr && ops.vm != nullptr &&
        ops.jni != nullptr && ops.revoke != nullptr &&
        ops.drain != nullptr && ops.invalidate != nullptr &&
        ops.thread_id != nullptr && ops.monotonic_ns != nullptr &&
        ops.digest != nullptr;
}

static bool AuditSnapshotValid(const LosslessAuditSnapshot &snapshot,
                               uint64_t expected_runtime_generation)
{
    uint64_t typeCount = UINT64_C(0);
    if (snapshot.abi_version != AUDIT_ABI_VERSION ||
        snapshot.struct_size != AUDIT_SNAPSHOT_SIZE ||
        snapshot.product_state != AUDIT_PRODUCT_READY ||
        snapshot.event_type_slots != AUDIT_EVENT_TYPE_SLOTS ||
        snapshot.runtime_generation != expected_runtime_generation ||
        snapshot.process_epoch == 0U ||
        snapshot.accepted_event_count == 0U ||
        snapshot.accepted_event_count != snapshot.registry_audit_sequence ||
        snapshot.registry_audit_drop_count != UINT64_C(0) ||
        snapshot.registry_ready_count != 1U ||
        snapshot.registry_active_ticket_count != 0U) {
        return false;
    }
    for (uint32_t i = 0; i < AUDIT_EVENT_TYPE_SLOTS; ++i) {
        if (snapshot.event_type_count[i] > UINT64_MAX - typeCount) {
            return false;
        }
        typeCount += snapshot.event_type_count[i];
    }
    return typeCount == snapshot.accepted_event_count &&
        wlgr_v2_bytes_zero(
            reinterpret_cast<const uint8_t *>(snapshot.reserved_zero),
            sizeof(snapshot.reserved_zero));
}

static bool PriorValid(const westlake_generation_identity_v2 &identity,
                       const westlake_runtime_stage_receipt_v2 *prior,
                       uint32_t count)
{
    static const uint32_t transitions[3] = {
        WLGR_V2_TRANSITION_T03,
        WLGR_V2_TRANSITION_T07,
        WLGR_V2_TRANSITION_T08,
    };
    if (!wlgr_v2_identity_valid(&identity) || prior == nullptr || count != 3U) {
        return false;
    }
    for (uint32_t i = 0; i < count; ++i) {
        if (!wlgr_v2_receipt_valid(&prior[i]) ||
            prior[i].transition_id != transitions[i] ||
            !wlgr_v2_identity_equal(&identity, &prior[i].identity) ||
            (i != 0U &&
             (prior[i].sequence <= prior[i - 1U].sequence ||
              prior[i].monotonic_timestamp_ns <
                  prior[i - 1U].monotonic_timestamp_ns))) {
            return false;
        }
    }
    return true;
}

static bool Hash(const Operations &ops, const void *data, size_t size,
                 uint8_t output[WLGR_V2_SHA256_SIZE])
{
    return ops.digest(ops.context, data, size, output) == 0 &&
        !wlgr_v2_bytes_zero(output, WLGR_V2_SHA256_SIZE);
}

static uint64_t NextTime(const Operations &ops, uint64_t previous)
{
    const uint64_t now = ops.monotonic_ns(ops.context);
    return now > previous ? now : previous + UINT64_C(1);
}

static int32_t TypedCause(int native_cause, int32_t fallback)
{
    return ((native_cause <= WLGR_V2_ERROR_INVALID_ARGUMENT &&
             native_cause >= WLGR_V2_ERROR_TERMINAL_CONFLICT) ||
            native_cause == WLGR_V2_ERROR_INTERNAL) ?
        static_cast<int32_t>(native_cause) : fallback;
}

static bool FillSuccessReceipt(
    const Operations &ops, const westlake_generation_identity_v2 &identity,
    uint32_t transition, uint64_t sequence, uint64_t previous_time,
    const void *input, size_t input_size,
    westlake_runtime_stage_receipt_v2 *out)
{
    struct OutputSeed {
        westlake_generation_identity_v2 identity;
        uint32_t transition;
        uint32_t owner;
        uint64_t sequence;
    } seed{};
    std::memset(out, 0, sizeof(*out));
    out->magic = WLGR_V2_RECEIPT_MAGIC;
    out->abi_version = WLGR_V2_ABI_VERSION;
    out->struct_size = WLGR_V2_RECEIPT_SIZE;
    out->struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    out->identity = identity;
    out->action_id = WLGR_V2_ACTION_FN02_A06;
    out->transition_id = transition;
    out->stage_before = wlgr_v2_expected_stage_before(transition);
    out->stage_after = wlgr_v2_expected_stage_after(transition);
    out->owner = wlgr_v2_expected_owner(transition);
    out->publication_state = WLGR_V2_PUBLICATION_COMMITTED;
    out->result_code = WLGR_V2_RESULT_OK;
    out->first_cause = WLGR_V2_RESULT_OK;
    out->child_thread_id = ops.thread_id(ops.context);
    out->sequence = sequence;
    out->monotonic_timestamp_ns = NextTime(ops, previous_time);
    seed.identity = identity;
    seed.transition = transition;
    seed.owner = out->owner;
    seed.sequence = sequence;
    return out->child_thread_id != 0U &&
        input != nullptr && input_size != 0U &&
        Hash(ops, input, input_size, out->input_digest) &&
        Hash(ops, &seed, sizeof(seed), out->output_digest) &&
        wlgr_v2_receipt_valid(out);
}

struct AuditInputSeed {
    westlake_runtime_stage_receipt_v2 previous;
    LosslessAuditSnapshot audit_snapshot;
};

static_assert(offsetof(AuditInputSeed, audit_snapshot) ==
                  sizeof(westlake_runtime_stage_receipt_v2),
              "T09 audit input seed padding drift");
static_assert(sizeof(AuditInputSeed) ==
                  sizeof(westlake_runtime_stage_receipt_v2) +
                      sizeof(LosslessAuditSnapshot),
              "T09 audit input seed trailing padding drift");

static bool SameRequest(const Ledger &ledger,
                        const westlake_generation_identity_v2 &identity,
                        const uint8_t digest[WLGR_V2_SHA256_SIZE])
{
    return wlgr_v2_identity_equal(&ledger.identity, &identity) &&
        wlgr_v2_bytes_equal(ledger.request_digest, digest,
                            WLGR_V2_SHA256_SIZE);
}

static int32_t CopyRecorded(
    const Ledger &ledger, const westlake_generation_identity_v2 &identity,
    const uint8_t digest[WLGR_V2_SHA256_SIZE],
    westlake_a02_prerequisite_bundle_v2 *bundle,
    westlake_runtime_stage_receipt_v2 *failure)
{
    const uint32_t state = __atomic_load_n(&ledger.state, __ATOMIC_ACQUIRE);
    if (state == CLAIMING) {
        return WLGR_V2_RESULT_IN_PROGRESS;
    }
    if (!SameRequest(ledger, identity, digest)) {
        return WLGR_V2_ERROR_EVENT_CONFLICT;
    }
    if (state == IN_PROGRESS) {
        return WLGR_V2_RESULT_IN_PROGRESS;
    }
    if (state == SUCCEEDED) {
        if (bundle != nullptr) {
            *bundle = ledger.bundle;
        }
        return WLGR_V2_RESULT_OK;
    }
    if (failure != nullptr) {
        *failure = ledger.failure;
    }
    return ledger.first_cause == 0 ? WLGR_V2_ERROR_INTERNAL :
        ledger.first_cause;
}

static int32_t Fail(Ledger *ledger, const Operations &ops,
                    uint32_t stage_before, int32_t cause, int native_cause,
                    const uint8_t request_digest[WLGR_V2_SHA256_SIZE],
                    westlake_runtime_stage_receipt_v2 *out_failure)
{
    const int revoke_rc = ops.revoke(ops.context);
    const int drain_rc = ops.drain(ops.context);
    const int invalidate_rc = ops.invalidate(ops.context);
    const bool reconcile = revoke_rc != 0 || drain_rc != 0 ||
        invalidate_rc != 0;
    westlake_runtime_stage_receipt_v2 failure{};
    failure.magic = WLGR_V2_RECEIPT_MAGIC;
    failure.abi_version = WLGR_V2_ABI_VERSION;
    failure.struct_size = WLGR_V2_RECEIPT_SIZE;
    failure.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    failure.identity = ledger->identity;
    failure.action_id = WLGR_V2_ACTION_FN02_A06;
    failure.transition_id = WLGR_V2_TRANSITION_T13;
    failure.stage_before = stage_before;
    failure.stage_after = reconcile ? WLGR_V2_STAGE_RECONCILE_REQUIRED :
        WLGR_V2_STAGE_STOPPING;
    failure.owner = WLGR_V2_OWNER_GENERATION_REDUCER;
    failure.publication_state = reconcile ?
        WLGR_V2_PUBLICATION_RECONCILE_REQUIRED :
        WLGR_V2_PUBLICATION_IN_PROGRESS;
    failure.result_code = cause;
    failure.first_cause = cause;
    failure.native_cause = native_cause;
    failure.child_thread_id = ops.thread_id(ops.context);
    failure.sequence = ledger->last_sequence + UINT64_C(1);
    failure.monotonic_timestamp_ns =
        NextTime(ops, ledger->last_timestamp_ns);
    std::memcpy(failure.input_digest, request_digest,
                WLGR_V2_SHA256_SIZE);
    if (!Hash(ops, &failure.identity, sizeof(failure.identity),
              failure.output_digest) || !wlgr_v2_receipt_valid(&failure)) {
        cause = WLGR_V2_ERROR_INTERNAL;
        failure.result_code = cause;
        failure.first_cause = cause;
    }
    ledger->first_cause = cause;
    ledger->failure = failure;
    __atomic_store_n(&ledger->inflight, UINT32_C(0), __ATOMIC_RELEASE);
    __atomic_store_n(&ledger->state,
                     reconcile ? RECONCILE_REQUIRED : STOPPING,
                     __ATOMIC_RELEASE);
    if (out_failure != nullptr) {
        *out_failure = failure;
    }
    return cause;
}

int32_t Run(Ledger *ledger,
            const westlake_generation_identity_v2 &identity,
            const westlake_runtime_stage_receipt_v2 *prior,
            uint32_t prior_count, const Operations &ops,
            westlake_a02_prerequisite_bundle_v2 *out_bundle,
            westlake_runtime_stage_receipt_v2 *out_failure)
{
    uint8_t request_digest[WLGR_V2_SHA256_SIZE]{};
    if (ledger == nullptr || out_bundle == nullptr || !OpsValid(ops) ||
        !PriorValid(identity, prior, prior_count) ||
        !Hash(ops, prior, sizeof(*prior) * prior_count, request_digest)) {
        return WLGR_V2_ERROR_INVALID_ARGUMENT;
    }
    uint32_t expected = EMPTY;
    if (!__atomic_compare_exchange_n(&ledger->state, &expected, CLAIMING,
                                     false, __ATOMIC_ACQ_REL,
                                     __ATOMIC_ACQUIRE)) {
        return CopyRecorded(*ledger, identity, request_digest,
                            out_bundle, out_failure);
    }
    ledger->identity = identity;
    std::memcpy(ledger->request_digest, request_digest,
                sizeof(ledger->request_digest));
    ledger->first_cause = 0;
    ledger->last_sequence = prior[2].sequence;
    ledger->last_timestamp_ns = prior[2].monotonic_timestamp_ns;
    __atomic_store_n(&ledger->inflight, UINT32_C(1), __ATOMIC_RELEASE);
    __atomic_store_n(&ledger->state, IN_PROGRESS, __ATOMIC_RELEASE);

    LosslessAuditSnapshot audit_snapshot{};
    const int audit_rc =
        ops.audit_snapshot(ops.context, &audit_snapshot);
    if (audit_rc != 0) {
        return Fail(ledger, ops, WLGR_V2_STAGE_PROVIDER_MAPPED,
                    TypedCause(audit_rc,
                               WLGR_V2_ERROR_MISSING_PREREQUISITE),
                    audit_rc, request_digest, out_failure);
    }
    if (!AuditSnapshotValid(audit_snapshot,
                            ops.expected_runtime_generation)) {
        return Fail(ledger, ops, WLGR_V2_STAGE_PROVIDER_MAPPED,
                    WLGR_V2_ERROR_DIGEST_INVALID, 0, request_digest,
                    out_failure);
    }
    const int audit_commit_rc = ops.commit_audit(ops.context);
    if (audit_commit_rc != 0) {
        return Fail(ledger, ops, WLGR_V2_STAGE_PROVIDER_MAPPED,
                    TypedCause(audit_commit_rc,
                               WLGR_V2_ERROR_MISSING_PREREQUISITE),
                    audit_commit_rc, request_digest, out_failure);
    }
    const int constructor_rc = ops.constructors(ops.context);
    if (constructor_rc != 0) {
        return Fail(ledger, ops, WLGR_V2_STAGE_PROVIDER_MAPPED,
                    TypedCause(constructor_rc,
                               WLGR_V2_ERROR_CONSTRUCTOR_FAILED),
                    constructor_rc, request_digest,
                    out_failure);
    }
    westlake_a02_prerequisite_bundle_v2 bundle{};
    bundle.magic = WLGR_V2_A02_BUNDLE_MAGIC;
    bundle.abi_version = WLGR_V2_ABI_VERSION;
    bundle.struct_size = WLGR_V2_A02_BUNDLE_SIZE;
    bundle.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    bundle.identity = identity;
    bundle.producer_action_id = WLGR_V2_ACTION_FN02_A06;
    bundle.consumer_action_id = WLGR_V2_ACTION_FN02_A02;
    bundle.producer_terminal_transition_id = WLGR_V2_TRANSITION_T11;
    bundle.next_transition_id = WLGR_V2_TRANSITION_T12;
    bundle.bundle_state = WLGR_V2_BUNDLE_READY_FOR_A02;
    bundle.receipt_count = WLGR_V2_A02_PREREQUISITE_COUNT;
    for (uint32_t i = 0; i < prior_count; ++i) {
        bundle.receipts[i] = prior[i];
    }
    uint64_t sequence = prior[2].sequence + UINT64_C(1);
    uint64_t time = prior[2].monotonic_timestamp_ns;
    const AuditInputSeed audit_input{bundle.receipts[2], audit_snapshot};
    if (!FillSuccessReceipt(ops, identity, WLGR_V2_TRANSITION_T09,
                            sequence++, time, &audit_input,
                            sizeof(audit_input),
                            &bundle.receipts[3])) {
        return Fail(ledger, ops, WLGR_V2_STAGE_PROVIDER_MAPPED,
                    WLGR_V2_ERROR_INTERNAL, 0, request_digest, out_failure);
    }
    time = bundle.receipts[3].monotonic_timestamp_ns;
    ledger->last_sequence = bundle.receipts[3].sequence;
    ledger->last_timestamp_ns = time;
    const int vm_rc = ops.vm(ops.context);
    if (vm_rc != 0) {
        return Fail(ledger, ops, WLGR_V2_STAGE_CONSTRUCTORS_COMPLETED,
                    WLGR_V2_ERROR_VM_CREATE_FAILED, vm_rc, request_digest,
                    out_failure);
    }
    if (!FillSuccessReceipt(ops, identity, WLGR_V2_TRANSITION_T10,
                            sequence++, time, &bundle.receipts[3],
                            sizeof(bundle.receipts[3]),
                            &bundle.receipts[4])) {
        return Fail(ledger, ops, WLGR_V2_STAGE_CONSTRUCTORS_COMPLETED,
                    WLGR_V2_ERROR_INTERNAL, 0, request_digest, out_failure);
    }
    time = bundle.receipts[4].monotonic_timestamp_ns;
    ledger->last_sequence = bundle.receipts[4].sequence;
    ledger->last_timestamp_ns = time;
    const int jni_rc = ops.jni(ops.context);
    if (jni_rc != 0) {
        return Fail(ledger, ops, WLGR_V2_STAGE_VM_CREATED,
                    WLGR_V2_ERROR_JNI_REGISTER_FAILED, jni_rc, request_digest,
                    out_failure);
    }
    if (!FillSuccessReceipt(ops, identity, WLGR_V2_TRANSITION_T11,
                            sequence, time, &bundle.receipts[4],
                            sizeof(bundle.receipts[4]),
                            &bundle.receipts[5])) {
        return Fail(ledger, ops, WLGR_V2_STAGE_VM_CREATED,
                    WLGR_V2_ERROR_INTERNAL, 0, request_digest, out_failure);
    }
    bundle.first_sequence = bundle.receipts[0].sequence;
    bundle.last_sequence = bundle.receipts[5].sequence;
    ledger->last_sequence = bundle.receipts[5].sequence;
    ledger->last_timestamp_ns = bundle.receipts[5].monotonic_timestamp_ns;
    bundle.monotonic_created_timestamp_ns =
        NextTime(ops, bundle.receipts[5].monotonic_timestamp_ns);
    if (!Hash(ops, &bundle, offsetof(westlake_a02_prerequisite_bundle_v2,
                                    bundle_digest), bundle.bundle_digest) ||
        !wlgr_v2_a02_bundle_valid(&bundle)) {
        return Fail(ledger, ops, WLGR_V2_STAGE_JNI_READY,
                    WLGR_V2_ERROR_INTERNAL, 0, request_digest, out_failure);
    }
    ledger->bundle = bundle;
    __atomic_store_n(&ledger->inflight, UINT32_C(0), __ATOMIC_RELEASE);
    __atomic_store_n(&ledger->state, SUCCEEDED, __ATOMIC_RELEASE);
    *out_bundle = bundle;
    return WLGR_V2_RESULT_OK;
}

int32_t AcknowledgeDeath(Ledger *ledger, const Operations &ops,
                         westlake_runtime_stage_receipt_v2 *out)
{
    if (ledger == nullptr || out == nullptr || !OpsValid(ops)) {
        return WLGR_V2_ERROR_INVALID_ARGUMENT;
    }
    const uint32_t state = __atomic_load_n(&ledger->state, __ATOMIC_ACQUIRE);
    if (state != STOPPING && state != RECONCILE_REQUIRED) {
        return WLGR_V2_ERROR_TERMINAL_CONFLICT;
    }
    westlake_runtime_stage_receipt_v2 terminal = ledger->failure;
    terminal.stage_after = WLGR_V2_STAGE_TERMINATED;
    terminal.publication_state = WLGR_V2_PUBLICATION_TERMINAL;
    terminal.monotonic_timestamp_ns =
        NextTime(ops, terminal.monotonic_timestamp_ns);
    if (!Hash(ops, &ledger->failure, sizeof(ledger->failure),
              terminal.terminal_tombstone_digest) ||
        !wlgr_v2_receipt_valid(&terminal)) {
        return WLGR_V2_ERROR_INTERNAL;
    }
    ledger->failure = terminal;
    __atomic_store_n(&ledger->state, TERMINAL, __ATOMIC_RELEASE);
    *out = terminal;
    return ledger->first_cause;
}

} // namespace wlar_child_sequence

#if !defined(WLAR_RUNTIME_PROVIDER_SEQUENCE_TEST)

#include "westlake_android_child_plugin.h"
#include "app_native_loader.h"
#include <nativeloader/native_loader.h>
#include "appspawnx_runtime.h"
#include "host_runtime_services.h"
#include "runtime_loader_phase.h"
#include "sealed_child_provider_loader.h"
#include "spawn_msg.h"
#include "westlake_sha256.h"

#include <cerrno>
#include <cstdlib>
#include <new>
#include <sys/resource.h>
#include <time.h>
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
#error "WLAR_GENERATION_SHA_HEX must bind the provider input closure"
#endif

namespace {
using appspawnx::AppSpawnXRuntime;
using appspawnx::SpawnMsg;

constexpr char kGenerationShaHex[] = WLAR_GENERATION_SHA_HEX;
constexpr uint8_t Nibble(char c) {
    return c >= '0' && c <= '9' ? static_cast<uint8_t>(c - '0') :
        c >= 'a' && c <= 'f' ? static_cast<uint8_t>(c - 'a' + 10) : 255U;
}
constexpr uint8_t Byte(size_t i) {
    return static_cast<uint8_t>((Nibble(kGenerationShaHex[i * 2U]) << 4U) |
                                Nibble(kGenerationShaHex[i * 2U + 1U]));
}
constexpr uint64_t ProviderGeneration() {
    uint64_t value = 0;
    for (size_t i = 0; i < 8U; ++i) value = (value << 8U) | Byte(i);
    return value;
}
const uint8_t kProviderSha[32] = {
    Byte(0),Byte(1),Byte(2),Byte(3),Byte(4),Byte(5),Byte(6),Byte(7),
    Byte(8),Byte(9),Byte(10),Byte(11),Byte(12),Byte(13),Byte(14),Byte(15),
    Byte(16),Byte(17),Byte(18),Byte(19),Byte(20),Byte(21),Byte(22),Byte(23),
    Byte(24),Byte(25),Byte(26),Byte(27),Byte(28),Byte(29),Byte(30),Byte(31)};
static_assert(sizeof(kGenerationShaHex) == 65U && ProviderGeneration() != 0U,
              "provider generation must be a nonzero SHA-256");

enum AdmissionState : uint32_t { ADMISSION_EMPTY, ADMISSION_INSTALLING,
    ADMISSION_READY, ADMISSION_FAILED };
uint32_t gAdmissionState;
WlarHostServicesRegistryV1 gHostServices{};
WlarLoaderPhaseRegistryV1 gLoaderPhase{};
wlar_child_sequence::Ledger gLedger{};

constexpr char kBootClasspath[] =
    "/system/android/framework/core-oj.jar:/system/android/framework/core-libart.jar:"
    "/system/android/framework/core-icu4j.jar:/system/android/framework/okhttp.jar:"
    "/system/android/framework/bouncycastle.jar:/system/android/framework/apache-xml.jar:"
    "/system/android/framework/adapter-mainline-stubs.jar:"
    "/system/android/framework/framework.jar:"
    "/system/android/framework/oh-adapter-framework.jar";

bool SetEnvironment() {
    return setenv("BOOTCLASSPATH", kBootClasspath, 1) == 0 &&
        setenv("ANDROID_ROOT", "/system/android", 1) == 0 &&
        setenv("ANDROID_DATA", "/data", 1) == 0 &&
        setenv("ANDROID_BOOT_IMAGE", "/system/android/framework/boot.art", 1) == 0;
}
bool Fixed(const char *s, size_t n) {
    return s != nullptr && n > 1U && s[0] != 0 && std::memchr(s, 0, n) != nullptr;
}
bool RequestValid(const WlascAndroidChildRequestV1 *r,
                  const WlascStockStageReceiptV1 *s) {
    return r != nullptr && s != nullptr && r->abi_version == WLASC_ABI_VERSION &&
        r->struct_size == sizeof(*r) && r->runtime_generation == ProviderGeneration() &&
        r->runtime_generation == s->runtime_generation && r->message_id == s->message_id &&
        Fixed(r->process_name, sizeof(r->process_name)) &&
        Fixed(r->bundle_name, sizeof(r->bundle_name)) &&
        s->abi_version == WLASC_ABI_VERSION && s->struct_size == sizeof(*s) &&
        s->parent_stage_tail_reached == 1U && s->child_stage_tail_reached == 1U &&
        s->bypass_guard_passed == 1U && s->security_owner_stock_appspawn == 1U;
}
bool LoaderAdmissionValid(const WlscplManifestV2 *manifest,
                          const WlscplLoadResultV2 *result) {
    if (manifest == nullptr || result == nullptr ||
        manifest->abi_version != WLSCPL_ABI_VERSION ||
        manifest->struct_size != sizeof(*manifest) ||
        result->abi_version != WLSCPL_ABI_VERSION ||
        result->struct_size != sizeof(*result) || result->error != WLSCPL_OK ||
        result->provider_handle == nullptr ||
        result->validated_artifact_count != manifest->artifact_count ||
        result->mapped_artifact_count == 0U ||
        result->constructor_completed_count != result->mapped_artifact_count ||
        result->constructor_timing !=
            WLSCPL_CONSTRUCTORS_COMPLETE_BEFORE_DLOPEN_RETURN ||
        !wlgr_v2_identity_valid(&result->generation_identity) ||
        !wlgr_v2_bytes_equal(
            manifest->manifest_digest,
            result->generation_identity.artifact_manifest_digest,
            WLGR_V2_SHA256_SIZE)) return false;
    bool javacore = false;
    bool provider = false;
    for (uint32_t i = 0; i < manifest->artifact_count; ++i) {
        const WlscplArtifactV2 &artifact = manifest->artifacts[i];
        if (artifact.artifact_kind != WLSCPL_ARTIFACT_SEALED_LOAD) continue;
        javacore = javacore || std::strcmp(artifact.soname, "libjavacore.so") == 0;
        provider = provider || std::strcmp(
            artifact.soname, WLSCPL_PROVIDER_SONAME) == 0;
    }
    return javacore && provider;
}
SpawnMsg Translate(const WlascAndroidChildRequestV1 &r) {
    SpawnMsg m; m.code = static_cast<int32_t>(r.message_type);
    m.procName = r.process_name; m.bundleName = r.bundle_name;
    m.uid = static_cast<int32_t>(r.uid); m.gid = static_cast<int32_t>(r.gid);
    m.accessTokenIdEx = r.access_token_id_ex; m.hapFlags = r.hap_flags;
    m.apl = r.apl; m.targetClass = "android.app.ActivityThread";
    m.ohMsgId = r.message_id; return m;
}
int VerifyReady(void *p) {
    const pid_t pid = getpid();
    return p == &gLoaderPhase && pid > 1 &&
        WLAR_LoaderPhaseIsChildReady(&gLoaderPhase, static_cast<uint64_t>(pid)) == 1 &&
        WLAR_HostServicesVerifyCurrentThreadReady(&gHostServices) == 0;
}
struct Context { alignas(AppSpawnXRuntime) uint8_t storage[sizeof(AppSpawnXRuntime)];
    AppSpawnXRuntime *runtime; SpawnMsg message;
    WlascAndroidChildRequestV1 request; WlascStockStageReceiptV1 stock;
    WlncProcessIdentityV1 process_identity; WlpbHostOpsV1 pthread_bridge_ops;
    uint64_t child_pid; };
void FillProcessIdentity(Context *c, WlncProcessIdentityV1 *process) {
    std::memset(process, 0, sizeof(*process));
    process->abi_version = WLNC_ABI_VERSION;
    process->struct_size = sizeof(*process);
    process->runtime_generation = c->request.runtime_generation;
    process->message_id = c->request.message_id;
    process->uid = c->request.uid;
    process->gid = c->request.gid;
    process->parent_stage_tail_reached = c->stock.parent_stage_tail_reached;
    process->child_stage_tail_reached = c->stock.child_stage_tail_reached;
    process->bypass_guard_passed = c->stock.bypass_guard_passed;
    process->security_owner_stock_appspawn =
        c->stock.security_owner_stock_appspawn;
    process->parent_tail_priority = c->stock.parent_tail_priority;
    process->child_tail_priority = c->stock.child_tail_priority;
    std::memcpy(process->runtime_provider_sha256, kProviderSha,
                sizeof(kProviderSha));
}
int CaptureAuditSnapshot(
    void *p, wlar_child_sequence::LosslessAuditSnapshot *out) {
    auto *c = static_cast<Context *>(p);
    if (out == nullptr ||
        WLAR_LoaderPhaseBeginChild(&gLoaderPhase,
            c->request.runtime_generation, kProviderSha, c->child_pid) != 0 ||
        WLAR_HostServicesGetPthreadBridgeOps(
            &gHostServices, &c->pthread_bridge_ops) != 0 ||
        WLAR_HostServicesBeginChild(&gHostServices) != 0)
        return WLGR_V2_ERROR_MISSING_PREREQUISITE;
    FillProcessIdentity(c, &c->process_identity);
    WlncAuditSnapshotV1 snapshot{};
    if (WLAR_HostServicesPrepareMain(
            &gHostServices, &c->process_identity) != 0 ||
        WLAR_HostServicesGetAuditSnapshot(&gHostServices, &snapshot) != 0)
        return WLGR_V2_ERROR_MISSING_PREREQUISITE;
    static_assert(sizeof(snapshot) == sizeof(*out),
                  "host/model WLTG audit snapshot size drift");
    static_assert(alignof(WlncAuditSnapshotV1) ==
                      alignof(wlar_child_sequence::LosslessAuditSnapshot),
                  "host/model WLTG audit snapshot alignment drift");
    std::memcpy(out, &snapshot, sizeof(*out));
    return 0;
}
int CommitAuditSnapshot(void *p) {
    auto *c = static_cast<Context *>(p);
    return WLAR_HostServicesMarkChildConsumed(&gHostServices) == 0 &&
        WLAR_LoaderPhaseMarkChildReady(&gLoaderPhase, c->child_pid) == 0 ?
        0 : WLGR_V2_ERROR_MISSING_PREREQUISITE;
}
bool InstallGate(const WlpbHostOpsV1 &pthread_bridge_ops) {
    AnlRuntimeGateV1 gate{}; gate.abi_version = ANL_RUNTIME_GATE_ABI_VERSION;
    gate.struct_size = sizeof(gate); gate.context = &gLoaderPhase;
    gate.verify_current_thread_ready = VerifyReady;
    gate.pthread_bridge_ops = pthread_bridge_ops;
    return ANL_InstallRuntimeGate(&gate) == 0;
}
int Constructors(void *p) { auto *c = static_cast<Context *>(p);
    WlncProcessIdentityV1 process{};
    process.abi_version = WLNC_ABI_VERSION; process.struct_size = sizeof(process);
    process.runtime_generation = c->request.runtime_generation;
    process.message_id = c->request.message_id; process.uid = c->request.uid;
    process.gid = c->request.gid;
    process.parent_stage_tail_reached = c->stock.parent_stage_tail_reached;
    process.child_stage_tail_reached = c->stock.child_stage_tail_reached;
    process.bypass_guard_passed = c->stock.bypass_guard_passed;
    process.security_owner_stock_appspawn = c->stock.security_owner_stock_appspawn;
    process.parent_tail_priority = c->stock.parent_tail_priority;
    process.child_tail_priority = c->stock.child_tail_priority;
    std::memcpy(process.runtime_provider_sha256, kProviderSha, sizeof(kProviderSha));
    if (std::memcmp(&process, &c->process_identity, sizeof(process)) != 0)
        return WLGR_V2_ERROR_GENERATION_MISMATCH;
    if (!SetEnvironment()) return -1;
    struct rlimit limit{RLIM_INFINITY, RLIM_INFINITY};
    if (setrlimit(RLIMIT_CORE, &limit) != 0) return -1;
    c->runtime = new (c->storage) AppSpawnXRuntime();
    return InstallGate(c->pthread_bridge_ops) ? 0 : -1; }
int Vm(void *p) { auto *c = static_cast<Context *>(p);
    return c->runtime != nullptr ? c->runtime->startVm() : -1; }
int Jni(void *p) { auto *c = static_cast<Context *>(p);
    return c->runtime != nullptr && c->runtime->getJNIEnv() != nullptr ?
        c->runtime->preload() : -1; }
int Noop(void *) { return 0; }
uint64_t Tid(void *) { return static_cast<uint64_t>(getpid()); }
uint64_t Now(void *) { struct timespec ts{}; return clock_gettime(CLOCK_MONOTONIC, &ts) == 0 ?
    static_cast<uint64_t>(ts.tv_sec) * UINT64_C(1000000000) + static_cast<uint64_t>(ts.tv_nsec) : 0U; }
int Digest(void *, const void *data, size_t size, uint8_t out[32]) {
    WlSha256Context sha{}; WLSha256Init(&sha);
    return WLSha256Update(&sha, data, size) == 0 ? WLSha256Final(&sha, out) : -1; }
} // namespace

extern "C" __attribute__((visibility("default")))
int WLAR_GetRuntimeIdentity(WlascRuntimeIdentityV1 *out) {
    if (out == nullptr) return -1; std::memset(out, 0, sizeof(*out));
    out->abi_version = WLASC_ABI_VERSION; out->struct_size = sizeof(*out);
    out->runtime_generation = ProviderGeneration();
    std::memcpy(out->runtime_provider_sha256, kProviderSha, sizeof(kProviderSha)); return 0;
}
extern "C" __attribute__((visibility("default")))
int WLAR_InstallHostRuntimeServices(const WlascHostRuntimeServicesV1 *services) {
    uint32_t expected = ADMISSION_EMPTY;
    if (!__atomic_compare_exchange_n(&gAdmissionState, &expected, ADMISSION_INSTALLING,
        false, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) return -1;
    if (WLAR_HostServicesInstall(&gHostServices, ProviderGeneration(), kProviderSha,
                                 services) != 0) {
        __atomic_store_n(&gAdmissionState, ADMISSION_FAILED, __ATOMIC_RELEASE); return -1;
    }
    __atomic_store_n(&gAdmissionState, ADMISSION_READY, __ATOMIC_RELEASE); return 0;
}
extern "C" __attribute__((visibility("default")))
int WLAR_EnterAndroidAfterStockSpecialization(
    const WlascAndroidChildRequestV1 *, const WlascStockStageReceiptV1 *) {
    return WLGR_V2_ERROR_MISSING_PREREQUISITE;
}
extern "C" __attribute__((visibility("default")))
int WLAR_PrepareA02PrerequisiteBundleV2(
    const WlascAndroidChildRequestV1 *request,
    const WlascStockStageReceiptV1 *stock,
    const WlscplManifestV2 *sealed_manifest,
    const WlscplLoadResultV2 *sealed_load_result,
    const westlake_runtime_stage_receipt_v2 *prior, uint32_t prior_count,
    westlake_a02_prerequisite_bundle_v2 *out_bundle,
    westlake_runtime_stage_receipt_v2 *out_failure) {
    const pid_t pid = getpid();
    const westlake_generation_identity_v2 *identity = sealed_load_result == nullptr ?
        nullptr : &sealed_load_result->generation_identity;
    if (__atomic_load_n(&gAdmissionState, __ATOMIC_ACQUIRE) != ADMISSION_READY ||
        !RequestValid(request, stock) ||
        !LoaderAdmissionValid(sealed_manifest, sealed_load_result) || identity == nullptr ||
        !wlgr_v2_identity_valid(identity) || pid <= 1 ||
        identity->child_pid != static_cast<uint64_t>(pid) ||
        identity->runtime_key.android_uid != request->uid ||
        identity->runtime_key.launch_generation != request->message_id ||
        std::strcmp(identity->runtime_key.android_package, request->bundle_name) != 0 ||
        std::strcmp(identity->runtime_key.android_process_name, request->process_name) != 0)
        return WLGR_V2_ERROR_IDENTITY_MISMATCH;
    Context context{}; context.message = Translate(*request);
    context.request = *request; context.stock = *stock;
    context.child_pid = static_cast<uint64_t>(pid);
    const wlar_child_sequence::Operations ops{
        &context, request->runtime_generation, CaptureAuditSnapshot,
        CommitAuditSnapshot, Constructors, Vm, Jni, Noop, Noop, Noop,
        Tid, Now, Digest};
    return wlar_child_sequence::Run(&gLedger, *identity, prior, prior_count,
                                    ops, out_bundle, out_failure);
}

#endif
