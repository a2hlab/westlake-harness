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
class Cta861_3 : public ::android::Parcelable {
public:
  float maxContentLightLevel = 0.000000f;
  float maxFrameAverageLightLevel = 0.000000f;
  inline bool operator!=(const Cta861_3& rhs) const {
    return std::tie(maxContentLightLevel, maxFrameAverageLightLevel) != std::tie(rhs.maxContentLightLevel, rhs.maxFrameAverageLightLevel);
  }
  inline bool operator<(const Cta861_3& rhs) const {
    return std::tie(maxContentLightLevel, maxFrameAverageLightLevel) < std::tie(rhs.maxContentLightLevel, rhs.maxFrameAverageLightLevel);
  }
  inline bool operator<=(const Cta861_3& rhs) const {
    return std::tie(maxContentLightLevel, maxFrameAverageLightLevel) <= std::tie(rhs.maxContentLightLevel, rhs.maxFrameAverageLightLevel);
  }
  inline bool operator==(const Cta861_3& rhs) const {
    return std::tie(maxContentLightLevel, maxFrameAverageLightLevel) == std::tie(rhs.maxContentLightLevel, rhs.maxFrameAverageLightLevel);
  }
  inline bool operator>(const Cta861_3& rhs) const {
    return std::tie(maxContentLightLevel, maxFrameAverageLightLevel) > std::tie(rhs.maxContentLightLevel, rhs.maxFrameAverageLightLevel);
  }
  inline bool operator>=(const Cta861_3& rhs) const {
    return std::tie(maxContentLightLevel, maxFrameAverageLightLevel) >= std::tie(rhs.maxContentLightLevel, rhs.maxFrameAverageLightLevel);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.Cta861_3");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "Cta861_3{";
    os << "maxContentLightLevel: " << ::android::internal::ToString(maxContentLightLevel);
    os << ", maxFrameAverageLightLevel: " << ::android::internal::ToString(maxFrameAverageLightLevel);
    os << "}";
    return os.str();
  }
};  // class Cta861_3
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
