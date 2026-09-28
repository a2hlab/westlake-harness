#ifndef WESTLAKE_THREAD_GUARD_REGISTRY_H
#define WESTLAKE_THREAD_GUARD_REGISTRY_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__) || defined(__clang__)
#define WLTG_EXPORT __attribute__((visibility("default")))
#else
#define WLTG_EXPORT
#endif

#define WLTG_ABI_VERSION UINT32_C(1)
#define WLTG_DIGEST_SIZE UINT32_C(32)
#define WLTG_MAX_THREAD_RECORDS UINT32_C(256)

/* Exact AArch64 Bionic positive-slot contract owned by appspawn-x MAIN PT_TLS. */
#define WLTG_RESERVATION_TP_START UINT32_C(0x10)
#define WLTG_RESERVATION_SIZE UINT32_C(0x30)
#define WLTG_STACK_GUARD_TP_OFFSET UINT32_C(0x28)
#define WLTG_STACK_GUARD_WIDTH UINT32_C(8)

typedef enum WltgStatus {
    WLTG_STATUS_OK = 0,
    WLTG_STATUS_OK_IDEMPOTENT = 1,
    WLTG_STATUS_DENIED_TRANSIENT = 2,
    WLTG_STATUS_DENIED_TERMINAL = 3,
    WLTG_STATUS_INVALID_ARGUMENT = 4
} WltgStatus;

typedef enum WltgReason {
    WLTG_REASON_NONE = 0,
    WLTG_REASON_ALREADY_INITIALIZED = 1,
    WLTG_REASON_INVALID_ARGUMENT = 2,
    WLTG_REASON_ABI_MISMATCH = 3,
    WLTG_REASON_FORK_RESET_REQUIRED = 4,
    WLTG_REASON_PROCESS_NOT_ARMED = 5,
    WLTG_REASON_PROCESS_TERMINAL = 6,
    WLTG_REASON_BINDING_REJECTED = 7,
    WLTG_REASON_BINDING_MISMATCH = 8,
    WLTG_REASON_CONCURRENT_ARM = 9,
    WLTG_REASON_REGISTRY_FULL = 10,
    WLTG_REASON_TICKET_UNKNOWN = 11,
    WLTG_REASON_TICKET_STATE = 12,
    WLTG_REASON_TICKET_REPLAY = 13,
    WLTG_REASON_TICKET_ROLE_MISMATCH = 14,
    WLTG_REASON_TICKET_CREATOR_MISMATCH = 15,
    WLTG_REASON_CURRENT_THREAD_INVALID = 16,
    WLTG_REASON_THREAD_ALREADY_ADMITTED = 17,
    WLTG_REASON_OWNER_UNAVAILABLE = 18,
    WLTG_REASON_OWNER_MISMATCH = 19,
    WLTG_REASON_OWNER_BOUNDS = 20,
    WLTG_REASON_CSPRNG_FAILED = 21,
    WLTG_REASON_CSPRNG_QUALITY = 22,
    WLTG_REASON_GUARD_VALUE_INVALID = 23,
    WLTG_REASON_PROCESS_GUARD_MISMATCH = 24,
    WLTG_REASON_READBACK_MISMATCH = 25,
    WLTG_REASON_RECEIPT_MISMATCH = 26,
    WLTG_REASON_AUDIT_SINK_REJECTED = 27,
    WLTG_REASON_STATE_RACE = 28,
    WLTG_REASON_INVALID_THREAD_ROLE = 29,
    WLTG_REASON_MAIN_TICKET_ALREADY_ISSUED = 30,
    WLTG_REASON_PROFILE_REVOKED = 31,
    WLTG_REASON_INTERNAL_STATE = 32
} WltgReason;

typedef enum WltgProcessState {
    WLTG_PROCESS_UNSEEDED = 0,
    WLTG_PROCESS_SEEDED = 1,
    WLTG_PROCESS_ARMING = 2,
    WLTG_PROCESS_ARMED = 3,
    WLTG_PROCESS_REVOKED = 4,
    WLTG_PROCESS_REJECTED = 5
} WltgProcessState;

typedef enum WltgThreadState {
    WLTG_THREAD_FREE = 0,
    WLTG_THREAD_ALLOCATING = 1,
    WLTG_THREAD_ISSUED = 2,
    WLTG_THREAD_PREPARING = 3,
    WLTG_THREAD_READY = 4,
    WLTG_THREAD_RETIRING = 5,
    WLTG_THREAD_RETIRED = 6,
    WLTG_THREAD_CANCELLED = 7,
    WLTG_THREAD_FAILED = 8
} WltgThreadState;

