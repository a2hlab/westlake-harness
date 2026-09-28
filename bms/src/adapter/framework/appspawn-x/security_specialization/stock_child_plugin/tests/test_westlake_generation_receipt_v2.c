#include "westlake_generation_receipt_v2.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static unsigned tests_run;
static unsigned failures;

static void FillNonzero(uint8_t *value, size_t size, uint8_t seed)
{
    size_t index;
    for (index = 0U; index < size; ++index) {
        value[index] = (uint8_t)(seed + (uint8_t)index);
    }
}

static westlake_generation_identity_v2 MakeIdentity(void)
{
    westlake_generation_identity_v2 identity;
    memset(&identity, 0, sizeof(identity));
    identity.magic = WLGR_V2_IDENTITY_MAGIC;
    identity.abi_version = WLGR_V2_ABI_VERSION;
    identity.struct_size = sizeof(identity);
    identity.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    identity.runtime_key.magic = WLGR_V2_RUNTIME_KEY_MAGIC;
    identity.runtime_key.abi_version = WLGR_V2_ABI_VERSION;
    identity.runtime_key.struct_size = sizeof(identity.runtime_key);
    identity.runtime_key.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    identity.runtime_key.android_uid = UINT32_C(20010001);
    identity.runtime_key.launch_generation = UINT64_C(41);
    (void)snprintf(identity.runtime_key.android_package,
                   sizeof(identity.runtime_key.android_package),
                   "%s", "com.westlake.receipt.test");
    (void)snprintf(identity.runtime_key.android_process_name,
                   sizeof(identity.runtime_key.android_process_name),
                   "%s", "com.westlake.receipt.test:main");
    FillNonzero(identity.boot_id, sizeof(identity.boot_id), UINT8_C(1));
    FillNonzero(identity.artifact_generation,
                sizeof(identity.artifact_generation), UINT8_C(17));
    identity.policy_epoch = UINT64_C(7);
    identity.child_pid = UINT64_C(4242);
    identity.child_proc_start_time_ticks = UINT64_C(998877);
    FillNonzero(identity.specialization_receipt_digest,
                sizeof(identity.specialization_receipt_digest), UINT8_C(33));
    FillNonzero(identity.artifact_manifest_digest,
                sizeof(identity.artifact_manifest_digest), UINT8_C(65));
    FillNonzero(identity.hook_schema_digest,
                sizeof(identity.hook_schema_digest), UINT8_C(97));
    FillNonzero(identity.request_nonce,
                sizeof(identity.request_nonce), UINT8_C(129));
    return identity;
}

static westlake_runtime_stage_receipt_v2 MakeReceipt(
    const westlake_generation_identity_v2 *identity,
    uint32_t transition, uint64_t sequence)
{
    westlake_runtime_stage_receipt_v2 receipt;
    memset(&receipt, 0, sizeof(receipt));
    receipt.magic = WLGR_V2_RECEIPT_MAGIC;
    receipt.abi_version = WLGR_V2_ABI_VERSION;
    receipt.struct_size = sizeof(receipt);
    receipt.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    receipt.identity = *identity;
    receipt.action_id = wlgr_v2_expected_action(transition);
    receipt.transition_id = transition;
    receipt.stage_before = wlgr_v2_expected_stage_before(transition);
    receipt.stage_after = wlgr_v2_expected_stage_after(transition);
    receipt.owner = wlgr_v2_expected_owner(transition);
    receipt.publication_state = WLGR_V2_PUBLICATION_COMMITTED;
    receipt.result_code = WLGR_V2_RESULT_OK;
    receipt.child_thread_id = UINT64_C(4242);
    receipt.sequence = sequence;
    receipt.monotonic_timestamp_ns = UINT64_C(1000) + sequence;
    FillNonzero(receipt.input_digest, sizeof(receipt.input_digest),
                (uint8_t)(sequence + UINT64_C(1)));
    FillNonzero(receipt.output_digest, sizeof(receipt.output_digest),
                (uint8_t)(sequence + UINT64_C(65)));
    return receipt;
}

