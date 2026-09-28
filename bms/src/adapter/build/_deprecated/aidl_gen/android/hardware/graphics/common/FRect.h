#pragma once

#include <android/binder_to_string.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <tuple>
#include <utils/String16.h>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
class FRect : public ::android::Parcelable {
public:
  float left = 0.000000f;
  float top = 0.000000f;
  float right = 0.000000f;
  float bottom = 0.000000f;
  inline bool operator!=(const FRect& rhs) const {
    return std::tie(left, top, right, bottom) != std::tie(rhs.left, rhs.top, rhs.right, rhs.bottom);
  }
  inline bool operator<(const FRect& rhs) const {
    return std::tie(left, top, right, bottom) < std::tie(rhs.left, rhs.top, rhs.right, rhs.bottom);
  }
  inline bool operator<=(const FRect& rhs) const {
    return std::tie(left, top, right, bottom) <= std::tie(rhs.left, rhs.top, rhs.right, rhs.bottom);
  }
  inline bool operator==(const FRect& rhs) const {
    return std::tie(left, top, right, bottom) == std::tie(rhs.left, rhs.top, rhs.right, rhs.bottom);
  }
  inline bool operator>(const FRect& rhs) const {
    return std::tie(left, top, right, bottom) > std::tie(rhs.left, rhs.top, rhs.right, rhs.bottom);
  }
  inline bool operator>=(const FRect& rhs) const {
    return std::tie(left, top, right, bottom) >= std::tie(rhs.left, rhs.top, rhs.right, rhs.bottom);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.FRect");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "FRect{";
    os << "left: " << ::android::internal::ToString(left);
    os << ", top: " << ::android::internal::ToString(top);
    os << ", right: " << ::android::internal::ToString(right);
    os << ", bottom: " << ::android::internal::ToString(bottom);
    os << "}";
    return os.str();
  }
};  // class FRect
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
