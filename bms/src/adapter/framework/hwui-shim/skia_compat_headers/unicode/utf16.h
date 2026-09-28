#pragma once
#include <cstdint>
#define U16_NEXT(s, i, len, c) do { c = (s)[i]; ++(i); } while(0)
#define U16_PREV(s, start, i, c) do { --(i); c = (s)[i]; } while(0)
#define U16_LENGTH(c) ((c) > 0xFFFF ? 2 : 1)
#define U16_IS_LEAD(c) (((c) & 0xFC00) == 0xD800)
#define U16_IS_TRAIL(c) (((c) & 0xFC00) == 0xDC00)
#define U16_IS_SURROGATE(c) (((c) & 0xF800) == 0xD800)
