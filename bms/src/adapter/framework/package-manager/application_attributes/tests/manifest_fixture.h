#ifndef APPLICATION_ATTRIBUTES_MANIFEST_FIXTURE_H
#define APPLICATION_ATTRIBUTES_MANIFEST_FIXTURE_H

// Binary AXML/ZIP encoding helpers adapted from manifest_facts_host_test.cpp.
// These only produce input bytes; production parser decisions are never copied.
#include "sha256.h"
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include <zlib.h>

namespace manifest_fixture {
void Require(bool condition, const std::string& message)
{
    if (!condition) throw std::runtime_error(message);
}

void U16(std::vector<uint8_t>* out, uint16_t value)
{
    out->push_back(static_cast<uint8_t>(value));
    out->push_back(static_cast<uint8_t>(value >> 8));
}

void U32(std::vector<uint8_t>* out, uint32_t value)
{
    out->push_back(static_cast<uint8_t>(value));
    out->push_back(static_cast<uint8_t>(value >> 8));
    out->push_back(static_cast<uint8_t>(value >> 16));
    out->push_back(static_cast<uint8_t>(value >> 24));
}

void Patch32(std::vector<uint8_t>* out, size_t offset, uint32_t value)
{
    Require(offset + 4 <= out->size(), "Patch32 range");
    for (size_t index = 0; index < 4; ++index) {
        (*out)[offset + index] =
            static_cast<uint8_t>(value >> (index * 8));
    }
}

std::string Hex(const uint8_t* bytes, size_t length)
{
    static constexpr char DIGITS[] = "0123456789abcdef";
    std::string result;
    result.reserve(length * 2);
    for (size_t index = 0; index < length; ++index) {
        result.push_back(DIGITS[bytes[index] >> 4]);
        result.push_back(DIGITS[bytes[index] & 0xf]);
    }
    return result;
}

std::string Sha(const std::vector<uint8_t>& bytes)
{
    uint8_t digest[32];
    sha256(bytes.empty() ? nullptr : bytes.data(), bytes.size(), digest);
    return Hex(digest, sizeof(digest));
}


struct Attr {
    std::string name;
    uint8_t type = 0x10;
    uint32_t bits = 0;
    std::string text;
    // 0: unqualified, 1: Android, 2: another namespace.
    uint8_t ns = 1;
};
struct Node { std::string name; std::vector<Attr> attrs; bool end; };

std::vector<uint8_t> MakeAxmlNodes(const std::vector<Node>& nodes)
{
    std::vector<std::string> strings;
    std::map<std::string, uint32_t> refs;
    auto attrKey = [](const Attr& attr) {
        return std::to_string(attr.ns) + ":" + attr.name;
    };
    auto intern = [&](const std::string& value, const std::string& alias = "") {
        const auto& key = alias.empty() ? value : alias;
        auto found = refs.find(key);
        if (found != refs.end()) return found->second;
        const uint32_t ref = static_cast<uint32_t>(strings.size());
        strings.push_back(value);
        refs.emplace(key, ref);
        return ref;
    };
    for (const Node& node : nodes) {
        intern(node.name);
        for (const Attr& attr : node.attrs) {
            intern(attr.name, attrKey(attr));
            if (attr.type == 0x03) intern(attr.text);
        }
    }

    const auto androidUri = intern("http://schemas.android.com/apk/res/android");
    const auto foreignUri = intern("urn:spc03:foreign");
    const auto androidPrefix = intern("android");
    const auto foreignPrefix = intern("foreign");
    std::vector<uint32_t> resourceIds(strings.size(), 0);
    for (const auto& node : nodes) {
        for (const auto& attr : node.attrs) {
            if (attr.ns != 1) continue;
            uint32_t id = 0;
            if (attr.name == "versionCode") id = 0x0101021b;
            if (attr.name == "versionCodeMajor") id = 0x01010576;
            if (attr.name == "minSdkVersion") id = 0x0101020c;
            if (attr.name == "targetSdkVersion") id = 0x01010270;
            if (attr.name == "maxSdkVersion") id = 0x01010271;
            if (attr.name == "sdkVersion") id = 0x01010610;
            if (attr.name == "minExtensionVersion") id = 0x01010611;
            resourceIds.at(refs.at(attrKey(attr))) = id;
        }
    }

    std::vector<uint8_t> poolData;
    std::vector<uint32_t> offsets;
    for (const std::string& value : strings) {
        Require(value.size() < 128, "synthetic AXML string too long");
        offsets.push_back(static_cast<uint32_t>(poolData.size()));
        size_t utf16Units = 0;
        for (unsigned char byte : value) {
            if ((byte & 0xc0U) != 0x80U) ++utf16Units;
            if (byte >= 0xf0U) ++utf16Units;
        }
        poolData.push_back(static_cast<uint8_t>(utf16Units));
        poolData.push_back(static_cast<uint8_t>(value.size()));
        poolData.insert(poolData.end(), value.begin(), value.end());
        poolData.push_back(0);
    }
    while ((poolData.size() % 4) != 0) poolData.push_back(0);

    std::vector<uint8_t> document;
    U16(&document, 0x0003);
    U16(&document, 8);
    U32(&document, 0);

    const uint32_t poolSize =
        static_cast<uint32_t>(28 + offsets.size() * 4 + poolData.size());
    U16(&document, 0x0001);
    U16(&document, 28);
    U32(&document, poolSize);
    U32(&document, static_cast<uint32_t>(strings.size()));
    U32(&document, 0);
    U32(&document, 1U << 8);
    U32(&document, static_cast<uint32_t>(28 + offsets.size() * 4));
    U32(&document, 0);
    for (uint32_t offset : offsets) U32(&document, offset);
    document.insert(document.end(), poolData.begin(), poolData.end());

    // Attribute names are separate pool entries for separate namespaces.
    // This matches AAPT's resource map binding instead of local-name guessing.
    U16(&document, 0x0180);
    U16(&document, 8);
    U32(&document, static_cast<uint32_t>(8 + resourceIds.size() * 4));
    for (auto id : resourceIds) U32(&document, id);
    auto namespaceChunk = [&](uint16_t type, uint32_t prefix, uint32_t uri) {
        U16(&document, type); U16(&document, 16); U32(&document, 24);
        U32(&document, 1); U32(&document, 0xffffffffU);
        U32(&document, prefix); U32(&document, uri);
    };
    namespaceChunk(0x0100, androidPrefix, androidUri);
    namespaceChunk(0x0100, foreignPrefix, foreignUri);

    for (const Node& node : nodes) {
        if (!node.end) {
            const uint32_t chunkSize =
                static_cast<uint32_t>(36 + node.attrs.size() * 20);
            U16(&document, 0x0102);
            U16(&document, 16);
            U32(&document, chunkSize);
            U32(&document, 1);
            U32(&document, 0xffffffffU);
            U32(&document, 0xffffffffU);
            U32(&document, refs.at(node.name));
            U16(&document, 20);
            U16(&document, 20);
            U16(&document, static_cast<uint16_t>(node.attrs.size()));
            U16(&document, 0);
            U16(&document, 0);
            U16(&document, 0);
            for (const Attr& attr : node.attrs) {
                U32(&document, attr.ns == 1 ? androidUri :
                    (attr.ns == 2 ? foreignUri : 0xffffffffU));
                U32(&document, refs.at(attrKey(attr)));
                if (attr.type != 0x03) {
                    U32(&document, 0xffffffffU);
                } else {
                    U32(&document, refs.at(attr.text));
                }
                U16(&document, 8);
                document.push_back(0);
                document.push_back(attr.type);
                U32(&document, attr.type == 0x03 ? refs.at(attr.text) : attr.bits);
            }
        } else {
            U16(&document, 0x0103);
            U16(&document, 16);
            U32(&document, 24);
            U32(&document, 1);
            U32(&document, 0xffffffffU);
            U32(&document, 0xffffffffU);
            U32(&document, refs.at(node.name));
        }
    }
    namespaceChunk(0x0101, foreignPrefix, foreignUri);
    namespaceChunk(0x0101, androidPrefix, androidUri);
    Patch32(&document, 4, static_cast<uint32_t>(document.size()));
    return document;
}

std::vector<uint8_t> MakeAxml(std::vector<Attr> versions)
{
    versions.insert(versions.begin(), {"package", 0x03, 0, "org.example.version", 0});
    return MakeAxmlNodes({{"manifest", std::move(versions), false},
        {"application", {}, false}, {"application", {}, true}, {"manifest", {}, true}});
}

std::vector<uint8_t> MakeZip(
    const std::vector<std::pair<std::string, std::vector<uint8_t>>>& entries)
{
    struct Central {
        std::string name;
        uint32_t crc = 0;
        uint32_t size = 0;
        uint32_t offset = 0;
    };
    std::vector<uint8_t> archive;
    std::vector<Central> central;
    for (const auto& entry : entries) {
        Central record;
        record.name = entry.first;
        record.crc = crc32(0L, reinterpret_cast<const Bytef*>(
            entry.second.data()), entry.second.size());
        record.size = static_cast<uint32_t>(entry.second.size());
        record.offset = static_cast<uint32_t>(archive.size());
        U32(&archive, 0x04034b50);
        U16(&archive, 20);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U32(&archive, record.crc);
        U32(&archive, record.size);
        U32(&archive, record.size);
        U16(&archive, static_cast<uint16_t>(record.name.size()));
        U16(&archive, 0);
        archive.insert(archive.end(), record.name.begin(), record.name.end());
        archive.insert(archive.end(), entry.second.begin(), entry.second.end());
        central.push_back(std::move(record));
    }
    const uint32_t centralOffset = static_cast<uint32_t>(archive.size());
    for (const Central& record : central) {
        U32(&archive, 0x02014b50);
        U16(&archive, 20);
        U16(&archive, 20);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U32(&archive, record.crc);
        U32(&archive, record.size);
        U32(&archive, record.size);
        U16(&archive, static_cast<uint16_t>(record.name.size()));
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U32(&archive, 0);
        U32(&archive, record.offset);
        archive.insert(archive.end(), record.name.begin(), record.name.end());
    }
    const uint32_t centralSize =
        static_cast<uint32_t>(archive.size()) - centralOffset;
    U32(&archive, 0x06054b50);
    U16(&archive, 0);
    U16(&archive, 0);
    U16(&archive, static_cast<uint16_t>(central.size()));
    U16(&archive, static_cast<uint16_t>(central.size()));
    U32(&archive, centralSize);
    U32(&archive, centralOffset);
    U16(&archive, 0);
    return archive;
}


// Structural counterexamples adapted from the independent T02-F02 probe.
uint32_t FixtureRead32(const std::vector<uint8_t>& input, size_t offset)
{
    return static_cast<uint32_t>(input.at(offset)) |
        (static_cast<uint32_t>(input.at(offset + 1)) << 8) |
        (static_cast<uint32_t>(input.at(offset + 2)) << 16) |
        (static_cast<uint32_t>(input.at(offset + 3)) << 24);
}
std::vector<uint8_t> MakeAdditionalManifest(bool nested)
{
    auto input = MakeAxml({{"versionCodeMajor", 0x10, 7, {}},
        {"versionCode", 0x10, 11, {}}});
    std::vector<size_t> starts, ends;
    for (size_t offset = 8; offset < input.size();) {
        auto type = FixtureRead32(input, offset) & 0xffffU;
        if (type == 0x0102) starts.push_back(offset);
        if (type == 0x0103) ends.push_back(offset);
        offset += FixtureRead32(input, offset + 4);
    }
    Require(starts.size() == 2 && ends.size() == 2, "additional manifest fixture structure");
    std::vector<uint8_t> extra(input.begin() + starts.front(),
        input.begin() + starts.front() + FixtureRead32(input, starts.front() + 4));
    Patch32(&extra, 36 + 20 + 16, 99);
    Patch32(&extra, 36 + 40 + 16, 88);
    extra.insert(extra.end(), input.begin() + ends.back(),
        input.begin() + ends.back() + FixtureRead32(input, ends.back() + 4));
    const size_t insertion = ends.back() + (nested ? 0 : FixtureRead32(input, ends.back() + 4));
    input.insert(input.begin() + insertion, extra.begin(), extra.end());
    Patch32(&input, 4, static_cast<uint32_t>(input.size()));
    return input;
}

}  // namespace manifest_fixture
#endif
