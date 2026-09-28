#include "westlake_thread_guard_registry.h"

#include <stddef.h>
#include <stdint.h>

_Static_assert(sizeof(void *) == 8, "WLTG ABI v1 is 64-bit");
_Static_assert(sizeof(uintptr_t) == 8, "WLTG ABI v1 is 64-bit");
_Static_assert(sizeof(WltgResult) == 16, "WltgResult ABI drift");
_Static_assert(sizeof(WltgForkSeed) == 32, "WltgForkSeed ABI drift");
_Static_assert(sizeof(WltgProcessBindingV1) == 128,
               "WltgProcessBindingV1 ABI drift");
_Static_assert(sizeof(WltgThreadTicketV1) == 72,
               "WltgThreadTicketV1 ABI drift");
_Static_assert(sizeof(WltgGuardSample) == 24,
               "WltgGuardSample ABI drift");
_Static_assert(sizeof(WltgOwnedRegion) == 64,
               "WltgOwnedRegion ABI drift");
_Static_assert(sizeof(WltgThreadReceiptV1) == 112,
               "WltgThreadReceiptV1 ABI drift");
_Static_assert(sizeof(WltgAuditEvent) == 112,
               "WltgAuditEvent ABI drift");
_Static_assert(sizeof(WltgPlatformOpsV1) == 56,
               "WltgPlatformOpsV1 ABI drift");
_Static_assert(sizeof(WltgProcessSnapshotV1) == 104,
               "WltgProcessSnapshotV1 ABI drift");

_Static_assert(offsetof(WltgProcessBindingV1, binding_nonce) == 32,
               "binding nonce offset drift");
_Static_assert(offsetof(WltgProcessBindingV1, profile_digest) == 40,
               "profile digest offset drift");
_Static_assert(offsetof(WltgProcessBindingV1, target_digest) == 72,
               "target digest offset drift");
_Static_assert(offsetof(WltgProcessBindingV1, stack_guard_tp_offset) == 112,
               "stack guard offset field drift");
_Static_assert(offsetof(WltgThreadTicketV1, ticket_id) == 8,
               "ticket id offset drift");
_Static_assert(offsetof(WltgThreadTicketV1, issuer_thread_id) == 48,
               "ticket issuer offset drift");
_Static_assert(offsetof(WltgOwnedRegion, base) == 16,
               "owned region base offset drift");
_Static_assert(offsetof(WltgOwnedRegion, current_thread_id) == 32,
               "owned region thread offset drift");
_Static_assert(offsetof(WltgThreadReceiptV1, current_thread_id) == 72,
               "receipt current thread offset drift");
_Static_assert(offsetof(WltgThreadReceiptV1, written_address) == 88,
               "receipt address offset drift");
_Static_assert(offsetof(WltgThreadReceiptV1, publication_sequence) == 104,
               "receipt publication offset drift");
_Static_assert(offsetof(WltgAuditEvent, sequence) == 32,
               "event sequence offset drift");
_Static_assert(offsetof(WltgPlatformOpsV1, context) == 8,
               "ops context offset drift");
_Static_assert(offsetof(WltgPlatformOpsV1, emit_audit_event) == 48,
               "ops audit callback offset drift");
_Static_assert(offsetof(WltgProcessSnapshotV1, active_ticket_count) == 72,
               "snapshot count offset drift");

_Static_assert(WLTG_RESERVATION_TP_START == UINT32_C(0x10),
               "reservation start changed");
_Static_assert(WLTG_RESERVATION_SIZE == UINT32_C(0x30),
               "reservation size changed");
_Static_assert(WLTG_STACK_GUARD_TP_OFFSET == UINT32_C(0x28),
               "Bionic slot-5 offset changed");
_Static_assert(WLTG_STACK_GUARD_WIDTH == UINT32_C(8),
               "Bionic slot-5 width changed");
