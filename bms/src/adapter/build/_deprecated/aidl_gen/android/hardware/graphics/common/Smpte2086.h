#pragma once

#include <android/binder_to_string.h>
#include <android/hardware/graphics/common/XyColor.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <tuple>
#include <utils/String16.h>

namespace android::hardware::graphics::common {
class XyColor;
}  // namespace android::hardware::graphics::common
namespace android {
namespace hardware {
namespace graphics {
namespace common {
class Smpte2086 : public ::android::Parcelable {
public:
  ::android::hardware::graphics::common::XyColor primaryRed;
  ::android::hardware::graphics::common::XyColor primaryGreen;
  ::android::hardware::graphics::common::XyColor primaryBlue;
  ::android::hardware::graphics::common::XyColor whitePoint;
  float maxLuminance = 0.000000f;
  float minLuminance = 0.000000f;
  inline bool operator!=(const Smpte2086& rhs) const {
    return std::tie(primaryRed, primaryGreen, primaryBlue, whitePoint, maxLuminance, minLuminance) != std::tie(rhs.primaryRed, rhs.primaryGreen, rhs.primaryBlue, rhs.whitePoint, rhs.maxLuminance, rhs.minLuminance);
  }
  inline bool operator<(const Smpte2086& rhs) const {
    return std::tie(primaryRed, primaryGreen, primaryBlue, whitePoint, maxLuminance, minLuminance) < std::tie(rhs.primaryRed, rhs.primaryGreen, rhs.primaryBlue, rhs.whitePoint, rhs.maxLuminance, rhs.minLuminance);
  }
  inline bool operator<=(const Smpte2086& rhs) const {
    return std::tie(primaryRed, primaryGreen, primaryBlue, whitePoint, maxLuminance, minLuminance) <= std::tie(rhs.primaryRed, rhs.primaryGreen, rhs.primaryBlue, rhs.whitePoint, rhs.maxLuminance, rhs.minLuminance);
  }
  inline bool operator==(const Smpte2086& rhs) const {
    return std::tie(primaryRed, primaryGreen, primaryBlue, whitePoint, maxLuminance, minLuminance) == std::tie(rhs.primaryRed, rhs.primaryGreen, rhs.primaryBlue, rhs.whitePoint, rhs.maxLuminance, rhs.minLuminance);
  }
  inline bool operator>(const Smpte2086& rhs) const {
    return std::tie(primaryRed, primaryGreen, primaryBlue, whitePoint, maxLuminance, minLuminance) > std::tie(rhs.primaryRed, rhs.primaryGreen, rhs.primaryBlue, rhs.whitePoint, rhs.maxLuminance, rhs.minLuminance);
  }
  inline bool operator>=(const Smpte2086& rhs) const {
    return std::tie(primaryRed, primaryGreen, primaryBlue, whitePoint, maxLuminance, minLuminance) >= std::tie(rhs.primaryRed, rhs.primaryGreen, rhs.primaryBlue, rhs.whitePoint, rhs.maxLuminance, rhs.minLuminance);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.Smpte2086");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "Smpte2086{";
    os << "primaryRed: " << ::android::internal::ToString(primaryRed);
    os << ", primaryGreen: " << ::android::internal::ToString(primaryGreen);
    os << ", primaryBlue: " << ::android::internal::ToString(primaryBlue);
    os << ", whitePoint: " << ::android::internal::ToString(whitePoint);
    os << ", maxLuminance: " << ::android::internal::ToString(maxLuminance);
    os << ", minLuminance: " << ::android::internal::ToString(minLuminance);
    os << "}";
    return os.str();
  }
};  // class Smpte2086
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
