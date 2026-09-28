// fixtures.h — generic ApkFixture builder infrastructure for the HP-2
// install-plan host oracle.
//
// This file only provides GENERIC construction helpers (a sane default
// fixture + small mutation helpers). It intentionally does NOT define the
// specific US1 (compliant fat arm64) or US2 (tampered/multi-apk/AAB/empty
// native) fixtures — those are built on top of this in each user story's
// own fixtures_us1.c / fixtures_us2.c (T009 / T013), by a later phase.

#ifndef HP2_INSTALL_PLAN_TEST_FIXTURES_H
#define HP2_INSTALL_PLAN_TEST_FIXTURES_H

#include "install_plan.h"

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Returns a minimal, self-consistent "everything is fine" ApkFixture:
// apk_count=1, ABI_LAYOUT_ARM64_FAT, SIG_V2_PLUS, non-empty deterministic
// content, tampered_after_verify=0. US1/US2 fixture builders should start
// from this and override only the fields relevant to the scenario under
// test, rather than constructing an ApkFixture from scratch field-by-field.
ApkFixture make_base_fixture(void);

// Fills `fixture->content` with `len` deterministic (non-random,
// reproducible across runs — spec.md SC-003) pseudo-content bytes and sets
// `content_len`. `len` MUST be <= FIXTURE_MAX_BYTES. Used by
// make_base_fixture() and available to US1/US2 fixture builders that need
// a specific content size.
void fill_deterministic_content(unsigned char* buf, size_t len, unsigned char seed);

#ifdef __cplusplus
}
#endif

#endif // HP2_INSTALL_PLAN_TEST_FIXTURES_H
