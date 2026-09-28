#ifndef WESTLAKE_NATIVE_COMPAT_INTERNAL_H
#define WESTLAKE_NATIVE_COMPAT_INTERNAL_H

#include "westlake_native_compat.h"

#if defined(WLNC_TESTING)
void WLNC_TestSetInheritedInitGate(uint32_t value);
uint32_t WLNC_TestGetInitGate(void);
#endif

#endif