static westlake_runtime_stage_receipt_v2 MakeFailureReceipt(
    const westlake_generation_identity_v2 *identity,
    uint32_t publication_state)
{
    westlake_runtime_stage_receipt_v2 receipt;
    memset(&receipt, 0, sizeof(receipt));
    receipt.magic = WLGR_V2_RECEIPT_MAGIC;
    receipt.abi_version = WLGR_V2_ABI_VERSION;
    receipt.struct_size = sizeof(receipt);
    receipt.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    receipt.identity = *identity;
    receipt.action_id = WLGR_V2_ACTION_FN02_A06;
    receipt.transition_id = WLGR_V2_TRANSITION_T13;
    receipt.stage_before = WLGR_V2_STAGE_VM_CREATED;
    receipt.owner = WLGR_V2_OWNER_GENERATION_REDUCER;
    receipt.publication_state = publication_state;
    receipt.result_code = WLGR_V2_ERROR_JNI_REGISTER_FAILED;
    receipt.first_cause = WLGR_V2_ERROR_JNI_REGISTER_FAILED;
    receipt.native_cause = -77;
    receipt.child_thread_id = UINT64_C(4242);
    receipt.sequence = UINT64_C(77);
    receipt.monotonic_timestamp_ns = UINT64_C(5000);
    FillNonzero(receipt.input_digest, sizeof(receipt.input_digest), UINT8_C(7));
    FillNonzero(receipt.output_digest, sizeof(receipt.output_digest), UINT8_C(71));
    if (publication_state == WLGR_V2_PUBLICATION_IN_PROGRESS) {
        receipt.stage_after = WLGR_V2_STAGE_STOPPING;
    } else if (publication_state == WLGR_V2_PUBLICATION_RECONCILE_REQUIRED) {
        receipt.stage_after = WLGR_V2_STAGE_RECONCILE_REQUIRED;
    } else {
        receipt.stage_after = WLGR_V2_STAGE_TERMINATED;
        FillNonzero(receipt.terminal_tombstone_digest,
                    sizeof(receipt.terminal_tombstone_digest), UINT8_C(151));
    }
    return receipt;
}

static westlake_a02_prerequisite_bundle_v2 MakeBundle(void)
{
    static const uint32_t transitions[WLGR_V2_A02_PREREQUISITE_COUNT] = {
        WLGR_V2_TRANSITION_T03, WLGR_V2_TRANSITION_T07,
        WLGR_V2_TRANSITION_T08, WLGR_V2_TRANSITION_T09,
        WLGR_V2_TRANSITION_T10, WLGR_V2_TRANSITION_T11,
    };
    westlake_a02_prerequisite_bundle_v2 bundle;
    size_t index;
    memset(&bundle, 0, sizeof(bundle));
    bundle.magic = WLGR_V2_A02_BUNDLE_MAGIC;
    bundle.abi_version = WLGR_V2_ABI_VERSION;
    bundle.struct_size = sizeof(bundle);
    bundle.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    bundle.identity = MakeIdentity();
    bundle.producer_action_id = WLGR_V2_ACTION_FN02_A06;
    bundle.consumer_action_id = WLGR_V2_ACTION_FN02_A02;
    bundle.producer_terminal_transition_id = WLGR_V2_TRANSITION_T11;
    bundle.next_transition_id = WLGR_V2_TRANSITION_T12;
    bundle.bundle_state = WLGR_V2_BUNDLE_READY_FOR_A02;
    bundle.receipt_count = WLGR_V2_A02_PREREQUISITE_COUNT;
    for (index = 0U; index < WLGR_V2_A02_PREREQUISITE_COUNT; ++index) {
        bundle.receipts[index] = MakeReceipt(
            &bundle.identity, transitions[index], UINT64_C(10) + index);
    }
    bundle.first_sequence = bundle.receipts[0].sequence;
    bundle.last_sequence =
        bundle.receipts[WLGR_V2_A02_PREREQUISITE_COUNT - 1U].sequence;
    bundle.monotonic_created_timestamp_ns =
        bundle.receipts[WLGR_V2_A02_PREREQUISITE_COUNT - 1U]
            .monotonic_timestamp_ns + UINT64_C(1);
    FillNonzero(bundle.bundle_digest, sizeof(bundle.bundle_digest), UINT8_C(201));
    return bundle;
}

