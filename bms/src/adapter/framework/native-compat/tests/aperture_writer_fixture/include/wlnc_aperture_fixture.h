#ifndef WLNC_APERTURE_FIXTURE_H
#define WLNC_APERTURE_FIXTURE_H

#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__) || defined(__clang__)
#define WLAF_EXPORT __attribute__((visibility("default")))
#else
#define WLAF_EXPORT
#endif

/*
 * This ABI exists only in the company-owned PR-08A target fixture.  It is not
 * a product capability and it is deliberately incompatible with
 * WlncLoadPermit from the audit-only native-compat core.
 */
#define WLAF_ABI_VERSION UINT32_C(1)
#define WLAF_PERMIT_STRUCT_TYPE UINT32_C(0x574c4146) /* "WLAF" */
#define WLAF_PERMIT_KIND_FIXTURE_ONLY UINT32_C(0x46585452) /* "FXTR" */
#define WLAF_MECHANISM_APERTURE_NATIVE_FIXTURE UINT32_C(0x41504658)
#define WLAF_SIGNATURE_SIZE UINT32_C(64)
#define WLAF_TARGET_DIGEST_SIZE UINT32_C(32)

/* Exact main-ELF reservation contract for AArch64 Bionic positive slots. */
#define WLAF_RESERVATION_TP_START UINT32_C(0x10)
#define WLAF_RESERVATION_SIZE UINT32_C(0x30)
#define WLAF_STACK_GUARD_TP_OFFSET UINT32_C(0x28)
#define WLAF_STACK_GUARD_WIDTH UINT32_C(8)

typedef enum WlafStatus {
    WLAF_STATUS_OK = 0,
    WLAF_STATUS_DENIED = 1,
    WLAF_STATUS_TERMINAL = 2,
    WLAF_STATUS_INVALID_ARGUMENT = 3
} WlafStatus;

typedef enum WlafReason {
    WLAF_REASON_NONE = 0,
    WLAF_REASON_INVALID_ARGUMENT = 1,
    WLAF_REASON_ABI_MISMATCH = 2,
    WLAF_REASON_NOT_FIXTURE_PERMIT = 3,
    WLAF_REASON_MECHANISM_MISMATCH = 4,
    WLAF_REASON_PERMIT_FIELDS_INVALID = 5,
    WLAF_REASON_SIGNATURE_REQUIRED = 6,
    WLAF_REASON_SIGNATURE_REJECTED = 7,
    WLAF_REASON_BINDING_UNAVAILABLE = 8,
    WLAF_REASON_BINDING_MISMATCH = 9,
    WLAF_REASON_OWNER_UNAVAILABLE = 10,
    WLAF_REASON_OWNER_MISMATCH = 11,
    WLAF_REASON_OWNER_BOUNDS = 12,
    WLAF_REASON_PERMIT_REPLAY = 13,
    WLAF_REASON_CSPRNG_FAILED = 14,
    WLAF_REASON_CSPRNG_QUALITY = 15,
    WLAF_REASON_GUARD_VALUE_INVALID = 16,
    WLAF_REASON_READBACK_MISMATCH = 17,
    WLAF_REASON_INTERNAL_STATE = 18
} WlafReason;

typedef enum WlafPublicationState {
    WLAF_PUBLICATION_UNSEEN = 0,
    WLAF_PUBLICATION_PREPARING = 1,
    WLAF_PUBLICATION_READY = 2,
    WLAF_PUBLICATION_FAILED = 3
} WlafPublicationState;

typedef enum WlafOwnerKind {
    WLAF_OWNER_INVALID = 0,
    WLAF_OWNER_MAIN_ELF_TLS_RESERVATION = 1
} WlafOwnerKind;

typedef enum WlafGuardSourceQuality {
    WLAF_GUARD_SOURCE_INVALID = 0,
    WLAF_GUARD_SOURCE_OS_CSPRNG = 1
} WlafGuardSourceQuality;

