#include "westlake_generation_identity_producer.h"

#include "westlake_sha256.h"

#include <stddef.h>
#include <string.h>

#define WLGR_IP_STATE_EMPTY UINT32_C(0)
#define WLGR_IP_STATE_READY UINT32_C(1)

static int Nonzero(const uint8_t *bytes, size_t size)
{
    size_t index;
    uint8_t value = 0U;
    for (index = 0U; index < size; ++index) {
        value |= bytes[index];
    }
    return value != 0U;
}

static int SourceFactsValid(const WlgrIpSourceFacts *facts)
{
    return facts != NULL &&
        wlgr_v2_runtime_key_valid(&facts->runtime_key) &&
        Nonzero(facts->boot_id, sizeof(facts->boot_id)) &&
        Nonzero(facts->artifact_generation,
                sizeof(facts->artifact_generation)) &&
        facts->policy_epoch != UINT64_C(0) &&
        Nonzero(facts->specialization_receipt_digest,
                sizeof(facts->specialization_receipt_digest)) &&
        Nonzero(facts->artifact_manifest_digest,
                sizeof(facts->artifact_manifest_digest)) &&
        Nonzero(facts->hook_schema_digest,
                sizeof(facts->hook_schema_digest)) &&
        Nonzero(facts->request_nonce, sizeof(facts->request_nonce));
}

static int ReadCurrentProcess(const WlgrIpOps *ops, uint64_t *pid,
                              uint64_t *start)
{
    if (ops == NULL || ops->read_current_process == NULL || pid == NULL ||
        start == NULL || ops->read_current_process(ops->context, pid, start) !=
            0) {
        return -1;
    }
    return *pid > UINT64_C(1) && *start != UINT64_C(0) ? 0 : -1;
}

static void BuildIdentity(westlake_generation_identity_v2 *identity,
                          const WlgrIpSourceFacts *facts, uint64_t pid,
                          uint64_t start)
{
    (void)memset(identity, 0, sizeof(*identity));
    identity->magic = WLGR_V2_IDENTITY_MAGIC;
    identity->abi_version = WLGR_V2_ABI_VERSION;
    identity->struct_size = WLGR_V2_IDENTITY_SIZE;
    identity->struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    identity->runtime_key = facts->runtime_key;
    (void)memcpy(identity->boot_id, facts->boot_id, sizeof(identity->boot_id));
    (void)memcpy(identity->artifact_generation, facts->artifact_generation,
                 sizeof(identity->artifact_generation));
    identity->policy_epoch = facts->policy_epoch;
    identity->child_pid = pid;
    identity->child_proc_start_time_ticks = start;
    (void)memcpy(identity->specialization_receipt_digest,
                 facts->specialization_receipt_digest,
                 sizeof(identity->specialization_receipt_digest));
    (void)memcpy(identity->artifact_manifest_digest,
                 facts->artifact_manifest_digest,
                 sizeof(identity->artifact_manifest_digest));
    (void)memcpy(identity->hook_schema_digest, facts->hook_schema_digest,
                 sizeof(identity->hook_schema_digest));
    (void)memcpy(identity->request_nonce, facts->request_nonce,
                 sizeof(identity->request_nonce));
}

static int InputDigest(const westlake_generation_identity_v2 *identity,
                       uint8_t output[WLGR_IP_INPUT_DIGEST_SIZE])
{
    WlSha256Context context;
    WLSha256Init(&context);
    if (WLSha256Update(&context, identity, sizeof(*identity)) != 0 ||
        WLSha256Final(&context, output) != 0) {
        return -1;
    }
    return 0;
}

static int DigestEqual(const WlgrIpProducer *producer)
{
    uint8_t digest[WLGR_IP_INPUT_DIGEST_SIZE];
    return InputDigest(&producer->identity, digest) == 0 &&
        memcmp(digest, producer->input_digest, sizeof(digest)) == 0;
}

WlgrIpError WlgrIpBuild(WlgrIpProducer *producer,
                        const WlgrIpSourceFacts *facts,
                        const WlgrIpOps *ops)
{
    westlake_generation_identity_v2 candidate;
    uint8_t digest[WLGR_IP_INPUT_DIGEST_SIZE];
    uint64_t pid;
    uint64_t start;
    if (producer == NULL || facts == NULL || ops == NULL ||
        ops->read_current_process == NULL) {
        return WLGR_IP_INVALID_ARGUMENT;
    }
    if (!SourceFactsValid(facts)) {
        return WLGR_IP_SOURCE_FACTS_INVALID;
    }
    if (ReadCurrentProcess(ops, &pid, &start) != 0) {
        return WLGR_IP_CURRENT_PROCESS_UNAVAILABLE;
    }
    BuildIdentity(&candidate, facts, pid, start);
    if (!wlgr_v2_identity_valid(&candidate) ||
        InputDigest(&candidate, digest) != 0) {
        return WLGR_IP_IDENTITY_INVALID;
    }
    if (producer->state == WLGR_IP_STATE_READY) {
        if (!DigestEqual(producer)) {
            return WLGR_IP_REPLAY_CONFLICT;
        }
        return wlgr_v2_identity_equal(&producer->identity, &candidate) ?
            WLGR_IP_ALREADY_BUILT : WLGR_IP_REPLAY_CONFLICT;
    }
    if (producer->state != WLGR_IP_STATE_EMPTY && producer->state != 0U) {
        return WLGR_IP_REPLAY_CONFLICT;
    }
    (void)memset(producer, 0, sizeof(*producer));
    producer->abi_version = WLGR_IP_ABI_VERSION;
    producer->struct_size = (uint32_t)sizeof(*producer);
    producer->state = WLGR_IP_STATE_READY;
    producer->identity = candidate;
    (void)memcpy(producer->input_digest, digest, sizeof(digest));
    return WLGR_IP_OK;
}

WlgrIpError WlgrIpValidate(const WlgrIpProducer *producer,
                           const WlgrIpSourceFacts *facts,
                           const WlgrIpOps *ops)
{
    westlake_generation_identity_v2 candidate;
    uint64_t pid;
    uint64_t start;
    if (producer == NULL || facts == NULL || ops == NULL ||
        producer->abi_version != WLGR_IP_ABI_VERSION ||
        producer->struct_size != sizeof(*producer) ||
        producer->state != WLGR_IP_STATE_READY || !DigestEqual(producer) ||
        !SourceFactsValid(facts)) {
        return WLGR_IP_TAMPERED;
    }
    if (ReadCurrentProcess(ops, &pid, &start) != 0) {
        return WLGR_IP_CURRENT_PROCESS_UNAVAILABLE;
    }
    BuildIdentity(&candidate, facts, pid, start);
    if (!wlgr_v2_identity_valid(&candidate)) {
        return WLGR_IP_IDENTITY_INVALID;
    }
    return wlgr_v2_identity_equal(&producer->identity, &candidate) ?
        WLGR_IP_OK : WLGR_IP_TAMPERED;
}

const westlake_generation_identity_v2 *WlgrIpGetIdentity(
    const WlgrIpProducer *producer)
{
    return producer != NULL && producer->state == WLGR_IP_STATE_READY &&
        producer->abi_version == WLGR_IP_ABI_VERSION &&
        producer->struct_size == sizeof(*producer) && DigestEqual(producer) ?
        &producer->identity : NULL;
}
