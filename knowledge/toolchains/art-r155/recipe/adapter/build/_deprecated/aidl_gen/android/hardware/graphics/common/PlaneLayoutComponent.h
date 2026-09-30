#pragma once

#include <android/binder_to_string.h>
#include <android/hardware/graphics/common/ExtendableType.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <cstdint>
#include <tuple>
#include <utils/String16.h>

namespace android::hardware::graphics::common {
class ExtendableType;
}  // namespace android::hardware::graphics::common
namespace android {
namespace hardware {
namespace graphics {
namespace common {
class PlaneLayoutComponent : public ::android::Parcelable {
public:
  ::android::hardware::graphics::common::ExtendableType type;
  int64_t offsetInBits = 0L;
  int64_t sizeInBits = 0L;
  inline bool operator!=(const PlaneLayoutComponent& rhs) const {
    return std::tie(type, offsetInBits, sizeInBits) != std::tie(rhs.type, rhs.offsetInBits, rhs.sizeInBits);
  }
  inline bool operator<(const PlaneLayoutComponent& rhs) const {
    return std::tie(type, offsetInBits, sizeInBits) < std::tie(rhs.type, rhs.offsetInBits, rhs.sizeInBits);
  }
  inline bool operator<=(const PlaneLayoutComponent& rhs) const {
    return std::tie(type, offsetInBits, sizeInBits) <= std::tie(rhs.type, rhs.offsetInBits, rhs.sizeInBits);
  }
  inline bool operator==(const PlaneLayoutComponent& rhs) const {
    return std::tie(type, offsetInBits, sizeInBits) == std::tie(rhs.type, rhs.offsetInBits, rhs.sizeInBits);
  }
  inline bool operator>(const PlaneLayoutComponent& rhs) const {
    return std::tie(type, offsetInBits, sizeInBits) > std::tie(rhs.type, rhs.offsetInBits, rhs.sizeInBits);
  }
  inline bool operator>=(const PlaneLayoutComponent& rhs) const {
    return std::tie(type, offsetInBits, sizeInBits) >= std::tie(rhs.type, rhs.offsetInBits, rhs.sizeInBits);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.PlaneLayoutComponent");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "PlaneLayoutComponent{";
    os << "type: " << ::android::internal::ToString(type);
    os << ", offsetInBits: " << ::android::internal::ToString(offsetInBits);
    os << ", sizeInBits: " << ::android::internal::ToString(sizeInBits);
    os << "}";
    return os.str();
  }
};  // class PlaneLayoutComponent
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
