#pragma once

#include <array>
#include <binder/Enums.h>
#include <cstdint>
#include <string>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
enum class Compression : int64_t {
  NONE = 0L,
  DISPLAY_STREAM_COMPRESSION = 1L,
};
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace hardware {
namespace graphics {
namespace common {
[[nodiscard]] static inline std::string toString(Compression val) {
  switch(val) {
  case Compression::NONE:
    return "NONE";
  case Compression::DISPLAY_STREAM_COMPRESSION:
    return "DISPLAY_STREAM_COMPRESSION";
  default:
    return std::to_string(static_cast<int64_t>(val));
  }
}
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace internal {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wc++17-extensions"
template <>
constexpr inline std::array<::android::hardware::graphics::common::Compression, 2> enum_values<::android::hardware::graphics::common::Compression> = {
  ::android::hardware::graphics::common::Compression::NONE,
  ::android::hardware::graphics::common::Compression::DISPLAY_STREAM_COMPRESSION,
};
#pragma clang diagnostic pop
}  // namespace internal
}  // namespace android
