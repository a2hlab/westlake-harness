#pragma once

#include <array>
#include <binder/Enums.h>
#include <cstdint>
#include <string>

namespace android {
namespace hardware {
namespace graphics {
namespace common {
enum class Dataspace : int32_t {
  UNKNOWN = 0,
  ARBITRARY = 1,
  STANDARD_SHIFT = 16,
  STANDARD_MASK = 4128768,
  STANDARD_UNSPECIFIED = 0,
  STANDARD_BT709 = 65536,
  STANDARD_BT601_625 = 131072,
  STANDARD_BT601_625_UNADJUSTED = 196608,
  STANDARD_BT601_525 = 262144,
  STANDARD_BT601_525_UNADJUSTED = 327680,
  STANDARD_BT2020 = 393216,
  STANDARD_BT2020_CONSTANT_LUMINANCE = 458752,
  STANDARD_BT470M = 524288,
  STANDARD_FILM = 589824,
  STANDARD_DCI_P3 = 655360,
  STANDARD_ADOBE_RGB = 720896,
  TRANSFER_SHIFT = 22,
  TRANSFER_MASK = 130023424,
  TRANSFER_UNSPECIFIED = 0,
  TRANSFER_LINEAR = 4194304,
  TRANSFER_SRGB = 8388608,
  TRANSFER_SMPTE_170M = 12582912,
  TRANSFER_GAMMA2_2 = 16777216,
  TRANSFER_GAMMA2_6 = 20971520,
  TRANSFER_GAMMA2_8 = 25165824,
  TRANSFER_ST2084 = 29360128,
  TRANSFER_HLG = 33554432,
  RANGE_SHIFT = 27,
  RANGE_MASK = 939524096,
  RANGE_UNSPECIFIED = 0,
  RANGE_FULL = 134217728,
  RANGE_LIMITED = 268435456,
  RANGE_EXTENDED = 402653184,
  SRGB_LINEAR = 138477568,
  SCRGB_LINEAR = 406913024,
  SRGB = 142671872,
  SCRGB = 411107328,
  JFIF = 146931712,
  BT601_625 = 281149440,
  BT601_525 = 281280512,
  BT709 = 281083904,
  DCI_P3_LINEAR = 139067392,
  DCI_P3 = 155844608,
  DISPLAY_P3_LINEAR = 139067392,
  DISPLAY_P3 = 143261696,
  ADOBE_RGB = 151715840,
  BT2020_LINEAR = 138805248,
  BT2020 = 147193856,
  BT2020_PQ = 163971072,
  DEPTH = 4096,
  SENSOR = 4097,
  BT2020_ITU = 281411584,
  BT2020_ITU_PQ = 298188800,
  BT2020_ITU_HLG = 302383104,
  BT2020_HLG = 168165376,
  DISPLAY_BT2020 = 142999552,
  DYNAMIC_DEPTH = 4098,
  JPEG_APP_SEGMENTS = 4099,
  HEIF = 4100,
  JPEG_R = 4101,
  BT709_FULL_RANGE = 146866176,
};
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace hardware {
namespace graphics {
namespace common {
[[nodiscard]] static inline std::string toString(Dataspace val) {
  switch(val) {
  case Dataspace::UNKNOWN:
    return "UNKNOWN";
  case Dataspace::ARBITRARY:
    return "ARBITRARY";
  case Dataspace::STANDARD_SHIFT:
    return "STANDARD_SHIFT";
  case Dataspace::STANDARD_MASK:
    return "STANDARD_MASK";
  case Dataspace::STANDARD_BT709:
    return "STANDARD_BT709";
  case Dataspace::STANDARD_BT601_625:
    return "STANDARD_BT601_625";
  case Dataspace::STANDARD_BT601_625_UNADJUSTED:
    return "STANDARD_BT601_625_UNADJUSTED";
  case Dataspace::STANDARD_BT601_525:
    return "STANDARD_BT601_525";
  case Dataspace::STANDARD_BT601_525_UNADJUSTED:
    return "STANDARD_BT601_525_UNADJUSTED";
  case Dataspace::STANDARD_BT2020:
    return "STANDARD_BT2020";
  case Dataspace::STANDARD_BT2020_CONSTANT_LUMINANCE:
    return "STANDARD_BT2020_CONSTANT_LUMINANCE";
  case Dataspace::STANDARD_BT470M:
    return "STANDARD_BT470M";
  case Dataspace::STANDARD_FILM:
    return "STANDARD_FILM";
  case Dataspace::STANDARD_DCI_P3:
    return "STANDARD_DCI_P3";
  case Dataspace::STANDARD_ADOBE_RGB:
    return "STANDARD_ADOBE_RGB";
  case Dataspace::TRANSFER_SHIFT:
    return "TRANSFER_SHIFT";
  case Dataspace::TRANSFER_MASK:
    return "TRANSFER_MASK";
  case Dataspace::TRANSFER_LINEAR:
    return "TRANSFER_LINEAR";
  case Dataspace::TRANSFER_SRGB:
    return "TRANSFER_SRGB";
  case Dataspace::TRANSFER_SMPTE_170M:
    return "TRANSFER_SMPTE_170M";
  case Dataspace::TRANSFER_GAMMA2_2:
    return "TRANSFER_GAMMA2_2";
  case Dataspace::TRANSFER_GAMMA2_6:
    return "TRANSFER_GAMMA2_6";
  case Dataspace::TRANSFER_GAMMA2_8:
    return "TRANSFER_GAMMA2_8";
  case Dataspace::TRANSFER_ST2084:
    return "TRANSFER_ST2084";
  case Dataspace::TRANSFER_HLG:
    return "TRANSFER_HLG";
  case Dataspace::RANGE_SHIFT:
    return "RANGE_SHIFT";
  case Dataspace::RANGE_MASK:
    return "RANGE_MASK";
  case Dataspace::RANGE_FULL:
    return "RANGE_FULL";
  case Dataspace::RANGE_LIMITED:
    return "RANGE_LIMITED";
  case Dataspace::RANGE_EXTENDED:
    return "RANGE_EXTENDED";
  case Dataspace::SRGB_LINEAR:
    return "SRGB_LINEAR";
  case Dataspace::SCRGB_LINEAR:
    return "SCRGB_LINEAR";
  case Dataspace::SRGB:
    return "SRGB";
  case Dataspace::SCRGB:
    return "SCRGB";
  case Dataspace::JFIF:
    return "JFIF";
  case Dataspace::BT601_625:
    return "BT601_625";
  case Dataspace::BT601_525:
    return "BT601_525";
  case Dataspace::BT709:
    return "BT709";
  case Dataspace::DCI_P3_LINEAR:
    return "DCI_P3_LINEAR";
  case Dataspace::DCI_P3:
    return "DCI_P3";
  case Dataspace::DISPLAY_P3:
    return "DISPLAY_P3";
  case Dataspace::ADOBE_RGB:
    return "ADOBE_RGB";
  case Dataspace::BT2020_LINEAR:
    return "BT2020_LINEAR";
  case Dataspace::BT2020:
    return "BT2020";
  case Dataspace::BT2020_PQ:
    return "BT2020_PQ";
  case Dataspace::DEPTH:
    return "DEPTH";
  case Dataspace::SENSOR:
    return "SENSOR";
  case Dataspace::BT2020_ITU:
    return "BT2020_ITU";
  case Dataspace::BT2020_ITU_PQ:
    return "BT2020_ITU_PQ";
  case Dataspace::BT2020_ITU_HLG:
    return "BT2020_ITU_HLG";
  case Dataspace::BT2020_HLG:
    return "BT2020_HLG";
  case Dataspace::DISPLAY_BT2020:
    return "DISPLAY_BT2020";
  case Dataspace::DYNAMIC_DEPTH:
    return "DYNAMIC_DEPTH";
  case Dataspace::JPEG_APP_SEGMENTS:
    return "JPEG_APP_SEGMENTS";
  case Dataspace::HEIF:
    return "HEIF";
  case Dataspace::JPEG_R:
    return "JPEG_R";
  case Dataspace::BT709_FULL_RANGE:
    return "BT709_FULL_RANGE";
  default:
    return std::to_string(static_cast<int32_t>(val));
  }
}
}  // namespace common
}  // namespace graphics
}  // namespace hardware
}  // namespace android
namespace android {
namespace internal {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wc++17-extensions"
template <>
constexpr inline std::array<::android::hardware::graphics::common::Dataspace, 61> enum_values<::android::hardware::graphics::common::Dataspace> = {
  ::android::hardware::graphics::common::Dataspace::UNKNOWN,
  ::android::hardware::graphics::common::Dataspace::ARBITRARY,
  ::android::hardware::graphics::common::Dataspace::STANDARD_SHIFT,
  ::android::hardware::graphics::common::Dataspace::STANDARD_MASK,
  ::android::hardware::graphics::common::Dataspace::STANDARD_UNSPECIFIED,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT709,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT601_625,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT601_625_UNADJUSTED,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT601_525,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT601_525_UNADJUSTED,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT2020,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT2020_CONSTANT_LUMINANCE,
  ::android::hardware::graphics::common::Dataspace::STANDARD_BT470M,
  ::android::hardware::graphics::common::Dataspace::STANDARD_FILM,
  ::android::hardware::graphics::common::Dataspace::STANDARD_DCI_P3,
  ::android::hardware::graphics::common::Dataspace::STANDARD_ADOBE_RGB,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_SHIFT,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_MASK,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_UNSPECIFIED,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_LINEAR,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_SRGB,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_SMPTE_170M,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_GAMMA2_2,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_GAMMA2_6,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_GAMMA2_8,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_ST2084,
  ::android::hardware::graphics::common::Dataspace::TRANSFER_HLG,
  ::android::hardware::graphics::common::Dataspace::RANGE_SHIFT,
  ::android::hardware::graphics::common::Dataspace::RANGE_MASK,
  ::android::hardware::graphics::common::Dataspace::RANGE_UNSPECIFIED,
  ::android::hardware::graphics::common::Dataspace::RANGE_FULL,
  ::android::hardware::graphics::common::Dataspace::RANGE_LIMITED,
  ::android::hardware::graphics::common::Dataspace::RANGE_EXTENDED,
  ::android::hardware::graphics::common::Dataspace::SRGB_LINEAR,
  ::android::hardware::graphics::common::Dataspace::SCRGB_LINEAR,
  ::android::hardware::graphics::common::Dataspace::SRGB,
  ::android::hardware::graphics::common::Dataspace::SCRGB,
  ::android::hardware::graphics::common::Dataspace::JFIF,
  ::android::hardware::graphics::common::Dataspace::BT601_625,
  ::android::hardware::graphics::common::Dataspace::BT601_525,
  ::android::hardware::graphics::common::Dataspace::BT709,
  ::android::hardware::graphics::common::Dataspace::DCI_P3_LINEAR,
  ::android::hardware::graphics::common::Dataspace::DCI_P3,
  ::android::hardware::graphics::common::Dataspace::DISPLAY_P3_LINEAR,
  ::android::hardware::graphics::common::Dataspace::DISPLAY_P3,
  ::android::hardware::graphics::common::Dataspace::ADOBE_RGB,
  ::android::hardware::graphics::common::Dataspace::BT2020_LINEAR,
  ::android::hardware::graphics::common::Dataspace::BT2020,
  ::android::hardware::graphics::common::Dataspace::BT2020_PQ,
  ::android::hardware::graphics::common::Dataspace::DEPTH,
  ::android::hardware::graphics::common::Dataspace::SENSOR,
  ::android::hardware::graphics::common::Dataspace::BT2020_ITU,
  ::android::hardware::graphics::common::Dataspace::BT2020_ITU_PQ,
  ::android::hardware::graphics::common::Dataspace::BT2020_ITU_HLG,
  ::android::hardware::graphics::common::Dataspace::BT2020_HLG,
  ::android::hardware::graphics::common::Dataspace::DISPLAY_BT2020,
  ::android::hardware::graphics::common::Dataspace::DYNAMIC_DEPTH,
  ::android::hardware::graphics::common::Dataspace::JPEG_APP_SEGMENTS,
  ::android::hardware::graphics::common::Dataspace::HEIF,
  ::android::hardware::graphics::common::Dataspace::JPEG_R,
  ::android::hardware::graphics::common::Dataspace::BT709_FULL_RANGE,
};
#pragma clang diagnostic pop
}  // namespace internal
}  // namespace android
