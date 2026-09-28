#pragma once

#include <array>
#include <binder/Enums.h>
#include <cstdint>
#include <string>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
enum class ColorTransform : int32_t {
  IDENTITY = 0,
  ARBITRARY_MATRIX = 1,
  VALUE_INVERSE = 2,
  GRAYSCALE = 3,
  CORRECT_PROTANOPIA = 4,
  CORRECT_DEUTERANOPIA = 5,
  CORRECT_TRITANOPIA = 6,
};
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace hardware {
namespace graphics {
namespace common {
[[nodiscard]] static inline std::string toString(ColorTransform val) {
  switch(val) {
  case ColorTransform::IDENTITY:
    return "IDENTITY";
  case ColorTransform::ARBITRARY_MATRIX:
    return "ARBITRARY_MATRIX";
  case ColorTransform::VALUE_INVERSE:
    return "VALUE_INVERSE";
  case ColorTransform::GRAYSCALE:
    return "GRAYSCALE";
  case ColorTransform::CORRECT_PROTANOPIA:
    return "CORRECT_PROTANOPIA";
  case ColorTransform::CORRECT_DEUTERANOPIA:
    return "CORRECT_DEUTERANOPIA";
  case ColorTransform::CORRECT_TRITANOPIA:
    return "CORRECT_TRITANOPIA";
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
constexpr inline std::array<::android::hardware::graphics::common::ColorTransform, 7> enum_values<::android::hardware::graphics::common::ColorTransform> = {
  ::android::hardware::graphics::common::ColorTransform::IDENTITY,
  ::android::hardware::graphics::common::ColorTransform::ARBITRARY_MATRIX,
  ::android::hardware::graphics::common::ColorTransform::VALUE_INVERSE,
  ::android::hardware::graphics::common::ColorTransform::GRAYSCALE,
  ::android::hardware::graphics::common::ColorTransform::CORRECT_PROTANOPIA,
  ::android::hardware::graphics::common::ColorTransform::CORRECT_DEUTERANOPIA,
  ::android::hardware::graphics::common::ColorTransform::CORRECT_TRITANOPIA,
};
#pragma clang diagnostic pop
}  // namespace internal
}  // namespace android
