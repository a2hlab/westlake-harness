#pragma once
#include "utypes.h"
typedef int32_t UChar;
int32_t u_strlen(const UChar*);
int32_t u_strFromUTF8(UChar*, int32_t, int32_t*, const char*, int32_t, UErrorCode*);
