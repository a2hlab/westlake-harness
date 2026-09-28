#pragma once
#include <cstdint>
typedef int32_t UErrorCode;
typedef struct UEnumeration UEnumeration;
#define U_ZERO_ERROR 0
#define U_FAILURE(e) (e)
#define ULOC_FULLNAME_CAPACITY 157

#ifdef __cplusplus
extern "C" {
#endif
int32_t uloc_canonicalize(const char*, char*, int32_t, UErrorCode*);
int32_t uloc_forLanguageTag(const char*, char*, int32_t, int32_t*, UErrorCode*);
int32_t uloc_toLanguageTag(const char*, char*, int32_t, int8_t, UErrorCode*);
const char* uloc_getDefault(void);
#ifdef __cplusplus
}
#endif
