#include "westlake_generation_identity_producer.h"

#include <stdio.h>
#include <string.h>

static uint64_t current_pid = UINT64_C(4242);
static uint64_t current_start = UINT64_C(777);

static int ReadCurrent(void *context, uint64_t *pid, uint64_t *start)
{
    (void)context;
    *pid = current_pid;
    *start = current_start;
    return 0;
}

static void Fill(uint8_t *bytes, size_t size, uint8_t value)
{
    memset(bytes, value, size);
}

static WlgrIpSourceFacts Facts(void)
{
    WlgrIpSourceFacts facts;
    memset(&facts, 0, sizeof(facts));
    facts.runtime_key.magic = WLGR_V2_RUNTIME_KEY_MAGIC;
    facts.runtime_key.abi_version = WLGR_V2_ABI_VERSION;
    facts.runtime_key.struct_size = WLGR_V2_RUNTIME_KEY_SIZE;
    facts.runtime_key.struct_alignment = WLGR_V2_REQUIRED_ALIGNMENT;
    facts.runtime_key.android_uid = 2000U;
    facts.runtime_key.launch_generation = UINT64_C(9);
    strcpy(facts.runtime_key.android_package, "com.example.app");
    strcpy(facts.runtime_key.android_process_name, "com.example.app");
    Fill(facts.boot_id, sizeof(facts.boot_id), 1U);
    Fill(facts.artifact_generation, sizeof(facts.artifact_generation), 2U);
    facts.policy_epoch = UINT64_C(3);
    Fill(facts.specialization_receipt_digest,
         sizeof(facts.specialization_receipt_digest), 4U);
    Fill(facts.artifact_manifest_digest,
         sizeof(facts.artifact_manifest_digest), 5U);
    Fill(facts.hook_schema_digest, sizeof(facts.hook_schema_digest), 6U);
    Fill(facts.request_nonce, sizeof(facts.request_nonce), 7U);
    return facts;
}

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "FAIL line=%d\n", __LINE__); return 1; } } while (0)

int main(void)
{
    WlgrIpSourceFacts facts = Facts();
    WlgrIpOps ops = { ReadCurrent, NULL };
    WlgrIpProducer producer;
    WlgrIpSourceFacts tampered;
    memset(&producer, 0, sizeof(producer));
    CHECK(WlgrIpBuild(&producer, &facts, &ops) == WLGR_IP_OK);
    CHECK(WlgrIpGetIdentity(&producer) != NULL);
    CHECK(WlgrIpValidate(&producer, &facts, &ops) == WLGR_IP_OK);
    CHECK(WlgrIpBuild(&producer, &facts, &ops) == WLGR_IP_ALREADY_BUILT);
    tampered = facts;
    tampered.artifact_generation[0] ^= 1U;
    CHECK(WlgrIpValidate(&producer, &tampered, &ops) == WLGR_IP_TAMPERED);
    producer.input_digest[0] ^= 1U;
    CHECK(WlgrIpGetIdentity(&producer) == NULL);
    producer.input_digest[0] ^= 1U;
    current_pid += 1U;
    CHECK(WlgrIpValidate(&producer, &facts, &ops) == WLGR_IP_TAMPERED);
    current_pid -= 1U;
    facts.request_nonce[0] = 0U;
    memset(facts.request_nonce + 1U, 0, sizeof(facts.request_nonce) - 1U);
    memset(&producer, 0, sizeof(producer));
    CHECK(WlgrIpBuild(&producer, &facts, &ops) ==
          WLGR_IP_SOURCE_FACTS_INVALID);
    printf("RESULT PASS tests=9\n");
    return 0;
}
