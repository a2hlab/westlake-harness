// fixtures_us1.c — US1 (spec.md P1) positive fixture: compliant fat-ABI
// arm64 il2cpp APK. See tasks.md T009.
//
// Builds on top of fixtures.h's make_base_fixture() (per fixtures.h's own
// guidance) rather than constructing an ApkFixture from scratch, and only
// overrides the fields spec.md P1 actually cares about.

#include "fixtures_us1.h"

#include <string.h>

ApkFixture make_us1_positive_fixture(void) {
    ApkFixture fixture = make_base_fixture();

    // Explicit about the dimensions spec.md P1 / research.md R1-R3 judge,
    // even though make_base_fixture() already defaults to a compliant
    // shape today — keep this scenario self-describing rather than
    // silently depending on the base fixture's defaults never changing.
    fixture.apk_count = 1;                        // R1: single-APK guard must pass
    fixture.abi_layout = ABI_LAYOUT_ARM64_FAT;     // R2: root lib/arm64-v8a/ + lib/armeabi-v7a/
    fixture.signature_scheme = SIG_V2_PLUS;        // R3: verified
    fixture.tampered_after_verify = 0;             // R3: no TOCTOU mismatch

    // T012 (US1 Acceptance Scenario 3): minimal synthetic manifest
    // metadata, not parsed from `content` — see install_plan.h's
    // ApkFixture.package_name/version_code doc comment for scope.
    strncpy(fixture.package_name, "com.hp2.fixture.us1positive", sizeof(fixture.package_name) - 1);
    fixture.package_name[sizeof(fixture.package_name) - 1] = '\0';
    fixture.version_code = 42;

    return fixture;
}
