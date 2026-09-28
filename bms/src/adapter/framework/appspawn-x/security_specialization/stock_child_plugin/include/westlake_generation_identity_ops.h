#ifndef WESTLAKE_GENERATION_IDENTITY_OPS_H
#define WESTLAKE_GENERATION_IDENTITY_OPS_H
#include "westlake_generation_identity_facts.h"
#include "westlake_android_child_plugin.h"
#define WLGR_IF_STOCK_RECEIPT_CANONICAL_SIZE ((size_t)52)
int WlgrIfProductionReadBootId(void *, char *, size_t);
int WlgrIfProductionReadProcess(void *, uint64_t *, uint64_t *);
int WlgrIfProductionRandom(void *, uint8_t *, size_t);
typedef struct WlgrIfProductionContext {
    const WlgrIfChildRequest *child_request;
    const WlascStockStageReceiptV1 *stock_receipt;
    const WlgrIfGenerationMetadata *sealed_metadata;
    const WlgrIfHookContract *published_hook;
    const WlscplManifestV2 *build_manifest;
} WlgrIfProductionContext;
int WlgrIfProductionReadMetadata(void *, WlgrIfGenerationMetadata *);
int WlgrIfProductionReadReceipt(void *, WlgrIfSpecializationReceipt *);
int WlgrIfProductionReadHook(void *, WlgrIfHookContract *);
int WlgrIfProductionReadManifest(void *, const WlscplManifestV2 **);
int WlgrIfDigestStockReceipt(const WlascStockStageReceiptV1 *, uint8_t[32]);
int WlgrIfSerializeStockReceipt(const WlascStockStageReceiptV1 *,
                                uint8_t *, size_t);
int WlgrIfProduceHookSchemaDigest(uint8_t[32]);
int WlgrIfParentSeal(const WlgrIfGenerationMetadata *, WlgrIfGenerationMetadata *);
int WlgrIfChildReadSeal(const WlgrIfGenerationMetadata *, WlgrIfGenerationMetadata *);
int WlgrIfProductionContextInit(
    WlgrIfProductionContext *, const WlgrIfChildRequest *,
    const WlascStockStageReceiptV1 *, const WlgrIfGenerationMetadata *,
    const WlgrIfHookContract *);
int WlgrIfProductionOps(WlgrIfProductionContext *, WlgrIfOps *);
#endif
