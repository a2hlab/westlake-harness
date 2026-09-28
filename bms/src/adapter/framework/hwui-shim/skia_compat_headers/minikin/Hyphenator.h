#ifndef MINIKIN_HYPHENATOR_H_STUB
#define MINIKIN_HYPHENATOR_H_STUB
#include <cstdint>
namespace minikin {
enum class StartHyphenEdit : uint8_t {
    NO_EDIT = 0,
    INSERT_HYPHEN = 1,
    INSERT_ARMENIAN_HYPHEN = 2,
    INSERT_MAQAF = 3,
    INSERT_UCAS_HYPHEN = 4,
    INSERT_ZWJ_AND_HYPHEN = 5,
};
enum class EndHyphenEdit : uint8_t {
    NO_EDIT = 0,
    INSERT_HYPHEN = 1,
    INSERT_ARMENIAN_HYPHEN = 2,
    INSERT_MAQAF = 3,
    INSERT_UCAS_HYPHEN = 4,
    INSERT_ZWJ = 5,
    REPLACE_WITH_HYPHEN = 6,
    INSERT_HYPHEN_AT_NEXT_LINE = 7,
};
inline uint32_t packHyphenEdit(StartHyphenEdit start, EndHyphenEdit end) {
    return (uint32_t)(((uint8_t)start << 8) | (uint8_t)end);
}
inline StartHyphenEdit startHyphenEdit(uint32_t v) {
    return (StartHyphenEdit)((v >> 8) & 0xFF);
}
inline EndHyphenEdit endHyphenEdit(uint32_t v) {
    return (EndHyphenEdit)(v & 0xFF);
}
class Hyphenator {};
}
#endif
