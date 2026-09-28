#ifndef WLAF_TEST_FIXTURE_SIGNING_H
#define WLAF_TEST_FIXTURE_SIGNING_H

#include "wlnc_aperture_fixture.h"

/*
 * Test-only typed seal used to exercise the permit-verifier boundary.  It is
 * deliberately not a production signature algorithm or trust root and must
 * never appear in libwestlake_native_compat.so or a product generation.
 */
void WLAF_TestFixtureSign(WlafFixturePermitV1 *permit);
int WLAF_TestFixtureVerify(const WlafFixturePermitV1 *permit);

#endif
