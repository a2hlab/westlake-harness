#include <android/hardware/graphics/common/HdrConversionStrategy.h>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
::android::status_t HdrConversionStrategy::readFromParcel(const ::android::Parcel* _aidl_parcel) {
  ::android::status_t _aidl_ret_status;
  int32_t _aidl_tag;
  if ((_aidl_ret_status = _aidl_parcel->readInt32(&_aidl_tag)) != ::android::OK) return _aidl_ret_status;
  switch (static_cast<Tag>(_aidl_tag)) {
  case passthrough: {
    bool _aidl_value;
    if ((_aidl_ret_status = _aidl_parcel->readBool(&_aidl_value)) != ::android::OK) return _aidl_ret_status;
    if constexpr (std::is_trivially_copyable_v<bool>) {
      set<passthrough>(_aidl_value);
    } else {
      // NOLINTNEXTLINE(performance-move-const-arg)
      set<passthrough>(std::move(_aidl_value));
    }
    return ::android::OK; }
  case autoAllowedHdrTypes: {
    ::std::vector<::android::hardware::graphics::common::Hdr> _aidl_value;
    if ((_aidl_ret_status = _aidl_parcel->readEnumVector(&_aidl_value)) != ::android::OK) return _aidl_ret_status;
    if constexpr (std::is_trivially_copyable_v<::std::vector<::android::hardware::graphics::common::Hdr>>) {
      set<autoAllowedHdrTypes>(_aidl_value);
    } else {
      // NOLINTNEXTLINE(performance-move-const-arg)
      set<autoAllowedHdrTypes>(std::move(_aidl_value));
    }
    return ::android::OK; }
  case forceHdrConversion: {
    ::android::hardware::graphics::common::Hdr _aidl_value;
    if ((_aidl_ret_status = _aidl_parcel->readInt32(reinterpret_cast<int32_t *>(&_aidl_value))) != ::android::OK) return _aidl_ret_status;
    if constexpr (std::is_trivially_copyable_v<::android::hardware::graphics::common::Hdr>) {
      set<forceHdrConversion>(_aidl_value);
    } else {
      // NOLINTNEXTLINE(performance-move-const-arg)
      set<forceHdrConversion>(std::move(_aidl_value));
    }
    return ::android::OK; }
  }
  return ::android::BAD_VALUE;
}
::android::status_t HdrConversionStrategy::writeToParcel(::android::Parcel* _aidl_parcel) const {
  ::android::status_t _aidl_ret_status = _aidl_parcel->writeInt32(static_cast<int32_t>(getTag()));
  if (_aidl_ret_status != ::android::OK) return _aidl_ret_status;
  switch (getTag()) {
  case passthrough: return _aidl_parcel->writeBool(get<passthrough>());
  case autoAllowedHdrTypes: return _aidl_parcel->writeEnumVector(get<autoAllowedHdrTypes>());
  case forceHdrConversion: return _aidl_parcel->writeInt32(static_cast<int32_t>(get<forceHdrConversion>()));
  }
  __assert2(__FILE__, __LINE__, __PRETTY_FUNCTION__, "can't reach here");
}
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
