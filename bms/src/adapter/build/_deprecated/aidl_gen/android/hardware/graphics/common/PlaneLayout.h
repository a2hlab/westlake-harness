#pragma once

#include <android/binder_to_string.h>
#include <android/hardware/graphics/common/PlaneLayoutComponent.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <cstdint>
#include <tuple>
#include <utils/String16.h>
#include <vector>

namespace android::hardware::graphics::common {
class PlaneLayoutComponent;
}  // namespace android::hardware::graphics::common
namespace android {
namespace hardware {
namespace graphics {
namespace common {
class PlaneLayout : public ::android::Parcelable {
public:
  ::std::vector<::android::hardware::graphics::common::PlaneLayoutComponent> components;
  int64_t offsetInBytes = 0L;
  int64_t sampleIncrementInBits = 0L;
  int64_t strideInBytes = 0L;
  int64_t widthInSamples = 0L;
  int64_t heightInSamples = 0L;
  int64_t totalSizeInBytes = 0L;
  int64_t horizontalSubsampling = 0L;
  int64_t verticalSubsampling = 0L;
  inline bool operator!=(const PlaneLayout& rhs) const {
    return std::tie(components, offsetInBytes, sampleIncrementInBits, strideInBytes, widthInSamples, heightInSamples, totalSizeInBytes, horizontalSubsampling, verticalSubsampling) != std::tie(rhs.components, rhs.offsetInBytes, rhs.sampleIncrementInBits, rhs.strideInBytes, rhs.widthInSamples, rhs.heightInSamples, rhs.totalSizeInBytes, rhs.horizontalSubsampling, rhs.verticalSubsampling);
  }
  inline bool operator<(const PlaneLayout& rhs) const {
    return std::tie(components, offsetInBytes, sampleIncrementInBits, strideInBytes, widthInSamples, heightInSamples, totalSizeInBytes, horizontalSubsampling, verticalSubsampling) < std::tie(rhs.components, rhs.offsetInBytes, rhs.sampleIncrementInBits, rhs.strideInBytes, rhs.widthInSamples, rhs.heightInSamples, rhs.totalSizeInBytes, rhs.horizontalSubsampling, rhs.verticalSubsampling);
  }
  inline bool operator<=(const PlaneLayout& rhs) const {
    return std::tie(components, offsetInBytes, sampleIncrementInBits, strideInBytes, widthInSamples, heightInSamples, totalSizeInBytes, horizontalSubsampling, verticalSubsampling) <= std::tie(rhs.components, rhs.offsetInBytes, rhs.sampleIncrementInBits, rhs.strideInBytes, rhs.widthInSamples, rhs.heightInSamples, rhs.totalSizeInBytes, rhs.horizontalSubsampling, rhs.verticalSubsampling);
  }
  inline bool operator==(const PlaneLayout& rhs) const {
    return std::tie(components, offsetInBytes, sampleIncrementInBits, strideInBytes, widthInSamples, heightInSamples, totalSizeInBytes, horizontalSubsampling, verticalSubsampling) == std::tie(rhs.components, rhs.offsetInBytes, rhs.sampleIncrementInBits, rhs.strideInBytes, rhs.widthInSamples, rhs.heightInSamples, rhs.totalSizeInBytes, rhs.horizontalSubsampling, rhs.verticalSubsampling);
  }
  inline bool operator>(const PlaneLayout& rhs) const {
    return std::tie(components, offsetInBytes, sampleIncrementInBits, strideInBytes, widthInSamples, heightInSamples, totalSizeInBytes, horizontalSubsampling, verticalSubsampling) > std::tie(rhs.components, rhs.offsetInBytes, rhs.sampleIncrementInBits, rhs.strideInBytes, rhs.widthInSamples, rhs.heightInSamples, rhs.totalSizeInBytes, rhs.horizontalSubsampling, rhs.verticalSubsampling);
  }
  inline bool operator>=(const PlaneLayout& rhs) const {
    return std::tie(components, offsetInBytes, sampleIncrementInBits, strideInBytes, widthInSamples, heightInSamples, totalSizeInBytes, horizontalSubsampling, verticalSubsampling) >= std::tie(rhs.components, rhs.offsetInBytes, rhs.sampleIncrementInBits, rhs.strideInBytes, rhs.widthInSamples, rhs.heightInSamples, rhs.totalSizeInBytes, rhs.horizontalSubsampling, rhs.verticalSubsampling);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.PlaneLayout");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "PlaneLayout{";
    os << "components: " << ::android::internal::ToString(components);
    os << ", offsetInBytes: " << ::android::internal::ToString(offsetInBytes);
    os << ", sampleIncrementInBits: " << ::android::internal::ToString(sampleIncrementInBits);
    os << ", strideInBytes: " << ::android::internal::ToString(strideInBytes);
    os << ", widthInSamples: " << ::android::internal::ToString(widthInSamples);
    os << ", heightInSamples: " << ::android::internal::ToString(heightInSamples);
    os << ", totalSizeInBytes: " << ::android::internal::ToString(totalSizeInBytes);
    os << ", horizontalSubsampling: " << ::android::internal::ToString(horizontalSubsampling);
    os << ", verticalSubsampling: " << ::android::internal::ToString(verticalSubsampling);
    os << "}";
    return os.str();
  }
};  // class PlaneLayout
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
