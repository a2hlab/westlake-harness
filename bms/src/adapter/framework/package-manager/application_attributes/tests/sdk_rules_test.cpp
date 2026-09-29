#include "manifest_facts_v1.h"
#include "apk_manifest_parser.h"
#include "manifest_fixture.h"
#include <gtest/gtest.h>
#include <fcntl.h>
#include <unistd.h>
#include <filesystem>

namespace {
using namespace oh_adapter::manifest_facts;
using namespace oh_adapter::package_transaction;
using namespace manifest_fixture;
class ApkFixture {
public:
    explicit ApkFixture(const std::vector<uint8_t>& axml)
        : bytes_(MakeZip({{"AndroidManifest.xml", axml}}))
    {
        std::string pattern = (std::filesystem::temp_directory_path() / "spc11-XXXXXX").string();
        std::vector<char> name(pattern.begin(), pattern.end());
        name.push_back('\0');
        int fd = mkstemp(name.data());
        Require(fd >= 0, "fixture mkstemp");
        path_ = name.data();
        size_t offset = 0;
        while (offset < bytes_.size()) {
            const auto count = write(fd, bytes_.data() + offset, bytes_.size() - offset);
            if (count <= 0) { close(fd); throw std::runtime_error("fixture write"); }
            offset += static_cast<size_t>(count);
        }
        close(fd);
        fd_ = open(path_.c_str(), O_RDONLY);
        Require(fd_ >= 0, "fixture read-only open");
    }
    ~ApkFixture() { if (fd_ >= 0) close(fd_); if (!path_.empty()) unlink(path_.c_str()); }
    ApkFixture(const ApkFixture&) = delete;
    ApkFixture& operator=(const ApkFixture&) = delete;