static bool IdentityCoverage(void)
{
    westlake_generation_identity_v2 identity = MakeIdentity();
    westlake_generation_identity_v2 changed;
    if (!wlgr_v2_identity_valid(&identity)) {
        return false;
    }
    changed = identity;
    changed.abi_version++;
    if (wlgr_v2_identity_valid(&changed)) return false;
    changed = identity;
    changed.struct_size--;
    if (wlgr_v2_identity_valid(&changed)) return false;
    changed = identity;
    changed.reserved_zero[0] = 1;
    if (wlgr_v2_identity_valid(&changed)) return false;
#define REJECT_ZERO(member) do { \
    changed = identity; \
    memset(changed.member, 0, sizeof(changed.member)); \
    if (wlgr_v2_identity_valid(&changed)) return false; \
} while (0)
    REJECT_ZERO(boot_id);
    REJECT_ZERO(artifact_generation);
    REJECT_ZERO(specialization_receipt_digest);
    REJECT_ZERO(artifact_manifest_digest);
    REJECT_ZERO(hook_schema_digest);
    REJECT_ZERO(request_nonce);
#undef REJECT_ZERO
    changed = identity;
    changed.runtime_key.launch_generation = 0;
    if (wlgr_v2_identity_valid(&changed)) return false;
    changed = identity;
    changed.policy_epoch = 0;
    if (wlgr_v2_identity_valid(&changed)) return false;
    changed = identity;
    changed.child_pid = 1;
    if (wlgr_v2_identity_valid(&changed)) return false;
    changed = identity;
    changed.child_proc_start_time_ticks = 0;
    if (wlgr_v2_identity_valid(&changed)) return false;
    changed = identity;
    memset(changed.runtime_key.android_package, 'x',
           sizeof(changed.runtime_key.android_package));
    if (wlgr_v2_identity_valid(&changed)) return false;
    changed = identity;
    changed.runtime_key.android_process_name[40] = 'x';
    return !wlgr_v2_identity_valid(&changed);
}

static bool OrderedReceipts(void)
{
    static const uint32_t transitions[] = {
        WLGR_V2_TRANSITION_T03, WLGR_V2_TRANSITION_T07,
        WLGR_V2_TRANSITION_T08, WLGR_V2_TRANSITION_T09,
        WLGR_V2_TRANSITION_T10, WLGR_V2_TRANSITION_T11,
        WLGR_V2_TRANSITION_T12,
    };
    westlake_generation_identity_v2 identity = MakeIdentity();
    size_t index;
    for (index = 0U; index < sizeof(transitions) / sizeof(transitions[0]);
         ++index) {
        westlake_runtime_stage_receipt_v2 receipt =
            MakeReceipt(&identity, transitions[index], index + 1U);
        if (!wlgr_v2_receipt_valid(&receipt)) return false;
    }
    return true;
}

static bool ReceiptNegatives(void)
{
    westlake_generation_identity_v2 identity = MakeIdentity();
    westlake_runtime_stage_receipt_v2 receipt =
        MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(5));
    receipt.owner = WLGR_V2_OWNER_ART_JNI;
    if (wlgr_v2_receipt_valid(&receipt)) return false;
    receipt = MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(5));
    receipt.stage_before = WLGR_V2_STAGE_HOOK_TABLE_READY;
    if (wlgr_v2_receipt_valid(&receipt)) return false;
    receipt = MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(5));
    receipt.sequence = 0;
    if (wlgr_v2_receipt_valid(&receipt)) return false;
    receipt = MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(5));
    receipt.child_thread_id = 0;
    if (wlgr_v2_receipt_valid(&receipt)) return false;
    receipt = MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(5));
    receipt.first_cause = WLGR_V2_ERROR_INTERNAL;
    if (wlgr_v2_receipt_valid(&receipt)) return false;
    receipt = MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(5));
    memset(receipt.output_digest, 0, sizeof(receipt.output_digest));
    if (wlgr_v2_receipt_valid(&receipt)) return false;
    receipt = MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(5));
    receipt.reserved_zero[0] = 1;
    return !wlgr_v2_receipt_valid(&receipt);
}

