#pragma once
#include <vector>
#include <string>
#include <cstdint>
namespace android::shaders {
struct ShaderCacheEntry { std::vector<uint8_t> blob; };
struct ShaderCache {};
}