    ManifestParseReceiptV1 ParseFacts(const std::optional<SdkProfileV2>& profile, bool apex) const
    {
        ManifestParseRequestV1 request;
        request.requestId = "spc11-parser";
        request.sdkProfile = profile;
        request.apkInApex = apex;
        request.artifactFd = fd_;
        request.byteLength = bytes_.size();
        request.artifactSha256 = Sha(bytes_);
        // This tier1 parser test supplies an owned read-only regular file.
        // Linux sealed-FD/install acceptance is a separate frozen criterion.
        request.requireLinuxSeals = false;
        ArtifactDescriptorV1 descriptor;
        descriptor.artifactId = "base";
        descriptor.role = ArtifactRole::BASE;
        descriptor.byteLength = request.byteLength;
        descriptor.sha256 = request.artifactSha256;
        request.artifactSet.artifacts.push_back(descriptor);
        request.artifactSet.artifactSetDigest = ComputeArtifactSetDigest(request.artifactSet);
        return ManifestFactsParserV1().Parse(request);
    }
    bool ParseFull(oh_adapter::ApkManifestParser::ManifestData& data) const
    { return oh_adapter::ApkManifestParser::Parse(path_, data); }
    std::string Digest() const { return Sha(bytes_); }
private:
    std::string path_;
    std::vector<uint8_t> bytes_;
    int fd_ = -1;
};

Attr Int(const std::string& name, int32_t value, uint8_t ns = 1)
{ return {name, 0x10, static_cast<uint32_t>(value), {}, ns}; }
Attr Code(const std::string& name, const std::string& value)
{ return {name, 0x03, 0, value}; }
struct Tag { std::vector<Attr> attrs; std::vector<std::vector<Attr>> extensions; };
std::vector<Attr> Ext(int32_t sdk, int32_t minimum)
{ return {Int("sdkVersion", sdk), Int("minExtensionVersion", minimum)}; }
SdkProfileV2 Release()
{
    return {36, "REL", {}, {"Q", "R", "S", "Sv2", "Tiramisu", "UpsideDownCake", "VanillaIceCream", "Baklava"},
        {{30, 3}, {31, 3}, {33, 3}, {34, 3}, {35, 3}, {36, 3}, {1000000, 3}}};
}
ManifestParseReceiptV1 Parse(const std::vector<Tag>& tags,
    std::optional<SdkProfileV2> profile = Release(), bool apex = false, bool lastAfterApp = false)
{
    std::vector<Node> nodes = {{"manifest", {{"package", 0x03, 0, "fixture.sdk", 0}}, false}};
    auto app = [&] { nodes.push_back({"application", {}, false}); nodes.push_back({"application", {}, true}); };
    for (size_t i = 0; i < tags.size(); ++i) {
        if (lastAfterApp && i + 1 == tags.size()) app();
        nodes.push_back({"uses-sdk", tags[i].attrs, false});
        for (const auto& ext : tags[i].extensions) {
            nodes.push_back({"extension-sdk", ext, false});
            nodes.push_back({"extension-sdk", {}, true});
        }
        nodes.push_back({"uses-sdk", {}, true});
    }
    if (!lastAfterApp || tags.empty()) app();
    nodes.push_back({"manifest", {}, true});
    return ApkFixture(MakeAxmlNodes(nodes)).ParseFacts(profile, apex);
}
void Ready(const ManifestParseReceiptV1& receipt, int32_t minimum, int32_t target,
    const std::map<int32_t, int32_t>& extensions = {}, int32_t maximum = INT32_MAX)
{
    ASSERT_TRUE(receipt.sdkCompatibility.has_value()) << "SPC11_SDK_RESULT_MISSING " << receipt.reason;
    ASSERT_EQ(receipt.sdkCompatibility->verdict, SdkCompatibilityVerdictV2::READY)
        << "SPC11_RESOLUTION_REJECTED " << receipt.sdkCompatibility->reason;
    ASSERT_TRUE(receipt.sdkCompatibility->resolved.has_value());
    const auto& sdk = *receipt.sdkCompatibility->resolved;
    EXPECT_EQ(sdk.minimum, minimum) << "SPC11_MIN_DEFAULT_OR_OVERWRITE";
    EXPECT_EQ(sdk.target, target) << "SPC11_TARGET_DEFAULT_OR_OVERWRITE";
    EXPECT_EQ(sdk.maximum, maximum);
    EXPECT_EQ(sdk.minimumExtensions, extensions) << "SPC11_EXTENSION_MAP_NOT_REPLACED";
    ASSERT_EQ(receipt.verdict, ManifestParseVerdict::PARSED);
    ASSERT_TRUE(receipt.facts.has_value());
    EXPECT_EQ(receipt.facts->minSdk, static_cast<uint32_t>(minimum));
    EXPECT_EQ(receipt.facts->targetSdk, static_cast<uint32_t>(target));
}
void Rejected(const ManifestParseReceiptV1& receipt, SdkCompatibilityVerdictV2 verdict,
    SdkFailureStageV2 stage)
{
    ASSERT_TRUE(receipt.sdkCompatibility.has_value()) << "SPC11_SDK_ERROR_DOMAIN_MISSING " << receipt.reason;
    EXPECT_EQ(receipt.sdkCompatibility->verdict, verdict) << "SPC11_WRONG_SDK_ERROR";
    EXPECT_EQ(receipt.sdkCompatibility->stage, stage) << "SPC11_WRONG_FAILURE_ORDER";
    EXPECT_FALSE(receipt.sdkCompatibility->resolved.has_value());
    EXPECT_FALSE(receipt.facts.has_value()) << "SPC11_REJECTED_FACTS_EXPOSED";
    EXPECT_NE(receipt.verdict, ManifestParseVerdict::PARSED);
}
TEST(SPC_11_Contract, DefaultsAndRepeats)
{
    // Original UsesSdkTest's eleven methods, in source order. These local fixtures
    // exercise the production parser; the unchanged original CTS remains tier3.
    Ready(Parse({}), 1, 0);
    Ready(Parse({{{}, {}}}), 1, 1);
    Ready(Parse({{{Int("targetSdkVersion", 29)}, {}}}), 1, 29);
    Ready(Parse({{{Int("minSdkVersion", 29)}, {}}}), 29, 29);
    Ready(Parse({{{Int("targetSdkVersion", 27, 0), Int("targetSdkVersion", 27)}, {Ext(30, 0)}},
        {{Int("targetSdkVersion", 29), Int("targetSdkVersion", 27, 0)}, {Ext(31, 0)}}}), 1, 29, {{31, 0}});
    Ready(Parse({{{Int("targetSdkVersion", 29)}, {Ext(30, 0)}},
        {{Int("targetSdkVersion", 27, 0)}, {}}}), 1, 1);
    Ready(Parse({{{Int("targetSdkVersion", 28)}, {}}, {{Int("targetSdkVersion", 29)}, {}}}), 1, 29);
    Ready(Parse({{{Int("minSdkVersion", 28)}, {}}, {{Int("minSdkVersion", 29)}, {}}}), 29, 29);
    Ready(Parse({{{}, {Ext(30, 0)}}, {{}, {Ext(31, 0)}}}), 1, 1, {{31, 0}});
    Ready(Parse({{{Int("minSdkVersion", 21)}, {Ext(30, 0)}}, {{Int("targetSdkVersion", 30)}, {}}}), 1, 30);
    Ready(Parse({{{Int("minSdkVersion", 29), Int("targetSdkVersion", 29)}, {Ext(30, 0)}},
        {{Int("minSdkVersion", 30), Int("targetSdkVersion", 30)}, {Ext(31, 0)}}}, Release(), false, true), 30, 30, {{31, 0}});
    Ready(Parse({{{Int("minSdkVersion", -1), Int("targetSdkVersion", 10001)}, {}}}), -1, 10001);
    Ready(Parse({{{Int("minSdkVersion", 34, 2), Int("targetSdkVersion", 34, 2)}, {}}}), 1, 1);
    Ready(Parse({{{{"minSdkVersion", 0x00, 0, {}}, {"targetSdkVersion", 0x00, 0, {}}}, {}}}), 1, 1);
    auto noProfile = Parse({}, std::nullopt);
    EXPECT_FALSE(noProfile.sdkCompatibility.has_value()) << "SPC11_NO_INVENTED_PROFILE";
    ASSERT_TRUE(noProfile.facts.has_value());
    EXPECT_EQ(noProfile.facts->minSdk, 1U);
    EXPECT_EQ(noProfile.facts->targetSdk, 0U);
}
TEST(SPC_11_Contract, CodenameAndExtensions)
{
    using V = SdkCompatibilityVerdictV2;
    using S = SdkFailureStageV2;
    auto preview = Release(); preview.codename = "Baklava"; preview.activeCodenames = {"Baklava"};
    Ready(Parse({{{Code("minSdkVersion", "Baklava.fingerprint")}, {}}}, preview), 10000, 10000);
    Ready(Parse({{{Code("targetSdkVersion", "Baklava")}, {}}}, preview), 10000, 10000);
    Ready(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", "Baklava")}, {}}}, preview), 23, 10000);
    Rejected(Parse({{{Code("targetSdkVersion", "Future")}, {}}}), V::OLDER_SDK, S::TARGET);
    Rejected(Parse({{{Int("minSdkVersion", 99), Code("targetSdkVersion", "Future")}, {Ext(29, 1)}}}), V::OLDER_SDK, S::TARGET);
    Rejected(Parse({{{Code("minSdkVersion", "Future"), Int("targetSdkVersion", 28)}, {}}}), V::OLDER_SDK, S::MINIMUM);
    Rejected(Parse({{{Int("minSdkVersion", 37)}, {}}, {{}, {}}}), V::OLDER_SDK, S::MINIMUM);
    Rejected(Parse({{{Code("minSdkVersion", "")}, {}}}), V::OLDER_SDK, S::TARGET);
    Ready(Parse({{{Int("maxSdkVersion", 1)}, {}}}), 1, 1);
    Rejected(Parse({{{Int("maxSdkVersion", 35)}, {Ext(29, 1)}}}, Release(), true), V::NEWER_SDK, S::MAXIMUM);
    Ready(Parse({{{Int("maxSdkVersion", 36)}, {}}}, Release(), true), 1, 1, {}, 36);
    Ready(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", "Future.fingerprint")}, {}}}, Release(), true), 23, 10000);
    Rejected(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", "Baklava")}, {}}}, Release(), true), V::OLDER_SDK, S::TARGET);
    Ready(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", "36")}, {}}}, Release(), true), 23, 10000);
    Rejected(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", "35")}, {}}}, Release(), true), V::OLDER_SDK, S::TARGET);
    Ready(Parse({{{}, {Ext(30, 2), Ext(30, 1), Ext(1000000, 3), Ext(999, 0)}}}), 1, 1, {{30, 1}, {999, 0}, {1000000, 3}});
    Rejected(Parse({{{}, {Ext(30, 4), Ext(30, 1)}}, {{}, {}}}), V::OLDER_SDK, S::EXTENSION);
    Rejected(Parse({{{}, {Ext(999, 1)}}}), V::OLDER_SDK, S::EXTENSION);
    Rejected(Parse({{{}, {Ext(29, 0)}}}), V::MANIFEST_MALFORMED, S::EXTENSION);
    Rejected(Parse({{{}, {Ext(30, -1)}}}), V::MANIFEST_MALFORMED, S::EXTENSION);
    Rejected(Parse({{{}, {{Int("sdkVersion", 30)}}}}), V::MANIFEST_MALFORMED, S::EXTENSION);
    Rejected(Parse({{{}, {{Int("minExtensionVersion", 0)}}}}), V::MANIFEST_MALFORMED, S::EXTENSION);
    Ready(Parse({{{}, {{Code("sdkVersion", "0x1e"), Code("minExtensionVersion", "02")}}}}), 1, 1, {{30, 2}});
    // Android Integer.parseInt accepts one sign and Unicode decimal digits.
    for (const auto& text : {"+-0", "0x+-0"}) {
        SCOPED_TRACE("SPC11_JAVA_INTEGER_SYNTAX");
        Rejected(Parse({{{}, {{Int("sdkVersion", 30), Code("minExtensionVersion", text)}}}}),
            V::PARSE_UNEXPECTED_EXCEPTION, S::EXTENSION);
    }
    Ready(Parse({{{}, {{Code("sdkVersion", "３０"), Code("minExtensionVersion", "٢")}}}}), 1, 1, {{30, 2}});
    {
        SCOPED_TRACE("SPC11_UNICODE_APEX_CODENAME");
        Ready(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", "Ωfuture.fp")}, {}}}, Release(), true), 23, 10000);
        Ready(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", "３６")}, {}}}, Release(), true), 23, 10000);
        // charAt(0) is a surrogate for supplementary letters. ICU u_isupper tests Lu,
        // not Unicode Other_Uppercase such as Roman numeral one (Nl).
        for (const auto& code : {"𐐀future", "Ⅰfuture", "ωfuture"})
            Rejected(Parse({{{Int("minSdkVersion", 23), Code("targetSdkVersion", code)}, {}}}, Release(), true), V::OLDER_SDK, S::TARGET);
    }
    auto missingExtension = Release(); missingExtension.extensionVersions.erase(30);
    Rejected(Parse({{{}, {Ext(30, 0)}}}, missingExtension), V::PROFILE_UNAVAILABLE, S::EXTENSION);
    Rejected(Parse({}, SdkProfileV2{}), V::PROFILE_UNAVAILABLE, S::PROFILE);
    Rejected(Parse({{{Code("targetSdkVersion", "Baklava")}, {}}}, std::nullopt), V::PROFILE_UNAVAILABLE, S::PROFILE);
}
} // namespace
