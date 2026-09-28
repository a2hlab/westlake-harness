#ifndef WESTLAKE_THREAD_TEMPLATE_PUBLISHER_H
#define WESTLAKE_THREAD_TEMPLATE_PUBLISHER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__GNUC__) || defined(__clang__)
#define WLTP_HIDDEN __attribute__((visibility("hidden")))
#else
#define WLTP_HIDDEN
#endif

#define WLTP_ABI_VERSION UINT32_C(1)
#define WLTP_RESERVATION_SIZE UINT32_C(48)
#define WLTP_GUARD_RELATIVE_OFFSET UINT32_C(24)
#define WLTP_GUARD_SIZE UINT32_C(8)
#define WLTP_MAIN_IMAGE_LOCATOR_AT_PHDR UINT8_C(1)
#define WLTP_CURRENT_THREAD_IMAGE_LOCATOR UINT8_C(2)

typedef enum WltpPublishStatus {
    WLTP_PUBLISH_OK = 0,
    WLTP_PUBLISH_INVALID_ARGUMENT = -1,
    WLTP_PUBLISH_MAIN_TLS_NOT_EXACT = -2,
    WLTP_PUBLISH_COMPETING_OWNER = -3,
    WLTP_PUBLISH_PROTECTION_FAILED = -4,
    WLTP_PUBLISH_VERIFY_FAILED = -5,
    WLTP_PUBLISH_ALREADY_PUBLISHED = -6
} WltpPublishStatus;

typedef enum WltpProcessEpochMode {
    WLTP_PROCESS_EPOCH_INVALID = 0,
    WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP = 1,
    WLTP_PROCESS_EPOCH_AFTER_FORK_CHILD = 2
} WltpProcessEpochMode;

typedef enum WltpProcessEpochStatus {
    WLTP_PROCESS_EPOCH_OK = 0,
    WLTP_PROCESS_EPOCH_INVALID_ARGUMENT = -1,
    WLTP_PROCESS_EPOCH_STATE_MISMATCH = -2,
    WLTP_PROCESS_EPOCH_MAIN_TLS_NOT_EXACT = -3,
    WLTP_PROCESS_EPOCH_INHERITED_IMAGE_MISMATCH = -4,
    WLTP_PROCESS_EPOCH_PROTECTION_FAILED = -5,
    WLTP_PROCESS_EPOCH_GENERATION_MISMATCH = -6
} WltpProcessEpochStatus;

typedef struct WltpProcessEpochSeedV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    WltpProcessEpochMode mode;
    uint32_t reserved_zero;
    uint64_t adapter_generation;
    uint64_t process_epoch;
} WltpProcessEpochSeedV1;

typedef struct WltpPublisherContractV1 {
    uint32_t magic;
    uint16_t version;
    uint16_t reservation_size;
    uint16_t publish_offset;
    uint16_t guard_size;
    uint8_t main_image_locator;
    uint8_t template_patch;
    uint8_t restore_protection;
    uint8_t requires_relro;
    uint8_t publisher_count;
    uint8_t explicit_epoch_mode;
    uint8_t child_reset_enabled;
    uint8_t clear_inherited_template;
    uint8_t same_adapter_generation;
    uint8_t full_image_compare;
    uint8_t reserved_zero[2];
} WltpPublisherContractV1;

/* Binary-auditable contract; hidden from the product dynamic ABI. */
extern WLTP_HIDDEN const WltpPublisherContractV1
    wltp_publisher_contract_v1;

/*
 * Required after fork and before WLTG arms the new child generation. If a
 * parent generation had published A, the child COW-clears only its inherited
 * template copy, restores RELRO, and then permits one publication of B.
 */
WLTP_HIDDEN int WLTP_BeginProcessEpoch(
    const WltpProcessEpochSeedV1 *seed,
    const uint8_t *current_reservation);

/*
 * Publish the already-admitted process guard from the current MAIN TLS
 * instance into the main ELF's file-backed PT_TLS initialization image.
 * Exact Musl pthread creation then copies that image before a new start
 * routine. Every execution entrance still requires an admission receipt.
 */
WLTP_HIDDEN int WLTP_PublishMainThreadTemplate(
    const uint8_t *current_reservation);

#ifdef __cplusplus
}
#endif

#endif