typedef enum WlafEventType {
    WLAF_EVENT_PERMIT_VERIFIED = 1,
    WLAF_EVENT_OWNER_RESOLVED = 2,
    WLAF_EVENT_PERMIT_CONSUMED = 3,
    WLAF_EVENT_GUARD_WRITTEN = 4,
    WLAF_EVENT_READBACK_VERIFIED = 5,
    WLAF_EVENT_METADATA_STAGED = 6,
    WLAF_EVENT_READY_PUBLISHED = 7,
    WLAF_EVENT_REJECTED = 8
} WlafEventType;

typedef struct WlafFixturePermitV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t struct_type;
    uint32_t permit_kind;
    uint32_t mechanism;
    uint32_t signature_size;
    uint32_t tp_offset;
    uint32_t width;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t one_shot_nonce;
    uint8_t target_digest[WLAF_TARGET_DIGEST_SIZE];
    uint8_t signature[WLAF_SIGNATURE_SIZE];
} WlafFixturePermitV1;

typedef struct WlafCurrentBinding {
    uint32_t abi_version;
    uint32_t reserved_zero;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint8_t target_digest[WLAF_TARGET_DIGEST_SIZE];
} WlafCurrentBinding;

/*
 * Metadata belongs to the trusted current-thread owner returned by the
 * platform callback.  The backend has no TLS object of its own.
 */
typedef struct WlafPublication {
    _Atomic uint32_t state;
    uint32_t reason;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t one_shot_nonce;
    uint64_t owner_cookie;
    uintptr_t written_address;
    uint32_t tp_offset;
    uint32_t width;
    uint64_t guard_value;
    uint64_t readback_value;
} WlafPublication;

typedef struct WlafOwnedRegion {
    uint32_t abi_version;
    WlafOwnerKind owner_kind;
    uint32_t tp_start_offset;
    uint32_t byte_size;
    uint8_t *base;
    WlafPublication *publication;
    uint64_t owner_cookie;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
} WlafOwnedRegion;

typedef struct WlafGuardSample {
    uint64_t value;
    uint64_t source_epoch;
    WlafGuardSourceQuality quality;
    uint32_t reserved_zero;
} WlafGuardSample;

typedef struct WlafEvent {
    uint32_t abi_version;
    WlafEventType type;
    WlafReason reason;
    WlafPublicationState publication_state;
    uint64_t adapter_generation;
    uint64_t process_epoch;
    uint64_t policy_epoch;
    uint64_t one_shot_nonce;
} WlafEvent;

typedef int (*WlafReadCurrentBinding)(void *context,
                                      WlafCurrentBinding *out_binding);
typedef int (*WlafVerifyFixtureSignature)(
    void *context, const WlafFixturePermitV1 *permit);
typedef int (*WlafResolveCurrentThreadRegion)(
    void *context, const WlafFixturePermitV1 *permit,
    WlafOwnedRegion *out_region);
typedef int (*WlafGetOsCsprng)(void *context,
                              uint64_t required_process_epoch,
                              WlafGuardSample *out_sample);
typedef void (*WlafEmitEvent)(void *context, const WlafEvent *event);

typedef struct WlafFixtureOps {
    uint32_t abi_version;
    uint32_t reserved_zero;
    void *context;
    WlafReadCurrentBinding read_current_binding;
    WlafVerifyFixtureSignature verify_fixture_signature;
    WlafResolveCurrentThreadRegion resolve_current_thread_region;
    WlafGetOsCsprng get_os_csprng;
    WlafEmitEvent emit_event;
} WlafFixtureOps;

typedef struct WlafResult {
    WlafStatus status;
    WlafReason reason;
    WlafPublicationState publication_state;
    uint32_t reserved_zero;
} WlafResult;

/*
 * Fixture-only data-plane entry.  There is intentionally no adapter product
 * caller and no conversion from WlncLoadPermit to WlafFixturePermitV1.
 */
WLAF_EXPORT WlafResult WLAF_PublishFixtureAperture(
    const WlafFixturePermitV1 *permit, const WlafFixtureOps *ops);

WLAF_EXPORT const char *WLAF_ReasonString(WlafReason reason);

#ifdef __cplusplus
}
#endif

#endif
