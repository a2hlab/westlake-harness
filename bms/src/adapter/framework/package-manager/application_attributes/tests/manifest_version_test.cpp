#include "manifest_facts_v1.h"
#include "apk_manifest_parser.h"
#include "version_code.h"
#include "manifest_fixture.h"

#include <gtest/gtest.h>
#include <algorithm>
#include <fcntl.h>
#include <unistd.h>
#include <filesystem>
#include <fstream>

namespace {
using namespace oh_adapter::manifest_facts;
using namespace oh_adapter::package_transaction;
using namespace manifest_fixture;

class ApkFixture {
public:
    explicit ApkFixture(const std::vector<uint8_t>& axml)
        : bytes_(MakeZip({{"AndroidManifest.xml", axml}}))
    {
        std::string pattern = (std::filesystem::temp_directory_path() / "spc03-XXXXXX").string();
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

    ManifestParseReceiptV1 ParseFacts() const
    {
        ManifestParseRequestV1 request;
        request.requestId = "spc03-parser";
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

void ExpectField(const VersionFieldV2& field, uint32_t bits, bool present,
    VersionValueSourceV2 source)
{
    EXPECT_EQ(field.bits, bits) << "SPC03_VERSION_BITS_LOST";
    EXPECT_EQ(field.present, present) << "SPC03_VERSION_PRESENCE_LOST";
    EXPECT_EQ(field.source, source) << "SPC03_VERSION_PROVENANCE_MISSING";
}

TEST(SPC_03_Contract, ParsedProvenance)
{
    struct Case { std::vector<Attr> attrs; uint32_t major; uint32_t minor; bool majorPresent; bool minorPresent; };
    std::vector<Case> cases = {
        {{}, 0, 0, false, false},
        {{{"versionCode", 0x10, 17, {}}}, 0, 17, false, true},
        {{{"versionCodeMajor", 0x11, 3, {}}}, 3, 0, true, false},
    };
    for (uint32_t high : {0U, 0x7fffffffU, 0x80000000U, 0xffffffffU}) {
        for (uint32_t low : {0U, 0x7fffffffU, 0x80000000U, 0xffffffffU}) {
            cases.push_back({{{"versionCodeMajor", 0x11, high, {}},
                {"versionCode", 0x10, low, {}}}, high, low, true, true});
        }
    }
    // Same low bits with a high value that crosses the JSON double precision boundary.
    cases.push_back({{{"versionCodeMajor", 0x10, 2097152, {}},
        {"versionCode", 0x10, 1, {}}}, 2097152, 1, true, true});
    for (uint8_t ns : {uint8_t{0}, uint8_t{2}}) {
        cases.push_back({{{"versionCodeMajor", 0x10, 99, {}, ns},
            {"versionCode", 0x10, 88, {}, ns}}, 0, 0, false, false});
        for (bool reverse : {false, true}) {
            std::vector<Attr> attrs = {{"versionCodeMajor", 0x10, 99, {}, ns},
                {"versionCode", 0x10, 88, {}, ns},
                {"versionCodeMajor", 0x10, 7, {}}, {"versionCode", 0x10, 11, {}}};
            if (reverse) std::reverse(attrs.begin(), attrs.end());
            cases.push_back({std::move(attrs), 7, 11, true, true});
        }
    }
    for (const auto& value : cases) {
        SCOPED_TRACE(::testing::Message() << "major=" << value.major << " minor=" << value.minor);
        const auto axml = MakeAxml(value.attrs);
        ApkFixture apk(axml);
        const auto receipt = apk.ParseFacts();
        ASSERT_EQ(receipt.verdict, ManifestParseVerdict::PARSED)
            << "SPC03_ANDROID_ATTRIBUTE_IDENTITY " << receipt.reason;
        ASSERT_TRUE(receipt.facts.has_value());
        const auto majorSource = value.majorPresent ? VersionValueSourceV2::EXPLICIT : VersionValueSourceV2::DEFAULT;
        const auto minorSource = value.minorPresent ? VersionValueSourceV2::EXPLICIT : VersionValueSourceV2::DEFAULT;
        ExpectField(receipt.versionV2.major, value.major, value.majorPresent, majorSource);
        ExpectField(receipt.versionV2.minor, value.minor, value.minorPresent, minorSource);
        const std::string json = ManifestParseReceiptJson(receipt);
        const std::string pair = "\"versionV2\":{\"schemaVersion\":2,\"major\":\"" +
            std::to_string(value.major) + "\",\"minor\":\"" + std::to_string(value.minor) + "\"";
        EXPECT_NE(json.find(pair), std::string::npos) << "SPC03_CANONICAL_DECIMAL_PAIR_MISSING";
        for (const auto& field : {"versionCode", "versionCodeMajor"}) {
            const auto& sources = receipt.facts->provenance;
            auto source = std::find_if(sources.begin(), sources.end(), [&](const auto& item) { return item.field == field; });
            ASSERT_NE(source, sources.end()) << "SPC03_VERSION_SOURCE_IDENTITY_MISSING";
            EXPECT_EQ(source->artifactSha256, apk.Digest());
            EXPECT_EQ(source->manifestEntrySha256, Sha(axml));
            EXPECT_GT(source->manifestChunkOffset, 0U);
        }
        oh_adapter::ApkManifestParser::ManifestData full;
        ASSERT_TRUE(apk.ParseFull(full));
        ExpectField(full.versionV2.major, value.major, value.majorPresent, majorSource);
        ExpectField(full.versionV2.minor, value.minor, value.minorPresent, minorSource);
        EXPECT_EQ(static_cast<uint32_t>(full.versionCode), value.minor);
    }
    ManifestParseReceiptV1 unknown;
    unknown.verdict = ManifestParseVerdict::PARSED;
    unknown.facts.emplace();
    EXPECT_NE(ManifestParseReceiptJson(unknown).find("\"versionV2\":null"), std::string::npos)
        << "SPC03_UNKNOWN_IS_NOT_DEFAULT_ZERO";
}

TEST(SPC_03_Contract, InvalidManifest)
{
    // Android full parsing retains its first root; the canonical facts parser
    // keeps its existing stricter document validation. Neither may use the new root.
    for (bool nested : {true, false}) {
        SCOPED_TRACE(nested ? "nested manifest" : "second root manifest");
        ApkFixture apk(MakeAdditionalManifest(nested));
        const auto receipt = apk.ParseFacts();
        EXPECT_EQ(receipt.verdict, ManifestParseVerdict::DECLARATION_CONFLICT);
        EXPECT_FALSE(receipt.facts.has_value());
        oh_adapter::ApkManifestParser::ManifestData full;
        ASSERT_TRUE(apk.ParseFull(full)) << "SPC03_FULL_ROOT_SKIP_OR_STOP";
        EXPECT_EQ(full.versionV2.major.bits, 7U) << "SPC03_NONROOT_MAJOR_REPLACED_ROOT";
        EXPECT_EQ(full.versionV2.minor.bits, 11U) << "SPC03_NONROOT_MINOR_REPLACED_ROOT";
        EXPECT_EQ(full.versionCode, 11) << "SPC03_NONROOT_LEGACY_REPLACED_ROOT";
    }
    // A malformed value in an unrelated attribute is not an Android version error.
    for (uint8_t ns : {uint8_t{0}, uint8_t{2}}) {
        ApkFixture apk(MakeAxml({{"versionCode", 0x03, 0, "not-a-version", ns},
            {"versionCodeMajor", 0x04, 0x3f800000, {}, ns}}));
        auto receipt = apk.ParseFacts();
        EXPECT_EQ(receipt.verdict, ManifestParseVerdict::PARSED)
            << "SPC03_FOREIGN_VERSION_ATTRIBUTE_MUST_BE_IGNORED";
        oh_adapter::ApkManifestParser::ManifestData full;
        EXPECT_TRUE(apk.ParseFull(full)) << "SPC03_FULL_FOREIGN_ATTRIBUTE_MUST_BE_IGNORED";
    }
    std::vector<std::vector<uint8_t>> invalid;
    for (const auto& field : {"versionCode", "versionCodeMajor"}) {
        for (const auto& text : {"4294967296", "18446744073709551616", "7", "-1", "1.0"}) {
            invalid.push_back(MakeAxml({{field, 0x03, 0, text}}));
        }
        invalid.push_back(MakeAxml({{field, 0x04, 0x3f800000, {}}}));
        invalid.push_back(MakeAxml({{field, 0x01, 0x7f010001, {}}}));
        invalid.push_back(MakeAxml({{field, 0x10, 1, {}}, {field, 0x10, 2, {}}}));
    }
    auto corrupt = MakeAxml({{"versionCode", 0x10, 1, {}}});
    corrupt.resize(7);
    invalid.push_back(corrupt);
    for (size_t i = 0; i < invalid.size(); ++i) {
        SCOPED_TRACE(::testing::Message() << "invalid variant=" << i);
        ApkFixture apk(invalid[i]);
        auto receipt = apk.ParseFacts();
        EXPECT_NE(receipt.verdict, ManifestParseVerdict::PARSED) << "SPC03_INVALID_VERSION_ACCEPTED";
        EXPECT_FALSE(receipt.facts.has_value()) << "SPC03_REJECTED_FACTS_EXPOSED";
        oh_adapter::ApkManifestParser::ManifestData full;
        EXPECT_FALSE(apk.ParseFull(full)) << "SPC03_FULL_PARSER_INVALID_VERSION_ACCEPTED";
    }
}
}  // namespace