static bool FailureStates(void)
{
    westlake_generation_identity_v2 identity = MakeIdentity();
    westlake_runtime_stage_receipt_v2 in_progress =
        MakeFailureReceipt(&identity, WLGR_V2_PUBLICATION_IN_PROGRESS);
    westlake_runtime_stage_receipt_v2 reconcile =
        MakeFailureReceipt(&identity,
                           WLGR_V2_PUBLICATION_RECONCILE_REQUIRED);
    westlake_runtime_stage_receipt_v2 terminal =
        MakeFailureReceipt(&identity, WLGR_V2_PUBLICATION_TERMINAL);
    westlake_runtime_stage_receipt_v2 bad = terminal;
    if (!wlgr_v2_receipt_valid(&in_progress) ||
        !wlgr_v2_receipt_valid(&reconcile) ||
        !wlgr_v2_receipt_valid(&terminal)) {
        return false;
    }
    memset(bad.terminal_tombstone_digest, 0,
           sizeof(bad.terminal_tombstone_digest));
    if (wlgr_v2_receipt_valid(&bad)) return false;
    bad = terminal;
    bad.first_cause = WLGR_V2_ERROR_VM_CREATE_FAILED;
    return !wlgr_v2_receipt_valid(&bad);
}

static bool ExactDuplicateReturnsRecorded(void)
{
    westlake_generation_identity_v2 identity = MakeIdentity();
    westlake_runtime_stage_receipt_v2 recorded =
        MakeReceipt(&identity, WLGR_V2_TRANSITION_T10, UINT64_C(23));
    westlake_runtime_stage_receipt_v2 incoming = recorded;
    westlake_generation_replay_result_v2 result;
    memset(&result, 0xff, sizeof(result));
    return wlgr_v2_classify_replay(&recorded, &incoming, &result) ==
               WLGR_V2_RESULT_OK &&
        result.disposition == WLGR_V2_REPLAY_RETURN_RECORDED &&
        result.recorded_result == recorded.result_code &&
        result.recorded_first_cause == recorded.first_cause &&
        result.recorded_sequence == recorded.sequence &&
        wlgr_v2_bytes_equal(result.recorded_output_digest,
                            recorded.output_digest,
                            sizeof(result.recorded_output_digest));
}

static bool ReplayProgressAndReconcile(void)
{
    westlake_generation_identity_v2 identity = MakeIdentity();
    westlake_runtime_stage_receipt_v2 progress =
        MakeFailureReceipt(&identity, WLGR_V2_PUBLICATION_IN_PROGRESS);
    westlake_runtime_stage_receipt_v2 reconcile =
        MakeFailureReceipt(&identity,
                           WLGR_V2_PUBLICATION_RECONCILE_REQUIRED);
    westlake_generation_replay_result_v2 result;
    if (wlgr_v2_classify_replay(&progress, &progress, &result) !=
            WLGR_V2_RESULT_OK ||
        result.disposition != WLGR_V2_REPLAY_RETURN_IN_PROGRESS ||
        result.recorded_first_cause != WLGR_V2_ERROR_JNI_REGISTER_FAILED) {
        return false;
    }
    return wlgr_v2_classify_replay(&reconcile, &reconcile, &result) ==
               WLGR_V2_RESULT_OK &&
        result.disposition == WLGR_V2_REPLAY_RETURN_RECONCILE_REQUIRED &&
        result.recorded_first_cause == WLGR_V2_ERROR_JNI_REGISTER_FAILED;
}

static bool TerminalReplayReturnsFirstCause(void)
{
    westlake_generation_identity_v2 identity = MakeIdentity();
    westlake_runtime_stage_receipt_v2 terminal =
        MakeFailureReceipt(&identity, WLGR_V2_PUBLICATION_TERMINAL);
    westlake_runtime_stage_receipt_v2 duplicate = terminal;
    westlake_generation_replay_result_v2 result;
    duplicate.result_code = WLGR_V2_ERROR_VM_CREATE_FAILED;
    duplicate.first_cause = WLGR_V2_ERROR_VM_CREATE_FAILED;
    duplicate.native_cause = -88;
    return wlgr_v2_classify_replay(&terminal, &duplicate, &result) ==
               WLGR_V2_RESULT_OK &&
        result.disposition == WLGR_V2_REPLAY_RETURN_RECORDED &&
        result.recorded_publication_state == WLGR_V2_PUBLICATION_TERMINAL &&
        result.recorded_result == WLGR_V2_ERROR_JNI_REGISTER_FAILED &&
        result.recorded_first_cause == WLGR_V2_ERROR_JNI_REGISTER_FAILED &&
        result.recorded_sequence == terminal.sequence;
}

