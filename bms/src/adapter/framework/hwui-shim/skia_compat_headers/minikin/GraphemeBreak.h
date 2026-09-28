#pragma once
#include <cstddef>
#include <cstdint>
namespace minikin {
class GraphemeBreak {
public:
    static size_t getTextRunCursor(const float*, const uint16_t*, size_t, size_t, size_t, int) { return 0; }
    static bool isGraphemeBreak(const float*, const uint16_t*, size_t, size_t, size_t) { return true; }
};
}
