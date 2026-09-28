#pragma once

#include <array>
#include <binder/Enums.h>
#include <cstdint>
#include <string>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
enum class AlphaInterpretation : int32_t {
  COVERAGE = 0,
  MASK = 1,
};
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace hardware {
namespace graphics {
namespace common {
[[nodiscard]] static inline std::string toString(AlphaInterpretation val) {
  switch(val) {
  case AlphaInterpretation::COVERAGE:
    return "COVERAGE";
  case AlphaInterpretation::MASK:
    return "MASK";
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
constexpr inline std::array<::android::hardware::graphics::common::AlphaInterpretation, 2> enum_values<::android::hardware::graphics::common::AlphaInterpretation> = {
  ::android::hardware::graphics::common::AlphaInterpretation::COVERAGE,
  ::android::hardware::graphics::common::AlphaInterpretation::MASK,
};
#pragma clang diagnostic pop
}  // namespace internal
}  // namespace android
