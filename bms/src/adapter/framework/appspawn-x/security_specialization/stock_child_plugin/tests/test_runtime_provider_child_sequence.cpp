#define WLAR_RUNTIME_PROVIDER_SEQUENCE_TEST 1
#include "../src/westlake_android_runtime_provider.cpp"

#include <atomic>
#include <cstdio>
#include <thread>

namespace {
struct Fixture {
    int fail_step{};
    int drain_fail{};
    int trace[32]{};
    size_t trace_size{};
    uint64_t now{100};
    uint64_t expected_runtime_generation{UINT64_C(0x1122334455667788)};
    wlar_child_sequence::LosslessAuditSnapshot audit{};
    std::atomic<int> audit_calls{0};
    std::atomic<int> block{0};
    std::atomic<int> entered{0};

    Fixture() {
        audit.abi_version = wlar_child_sequence::AUDIT_ABI_VERSION;
        audit.struct_size = wlar_child_sequence::AUDIT_SNAPSHOT_SIZE;
        audit.product_state = wlar_child_sequence::AUDIT_PRODUCT_READY;
        audit.event_type_slots =
            wlar_child_sequence::AUDIT_EVENT_TYPE_SLOTS;
        audit.runtime_generation = expected_runtime_generation;
        audit.process_epoch = UINT64_C(91);
        audit.accepted_event_count = UINT64_C(6);
        audit.sequence_xor_digest = UINT64_C(0x1020304050607080);
        audit.payload_xor_digest = UINT64_C(0x8877665544332211);
        audit.registry_audit_sequence = audit.accepted_event_count;
        audit.event_type_count[0] = UINT64_C(1);
        audit.event_type_count[2] = UINT64_C(2);
        audit.event_type_count[9] = UINT64_C(3);
        audit.registry_ready_count = UINT32_C(1);
    }
};
void Push(Fixture *f, int value) {
    if (f->trace_size < 32U) f->trace[f->trace_size++] = value;
}
int AuditSnapshot(
    void *p, wlar_child_sequence::LosslessAuditSnapshot *out) {
    auto *f = static_cast<Fixture *>(p);
    Push(f, 8);
    f->audit_calls.fetch_add(1, std::memory_order_acq_rel);
    if (f->fail_step == 8) return WLGR_V2_ERROR_MISSING_PREREQUISITE;
    *out = f->audit;
    return 0;
}
int CommitAudit(void *p) {
    auto *f = static_cast<Fixture *>(p);
    Push(f, 89);
    return f->fail_step == 89 ? WLGR_V2_ERROR_MISSING_PREREQUISITE : 0;
}
int Constructors(void *p) { auto *f = static_cast<Fixture *>(p); Push(f, 9);
    f->entered.store(1, std::memory_order_release);
    while (f->block.load(std::memory_order_acquire) != 0) std::this_thread::yield();
    return f->fail_step == 9 ? -9 :
        f->fail_step == 90 ? WLGR_V2_ERROR_GENERATION_MISMATCH : 0; }
int Vm(void *p) { auto *f = static_cast<Fixture *>(p); Push(f, 10);
    return f->fail_step == 10 ? -10 : 0; }
int Jni(void *p) { auto *f = static_cast<Fixture *>(p); Push(f, 11);
    return f->fail_step == 11 ? -11 : 0; }
int Revoke(void *p) { Push(static_cast<Fixture *>(p), 13); return 0; }
int Drain(void *p) { auto *f = static_cast<Fixture *>(p); Push(f, 14);
    return f->drain_fail; }
int Invalidate(void *p) { Push(static_cast<Fixture *>(p), 15); return 0; }
uint64_t Tid(void *) { return 77; }
uint64_t Now(void *p) { return ++static_cast<Fixture *>(p)->now; }
int Digest(void *, const void *data, size_t size, uint8_t out[32]) {
    const auto *bytes = static_cast<const uint8_t *>(data);
    uint64_t hash = UINT64_C(1469598103934665603);
    for (size_t i = 0; i < size; ++i) hash = (hash ^ bytes[i]) * UINT64_C(1099511628211);
    if (hash == 0) hash = 1;
    for (size_t i = 0; i < 32U; ++i) out[i] = static_cast<uint8_t>((hash >> ((i % 8U) * 8U)) ^ (i + 1U));
    return 0;
}
wlar_child_sequence::Operations Ops(Fixture *f) {
    return {f, f->expected_runtime_generation, AuditSnapshot, CommitAudit,
        Constructors, Vm, Jni, Revoke, Drain, Invalidate, Tid, Now, Digest};
}
void Fill(uint8_t *p, size_t n, uint8_t seed) {
    for (size_t i = 0; i < n; ++i) p[i] = static_cast<uint8_t>(seed + i);
}
westlake_generation_identity_v2 Identity() {
    westlake_generation_identity_v2 i{};
    i.magic = WLGR_V2_IDENTITY_MAGIC; i.abi_version = WLGR_V2_ABI_VERSION;
    i.struct_size = WLGR_V2_IDENTITY_SIZE; i.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    i.runtime_key.magic = WLGR_V2_RUNTIME_KEY_MAGIC;
    i.runtime_key.abi_version = WLGR_V2_ABI_VERSION;
    i.runtime_key.struct_size = WLGR_V2_RUNTIME_KEY_SIZE;
    i.runtime_key.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    i.runtime_key.android_uid = 10001; i.runtime_key.launch_generation = 42;
    std::memcpy(i.runtime_key.android_package, "dev.westlake.test", 18);
    std::memcpy(i.runtime_key.android_process_name, "dev.westlake.test:p", 20);
    Fill(i.boot_id, sizeof(i.boot_id), 1); Fill(i.artifact_generation, 32, 2);
    i.policy_epoch = 3; i.child_pid = 71; i.child_proc_start_time_ticks = 99;
    Fill(i.specialization_receipt_digest, 32, 4);
    Fill(i.artifact_manifest_digest, 32, 5); Fill(i.hook_schema_digest, 32, 6);
    Fill(i.request_nonce, sizeof(i.request_nonce), 7); return i;
}
void Prior(const westlake_generation_identity_v2 &identity,
           westlake_runtime_stage_receipt_v2 out[3]) {
    const uint32_t transition[3] = {WLGR_V2_TRANSITION_T03,
        WLGR_V2_TRANSITION_T07, WLGR_V2_TRANSITION_T08};
    for (size_t n = 0; n < 3U; ++n) {
        auto &r = out[n]; r.magic = WLGR_V2_RECEIPT_MAGIC;
        r.abi_version = WLGR_V2_ABI_VERSION; r.struct_size = WLGR_V2_RECEIPT_SIZE;
        r.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT; r.identity = identity;
        r.action_id = WLGR_V2_ACTION_FN02_A06; r.transition_id = transition[n];
        r.stage_before = wlgr_v2_expected_stage_before(transition[n]);
        r.stage_after = wlgr_v2_expected_stage_after(transition[n]);
        r.owner = wlgr_v2_expected_owner(transition[n]);
        r.publication_state = WLGR_V2_PUBLICATION_COMMITTED;
        r.child_thread_id = 77; r.sequence = n + 1U; r.monotonic_timestamp_ns = n + 10U;
        Fill(r.input_digest, 32, static_cast<uint8_t>(20 + n));
        Fill(r.output_digest, 32, static_cast<uint8_t>(30 + n));
    }
}
bool PositiveReplayConflict() {
    wlar_child_sequence::Ledger ledger{}; Fixture f{}; auto identity = Identity();
    westlake_runtime_stage_receipt_v2 prior[3]{}; Prior(identity, prior);
    westlake_a02_prerequisite_bundle_v2 bundle{}, replay{};
    westlake_runtime_stage_receipt_v2 failure{};
    if (wlar_child_sequence::Run(&ledger, identity, prior, 3, Ops(&f), &bundle, &failure) != 0 ||
        !wlgr_v2_a02_bundle_valid(&bundle) || bundle.t12_receipt_present != 0 ||
        bundle.next_transition_id != WLGR_V2_TRANSITION_T12 ||
        f.trace_size != 5U || f.audit_calls.load() != 1)
        return false;
    const wlar_child_sequence::AuditInputSeed audit_input{
        prior[2], f.audit};
    uint8_t expected_t09_input[WLGR_V2_SHA256_SIZE]{};
    if (Digest(&f, &audit_input, sizeof(audit_input),
               expected_t09_input) != 0 ||
        std::memcmp(expected_t09_input, bundle.receipts[3].input_digest,
                    sizeof(expected_t09_input)) != 0)
        return false;
    f.audit.registry_audit_drop_count = UINT64_C(7);
    if (wlar_child_sequence::Run(&ledger, identity, prior, 3, Ops(&f), &replay, &failure) != 0 ||
        std::memcmp(&bundle, &replay, sizeof(bundle)) != 0 ||
        f.trace_size != 5U || f.audit_calls.load() != 1) return false;
    prior[2].input_digest[0] ^= 1U;
    return wlar_child_sequence::Run(&ledger, identity, prior, 3, Ops(&f), &replay, &failure) ==
        WLGR_V2_ERROR_EVENT_CONFLICT;
}
bool ConcurrentInProgress() {
    wlar_child_sequence::Ledger ledger{}; Fixture f{}; f.block.store(1);
    auto identity = Identity(); westlake_runtime_stage_receipt_v2 prior[3]{}; Prior(identity, prior);
    westlake_a02_prerequisite_bundle_v2 first{}, second{}; westlake_runtime_stage_receipt_v2 failure{};
    int32_t winner = -1;
    std::thread thread([&] { winner = wlar_child_sequence::Run(&ledger, identity, prior, 3,
        Ops(&f), &first, &failure); });
    while (f.entered.load(std::memory_order_acquire) == 0) std::this_thread::yield();
    const int32_t waiter = wlar_child_sequence::Run(&ledger, identity, prior, 3,
        Ops(&f), &second, &failure);
    f.block.store(0, std::memory_order_release); thread.join();
    return waiter == WLGR_V2_RESULT_IN_PROGRESS && winner == 0 &&
        f.trace_size == 5U && f.audit_calls.load() == 1 &&
        wlar_child_sequence::Run(&ledger, identity, prior, 3,
            Ops(&f), &second, &failure) == 0 && f.trace_size == 5U &&
        f.audit_calls.load() == 1;
}
bool FailureLifecycle(int step, int32_t cause, bool reconcile) {
    wlar_child_sequence::Ledger ledger{}; Fixture f{}; f.fail_step = step;
    f.drain_fail = reconcile ? -1 : 0; auto identity = Identity();
    westlake_runtime_stage_receipt_v2 prior[3]{}; Prior(identity, prior);
    westlake_a02_prerequisite_bundle_v2 bundle{}; westlake_runtime_stage_receipt_v2 failure{};
    if (wlar_child_sequence::Run(&ledger, identity, prior, 3, Ops(&f), &bundle, &failure) != cause ||
        failure.first_cause != cause || failure.transition_id != WLGR_V2_TRANSITION_T13 ||
        failure.publication_state != (reconcile ? WLGR_V2_PUBLICATION_RECONCILE_REQUIRED :
                                              WLGR_V2_PUBLICATION_IN_PROGRESS) ||
        failure.stage_after != (reconcile ? WLGR_V2_STAGE_RECONCILE_REQUIRED :
                                           WLGR_V2_STAGE_STOPPING) ||
        !wlgr_v2_bytes_zero(failure.terminal_tombstone_digest, 32)) return false;
    const size_t effects = f.trace_size;
    if (wlar_child_sequence::Run(&ledger, identity, prior, 3, Ops(&f), &bundle, &failure) != cause ||
        f.trace_size != effects) return false;
    westlake_runtime_stage_receipt_v2 terminal{};
    return wlar_child_sequence::AcknowledgeDeath(&ledger, Ops(&f), &terminal) == cause &&
        terminal.publication_state == WLGR_V2_PUBLICATION_TERMINAL &&
        terminal.stage_after == WLGR_V2_STAGE_TERMINATED &&
        !wlgr_v2_bytes_zero(terminal.terminal_tombstone_digest, 32) &&
        wlgr_v2_receipt_valid(&terminal);
}
bool InvalidPrerequisite() {
    wlar_child_sequence::Ledger ledger{}; Fixture f{}; auto identity = Identity();
    westlake_runtime_stage_receipt_v2 prior[3]{}; Prior(identity, prior);
    prior[1].owner = WLGR_V2_OWNER_ART_VM;
    westlake_a02_prerequisite_bundle_v2 bundle{}; westlake_runtime_stage_receipt_v2 failure{};
    return wlar_child_sequence::Run(&ledger, identity, prior, 3, Ops(&f), &bundle, &failure) ==
        WLGR_V2_ERROR_INVALID_ARGUMENT && f.trace_size == 0;
}
bool AuditBoundaryFailure(int step) {
    wlar_child_sequence::Ledger ledger{}; Fixture f{}; f.fail_step = step;
    auto identity = Identity();
    westlake_runtime_stage_receipt_v2 prior[3]{}; Prior(identity, prior);
    westlake_a02_prerequisite_bundle_v2 bundle{};
    westlake_runtime_stage_receipt_v2 failure{};
    return wlar_child_sequence::Run(
               &ledger, identity, prior, 3, Ops(&f), &bundle, &failure) ==
               WLGR_V2_ERROR_MISSING_PREREQUISITE &&
        failure.first_cause == WLGR_V2_ERROR_MISSING_PREREQUISITE &&
        failure.stage_before == WLGR_V2_STAGE_PROVIDER_MAPPED &&
        f.audit_calls.load() == 1 &&
        f.trace_size == (step == 8 ? 4U : 5U) &&
        f.trace[0] == 8 &&
        f.trace[step == 8 ? 1U : 2U] == 13 &&
        f.trace[step == 8 ? 2U : 3U] == 14 &&
        f.trace[step == 8 ? 3U : 4U] == 15 &&
        (step == 8 || f.trace[1] == 89);
}
bool AuditTamper(int mutant) {
    wlar_child_sequence::Ledger ledger{}; Fixture f{};
    switch (mutant) {
        case 0: f.audit.product_state = 3U; break;
        case 1: f.audit.runtime_generation++; break;
        case 2: f.audit.process_epoch = 0U; break;
        case 3: f.audit.registry_audit_sequence++; break;
        case 4: f.audit.registry_audit_drop_count = 1U; break;
        case 5: f.audit.event_type_count[9]--; break;
        case 6: f.audit.registry_active_ticket_count = 1U; break;
        case 7: f.audit.reserved_zero[3] = 1U; break;
        case 8:
            f.audit.event_type_count[0] = UINT64_MAX;
            f.audit.event_type_count[2] = UINT64_MAX;
            break;
        case 9: f.audit.abi_version++; break;
        case 10: f.audit.struct_size--; break;
        case 11: f.audit.event_type_slots--; break;
        case 12: f.audit.accepted_event_count = 0U;
            f.audit.registry_audit_sequence = 0U; break;
        case 13: f.audit.registry_ready_count = 0U; break;
        default: return false;
    }
    auto identity = Identity();
    westlake_runtime_stage_receipt_v2 prior[3]{}; Prior(identity, prior);
    westlake_a02_prerequisite_bundle_v2 bundle{};
    westlake_runtime_stage_receipt_v2 failure{};
    const int32_t result = wlar_child_sequence::Run(
        &ledger, identity, prior, 3, Ops(&f), &bundle, &failure);
    return result == WLGR_V2_ERROR_DIGEST_INVALID &&
        failure.first_cause == WLGR_V2_ERROR_DIGEST_INVALID &&
        failure.stage_before == WLGR_V2_STAGE_PROVIDER_MAPPED &&
        f.audit_calls.load() == 1 && f.trace_size == 4U &&
        f.trace[0] == 8 && f.trace[1] == 13 &&
        f.trace[2] == 14 && f.trace[3] == 15;
}
} // namespace

