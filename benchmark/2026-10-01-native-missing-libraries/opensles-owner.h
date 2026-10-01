#ifndef WESTLAKE_OPENSLES_OWNER_V1_H
#define WESTLAKE_OPENSLES_OWNER_V1_H

#include <stdint.h>

typedef struct SLInterfaceID_ {
    uint32_t time_low;
    uint16_t time_mid;
    uint16_t time_hi_and_version;
    uint16_t clock_seq;
    uint8_t node[6];
} WlSlInterfaceId;
typedef const WlSlInterfaceId *WlSlId;
struct SLObjectItf_;
typedef const struct SLObjectItf_ *const *WlSlObject;
typedef struct SLEngineOption_ {
    uint32_t feature;
    uint32_t data;
} WlSlEngineOption;
typedef uint32_t (*WlSlCreateEngine)(WlSlObject *, uint32_t,
    const WlSlEngineOption *, uint32_t, const WlSlId *, const uint32_t *);
typedef struct WlSlOwnerV1 {
    uint32_t version;
    WlSlCreateEngine create_engine;
    WlSlId engine;
    WlSlId volume;
    WlSlId play;
    WlSlId buffer_queue;
} WlSlOwnerV1;
typedef int (*WlSlBindOwner)(const WlSlOwnerV1 *);

int WestlakeBindOpenSlesOwnerV1(const WlSlOwnerV1 *owner);
uint32_t slCreateEngine(WlSlObject *engine, uint32_t option_count,
    const WlSlEngineOption *options, uint32_t interface_count,
    const WlSlId *interfaces, const uint32_t *required);

#endif