typedef enum WltgThreadRole {
    WLTG_THREAD_ROLE_INVALID = 0,
    WLTG_THREAD_ROLE_MAIN = 1,
    WLTG_THREAD_ROLE_GUEST_PTHREAD = 2,
    WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH = 3,
    WLTG_THREAD_ROLE_PARENT_PRELOAD = 4
} WltgThreadRole;

typedef enum WltgAdmissionKind {
    WLTG_ADMISSION_INVALID = 0,
    WLTG_ADMISSION_MAIN_POST_SPECIALIZATION = 1,
    WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE = 2,
    WLTG_ADMISSION_ADAPTER_JNI_ATTACH = 3,
    WLTG_ADMISSION_PARENT_PRELOAD = 4
} WltgAdmissionKind;

typedef enum WltgOwnerKind {
    WLTG_OWNER_INVALID = 0,
    WLTG_OWNER_MAIN_ELF_TLS_RESERVATION = 1
} WltgOwnerKind;

typedef enum WltgGuardSourceQuality {
    WLTG_GUARD_SOURCE_INVALID = 0,
    WLTG_GUARD_SOURCE_OS_CSPRNG = 1
} WltgGuardSourceQuality;

typedef enum WltgEventType {
    WLTG_EVENT_PROCESS_ARMED = 1,
    WLTG_EVENT_TICKET_ISSUED = 2,
    WLTG_EVENT_THREAD_PREPARING = 3,
    WLTG_EVENT_GUARD_WRITTEN = 4,
    WLTG_EVENT_THREAD_READY = 5,
    WLTG_EVENT_TICKET_CANCELLED = 6,
    WLTG_EVENT_THREAD_RETIRED = 7,
    WLTG_EVENT_PROCESS_REVOKED = 8,
    WLTG_EVENT_PROCESS_REJECTED = 9
} WltgEventType;

typedef struct WltgResult {
    WltgStatus status;
    WltgReason reason;
    WltgProcessState process_state;
    WltgThreadState thread_state;
} WltgResult;

typedef struct WltgForkSeed {
    uint32_t abi_version;
    uint32_t reserved_zero;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
} WltgForkSeed;

/*
 * The registry validates this immutable process binding but does not establish
 * issuer trust by itself. Product activation requires the existing appspawn
 * certificate/sealed-generation owner to implement verify_process_binding.
 */
typedef struct WltgProcessBindingV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t binding_nonce;
    uint8_t profile_digest[WLTG_DIGEST_SIZE];
    uint8_t target_digest[WLTG_DIGEST_SIZE];
    uint32_t reservation_tp_start;
    uint32_t reservation_size;
    uint32_t stack_guard_tp_offset;
    uint32_t stack_guard_width;
    uint32_t max_live_threads;
    uint32_t reserved_zero;
} WltgProcessBindingV1;

typedef struct WltgThreadTicketV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t ticket_id;
    uint64_t one_shot_nonce;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t issuer_thread_id;
    WltgAdmissionKind admission_kind;
    WltgThreadRole role;
    uint32_t reserved_zero;
    uint32_t reserved_zero_2;
} WltgThreadTicketV1;

typedef struct WltgGuardSample {
    uint64_t value;
    uint64_t source_epoch;
    WltgGuardSourceQuality quality;
    uint32_t reserved_zero;
} WltgGuardSample;

typedef struct WltgOwnedRegion {
    uint32_t abi_version;
    WltgOwnerKind owner_kind;
    uint32_t tp_start_offset;
    uint32_t byte_size;
    uint8_t *base;
    uint64_t owner_cookie;
    uint64_t current_thread_id;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
} WltgOwnedRegion;

typedef struct WltgThreadReceiptV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    WltgThreadState state;
    WltgAdmissionKind admission_kind;
    WltgThreadRole role;
    uint32_t reserved_zero;
    uint64_t ticket_id;
    uint64_t one_shot_nonce;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t issuer_thread_id;
    uint64_t current_thread_id;
    uint64_t owner_cookie;
    uintptr_t written_address;
    uint32_t tp_offset;
    uint32_t width;
    uint64_t publication_sequence;
} WltgThreadReceiptV1;

typedef struct WltgAuditEvent {
    uint32_t abi_version;
    WltgEventType type;
    WltgReason reason;
    WltgProcessState process_state;
    WltgThreadState thread_state;
    WltgAdmissionKind admission_kind;
    WltgThreadRole role;
    uint32_t reserved_zero;
    uint64_t sequence;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t ticket_id;
    uint64_t issuer_thread_id;
    uint64_t current_thread_id;
    uint64_t owner_cookie;
    uintptr_t written_address;
    uint64_t publication_sequence;
} WltgAuditEvent;

