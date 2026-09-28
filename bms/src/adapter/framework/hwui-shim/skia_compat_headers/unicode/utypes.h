#pragma once
typedef int32_t UErrorCode;
#define U_ZERO_ERROR 0
#define U_FAILURE(e) (e)
#define U_SUCCESS(e) (!(e))
#define U_BUFFER_OVERFLOW_ERROR 15
