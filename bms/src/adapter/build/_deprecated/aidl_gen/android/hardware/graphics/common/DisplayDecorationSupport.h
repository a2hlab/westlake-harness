#pragma once

#include <android/binder_to_string.h>
#include <android/hardware/graphics/common/AlphaInterpretation.h>
#include <android/hardware/graphics/common/PixelFormat.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <tuple>
#include <utils/String16.h>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
class DisplayDecorationSupport : public ::android::Parcelable {
public:
  ::android::hardware::graphics::common::PixelFormat format = ::android::hardware::graphics::common::PixelFormat(0);
  ::android::hardware::graphics::common::AlphaInterpretation alphaInterpretation = ::android::hardware::graphics::common::AlphaInterpretation(0);
  inline bool operator!=(const DisplayDecorationSupport& rhs) const {
    return std::tie(format, alphaInterpretation) != std::tie(rhs.format, rhs.alphaInterpretation);
  }
  inline bool operator<(const DisplayDecorationSupport& rhs) const {
    return std::tie(format, alphaInterpretation) < std::tie(rhs.format, rhs.alphaInterpretation);
  }
  inline bool operator<=(const DisplayDecorationSupport& rhs) const {
    return std::tie(format, alphaInterpretation) <= std::tie(rhs.format, rhs.alphaInterpretation);
  }
  inline bool operator==(const DisplayDecorationSupport& rhs) const {
    return std::tie(format, alphaInterpretation) == std::tie(rhs.format, rhs.alphaInterpretation);
  }
  inline bool operator>(const DisplayDecorationSupport& rhs) const {
    return std::tie(format, alphaInterpretation) > std::tie(rhs.format, rhs.alphaInterpretation);
  }
  inline bool operator>=(const DisplayDecorationSupport& rhs) const {
    return std::tie(format, alphaInterpretation) >= std::tie(rhs.format, rhs.alphaInterpretation);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.DisplayDecorationSupport");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "DisplayDecorationSupport{";
    os << "format: " << ::android::internal::ToString(format);
    os << ", alphaInterpretation: " << ::android::internal::ToString(alphaInterpretation);
    os << "}";
    return os.str();
  }
};  // class DisplayDecorationSupport
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