typedef int (*WltgVerifyProcessBinding)(
    void *context, const WltgProcessBindingV1 *binding);
typedef uint64_t (*WltgGetCurrentThreadId)(void *context);
typedef int (*WltgResolveCurrentThreadRegion)(
    void *context, const WltgProcessBindingV1 *binding,
    const WltgThreadTicketV1 *ticket, WltgOwnedRegion *out_region);
typedef int (*WltgGetOsCsprng)(void *context,
                              uint64_t required_process_epoch,
                              WltgGuardSample *out_sample);
typedef int (*WltgEmitAuditEvent)(void *context,
                                 const WltgAuditEvent *event);

/*
 * Callback success is exactly 1. Every other value is failure. get_os_csprng
 * supplies the one canonical Bionic guard for this process epoch and is called
 * only while arming; thread tickets/preparation copy that value and never ask
 * for per-thread entropy. Callbacks must not re-enter WLTG. In the post-setcon
 * MAIN window they must also be proven not to create threads.
 */
typedef struct WltgPlatformOpsV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    void *context;
    WltgVerifyProcessBinding verify_process_binding;
    WltgGetCurrentThreadId get_current_thread_id;
    WltgResolveCurrentThreadRegion resolve_current_thread_region;
    WltgGetOsCsprng get_os_csprng;
    WltgEmitAuditEvent emit_audit_event;
} WltgPlatformOpsV1;

typedef struct WltgProcessSnapshotV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    WltgProcessState process_state;
    WltgReason last_reason;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t binding_nonce;
    uint64_t audit_sequence;
    uint64_t audit_drop_count;
    uint64_t next_ticket_id;
    uint32_t active_ticket_count;
    uint32_t issued_count;
    uint32_t preparing_count;
    uint32_t ready_count;
    uint32_t retired_count;
    uint32_t cancelled_count;
    uint32_t failed_count;
    uint32_t reserved_zero;
} WltgProcessSnapshotV1;

WLTG_EXPORT uint32_t WLTG_GetAbiVersion(void);
WLTG_EXPORT const char *WLTG_ReasonString(WltgReason reason);

/*
 * Earliest single-threaded child boundary. It uses no lock, allocation, system
 * call, or callback; scalar publication state is reset with lock-free atomics.
 */
WLTG_EXPORT WltgResult WLTG_AfterForkChildReset(const WltgForkSeed *seed);

/*
 * Verifies the process binding and obtains exactly one non-zero OS-CSPRNG
 * process guard. Entropy/quality failure rejects the process; no fallback is
 * permitted.
 */
WLTG_EXPORT WltgResult WLTG_ProcessArm(
    const WltgProcessBindingV1 *binding,
    const WltgPlatformOpsV1 *platform_ops);

/*
 * PARENT_PRELOAD: issue before ART startVm/preload on the stock appspawn
 * server thread. MAIN: issue after stock setcon succeeds and consume on the
 * same child thread before ZygoteHooks post-fork work. JNI_ATTACH is likewise
 * same-thread. A
 * NAMESPACE_PTHREAD_CREATE ticket is issued by the guest namespace bridge and
 * consumed by the newly created real Musl thread before its guest start routine.
 */
WLTG_EXPORT WltgResult WLTG_IssueThreadTicket(
    WltgAdmissionKind admission_kind, WltgThreadRole role,
    WltgThreadTicketV1 *out_ticket);

WLTG_EXPORT WltgResult WLTG_CancelThreadTicket(
    const WltgThreadTicketV1 *ticket);

/* Copies the already-armed process guard into the current owned slot. */
WLTG_EXPORT WltgResult WLTG_PrepareCurrentThread(
    const WltgThreadTicketV1 *ticket,
    WltgThreadReceiptV1 *out_receipt);

WLTG_EXPORT WltgResult WLTG_VerifyCurrentThreadReady(
    WltgThreadReceiptV1 *out_receipt);

/*
 * Call only after all guest guarded frames and guest destructors have left the
 * thread. The registry clears its secret receipt but deliberately never writes
 * zero/fallback data back into the dying Musl thread's reservation.
 */
WLTG_EXPORT WltgResult WLTG_RetireCurrentThread(
    const WltgThreadReceiptV1 *receipt);

WLTG_EXPORT WltgResult WLTG_Revoke(void);

WLTG_EXPORT WltgResult WLTG_GetProcessSnapshot(
    WltgProcessSnapshotV1 *out_snapshot);

#ifdef __cplusplus
}
#endif

#endif
