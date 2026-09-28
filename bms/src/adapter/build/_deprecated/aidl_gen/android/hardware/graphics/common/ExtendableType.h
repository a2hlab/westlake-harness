#pragma once

#include <android/binder_to_string.h>
#include <binder/Parcel.h>
#include <binder/Status.h>
#include <cstdint>
#include <string>
#include <tuple>
#include <utils/String16.h>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
class ExtendableType : public ::android::Parcelable {
public:
  ::std::string name;
  int64_t value = 0L;
  inline bool operator!=(const ExtendableType& rhs) const {
    return std::tie(name, value) != std::tie(rhs.name, rhs.value);
  }
  inline bool operator<(const ExtendableType& rhs) const {
    return std::tie(name, value) < std::tie(rhs.name, rhs.value);
  }
  inline bool operator<=(const ExtendableType& rhs) const {
    return std::tie(name, value) <= std::tie(rhs.name, rhs.value);
  }
  inline bool operator==(const ExtendableType& rhs) const {
    return std::tie(name, value) == std::tie(rhs.name, rhs.value);
  }
  inline bool operator>(const ExtendableType& rhs) const {
    return std::tie(name, value) > std::tie(rhs.name, rhs.value);
  }
  inline bool operator>=(const ExtendableType& rhs) const {
    return std::tie(name, value) >= std::tie(rhs.name, rhs.value);
  }

  ::android::Parcelable::Stability getStability() const override { return ::android::Parcelable::Stability::STABILITY_VINTF; }
  ::android::status_t readFromParcel(const ::android::Parcel* _aidl_parcel) final;
  ::android::status_t writeToParcel(::android::Parcel* _aidl_parcel) const final;
  static const ::android::String16& getParcelableDescriptor() {
    static const ::android::StaticString16 DESCRIPTOR (u"android.hardware.graphics.common.ExtendableType");
    return DESCRIPTOR;
  }
  inline std::string toString() const {
    std::ostringstream os;
    os << "ExtendableType{";
    os << "name: " << ::android::internal::ToString(name);
    os << ", value: " << ::android::internal::ToString(value);
    os << "}";
    return os.str();
  }
};  // class ExtendableType
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
