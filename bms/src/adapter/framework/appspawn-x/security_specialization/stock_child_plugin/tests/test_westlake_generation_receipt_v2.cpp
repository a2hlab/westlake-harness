#include "westlake_generation_receipt_v2.h"

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <type_traits>

static_assert(std::is_standard_layout<westlake_runtime_instance_key_v2>::value,
              "runtime key must remain standard-layout");
static_assert(std::is_trivially_copyable<westlake_runtime_instance_key_v2>::value,
              "runtime key must remain trivially copyable");
static_assert(std::is_standard_layout<westlake_generation_identity_v2>::value,
              "generation identity must remain standard-layout");
static_assert(std::is_trivially_copyable<westlake_generation_identity_v2>::value,
              "generation identity must remain trivially copyable");
static_assert(std::is_standard_layout<westlake_runtime_stage_receipt_v2>::value,
              "receipt must remain standard-layout");
static_assert(std::is_trivially_copyable<westlake_runtime_stage_receipt_v2>::value,
              "receipt must remain trivially copyable");
static_assert(std::is_standard_layout<westlake_a02_prerequisite_bundle_v2>::value,
              "A02 bundle must remain standard-layout");
static_assert(std::is_trivially_copyable<westlake_a02_prerequisite_bundle_v2>::value,
              "A02 bundle must remain trivially copyable");

#define WLGR_V2_ASSERT_NOT_POINTER(type, member) \
    static_assert(!std::is_pointer<decltype(((type *)nullptr)->member)>::value, \
                  #type "." #member " must not be a pointer")

WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, magic);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, abi_version);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, struct_size);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, struct_alignment);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, android_uid);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, launch_generation);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, android_package);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2,
                           android_process_name);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_instance_key_v2, reserved_zero);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, magic);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, abi_version);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, struct_size);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2,
                           struct_alignment);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, reserved_zero0);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, runtime_key);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, boot_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2,
                           artifact_generation);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, policy_epoch);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, child_pid);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2,
                           child_proc_start_time_ticks);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2,
                           specialization_receipt_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2,
                           artifact_manifest_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2,
                           hook_schema_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, request_nonce);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_identity_v2, reserved_zero);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, magic);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, abi_version);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, struct_size);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2,
                           struct_alignment);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, reserved_zero0);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, identity);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, action_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, transition_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, stage_before);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, stage_after);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, owner);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2,
                           publication_state);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, result_code);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, first_cause);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, native_cause);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, receipt_flags);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2,
                           child_thread_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, sequence);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2,
                           monotonic_timestamp_ns);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2,
                           reserved_zero1);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, input_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, output_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2,
                           terminal_tombstone_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_runtime_stage_receipt_v2, reserved_zero);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2, magic);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           abi_version);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           struct_size);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           struct_alignment);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           reserved_zero0);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2, disposition);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           recorded_publication_state);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           recorded_result);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           recorded_first_cause);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           recorded_sequence);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           recorded_output_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_generation_replay_result_v2,
                           reserved_zero);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2, magic);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2, abi_version);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2, struct_size);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           struct_alignment);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           reserved_zero0);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2, identity);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           producer_action_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           consumer_action_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           producer_terminal_transition_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           next_transition_id);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           bundle_state);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           receipt_count);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           t12_receipt_present);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           reserved_zero1);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           first_sequence);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           last_sequence);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           monotonic_created_timestamp_ns);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2, receipts);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           bundle_digest);
WLGR_V2_ASSERT_NOT_POINTER(westlake_a02_prerequisite_bundle_v2,
                           reserved_zero);

#undef WLGR_V2_ASSERT_NOT_POINTER

static_assert(sizeof(westlake_runtime_instance_key_v2) == 576);
static_assert(sizeof(westlake_generation_identity_v2) == 816);
static_assert(sizeof(westlake_runtime_stage_receipt_v2) == 1040);
static_assert(sizeof(westlake_generation_replay_result_v2) == 112);
static_assert(sizeof(westlake_a02_prerequisite_bundle_v2) == 7200);
static_assert(alignof(westlake_runtime_instance_key_v2) == 8);
static_assert(alignof(westlake_generation_identity_v2) == 8);
static_assert(alignof(westlake_runtime_stage_receipt_v2) == 8);
static_assert(alignof(westlake_a02_prerequisite_bundle_v2) == 8);
static_assert(offsetof(westlake_runtime_instance_key_v2, launch_generation) == 24);
static_assert(offsetof(westlake_generation_identity_v2, artifact_generation) == 616);
static_assert(offsetof(westlake_generation_identity_v2,
                       specialization_receipt_digest) == 672);
static_assert(offsetof(westlake_generation_identity_v2, request_nonce) == 768);
static_assert(offsetof(westlake_runtime_stage_receipt_v2, identity) == 24);
static_assert(offsetof(westlake_runtime_stage_receipt_v2,
                       child_thread_id) == 880);
static_assert(offsetof(westlake_runtime_stage_receipt_v2, sequence) == 888);
static_assert(offsetof(westlake_runtime_stage_receipt_v2, input_digest) == 912);
static_assert(offsetof(westlake_runtime_stage_receipt_v2,
                       terminal_tombstone_digest) == 976);
static_assert(offsetof(westlake_a02_prerequisite_bundle_v2, receipts) == 896);

int main()
{
    std::printf("generation-receipt-v2 C++ layout: key=%zu identity=%zu "
                "receipt=%zu replay=%zu bundle=%zu PASS\n",
                sizeof(westlake_runtime_instance_key_v2),
                sizeof(westlake_generation_identity_v2),
                sizeof(westlake_runtime_stage_receipt_v2),
                sizeof(westlake_generation_replay_result_v2),
                sizeof(westlake_a02_prerequisite_bundle_v2));
    return 0;
}
