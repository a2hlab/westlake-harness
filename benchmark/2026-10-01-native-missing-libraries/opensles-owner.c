#include "opensles-owner.h"
#include <stdatomic.h>

_Static_assert(sizeof(WlSlInterfaceId) == 16, "OpenSLES IID layout");
_Static_assert(sizeof(WlSlEngineOption) == 8, "OpenSLES engine option layout");

__attribute__((visibility("default"))) WlSlId SL_IID_ENGINE;
__attribute__((visibility("default"))) WlSlId SL_IID_VOLUME;
__attribute__((visibility("default"))) WlSlId SL_IID_PLAY;
__attribute__((visibility("default"))) WlSlId SL_IID_ANDROIDSIMPLEBUFFERQUEUE;
static const WlSlInterfaceId configuration = {
    0x89f6a7e0, 0xbeac, 0x11df, 0x8b5c, {0, 2, 0xa5, 0xd5, 0xc5, 0x1b}
};
__attribute__((visibility("default"))) WlSlId SL_IID_ANDROIDCONFIGURATION = &configuration;
static _Atomic(WlSlCreateEngine) bound_engine;
static atomic_flag binding = ATOMIC_FLAG_INIT;

__attribute__((visibility("default")))
int WestlakeBindOpenSlesOwnerV1(const WlSlOwnerV1 *owner) {
    if (!owner || owner->version != 1 || !owner->create_engine ||
        owner->create_engine == slCreateEngine || !owner->engine ||
        !owner->volume || !owner->play || !owner->buffer_queue) return 22;
    if (atomic_flag_test_and_set_explicit(&binding, memory_order_acquire)) return 16;
    WlSlCreateEngine previous = atomic_load_explicit(&bound_engine, memory_order_acquire);
    if (previous) {
        int result = previous == owner->create_engine && SL_IID_ENGINE == owner->engine &&
            SL_IID_VOLUME == owner->volume && SL_IID_PLAY == owner->play &&
            SL_IID_ANDROIDSIMPLEBUFFERQUEUE == owner->buffer_queue ? 0 : 17;
        atomic_flag_clear_explicit(&binding, memory_order_release);
        return result;
    }
    SL_IID_ENGINE = owner->engine;
    SL_IID_VOLUME = owner->volume;
    SL_IID_PLAY = owner->play;
    SL_IID_ANDROIDSIMPLEBUFFERQUEUE = owner->buffer_queue;
    atomic_store_explicit(&bound_engine, owner->create_engine, memory_order_release);
    atomic_flag_clear_explicit(&binding, memory_order_release);
    return 0;
}

__attribute__((visibility("default")))
uint32_t slCreateEngine(WlSlObject *engine, uint32_t option_count,
    const WlSlEngineOption *options, uint32_t interface_count,
    const WlSlId *interfaces, const uint32_t *required) {
    WlSlCreateEngine provider = atomic_load_explicit(&bound_engine, memory_order_acquire);
    if (!provider) {
        if (engine) *engine = 0;
        return 1;
    }
    return provider(engine, option_count, options, interface_count, interfaces, required);
}