int main() {
    const bool cases[] = {PositiveReplayConflict(), ConcurrentInProgress(), InvalidPrerequisite(),
        AuditBoundaryFailure(8), AuditBoundaryFailure(89),
        AuditTamper(0), AuditTamper(1), AuditTamper(2), AuditTamper(3),
        AuditTamper(4), AuditTamper(5), AuditTamper(6), AuditTamper(7),
        AuditTamper(8), AuditTamper(9), AuditTamper(10), AuditTamper(11),
        AuditTamper(12), AuditTamper(13),
        FailureLifecycle(9, WLGR_V2_ERROR_CONSTRUCTOR_FAILED, false),
        FailureLifecycle(90, WLGR_V2_ERROR_GENERATION_MISMATCH, false),
        FailureLifecycle(10, WLGR_V2_ERROR_VM_CREATE_FAILED, false),
        FailureLifecycle(11, WLGR_V2_ERROR_JNI_REGISTER_FAILED, false),
        FailureLifecycle(10, WLGR_V2_ERROR_VM_CREATE_FAILED, true)};
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        if (!cases[i]) { std::fprintf(stderr, "provider reducer case %zu failed\n", i + 1U); return 1; }
    }
    std::printf("runtime-provider ABI-v2 WLTG reducer: %zu/%zu PNF PASS\n",
        sizeof(cases) / sizeof(cases[0]),
        sizeof(cases) / sizeof(cases[0])); return 0;
}
