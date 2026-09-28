#pragma once

#include <array>
#include <binder/Enums.h>
#include <cstdint>
#include <string>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
enum class BlendMode : int32_t {
  INVALID = 0,
  NONE = 1,
  PREMULTIPLIED = 2,
  COVERAGE = 3,
};
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace hardware {
namespace graphics {
namespace common {
[[nodiscard]] static inline std::string toString(BlendMode val) {
  switch(val) {
  case BlendMode::INVALID:
    return "INVALID";
  case BlendMode::NONE:
    return "NONE";
  case BlendMode::PREMULTIPLIED:
    return "PREMULTIPLIED";
  case BlendMode::COVERAGE:
    return "COVERAGE";
  default:
    return std::to_string(static_cast<int32_t>(val));
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
constexpr inline std::array<::android::hardware::graphics::common::BlendMode, 4> enum_values<::android::hardware::graphics::common::BlendMode> = {
  ::android::hardware::graphics::common::BlendMode::INVALID,
  ::android::hardware::graphics::common::BlendMode::NONE,
  ::android::hardware::graphics::common::BlendMode::PREMULTIPLIED,
  ::android::hardware::graphics::common::BlendMode::COVERAGE,
};
#pragma clang diagnostic pop
}  // namespace internal
}  // namespace android
