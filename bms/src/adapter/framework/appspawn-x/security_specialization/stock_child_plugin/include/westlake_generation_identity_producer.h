#ifndef WESTLAKE_GENERATION_IDENTITY_PRODUCER_H
#define WESTLAKE_GENERATION_IDENTITY_PRODUCER_H

#include "westlake_generation_receipt_v2.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WLGR_IP_ABI_VERSION UINT32_C(1)
#define WLGR_IP_INPUT_DIGEST_SIZE WLGR_V2_SHA256_SIZE

typedef enum WlgrIpError {
    WLGR_IP_OK = 0,
    WLGR_IP_INVALID_ARGUMENT = 1,
    WLGR_IP_SOURCE_FACTS_INVALID = 2,
    WLGR_IP_CURRENT_PROCESS_UNAVAILABLE = 3,
    WLGR_IP_CURRENT_PROCESS_MISMATCH = 4,
    WLGR_IP_ALREADY_BUILT = 5,
    WLGR_IP_REPLAY_CONFLICT = 6,
    WLGR_IP_IDENTITY_INVALID = 7,
    WLGR_IP_TAMPERED = 8
} WlgrIpError;

/* Every security-bearing field is supplied by the generation owner.  The
 * producer never manufactures a digest, nonce, boot id, epoch, or key. */
typedef struct WlgrIpSourceFacts {
    westlake_runtime_instance_key_v2 runtime_key;
    uint8_t boot_id[WLGR_V2_BOOT_ID_SIZE];
    uint8_t artifact_generation[WLGR_V2_SHA256_SIZE];
    uint64_t policy_epoch;
    uint8_t specialization_receipt_digest[WLGR_V2_SHA256_SIZE];
    uint8_t artifact_manifest_digest[WLGR_V2_SHA256_SIZE];
    uint8_t hook_schema_digest[WLGR_V2_SHA256_SIZE];
    uint8_t request_nonce[WLGR_V2_NONCE_SIZE];
} WlgrIpSourceFacts;

typedef int (*WlgrIpReadCurrentProcessFn)(
    void *context, uint64_t *child_pid, uint64_t *proc_start_time_ticks);

typedef struct WlgrIpOps {
    WlgrIpReadCurrentProcessFn read_current_process;
    void *context;
} WlgrIpOps;

typedef struct WlgrIpProducer {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t state;
    uint32_t reserved_zero;
    westlake_generation_identity_v2 identity;
    uint8_t input_digest[WLGR_IP_INPUT_DIGEST_SIZE];
} WlgrIpProducer;

WlgrIpError WlgrIpBuild(
    WlgrIpProducer *producer, const WlgrIpSourceFacts *facts,
    const WlgrIpOps *ops);

WlgrIpError WlgrIpValidate(
    const WlgrIpProducer *producer, const WlgrIpSourceFacts *facts,
    const WlgrIpOps *ops);

const westlake_generation_identity_v2 *WlgrIpGetIdentity(
    const WlgrIpProducer *producer);

#ifdef __cplusplus
}
#endif

#endif
