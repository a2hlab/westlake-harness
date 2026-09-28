// fixtures.c — generic ApkFixture builder infrastructure. See fixtures.h.

#include "fixtures.h"

#include <string.h>

void fill_deterministic_content(unsigned char* buf, size_t len, unsigned char seed) {
    for (size_t i = 0; i < len; ++i) {
        // Simple deterministic LCG-ish byte fill: reproducible across runs
        // and across process invocations (no rand()/time() dependency),
        // which SC-003 (determinism) requires.
        buf[i] = (unsigned char)((seed + i * 31u + (i >> 3)) & 0xFFu);
    }
}

ApkFixture make_base_fixture(void) {
    ApkFixture fixture;
    memset(&fixture, 0, sizeof(fixture));

    fixture.apk_count = 1;
    fixture.bundle_path_count = 1;
    fixture.abi_layout = ABI_LAYOUT_ARM64_FAT;
    fixture.signature_scheme = SIG_V2_PLUS;

    fixture.content_len = 256;
    fill_deterministic_content(fixture.content, fixture.content_len, 0x5Au);

    fixture.tampered_after_verify = 0;
    fixture.tampered_content_len = 0;

    return fixture;
}
