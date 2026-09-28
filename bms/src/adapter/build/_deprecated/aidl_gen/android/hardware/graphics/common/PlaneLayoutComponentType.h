#pragma once

#include <array>
#include <binder/Enums.h>
#include <cstdint>
#include <string>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
enum class PlaneLayoutComponentType : int64_t {
  Y = 1L,
  CB = 2L,
  CR = 4L,
  R = 1024L,
  G = 2048L,
  B = 4096L,
  RAW = 1048576L,
  A = 1073741824L,
};
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace hardware {
namespace graphics {
namespace common {
[[nodiscard]] static inline std::string toString(PlaneLayoutComponentType val) {
  switch(val) {
  case PlaneLayoutComponentType::Y:
    return "Y";
  case PlaneLayoutComponentType::CB:
    return "CB";
  case PlaneLayoutComponentType::CR:
    return "CR";
  case PlaneLayoutComponentType::R:
    return "R";
  case PlaneLayoutComponentType::G:
    return "G";
  case PlaneLayoutComponentType::B:
    return "B";
  case PlaneLayoutComponentType::RAW:
    return "RAW";
  case PlaneLayoutComponentType::A:
    return "A";
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
constexpr inline std::array<::android::hardware::graphics::common::PlaneLayoutComponentType, 8> enum_values<::android::hardware::graphics::common::PlaneLayoutComponentType> = {
  ::android::hardware::graphics::common::PlaneLayoutComponentType::Y,
  ::android::hardware::graphics::common::PlaneLayoutComponentType::CB,
  ::android::hardware::graphics::common::PlaneLayoutComponentType::CR,
  ::android::hardware::graphics::common::PlaneLayoutComponentType::R,
  ::android::hardware::graphics::common::PlaneLayoutComponentType::G,
  ::android::hardware::graphics::common::PlaneLayoutComponentType::B,
  ::android::hardware::graphics::common::PlaneLayoutComponentType::RAW,
  ::android::hardware::graphics::common::PlaneLayoutComponentType::A,
};
#pragma clang diagnostic pop
}  // namespace internal
}  // namespace android
