#pragma once

#include <android/binder_to_string.h>
#include <android/hardware/graphics/common/BufferUsage.h>
#include <android/hardware/graphics/common/PixelFormat.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <cstdint>
#include <tuple>
#include <utils/String16.h>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
class HardwareBufferDescription : public ::android::Parcelable {
public:
  int32_t width = 0;
  int32_t height = 0;
  int32_t layers = 0;
  ::android::hardware::graphics::common::PixelFormat format = ::android::hardware::graphics::common::PixelFormat::UNSPECIFIED;
  ::android::hardware::graphics::common::BufferUsage usage = ::android::hardware::graphics::common::BufferUsage::CPU_READ_NEVER;
  int32_t stride = 0;
  inline bool operator!=(const HardwareBufferDescription& rhs) const {
    return std::tie(width, height, layers, format, usage, stride) != std::tie(rhs.width, rhs.height, rhs.layers, rhs.format, rhs.usage, rhs.stride);
  }
  inline bool operator<(const HardwareBufferDescription& rhs) const {
    return std::tie(width, height, layers, format, usage, stride) < std::tie(rhs.width, rhs.height, rhs.layers, rhs.format, rhs.usage, rhs.stride);
  }
  inline bool operator<=(const HardwareBufferDescription& rhs) const {
    return std::tie(width, height, layers, format, usage, stride) <= std::tie(rhs.width, rhs.height, rhs.layers, rhs.format, rhs.usage, rhs.stride);
  }
  inline bool operator==(const HardwareBufferDescription& rhs) const {
    return std::tie(width, height, layers, format, usage, stride) == std::tie(rhs.width, rhs.height, rhs.layers, rhs.format, rhs.usage, rhs.stride);
  }
  inline bool operator>(const HardwareBufferDescription& rhs) const {
    return std::tie(width, height, layers, format, usage, stride) > std::tie(rhs.width, rhs.height, rhs.layers, rhs.format, rhs.usage, rhs.stride);
  }
  inline bool operator>=(const HardwareBufferDescription& rhs) const {
    return std::tie(width, height, layers, format, usage, stride) >= std::tie(rhs.width, rhs.height, rhs.layers, rhs.format, rhs.usage, rhs.stride);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.HardwareBufferDescription");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "HardwareBufferDescription{";
    os << "width: " << ::android::internal::ToString(width);
    os << ", height: " << ::android::internal::ToString(height);
    os << ", layers: " << ::android::internal::ToString(layers);
    os << ", format: " << ::android::internal::ToString(format);
    os << ", usage: " << ::android::internal::ToString(usage);
    os << ", stride: " << ::android::internal::ToString(stride);
    os << "}";
    return os.str();
  }
};  // class HardwareBufferDescription
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