static bool ReplayConflictNegatives(void)
{
    westlake_generation_identity_v2 identity = MakeIdentity();
    westlake_runtime_stage_receipt_v2 recorded =
        MakeReceipt(&identity, WLGR_V2_TRANSITION_T09, UINT64_C(9));
    westlake_runtime_stage_receipt_v2 incoming = recorded;
    westlake_generation_replay_result_v2 result;
    incoming.input_digest[0] ^= UINT8_C(1);
    if (wlgr_v2_classify_replay(&recorded, &incoming, &result) !=
            WLGR_V2_RESULT_OK ||
        result.disposition != WLGR_V2_REPLAY_REJECT_EVENT_CONFLICT) {
        return false;
    }
    incoming = recorded;
    incoming.identity.artifact_generation[0] ^= UINT8_C(1);
    if (wlgr_v2_classify_replay(&recorded, &incoming, &result) !=
            WLGR_V2_RESULT_OK ||
        result.disposition != WLGR_V2_REPLAY_REJECT_IDENTITY_CONFLICT) {
        return false;
    }
    incoming = recorded;
    incoming.identity.request_nonce[0] ^= UINT8_C(1);
    return wlgr_v2_classify_replay(&recorded, &incoming, &result) ==
               WLGR_V2_RESULT_OK &&
        result.disposition == WLGR_V2_REPLAY_ACCEPT_NEW;
}

static bool A02BundlePositive(void)
{
    westlake_a02_prerequisite_bundle_v2 bundle = MakeBundle();
    return wlgr_v2_a02_bundle_valid(&bundle) &&
        bundle.next_transition_id == WLGR_V2_TRANSITION_T12 &&
        bundle.t12_receipt_present == 0 &&
        bundle.receipts[WLGR_V2_A02_PREREQUISITE_COUNT - 1U]
                .transition_id == WLGR_V2_TRANSITION_T11;
}

static bool A02BundleNegatives(void)
{
    westlake_a02_prerequisite_bundle_v2 bundle = MakeBundle();
    bundle.t12_receipt_present = 1;
    if (wlgr_v2_a02_bundle_valid(&bundle)) return false;
    bundle = MakeBundle();
    bundle.receipts[5] = MakeReceipt(
        &bundle.identity, WLGR_V2_TRANSITION_T12, UINT64_C(15));
    if (wlgr_v2_a02_bundle_valid(&bundle)) return false;
    bundle = MakeBundle();
    bundle.receipts[4].sequence = bundle.receipts[3].sequence;
    if (wlgr_v2_a02_bundle_valid(&bundle)) return false;
    bundle = MakeBundle();
    bundle.receipts[2].identity.child_proc_start_time_ticks++;
    if (wlgr_v2_a02_bundle_valid(&bundle)) return false;
    bundle = MakeBundle();
    memset(bundle.bundle_digest, 0, sizeof(bundle.bundle_digest));
    return !wlgr_v2_a02_bundle_valid(&bundle);
}

static void Run(const char *name, bool (*test)(void))
{
    ++tests_run;
    if (!test()) {
        ++failures;
        (void)fprintf(stderr, "FAIL %s\n", name);
    }
}

int main(void)
{
    Run("identity_coverage", IdentityCoverage);
    Run("ordered_receipts", OrderedReceipts);
    Run("receipt_negatives", ReceiptNegatives);
    Run("failure_states", FailureStates);
    Run("exact_duplicate", ExactDuplicateReturnsRecorded);
    Run("replay_progress_reconcile", ReplayProgressAndReconcile);
    Run("terminal_replay", TerminalReplayReturnsFirstCause);
    Run("replay_conflicts", ReplayConflictNegatives);
    Run("a02_bundle_positive", A02BundlePositive);
    Run("a02_bundle_negatives", A02BundleNegatives);
    if (failures != 0U) {
        (void)fprintf(stderr, "RESULT FAIL tests=%u failures=%u\n",
                      tests_run, failures);
        return 1;
    }
    (void)printf("generation-receipt-v2 C semantics: %u/%u PASS\n",
                 tests_run, tests_run);
    return 0;
}
