#include "opensles-owner.h"
#include <assert.h>
#include <string.h>

extern WlSlId SL_IID_ENGINE, SL_IID_VOLUME, SL_IID_PLAY, SL_IID_ANDROIDSIMPLEBUFFERQUEUE;
static WlSlInterfaceId ids[4];
static const WlSlEngineOption *expected_options;
static const WlSlId *expected_interfaces;
static const uint32_t *expected_required;
static WlSlObject *expected_engine;
static unsigned calls;

static uint32_t backend(WlSlObject *engine, uint32_t option_count,
    const WlSlEngineOption *options, uint32_t interface_count,
    const WlSlId *interfaces, const uint32_t *required) {
    assert(engine == expected_engine && option_count == 2 && interface_count == 1);
    assert(options == expected_options && interfaces == expected_interfaces && required == expected_required);
    ++calls;
    return 0x12345678;
}

int main(int argc, char **argv) {
    assert(argc == 2);
    WlSlOwnerV1 owner = {1, backend, &ids[0], &ids[1], &ids[2], &ids[3]};
    WlSlObject engine = (WlSlObject)(uintptr_t)0x44;
    if (!strcmp(argv[1], "unbound")) {
        assert(slCreateEngine(&engine, 0, 0, 0, 0, 0) == 1 && !engine && !calls);
        assert(WestlakeBindOpenSlesOwnerV1(0) == 22);
        owner.buffer_queue = 0;
        assert(WestlakeBindOpenSlesOwnerV1(&owner) == 22 && !SL_IID_ENGINE);
        owner.buffer_queue = &ids[3];
        owner.version = 2;
        assert(WestlakeBindOpenSlesOwnerV1(&owner) == 22);
        owner.version = 1;
        owner.create_engine = slCreateEngine;
        assert(WestlakeBindOpenSlesOwnerV1(&owner) == 22);
        return 0;
    }
    assert(WestlakeBindOpenSlesOwnerV1(&owner) == 0);
    assert(SL_IID_ENGINE == &ids[0] && SL_IID_VOLUME == &ids[1] && SL_IID_PLAY == &ids[2]);
    assert(SL_IID_ANDROIDSIMPLEBUFFERQUEUE == &ids[3]);
    assert(WestlakeBindOpenSlesOwnerV1(&owner) == 0);
    WlSlEngineOption options[2] = {{1, 1}, {2, 0}};
    WlSlId interfaces[] = {&ids[0]};
    uint32_t required[] = {1};
    expected_options = options;
    expected_interfaces = interfaces;
    expected_required = required;
    expected_engine = &engine;
    assert(slCreateEngine(&engine, 2, options, 1, interfaces, required) == 0x12345678 && calls == 1);
    owner.play = &ids[0];
    assert(WestlakeBindOpenSlesOwnerV1(&owner) == 17 && SL_IID_PLAY == &ids[2]);
    return 0;
}
