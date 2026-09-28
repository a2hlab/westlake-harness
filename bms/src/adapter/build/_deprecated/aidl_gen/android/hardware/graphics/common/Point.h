#pragma once

#include <android/binder_to_string.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <cstdint>
#include <tuple>
#include <utils/String16.h>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
class Point : public ::android::Parcelable {
public:
  int32_t x = 0;
  int32_t y = 0;
  inline bool operator!=(const Point& rhs) const {
    return std::tie(x, y) != std::tie(rhs.x, rhs.y);
  }
  inline bool operator<(const Point& rhs) const {
    return std::tie(x, y) < std::tie(rhs.x, rhs.y);
  }
  inline bool operator<=(const Point& rhs) const {
    return std::tie(x, y) <= std::tie(rhs.x, rhs.y);
  }
  inline bool operator==(const Point& rhs) const {
    return std::tie(x, y) == std::tie(rhs.x, rhs.y);
  }
  inline bool operator>(const Point& rhs) const {
    return std::tie(x, y) > std::tie(rhs.x, rhs.y);
  }
  inline bool operator>=(const Point& rhs) const {
    return std::tie(x, y) >= std::tie(rhs.x, rhs.y);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.Point");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "Point{";
    os << "x: " << ::android::internal::ToString(x);
    os << ", y: " << ::android::internal::ToString(y);
    os << "}";
    return os.str();
  }
};  // class Point
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
