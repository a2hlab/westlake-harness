#pragma once
#include "MinikinFont.h"
#include <vector>
namespace minikin {
class LocaleList {
public:
    static uint32_t getId(const std::string&) { return 0; }
};
class LocaleListCache {
public:
    static uint32_t getId(const std::string&) { return 0; }
    static const LocaleList& getById(uint32_t) { static LocaleList l; return l; }
};
}
