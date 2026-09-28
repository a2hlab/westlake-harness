#pragma once

#include <array>
#include <binder/Enums.h>
#include <cstdint>
#include <string>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
enum class ChromaSiting : int64_t {
  NONE = 0L,
  UNKNOWN = 1L,
  SITED_INTERSTITIAL = 2L,
  COSITED_HORIZONTAL = 3L,
};
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace hardware {
namespace graphics {
namespace common {
[[nodiscard]] static inline std::string toString(ChromaSiting val) {
  switch(val) {
  case ChromaSiting::NONE:
    return "NONE";
  case ChromaSiting::UNKNOWN:
    return "UNKNOWN";
  case ChromaSiting::SITED_INTERSTITIAL:
    return "SITED_INTERSTITIAL";
  case ChromaSiting::COSITED_HORIZONTAL:
    return "COSITED_HORIZONTAL";
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
constexpr inline std::array<::android::hardware::graphics::common::ChromaSiting, 4> enum_values<::android::hardware::graphics::common::ChromaSiting> = {
  ::android::hardware::graphics::common::ChromaSiting::NONE,
  ::android::hardware::graphics::common::ChromaSiting::UNKNOWN,
  ::android::hardware::graphics::common::ChromaSiting::SITED_INTERSTITIAL,
  ::android::hardware::graphics::common::ChromaSiting::COSITED_HORIZONTAL,
};
#pragma clang diagnostic pop
}  // namespace internal
}  // namespace android
