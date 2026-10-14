#ifndef OH_ADAPTER_MANIFEST_VERSION_PARSER_H
#define OH_ADAPTER_MANIFEST_VERSION_PARSER_H

#include "../../jni/axml_parser.h"
#include "../../manifest_facts/include/manifest_version_v2.h"

#include <limits>

namespace oh_adapter::application_attributes::manifest_parser {

// Called on the root of a full AXML parse, never on an unverified old record.
// Android r4 PackageImpl uses TypedArray.getInteger: null defaults to zero,
// the integer type range preserves all 32 bits, other unresolved types fail.
inline bool ReadVersionField(const AxmlParser& parser, uint32_t resourceId,
    manifest_facts::VersionFieldV2* output)
{
    using manifest_facts::VersionValueSourceV2;
    manifest_facts::VersionFieldV2 field;
    field.source = VersionValueSourceV2::DEFAULT;
    for (size_t index = 0; index < parser.getAttributeCount(); ++index) {
        // Match the framework styleable's identity, not a same-name attribute
        // from another namespace. AXML's resource map is already decoded.
        if (parser.getAttributeNameResID(index) != resourceId) continue;
        if (field.present) return false;
        field.present = true;
        ResValue value {};
        if (parser.getAttributeValue(index, &value) != 0) return false;
        if (value.dataType == ResValue::TYPE_NULL) continue;
        if (value.dataType < ResValue::TYPE_INT_DEC ||
            value.dataType > ResValue::TYPE_INT_COLOR_RGB4) return false;
        field.bits = value.data;
        field.source = VersionValueSourceV2::EXPLICIT;
    }
    *output = field;
    return true;
}

inline bool ReadVersion(const AxmlParser& parser,
    manifest_facts::ManifestVersionV2* output)
{
    manifest_facts::ManifestVersionV2 candidate;
    if (!ReadVersionField(parser, 0x01010576, &candidate.major) ||
        !ReadVersionField(parser, 0x0101021b, &candidate.minor)) return false;
    *output = candidate;
    return true;
}

inline int32_t LegacyMinorBits(uint32_t bits)
{
    const int64_t signedValue = static_cast<int64_t>(bits) -
        (bits > static_cast<uint32_t>(std::numeric_limits<int32_t>::max())
            ? INT64_C(4294967296) : INT64_C(0));
    return static_cast<int32_t>(signedValue);
}

}  // namespace oh_adapter::application_attributes::manifest_parser
#endif  // OH_ADAPTER_MANIFEST_VERSION_PARSER_H
