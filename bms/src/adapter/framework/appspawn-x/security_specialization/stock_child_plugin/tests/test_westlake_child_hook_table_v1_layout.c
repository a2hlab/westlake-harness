#include "westlake_child_hook_table_v1.h"

#include <stddef.h>
#include <stdint.h>

WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_TABLE_V1_CAPABILITY_COUNT == 10,
    "the V1 table must expose exactly ten capabilities");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_THREAD_TLS_SIGNAL_BITMAP == UINT64_C(0x7f),
    "thread/TLS/signal owner must own exactly seven capabilities");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_ALLOCATOR_BITMAP == UINT64_C(0x80),
    "allocator owner must own exactly one capability");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_UNWIND_CPP_BITMAP == UINT64_C(0x300),
    "unwind/C++ owner must own exactly two capabilities");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE == 32,
    "generation identity must retain the exact SHA-256 digest");
WESTLAKE_CHILD_HOOK_STATIC_ASSERT(
    WESTLAKE_CHILD_HOOK_UNPUBLISHED == 0 &&
    WESTLAKE_CHILD_HOOK_INSTALLING == 1 &&
    WESTLAKE_CHILD_HOOK_READY == 2 &&
    WESTLAKE_CHILD_HOOK_REVOKING == 3 &&
    WESTLAKE_CHILD_HOOK_DRAINING == 4 &&
    WESTLAKE_CHILD_HOOK_INVALID == 5,
    "lifecycle numeric ABI drift");

int main(void)
{
    return sizeof(westlake_child_hook_table_v1) == 160 &&
        sizeof(westlake_child_hook_control_v1) == 112 &&
        sizeof(westlake_child_hook_lease_v1) == 56 &&
        offsetof(westlake_child_hook_table_v1, generation_digest) == 32 &&
        offsetof(westlake_child_hook_table_v1, thread_create) == 80 &&
        offsetof(westlake_child_hook_table_v1, cpp_runtime_domain) == 152 &&
        offsetof(westlake_child_hook_control_v1,
                 atomic_published_table_address) == 72 &&
        offsetof(westlake_child_hook_control_v1, atomic_first_cause) == 104
        ? 0 : 1;
}
