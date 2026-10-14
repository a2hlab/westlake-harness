#include "sdk_rules.h"
#include <algorithm>
#include "android_character_data.h"
#include <limits>

namespace oh_adapter::application_attributes {
namespace {
using namespace manifest_facts;
using Verdict = SdkCompatibilityVerdictV2;
using Stage = SdkFailureStageV2;
constexpr int32_t DEVELOPMENT = 10000;
int32_t SignedBits(uint32_t bits)
{
    return bits <= INT32_MAX ? static_cast<int32_t>(bits)
        : -1 - static_cast<int32_t>(UINT32_MAX - bits);
}
bool Has(const SdkAttributeV2& attr) { return attr.present && attr.type != 0; }
struct SdkValue { int32_t number; std::optional<std::string> code; };
struct Normalized { SdkValue minimum{1, {}}, target{0, {}}; int32_t maximum = INT32_MAX; };
Normalized Normalize(const UsesSdkDeclarationV2& tag, bool apex)
{
    Normalized out;
    bool minAssigned = false;
    if (Has(tag.minimum)) {
        if (tag.minimum.type == 3) {
            out.minimum.code = tag.minimum.text;
            minAssigned = !tag.minimum.text.empty();
        } else { out.minimum.number = SignedBits(tag.minimum.bits); minAssigned = true; }
    }
    if (Has(tag.target)) {
        if (tag.target.type == 3) {
            out.target.code = tag.target.text;
            if (!minAssigned) out.minimum.code = out.target.code;
        } else out.target.number = SignedBits(tag.target.bits);
    } else out.target = out.minimum;
    if (apex && Has(tag.maximum)) out.maximum = SignedBits(tag.maximum.bits);
    return out;
}
bool Contains(const std::vector<std::string>& values, const std::string& value)
{ return std::find(values.begin(), values.end(), value) != values.end(); }
std::string WithoutFingerprint(const std::string& code) { return code.substr(0, code.find('.')); }
bool Matches(const SdkProfileV2& profile, const std::string& code)
{ return Contains(profile.activeCodenames, WithoutFingerprint(code)); }
// Decode the first Java UTF-16 unit from a valid UTF-8 character. The SDK
// helpers use charAt, so supplementary code points expose a surrogate, not Lu/Nd.
bool NextUnit(const std::string& text, size_t* offset, uint16_t* unit)
{
    if (*offset >= text.size()) return false;
    const uint8_t first = static_cast<uint8_t>(text[(*offset)++]);
    uint32_t cp = first;
    unsigned remaining = 0;
    uint32_t minimum = 0;
    if (first >= 0xc2 && first <= 0xdf) { cp = first & 0x1f; remaining = 1; minimum = 0x80; }
    else if (first >= 0xe0 && first <= 0xef) { cp = first & 0x0f; remaining = 2; minimum = 0x800; }
    else if (first >= 0xf0 && first <= 0xf4) { cp = first & 0x07; remaining = 3; minimum = 0x10000; }
    else if (first >= 0x80) return false;
    for (unsigned i = 0; i < remaining; ++i) {
        if (*offset >= text.size()) return false;
        const uint8_t next = static_cast<uint8_t>(text[(*offset)++]);
        if ((next & 0xc0) != 0x80) return false;
        cp = (cp << 6) | (next & 0x3f);
    }
    if (cp < minimum || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) return false;
    *unit = cp > 0xffff ? static_cast<uint16_t>(0xd800 + ((cp - 0x10000) >> 10))
        : static_cast<uint16_t>(cp);
    return true;
}
bool IsUppercaseFirstUnit(const std::string& text)
{
    size_t offset = 0;
    uint16_t unit;
    if (!NextUnit(text, &offset, &unit)) return false;
    for (const auto& range : android_character_data::UPPERCASE) {
        if (unit < range.first) return false;
        if (unit <= range.last) return true;
    }
    return false;
}
int Digit(uint16_t unit)
{
    for (const auto zero : android_character_data::DIGIT_ZERO)
        if (unit >= zero && unit <= zero + 9) return unit - zero;
    if (unit >= 'a' && unit <= 'z') return unit - 'a' + 10;
    if (unit >= 'A' && unit <= 'Z') return unit - 'A' + 10;
    if (unit >= 0xff41 && unit <= 0xff5a) return unit - 0xff41 + 10;
    if (unit >= 0xff21 && unit <= 0xff3a) return unit - 0xff21 + 10;
    return -1;
}
// Integer.parseInt: one optional sign, Character.digit(charAt(i)), int bounds.
bool ParseInt(const std::string& text, int base, int32_t* out)
{
    if (text.empty()) return false;
    const bool negative = text.front() == '-';
    size_t offset = (negative || text.front() == '+') ? 1 : 0;
    if (offset == text.size()) return false;
    const uint32_t limit = negative ? uint32_t{INT32_MAX} + 1U : INT32_MAX;
    uint32_t magnitude = 0;
    while (offset < text.size()) {
        uint16_t unit;
        if (!NextUnit(text, &offset, &unit)) return false;
        const int digit = Digit(unit);
        if (digit < 0 || digit >= base || magnitude > (limit - digit) / base) return false;
        magnitude = magnitude * base + digit;
    }
    *out = negative ? (magnitude == uint32_t{INT32_MAX} + 1U ? INT32_MIN : -static_cast<int32_t>(magnitude))
        : static_cast<int32_t>(magnitude);
    return true;
}
bool ApexAtMost(const SdkProfileV2& profile, const std::string& input, bool* invalid)
{
    if (input.empty()) { *invalid = true; return false; }
    if (IsUppercaseFirstUnit(input)) {
        const auto code = WithoutFingerprint(input);
        const bool known = Contains(profile.knownCodenames, code);
        if (profile.codename == "REL") {
            if (known) *invalid = true;
            return !known;
        }
        return !known || profile.codename == code;
    }
    int32_t version = 0;
    if (!ParseInt(input, 10, &version)) { *invalid = true; return false; }
    return profile.codename == "REL" ? profile.sdkVersion <= version : profile.sdkVersion < version;
}
SdkCompatibilityResultV2 Fail(Verdict verdict, Stage stage, const std::string& reason)
{ return {verdict, stage, reason, {}}; }
bool ExtensionInt(const SdkAttributeV2& attr, int32_t* out)
{
    *out = -1;
    if (!Has(attr)) return true;
    if (attr.type >= 0x10 && attr.type <= 0x1f) { *out = SignedBits(attr.bits); return true; }
    if (attr.type != 3) return false; // No unresolved resource is treated as an integer.
    std::string text = attr.text;
    if (text.empty()) return true;
    bool negative = text.front() == '-';
    if (negative) text.erase(0, 1);
    int base = 10;
    if (text.size() > 1 && text[0] == '0') {
        if (text[1] == 'x' || text[1] == 'X') { base = 16; text.erase(0, 2); }
        else { base = 8; text.erase(0, 1); }
    } else if (!text.empty() && text[0] == '#') { base = 16; text.erase(0, 1); }
    int32_t magnitude = 0;
    if (!ParseInt(text, base, &magnitude)) return false;
    // XmlUtils parses the magnitude before applying the sign.
    *out = negative ? (magnitude == INT32_MIN ? INT32_MIN : -magnitude) : magnitude;
    return true;
}
bool IsKnownExtension(int32_t sdk)
{ return sdk == 30 || sdk == 31 || sdk == 33 || sdk == 34 || sdk == 35 || sdk == 36 || sdk == 1000000; }
}

std::optional<manifest_facts::ResolvedSdkV2> ResolveNumericSdkDeclarations(
    const std::vector<manifest_facts::UsesSdkDeclarationV2>& declarations)
{
    ResolvedSdkV2 resolved;
    for (const auto& tag : declarations) {
        const auto values = Normalize(tag, false);
        if (values.minimum.code || values.target.code || !tag.extensions.empty()) return {};
        resolved.minimum = values.minimum.number;
        resolved.target = values.target.number;
    }
    return resolved;
}

manifest_facts::SdkCompatibilityResultV2 EvaluateSdkRequirements(
    const std::vector<manifest_facts::UsesSdkDeclarationV2>& declarations,
    const manifest_facts::SdkProfileV2& profile, bool apkInApex)
{
    if (profile.sdkVersion <= 0 || profile.codename.empty())
        return Fail(Verdict::PROFILE_UNAVAILABLE, Stage::PROFILE, "SDK profile is absent or incomplete");
    ResolvedSdkV2 resolved;
    for (const auto& tag : declarations) {
        const auto values = Normalize(tag, apkInApex);
        ResolvedSdkV2 current;
        current.target = values.target.number;
        if (values.target.code) {
            bool invalid = false;
            const bool allowed = apkInApex && ApexAtMost(profile, *values.target.code, &invalid);
            if (invalid || (!allowed && !Matches(profile, *values.target.code)))
                return Fail(Verdict::OLDER_SDK, Stage::TARGET, "Target SDK codename is incompatible");
            current.target = DEVELOPMENT;
        }
        current.minimum = values.minimum.number;
        if (values.minimum.code) {
            if (!Matches(profile, *values.minimum.code))
                return Fail(Verdict::OLDER_SDK, Stage::MINIMUM, "Minimum SDK codename is incompatible");
            current.minimum = DEVELOPMENT;
        } else if (current.minimum > profile.sdkVersion) {
            return Fail(Verdict::OLDER_SDK, Stage::MINIMUM, "Minimum SDK exceeds platform SDK");
        }
        current.maximum = values.maximum;
        if (apkInApex && current.maximum < profile.sdkVersion)
            return Fail(Verdict::NEWER_SDK, Stage::MAXIMUM, "Platform SDK exceeds APEX maximum SDK");
        for (const auto& ext : tag.extensions) {
            int32_t sdk, minimum;
            if (!ExtensionInt(ext.sdk, &sdk) || !ExtensionInt(ext.minimum, &minimum))
                return Fail(Verdict::PARSE_UNEXPECTED_EXCEPTION, Stage::EXTENSION,
                    "Extension SDK integer coercion failed");
            if (sdk < 30 || minimum < 0)
                return Fail(Verdict::MANIFEST_MALFORMED, Stage::EXTENSION, "Invalid extension SDK declaration");
            int32_t available = 0;
            if (IsKnownExtension(sdk)) {
                const auto found = profile.extensionVersions.find(sdk);
                if (found == profile.extensionVersions.end() || found->second < 0)
                    return Fail(Verdict::PROFILE_UNAVAILABLE, Stage::EXTENSION, "Extension version is unavailable");
                available = found->second;
            }
            if (minimum > available)
                return Fail(Verdict::OLDER_SDK, Stage::EXTENSION, "Required extension exceeds platform version");
            current.minimumExtensions[sdk] = minimum;
        }
        resolved = std::move(current);
    }
    return {Verdict::READY, Stage::NONE, "SDK requirements satisfied", std::move(resolved)};
}
} // namespace oh_adapter::application_attributes
