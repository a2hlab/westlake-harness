/*
 * apk_signature_verifier.cpp
 *
 * Real APK Signature Scheme v2/v3 verification: chunked SHA-256/SHA-512
 * content digest (per the public APK Signing Block format) plus RSA-PSS,
 * RSA-PKCS1-v1.5 and ECDSA signature verification via OpenSSL, all against
 * a single caller-owned fd.
 */
#include "apk_signature_verifier.h"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cctype>
#include <cstring>
#include <map>
#include <set>
#include <sstream>
#include <vector>

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/pkcs7.h>
#include <openssl/rsa.h>
#include <openssl/sha.h>
#include <openssl/x509.h>
#include <unzip.h>

namespace oh_adapter {

namespace {

// ---- APK Signing Block constants (public format, source.android.com) ----
constexpr uint64_t kSigBlockMagicLo = 0x20676953204b5041ULL;  // "APK Sig "
constexpr uint64_t kSigBlockMagicHi = 0x3234206b636f6c42ULL;  // "Block 42"
constexpr uint32_t kV2BlockId = 0x7109871au;
constexpr uint32_t kV3BlockId = 0xf05368c0u;
constexpr uint32_t kV31BlockId = 0x1b93ad61u;  // matches apk_verify_result.cpp's accepted v3.1 id
constexpr uint32_t kRotationAttrId = 0x3ba06f8cu;  // PROOF_OF_ROTATION_ATTR_ID
constexpr uint32_t kRotationMinSdkAttrId = 0x559f8b02u;

constexpr uint32_t kZipEocdSignature = 0x06054b50u;
constexpr size_t kZipEocdMinSize = 22;
constexpr size_t kZipEocdMaxComment = 65535;

constexpr uint64_t kMaxApkBytes = 1024ull * 1024ull * 1024ull;  // 1 GiB hard cap
constexpr uint64_t kMinApkBytes = kZipEocdMinSize + 24;         // EOCD + sig-block footer

constexpr size_t kChunkSize = 1024ull * 1024ull;  // 1 MiB
constexpr uint8_t kChunkPrefixByte = 0xa5;
constexpr uint8_t kTopPrefixByte = 0x5a;

constexpr size_t kMaxSignerBlockBytes = 64ull * 1024ull * 1024ull;  // defensive cap
constexpr size_t kMaxCertBytes = 16 * 1024;
constexpr size_t kMaxSignersPerBlock = 16;
constexpr size_t kMaxV1EntryBytes = 256ull * 1024ull * 1024ull;

void SetErr(std::string* e, const std::string& v)
{
    if (e != nullptr) *e = v;
}

bool PReadAll(int fd, uint64_t offset, void* buf, size_t len)
{
    auto* p = static_cast<uint8_t*>(buf);
    size_t got = 0;
    while (got < len) {
        ssize_t n = pread(fd, p + got, len - got, static_cast<off_t>(offset + got));
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;
        got += static_cast<size_t>(n);
    }
    return true;
}

uint32_t ReadU32LE(const uint8_t* p)
{
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
        (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

uint64_t ReadU64LE(const uint8_t* p)
{
    return static_cast<uint64_t>(ReadU32LE(p)) | (static_cast<uint64_t>(ReadU32LE(p + 4)) << 32);
}

std::array<uint8_t, 4> LE32(uint32_t v)
{
    return {static_cast<uint8_t>(v), static_cast<uint8_t>(v >> 8),
            static_cast<uint8_t>(v >> 16), static_cast<uint8_t>(v >> 24)};
}

uint64_t NumChunks(uint64_t len)
{
    return len == 0 ? 0 : (len + kChunkSize - 1) / kChunkSize;
}

// Bounds-checked cursor over an in-memory buffer (signer/signed-data parsing).
class Cursor {
public:
    Cursor(const uint8_t* data, size_t size) : data_(data), size_(size), pos_(0) {}
    size_t Remaining() const { return size_ - pos_; }

    bool ReadU32(uint32_t* v)
    {
        if (Remaining() < 4) return false;
        *v = ReadU32LE(data_ + pos_);
        pos_ += 4;
        return true;
    }

    // Reads a u32 length prefix, returns a bounds-checked sub-view of exactly
    // that many bytes, and advances past it.
    bool ReadLenPrefixed(const uint8_t** outData, size_t* outLen)
    {
        uint32_t len = 0;
        if (!ReadU32(&len) || len > Remaining()) return false;
        *outData = data_ + pos_;
        *outLen = len;
        pos_ += len;
        return true;
    }

    bool AtEnd() const { return pos_ == size_; }

private:
    const uint8_t* data_;
    size_t size_;
    size_t pos_;
};

// ---- Find EOCD / APK Signing Block --------------------------------------

bool FindEocd(int fd, uint64_t fileSize, uint64_t* outEocdOffset, uint32_t* outCdOffset,
              uint32_t* outCdSize, std::string* error)
{
    if (fileSize < kZipEocdMinSize) {
        SetErr(error, "file too small to contain an EOCD record");
        return false;
    }
    const uint64_t searchWindow = std::min<uint64_t>(fileSize, kZipEocdMinSize + kZipEocdMaxComment);
    const uint64_t windowStart = fileSize - searchWindow;
    std::vector<uint8_t> tail(searchWindow);
    if (!PReadAll(fd, windowStart, tail.data(), tail.size())) {
        SetErr(error, "failed to read EOCD search window");
        return false;
    }
    for (size_t i = tail.size() - kZipEocdMinSize + 1; i-- > 0;) {
        if (ReadU32LE(&tail[i]) != kZipEocdSignature) continue;
        const uint16_t commentLen = static_cast<uint16_t>(tail[i + 20]) |
            (static_cast<uint16_t>(tail[i + 21]) << 8);
        const uint64_t eocdOffset = windowStart + i;
        if (eocdOffset + kZipEocdMinSize + commentLen != fileSize) continue;  // reject look-alikes
        *outEocdOffset = eocdOffset;
        *outCdSize = ReadU32LE(&tail[i + 12]);
        *outCdOffset = ReadU32LE(&tail[i + 16]);
        return true;
    }
    SetErr(error, "EOCD signature not found");
    return false;
}

// pairsBegin/pairsEnd bound the ID-value pair region inside the signing block
// (excludes the 8-byte outer size prefix and the trailing 24-byte footer).
bool FindSigningBlock(int fd, uint64_t cdOffset, uint64_t* outBlockOffset,
                      uint64_t* outPairsBegin, uint64_t* outPairsEnd, std::string* error)
{
    if (cdOffset < 24) {
        SetErr(error, "central directory offset too small for a signing block");
        return false;
    }
    uint8_t footer[24];
    if (!PReadAll(fd, cdOffset - 24, footer, sizeof(footer))) {
        SetErr(error, "failed to read signing-block footer");
        return false;
    }
    const uint64_t sizeRepeat = ReadU64LE(footer);
    const uint64_t magicLo = ReadU64LE(footer + 8);
    const uint64_t magicHi = ReadU64LE(footer + 16);
    if (magicLo != kSigBlockMagicLo || magicHi != kSigBlockMagicHi) {
        SetErr(error, "APK Signing Block not present (unsigned or v1-only)");
        return false;
    }
    if (sizeRepeat < 24 || sizeRepeat > cdOffset - 8) {
        SetErr(error, "malformed signing-block footer size");
        return false;
    }
    const uint64_t blockOffset = cdOffset - 8 - sizeRepeat;
    uint8_t sizePrefixBuf[8];
    if (!PReadAll(fd, blockOffset, sizePrefixBuf, sizeof(sizePrefixBuf))) {
        SetErr(error, "failed to read signing-block size prefix");
        return false;
    }
    const uint64_t sizePrefix = ReadU64LE(sizePrefixBuf);
    if (sizePrefix != sizeRepeat) {
        SetErr(error, "signing-block size prefix/footer mismatch");
        return false;
    }
    *outBlockOffset = blockOffset;
    *outPairsBegin = blockOffset + 8;
    *outPairsEnd = blockOffset + 8 + sizeRepeat - 24;
    return true;
}

// Reads every ID-value pair, rejecting any framing error or duplicate ID.
// On success, `outValues` maps blockId -> (fileOffset, length) of its value.
bool ReadIdValuePairs(int fd, uint64_t pairsBegin, uint64_t pairsEnd,
                      std::vector<std::pair<uint32_t, std::pair<uint64_t, uint64_t>>>* outValues,
                      std::string* error)
{
    std::set<uint32_t> seenIds;
    uint64_t offset = pairsBegin;
    while (offset != pairsEnd) {
        if (offset + 12 > pairsEnd) {
            SetErr(error, "truncated id-value pair header");
            return false;
        }
        uint8_t header[12];
        if (!PReadAll(fd, offset, header, sizeof(header))) {
            SetErr(error, "failed to read id-value pair header");
            return false;
        }
        const uint64_t pairLen = ReadU64LE(header);
        const uint32_t id = ReadU32LE(header + 8);
        if (pairLen < 4 || offset + 8 + pairLen > pairsEnd) {
            SetErr(error, "malformed or duplicate-overlapping id-value pair framing");
            return false;
        }
        if (!seenIds.insert(id).second) {
            SetErr(error, "duplicate block ID in APK Signing Block");
            return false;
        }
        const uint64_t valueLen = pairLen - 4;
        if (valueLen > kMaxSignerBlockBytes) {
            SetErr(error, "id-value pair exceeds defensive size cap");
            return false;
        }
        outValues->push_back({id, {offset + 12, valueLen}});
        offset += 8 + pairLen;
    }
    return true;
}

// ---- Content digest: chunked SHA-256/SHA-512 over the three sections ----

bool HashChunksFromFd(int fd, uint64_t offset, uint64_t len, const EVP_MD* md,
                      std::vector<uint8_t>* chunkDigests, std::string* error)
{
    std::vector<uint8_t> buf(kChunkSize);
    uint64_t remaining = len;
    uint64_t cur = offset;
    while (remaining > 0) {
        const size_t want = static_cast<size_t>(std::min<uint64_t>(kChunkSize, remaining));
        if (!PReadAll(fd, cur, buf.data(), want)) {
            SetErr(error, "failed to read content-digest section from fd");
            return false;
        }
        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        std::array<uint8_t, EVP_MAX_MD_SIZE> out{};
        unsigned int outLen = 0;
        const auto lenLe = LE32(static_cast<uint32_t>(want));
        const bool ok = ctx != nullptr &&
            EVP_DigestInit_ex(ctx, md, nullptr) == 1 &&
            EVP_DigestUpdate(ctx, &kChunkPrefixByte, 1) == 1 &&
            EVP_DigestUpdate(ctx, lenLe.data(), 4) == 1 &&
            EVP_DigestUpdate(ctx, buf.data(), want) == 1 &&
            EVP_DigestFinal_ex(ctx, out.data(), &outLen) == 1;
        EVP_MD_CTX_free(ctx);
        if (!ok) {
            SetErr(error, "chunk digest computation failed");
            return false;
        }
        chunkDigests->insert(chunkDigests->end(), out.begin(), out.begin() + outLen);
        cur += want;
        remaining -= want;
    }
    return true;
}

bool HashChunksFromBuffer(const std::vector<uint8_t>& buffer, const EVP_MD* md,
                          std::vector<uint8_t>* chunkDigests, std::string* error)
{
    size_t remaining = buffer.size();
    size_t cur = 0;
    while (remaining > 0) {
        const size_t want = std::min(kChunkSize, remaining);
        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        std::array<uint8_t, EVP_MAX_MD_SIZE> out{};
        unsigned int outLen = 0;
        const auto lenLe = LE32(static_cast<uint32_t>(want));
        const bool ok = ctx != nullptr &&
            EVP_DigestInit_ex(ctx, md, nullptr) == 1 &&
            EVP_DigestUpdate(ctx, &kChunkPrefixByte, 1) == 1 &&
            EVP_DigestUpdate(ctx, lenLe.data(), 4) == 1 &&
            EVP_DigestUpdate(ctx, buffer.data() + cur, want) == 1 &&
            EVP_DigestFinal_ex(ctx, out.data(), &outLen) == 1;
        EVP_MD_CTX_free(ctx);
        if (!ok) {
            SetErr(error, "chunk digest computation failed");
            return false;
        }
        chunkDigests->insert(chunkDigests->end(), out.begin(), out.begin() + outLen);
        cur += want;
        remaining -= want;
    }
    return true;
}

// Computes the APK v2/v3 content digest over sections A (contents before the
// signing block), B (central directory) and C (EOCD, with the "offset of
// start of central directory" field patched to pretend the signing block
// does not exist), using digest algorithm `md`.
bool ComputeContentDigest(int fd, uint64_t sigBlockOffset, uint64_t cdOffset, uint32_t cdSize,
                          uint64_t eocdOffset, uint64_t fileSize, const EVP_MD* md,
                          std::array<uint8_t, EVP_MAX_MD_SIZE>* outDigest, unsigned int* outLen,
                          std::string* error)
{
    std::vector<uint8_t> chunkDigests;
    uint64_t chunkCount = 0;

    if (!HashChunksFromFd(fd, 0, sigBlockOffset, md, &chunkDigests, error)) return false;
    chunkCount += NumChunks(sigBlockOffset);

    if (!HashChunksFromFd(fd, cdOffset, cdSize, md, &chunkDigests, error)) return false;
    chunkCount += NumChunks(cdSize);

    std::vector<uint8_t> eocd(fileSize - eocdOffset);
    if (!PReadAll(fd, eocdOffset, eocd.data(), eocd.size())) {
        SetErr(error, "failed to read EOCD for content digest");
        return false;
    }
    const auto patched = LE32(static_cast<uint32_t>(sigBlockOffset));
    std::memcpy(eocd.data() + 16, patched.data(), 4);
    if (!HashChunksFromBuffer(eocd, md, &chunkDigests, error)) return false;
    chunkCount += NumChunks(eocd.size());

    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    const auto countLe = LE32(static_cast<uint32_t>(chunkCount));
    const bool ok = ctx != nullptr &&
        EVP_DigestInit_ex(ctx, md, nullptr) == 1 &&
        EVP_DigestUpdate(ctx, &kTopPrefixByte, 1) == 1 &&
        EVP_DigestUpdate(ctx, countLe.data(), 4) == 1 &&
        EVP_DigestUpdate(ctx, chunkDigests.data(), chunkDigests.size()) == 1 &&
        EVP_DigestFinal_ex(ctx, outDigest->data(), outLen) == 1;
    EVP_MD_CTX_free(ctx);
    if (!ok) {
        SetErr(error, "top-level content digest computation failed");
        return false;
    }
    return true;
}

// ---- Signature algorithm table ------------------------------------------

struct AlgoInfo {
    uint32_t id;
    const EVP_MD* (*mdFn)();
    bool isPss;
    bool isEc;
};

const AlgoInfo* LookupAlgo(uint32_t id)
{
    static const AlgoInfo kTable[] = {
        {0x0103u, EVP_sha256, false, false},  // RSASSA-PKCS1-v1_5 SHA2-256
        {0x0104u, EVP_sha512, false, false},  // RSASSA-PKCS1-v1_5 SHA2-512
        {0x0101u, EVP_sha256, true, false},   // RSASSA-PSS SHA2-256
        {0x0102u, EVP_sha512, true, false},   // RSASSA-PSS SHA2-512
        {0x0201u, EVP_sha256, false, true},   // ECDSA SHA2-256
        {0x0202u, EVP_sha512, false, true},   // ECDSA SHA2-512
        // 0x0301 (DSA SHA2-256) is intentionally absent: treated as a weak/
        // unsupported algorithm and rejected fail-closed.
    };
    for (const auto& entry : kTable) {
        if (entry.id == id) return &entry;
    }
    return nullptr;
}

int SignatureStrength(const AlgoInfo& algorithm)
{
    return algorithm.mdFn == &EVP_sha512 ? 2 : 1;
}

bool VerifyRawSignature(EVP_PKEY* pkey, const AlgoInfo& algo, const uint8_t* data, size_t dataLen,
                        const uint8_t* sig, size_t sigLen)
{
    const int keyType = EVP_PKEY_id(pkey);
    if (algo.isEc && keyType != EVP_PKEY_EC) return false;
    if (!algo.isEc && keyType != EVP_PKEY_RSA) return false;

    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (ctx == nullptr) return false;
    EVP_PKEY_CTX* pctx = nullptr;
    bool ok = EVP_DigestVerifyInit(ctx, &pctx, algo.mdFn(), nullptr, pkey) == 1;
    if (ok && algo.isPss) {
        ok = EVP_PKEY_CTX_set_rsa_padding(pctx, RSA_PKCS1_PSS_PADDING) == 1 &&
            EVP_PKEY_CTX_set_rsa_pss_saltlen(pctx, RSA_PSS_SALTLEN_DIGEST) == 1 &&
            EVP_PKEY_CTX_set_rsa_mgf1_md(pctx, algo.mdFn()) == 1;
    }
    if (ok) ok = EVP_DigestVerifyUpdate(ctx, data, dataLen) == 1;
    if (ok) ok = EVP_DigestVerifyFinal(ctx, sig, sigLen) == 1;
    EVP_MD_CTX_free(ctx);
    return ok;
}

// ---- Signed-data / signer parsing ----------------------------------------

struct DigestEntry { uint32_t algoId; const uint8_t* data; size_t len; };
struct SignatureEntry { uint32_t algoId; const uint8_t* data; size_t len; };

struct ZipHandle {
    explicit ZipHandle(unzFile value = nullptr) : file(value) {}
    ~ZipHandle() { if (file != nullptr) unzClose(file); }
    ZipHandle(const ZipHandle&) = delete;
    ZipHandle& operator=(const ZipHandle&) = delete;
    unzFile file = nullptr;
};

bool EndsWith(const std::string& value, const std::string& suffix)
{
    return value.size() >= suffix.size() &&
        value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

bool StartsWith(const std::string& value, const std::string& prefix)
{
    return value.size() >= prefix.size() && value.compare(0, prefix.size(), prefix) == 0;
}

std::string UpperAscii(std::string value)
{
    for (char& c : value) {
        c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    }
    return value;
}

std::string TrimAscii(std::string value)
{
    while (!value.empty() && (value.back() == '\r' || value.back() == '\n' ||
                             value.back() == ' ' || value.back() == '\t')) {
        value.pop_back();
    }
    size_t first = 0;
    while (first < value.size() && (value[first] == ' ' || value[first] == '\t')) {
        ++first;
    }
    return value.substr(first);
}

bool Base64Decode(const std::string& encoded, std::vector<uint8_t>* out)
{
    std::string compact;
    compact.reserve(encoded.size());
    for (char c : encoded) {
        if (c != '\r' && c != '\n' && c != ' ' && c != '\t') compact.push_back(c);
    }
    if (compact.empty() || compact.size() % 4 != 0) return false;
    std::vector<uint8_t> decoded((compact.size() / 4) * 3 + 3);
    const int len = EVP_DecodeBlock(decoded.data(),
        reinterpret_cast<const unsigned char*>(compact.data()),
        static_cast<int>(compact.size()));
    if (len < 0) return false;
    size_t actual = static_cast<size_t>(len);
    while (!compact.empty() && compact.back() == '=') {
        --actual;
        compact.pop_back();
    }
    decoded.resize(actual);
    *out = std::move(decoded);
    return true;
}

const EVP_MD* DigestForManifestAttr(const std::string& attr)
{
    const std::string upper = UpperAscii(attr);
    if (upper == "SHA1-DIGEST" || upper == "SHA1-DIGEST-MANIFEST") return EVP_sha1();
    if (upper == "SHA-256-DIGEST" || upper == "SHA-256-DIGEST-MANIFEST") return EVP_sha256();
    return nullptr;
}

bool DigestBytes(const std::vector<uint8_t>& data, const EVP_MD* md, std::vector<uint8_t>* out)
{
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    std::array<uint8_t, EVP_MAX_MD_SIZE> digest{};
    unsigned int len = 0;
    const bool ok = ctx != nullptr &&
        EVP_DigestInit_ex(ctx, md, nullptr) == 1 &&
        EVP_DigestUpdate(ctx, data.data(), data.size()) == 1 &&
        EVP_DigestFinal_ex(ctx, digest.data(), &len) == 1;
    EVP_MD_CTX_free(ctx);
    if (!ok) return false;
    out->assign(digest.begin(), digest.begin() + len);
    return true;
}

using Attributes = std::map<std::string, std::string>;

std::vector<Attributes> ParseJarAttributes(const std::vector<uint8_t>& bytes)
{
    std::vector<Attributes> sections(1);
    std::string lastKey;
    std::istringstream stream(std::string(reinterpret_cast<const char*>(bytes.data()), bytes.size()));
    std::string line;
    while (std::getline(stream, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) {
            if (!sections.back().empty()) sections.emplace_back();
            lastKey.clear();
            continue;
        }
        if (!lastKey.empty() && line[0] == ' ') {
            sections.back()[lastKey] += line.substr(1);
            continue;
        }
        const size_t colon = line.find(':');
        if (colon == std::string::npos) {
            lastKey.clear();
            continue;
        }
        lastKey = line.substr(0, colon);
        sections.back()[lastKey] = TrimAscii(line.substr(colon + 1));
    }
    if (sections.size() > 1 && sections.back().empty()) sections.pop_back();
    return sections;
}

bool ReadZipEntry(unzFile zip, const std::string& name, std::vector<uint8_t>* out, std::string* error)
{
    if (unzLocateFile(zip, name.c_str(), 0) != UNZ_OK) {
        SetErr(error, "v1 ZIP entry missing: " + name);
        return false;
    }
    unz_file_info64 info{};
    if (unzGetCurrentFileInfo64(zip, &info, nullptr, 0, nullptr, 0, nullptr, 0) != UNZ_OK ||
        info.uncompressed_size > kMaxV1EntryBytes) {
        SetErr(error, "v1 ZIP entry metadata rejected: " + name);
        return false;
    }
    if (unzOpenCurrentFile(zip) != UNZ_OK) {
        SetErr(error, "cannot open v1 ZIP entry: " + name);
        return false;
    }
    out->assign(static_cast<size_t>(info.uncompressed_size), 0);
    size_t offset = 0;
    while (offset < out->size()) {
        const int chunk = unzReadCurrentFile(zip, out->data() + offset,
            static_cast<unsigned int>(std::min<size_t>(64 * 1024, out->size() - offset)));
        if (chunk <= 0) {
            unzCloseCurrentFile(zip);
            SetErr(error, "cannot read v1 ZIP entry: " + name);
            return false;
        }
        offset += static_cast<size_t>(chunk);
    }
    const int tail = unzReadCurrentFile(zip, nullptr, 0);
    const int closeRc = unzCloseCurrentFile(zip);
    if (tail != 0 || closeRc != UNZ_OK) {
        SetErr(error, "v1 ZIP entry CRC/framing rejected: " + name);
        return false;
    }
    return true;
}

bool ListZipEntries(unzFile zip, std::vector<std::string>* entries, std::string* error)
{
    int rc = unzGoToFirstFile(zip);
    while (rc == UNZ_OK) {
        unz_file_info64 info{};
        char nameBuf[4096]{};
        if (unzGetCurrentFileInfo64(zip, &info, nameBuf, sizeof(nameBuf), nullptr, 0, nullptr, 0) != UNZ_OK ||
            info.size_filename == 0 || info.size_filename >= sizeof(nameBuf)) {
            SetErr(error, "malformed ZIP entry name");
            return false;
        }
        std::string name(nameBuf);
        if (!EndsWith(name, "/")) entries->push_back(name);
        rc = unzGoToNextFile(zip);
    }
    if (rc != UNZ_END_OF_LIST_OF_FILE) {
        SetErr(error, "cannot enumerate ZIP entries for v1 verifier");
        return false;
    }
    return true;
}

bool VerifyPkcs7SignatureOverSf(const std::vector<uint8_t>& sfBytes,
                                const std::vector<uint8_t>& signatureBytes,
                                Sha256Digest* outCertSha256,
                                std::vector<uint8_t>* outCertDer,
                                std::string* error)
{
    BIO* sigBio = BIO_new_mem_buf(signatureBytes.data(), static_cast<int>(signatureBytes.size()));
    PKCS7* pkcs7 = sigBio != nullptr ? d2i_PKCS7_bio(sigBio, nullptr) : nullptr;
    BIO_free(sigBio);
    if (pkcs7 == nullptr) {
        SetErr(error, "v1 PKCS7 signature block is malformed");
        return false;
    }
    BIO* sfBio = BIO_new_mem_buf(sfBytes.data(), static_cast<int>(sfBytes.size()));
    const int flags = PKCS7_NOVERIFY | PKCS7_BINARY;
    const bool verified = sfBio != nullptr && PKCS7_verify(pkcs7, nullptr, nullptr, sfBio, nullptr, flags) == 1;
    BIO_free(sfBio);
    if (!verified) {
        PKCS7_free(pkcs7);
        SetErr(error, "v1 PKCS7 signature over CERT.SF did not verify");
        return false;
    }
    STACK_OF(X509)* signers = PKCS7_get0_signers(pkcs7, nullptr, PKCS7_NOVERIFY);
    if (signers == nullptr || sk_X509_num(signers) <= 0) {
        if (signers != nullptr) sk_X509_free(signers);
        PKCS7_free(pkcs7);
        SetErr(error, "v1 PKCS7 contains no signer certificate");
        return false;
    }
    X509* cert = sk_X509_value(signers, 0);
    unsigned char* der = nullptr;
    const int derLen = i2d_X509(cert, &der);
    if (derLen <= 0) {
        sk_X509_free(signers);
        PKCS7_free(pkcs7);
        SetErr(error, "cannot encode v1 signer certificate");
        return false;
    }
    SHA256(der, static_cast<size_t>(derLen), outCertSha256->data());
    outCertDer->assign(der, der + derLen);
    OPENSSL_free(der);
    sk_X509_free(signers);
    PKCS7_free(pkcs7);
    return true;
}

bool VerifyManifestDigestFromSf(const std::vector<uint8_t>& sfBytes,
                                const std::vector<uint8_t>& manifestBytes, std::string* error)
{
    const auto sfSections = ParseJarAttributes(sfBytes);
    if (sfSections.empty()) {
        SetErr(error, "v1 CERT.SF has no main attributes");
        return false;
    }
    for (const auto& attr : sfSections.front()) {
        if (!EndsWith(UpperAscii(attr.first), "-DIGEST-MANIFEST")) continue;
        const EVP_MD* md = DigestForManifestAttr(attr.first);
        std::vector<uint8_t> expected;
        std::vector<uint8_t> actual;
        if (md != nullptr && Base64Decode(attr.second, &expected) &&
            DigestBytes(manifestBytes, md, &actual) && expected == actual) {
            return true;
        }
    }
    SetErr(error, "v1 CERT.SF does not match MANIFEST.MF digest");
    return false;
}

bool VerifyV1ManifestEntries(unzFile zip, const std::vector<std::string>& zipEntries,
                             const std::vector<uint8_t>& manifestBytes, std::string* error)
{
    std::map<std::string, Attributes> manifestByName;
    const auto sections = ParseJarAttributes(manifestBytes);
    for (size_t i = 1; i < sections.size(); ++i) {
        const auto nameIt = sections[i].find("Name");
        if (nameIt != sections[i].end() && !nameIt->second.empty()) {
            manifestByName[nameIt->second] = sections[i];
        }
    }
    for (const auto& entryName : zipEntries) {
        if (StartsWith(UpperAscii(entryName), "META-INF/")) continue;
        const auto sectionIt = manifestByName.find(entryName);
        if (sectionIt == manifestByName.end()) {
            SetErr(error, "v1 manifest does not cover ZIP entry: " + entryName);
            return false;
        }
        std::vector<uint8_t> entryBytes;
        if (!ReadZipEntry(zip, entryName, &entryBytes, error)) return false;
        bool matchedDigest = false;
        for (const auto& attr : sectionIt->second) {
            const EVP_MD* md = DigestForManifestAttr(attr.first);
            if (md == nullptr || EndsWith(UpperAscii(attr.first), "-DIGEST-MANIFEST")) continue;
            std::vector<uint8_t> expected;
            std::vector<uint8_t> actual;
            if (Base64Decode(attr.second, &expected) && DigestBytes(entryBytes, md, &actual) &&
                expected == actual) {
                matchedDigest = true;
                break;
            }
        }
        if (!matchedDigest) {
            SetErr(error, "v1 manifest digest mismatch for ZIP entry: " + entryName);
            return false;
        }
    }
    return true;
}

bool VerifyV1JarSignature(int fd, ApkVerifiedIdentity* out, std::string* error)
{
    char fdPath[64]{};
    if (snprintf(fdPath, sizeof(fdPath), "/proc/self/fd/%d", fd) <= 0) {
        SetErr(error, "cannot address sealed APK fd for v1 verifier");
        return false;
    }
    ZipHandle zip(unzOpen64(fdPath));
    if (zip.file == nullptr) {
        SetErr(error, "cannot open sealed APK as ZIP for v1 verifier");
        return false;
    }
    std::vector<std::string> entries;
    if (!ListZipEntries(zip.file, &entries, error)) return false;

    std::string sfName;
    std::string blockName;
    std::set<std::string> entrySet(entries.begin(), entries.end());
    for (const auto& name : entries) {
        const std::string upper = UpperAscii(name);
        if (!StartsWith(upper, "META-INF/") || !EndsWith(upper, ".SF")) continue;
        const std::string base = name.substr(0, name.size() - 3);
        for (const char* ext : {".RSA", ".DSA", ".EC"}) {
            const std::string candidate = base + ext;
            if (entrySet.count(candidate) != 0) {
                sfName = name;
                blockName = candidate;
                break;
            }
        }
        if (!sfName.empty()) break;
    }
    if (sfName.empty()) {
        SetErr(error, "v1 signature files not found");
        return false;
    }

    std::vector<uint8_t> manifestBytes;
    std::vector<uint8_t> sfBytes;
    std::vector<uint8_t> signatureBytes;
    if (!ReadZipEntry(zip.file, "META-INF/MANIFEST.MF", &manifestBytes, error) ||
        !ReadZipEntry(zip.file, sfName, &sfBytes, error) ||
        !ReadZipEntry(zip.file, blockName, &signatureBytes, error)) {
        return false;
    }

    Sha256Digest certSha256{};
    std::vector<uint8_t> certDer;
    if (!VerifyPkcs7SignatureOverSf(
            sfBytes, signatureBytes, &certSha256, &certDer, error) ||
        !VerifyManifestDigestFromSf(sfBytes, manifestBytes, error) ||
        !VerifyV1ManifestEntries(zip.file, entries, manifestBytes, error)) {
        return false;
    }

    ApkVerifiedIdentity identity;
    identity.schemeVersion = 1;
    identity.v3BlockId = 0;
    identity.apkSha256 = Sha256Digest{};
    identity.currentSignerSha256.push_back(certSha256);
    identity.currentSignerCertificateDer.push_back(std::move(certDer));
    *out = std::move(identity);
    if (error != nullptr) error->clear();
    return true;
}

// Parses a length-prefixed sequence of length-prefixed entries, where each
// entry is itself [u32 algoId][u32 payloadLen + payload bytes] (the shared
// wire shape of both the "digests" and "signatures" lists: signature
// algorithm ID followed by a length-prefixed digest/signature value).
bool ParseAlgoValueSequence(const uint8_t* data, size_t len,
                            std::vector<std::pair<uint32_t, std::pair<const uint8_t*, size_t>>>* out)
{
    Cursor cursor(data, len);
    while (!cursor.AtEnd()) {
        const uint8_t* entry = nullptr;
        size_t entryLen = 0;
        if (!cursor.ReadLenPrefixed(&entry, &entryLen) || entryLen < 8) return false;
        const uint32_t algoId = ReadU32LE(entry);
        Cursor entryCursor(entry + 4, entryLen - 4);
        const uint8_t* payload = nullptr;
        size_t payloadLen = 0;
        if (!entryCursor.ReadLenPrefixed(&payload, &payloadLen) || !entryCursor.AtEnd()) return false;
        out->push_back({algoId, {payload, payloadLen}});
    }
    return true;
}

struct ParsedSignedData {
    std::vector<DigestEntry> digests;
    std::vector<const uint8_t*> certData;
    std::vector<size_t> certLen;
    uint32_t minSdkVersion = 0;
    uint32_t maxSdkVersion = 0;
    bool hasRotationAttr = false;
    bool rotationAttrMalformed = false;
    const uint8_t* rotationAttr = nullptr;
    size_t rotationAttrLen = 0;
    bool hasRotationMinSdkAttr = false;
    bool rotationMinSdkAttrMalformed = false;
    uint32_t rotationMinSdkVersion = 0;
    const uint8_t* raw = nullptr;
    size_t rawLen = 0;
};

bool ParseSignedData(const uint8_t* data, size_t len, bool isV3, ParsedSignedData* out,
                     std::string* error)
{
    out->raw = data;
    out->rawLen = len;
    Cursor cursor(data, len);

    const uint8_t* digestsBlob = nullptr;
    size_t digestsLen = 0;
    if (!cursor.ReadLenPrefixed(&digestsBlob, &digestsLen)) {
        SetErr(error, "malformed signed-data digests sequence");
        return false;
    }
    std::vector<std::pair<uint32_t, std::pair<const uint8_t*, size_t>>> digestPairs;
    if (!ParseAlgoValueSequence(digestsBlob, digestsLen, &digestPairs)) {
        SetErr(error, "malformed signed-data digest entry framing");
        return false;
    }
    for (const auto& pair : digestPairs) {
        out->digests.push_back({pair.first, pair.second.first, pair.second.second});
    }

    const uint8_t* certsBlob = nullptr;
    size_t certsLen = 0;
    if (!cursor.ReadLenPrefixed(&certsBlob, &certsLen)) {
        SetErr(error, "malformed signed-data certificates sequence");
        return false;
    }
    Cursor certCursor(certsBlob, certsLen);
    while (!certCursor.AtEnd()) {
        const uint8_t* cert = nullptr;
        size_t certLen = 0;
        if (!certCursor.ReadLenPrefixed(&cert, &certLen) || certLen == 0 ||
            certLen > kMaxCertBytes) {
            SetErr(error, "malformed signed-data certificate entry");
            return false;
        }
        out->certData.push_back(cert);
        out->certLen.push_back(certLen);
    }
    if (out->certData.empty()) {
        SetErr(error, "signed-data contains no certificate");
        return false;
    }

    if (isV3) {
        if (!cursor.ReadU32(&out->minSdkVersion) || !cursor.ReadU32(&out->maxSdkVersion) ||
            out->minSdkVersion > out->maxSdkVersion) {
            SetErr(error, "malformed v3 signed-data minSdk/maxSdk");
            return false;
        }
    }

    const uint8_t* attrsBlob = nullptr;
    size_t attrsLen = 0;
    if (!cursor.ReadLenPrefixed(&attrsBlob, &attrsLen)) {
        SetErr(error, "malformed signed-data attributes sequence");
        return false;
    }
    Cursor attrCursor(attrsBlob, attrsLen);
    while (!attrCursor.AtEnd()) {
        const uint8_t* attr = nullptr;
        size_t attrLen = 0;
        if (!attrCursor.ReadLenPrefixed(&attr, &attrLen) || attrLen < 4) {
            SetErr(error, "malformed signed-data attribute framing");
            return false;
        }
        const uint32_t attrId = ReadU32LE(attr);
        if (attrId == kRotationAttrId) {
            if (out->hasRotationAttr) {
                SetErr(error, "duplicate proof-of-rotation attribute");
                return false;
            }
            out->hasRotationAttr = true;
            if (attrLen < 8) {
                out->rotationAttrMalformed = true;
            } else {
                out->rotationAttr = attr + 4;
                out->rotationAttrLen = attrLen - 4;
            }
        } else if (attrId == kRotationMinSdkAttrId) {
            if (out->hasRotationMinSdkAttr) {
                SetErr(error,
                    "duplicate rotation-min-sdk stripping attribute");
                return false;
            }
            out->hasRotationMinSdkAttr = true;
            if (attrLen != 8) {
                out->rotationMinSdkAttrMalformed = true;
            } else {
                out->rotationMinSdkVersion = ReadU32LE(attr + 4);
            }
        }
    }

    // Real-world signed-data blobs observed from current apksigner output
    // carry one more 4-byte field after additional attributes (a reserved/
    // versioning word not covered by the historical 3-field public
    // description of the v2 format). It is bounded and ignored here; any
    // other trailing content is still rejected fail-closed.
    if (cursor.Remaining() == 4) {
        uint32_t reserved = 0;
        if (!cursor.ReadU32(&reserved)) {
            SetErr(error, "malformed signed-data trailing reserved field");
            return false;
        }
    }
    if (!cursor.AtEnd()) {
        SetErr(error, "trailing bytes in signed-data");
        return false;
    }
    return true;
}

struct ParsedSigner {
    ParsedSignedData signedData;
    std::vector<SignatureEntry> signatures;
    uint32_t minSdkVersion = 0;
    uint32_t maxSdkVersion = 0;
    const uint8_t* publicKey = nullptr;
    size_t publicKeyLen = 0;
};

bool ParseSigner(const uint8_t* data, size_t len, bool isV3, ParsedSigner* out, std::string* error)
{
    Cursor cursor(data, len);
    const uint8_t* signedDataBlob = nullptr;
    size_t signedDataLen = 0;
    if (!cursor.ReadLenPrefixed(&signedDataBlob, &signedDataLen) ||
        !ParseSignedData(signedDataBlob, signedDataLen, isV3, &out->signedData, error)) {
        if (error != nullptr && error->empty()) SetErr(error, "malformed signer signed-data");
        return false;
    }

    // V3 stores minSdk/maxSdk twice: in signed-data (covered by the signature)
    // and as signer-level fields immediately before the signatures list.
    if (isV3) {
        if (!cursor.ReadU32(&out->minSdkVersion) || !cursor.ReadU32(&out->maxSdkVersion) ||
            out->minSdkVersion > out->maxSdkVersion) {
            SetErr(error, "malformed v3 signer minSdk/maxSdk");
            return false;
        }
        if (out->minSdkVersion != out->signedData.minSdkVersion ||
            out->maxSdkVersion != out->signedData.maxSdkVersion) {
            SetErr(error, "v3 signer minSdk/maxSdk mismatch with signed-data");
            return false;
        }
    }

    const uint8_t* sigsBlob = nullptr;
    size_t sigsLen = 0;
    if (!cursor.ReadLenPrefixed(&sigsBlob, &sigsLen)) {
        SetErr(error, "malformed signer signatures sequence");
        return false;
    }
    std::vector<std::pair<uint32_t, std::pair<const uint8_t*, size_t>>> sigPairs;
    if (!ParseAlgoValueSequence(sigsBlob, sigsLen, &sigPairs)) {
        SetErr(error, "malformed signer signature entry framing");
        return false;
    }
    for (const auto& pair : sigPairs) {
        out->signatures.push_back({pair.first, pair.second.first, pair.second.second});
    }

    if (!cursor.ReadLenPrefixed(&out->publicKey, &out->publicKeyLen) || out->publicKeyLen == 0) {
        SetErr(error, "malformed signer public key field");
        return false;
    }
    if (!cursor.AtEnd()) {
        SetErr(error, "trailing bytes in signer record");
        return false;
    }
    return true;
}

bool ParseSignersSequence(const uint8_t* blockValue, size_t blockValueLen, bool isV3,
                          std::vector<ParsedSigner>* outSigners, std::string* error)
{
    Cursor outer(blockValue, blockValueLen);
    const uint8_t* signersBlob = nullptr;
    size_t signersLen = 0;
    if (!outer.ReadLenPrefixed(&signersBlob, &signersLen) || !outer.AtEnd()) {
        SetErr(error, "malformed signer-sequence framing");
        return false;
    }
    Cursor inner(signersBlob, signersLen);
    while (!inner.AtEnd()) {
        const uint8_t* signerBlob = nullptr;
        size_t signerLen = 0;
        if (!inner.ReadLenPrefixed(&signerBlob, &signerLen)) {
            SetErr(error, "malformed signer entry length");
            return false;
        }
        ParsedSigner signer;
        if (!ParseSigner(signerBlob, signerLen, isV3, &signer, error)) return false;
        outSigners->push_back(std::move(signer));
        if (outSigners->size() > kMaxSignersPerBlock) {
            SetErr(error, "too many signers in one block");
            return false;
        }
    }
    if (outSigners->empty()) {
        SetErr(error, "signer sequence is empty");
        return false;
    }
    return true;
}

Sha256Digest Sha256Of(const uint8_t* data, size_t len)
{
    Sha256Digest digest{};
    SHA256(data, len, digest.data());
    return digest;
}

// Verifies one signer record: at least one supported-algorithm signature
// must verify, none of the recognized-strong signatures may fail, and the
// matching content digest must equal the recomputed value.
bool VerifyAndCollectSigner(int fd, const ParsedSigner& signer, uint64_t sigBlockOffset,
                            uint64_t cdOffset, uint32_t cdSize, uint64_t eocdOffset,
                            uint64_t fileSize, Sha256Digest* outCertSha256,
                            std::vector<uint8_t>* outCertDer,
                            std::vector<ApkVerifiedContentDigest>* outContentDigests,
                            std::vector<ApkLineageCertificate>* outLineage,
                            std::string* error)
{
    // Parse the first (leaf/signing) certificate.
    const uint8_t* leafCert = signer.signedData.certData.front();
    const size_t leafCertLen = signer.signedData.certLen.front();
    const uint8_t* certCursor = leafCert;
    X509* cert = d2i_X509(nullptr, &certCursor, static_cast<long>(leafCertLen));
    if (cert == nullptr) {
        SetErr(error, "signing certificate is not valid DER X.509");
        return false;
    }
    EVP_PKEY* certPubKey = X509_get_pubkey(cert);
    if (certPubKey == nullptr) {
        X509_free(cert);
        SetErr(error, "signing certificate has no public key");
        return false;
    }

    // Cross-check that the standalone "public key" field byte-matches the
    // certificate's SubjectPublicKeyInfo (defends against key substitution).
    std::vector<uint8_t> certPubKeyDer;
    {
        unsigned char* derPtr = nullptr;
        const int derLen = i2d_PUBKEY(certPubKey, &derPtr);
        if (derLen <= 0) {
            EVP_PKEY_free(certPubKey);
            X509_free(cert);
            SetErr(error, "cannot re-encode certificate public key");
            return false;
        }
        certPubKeyDer.assign(derPtr, derPtr + derLen);
        OPENSSL_free(derPtr);
    }
    if (certPubKeyDer.size() != signer.publicKeyLen ||
        std::memcmp(certPubKeyDer.data(), signer.publicKey, certPubKeyDer.size()) != 0) {
        EVP_PKEY_free(certPubKey);
        X509_free(cert);
        SetErr(error, "public key field does not match certificate public key");
        return false;
    }

    std::vector<uint32_t> signatureAlgorithms;
    signatureAlgorithms.reserve(signer.signatures.size());
    for (const auto& signature : signer.signatures) {
        signatureAlgorithms.push_back(signature.algoId);
    }
    std::vector<uint32_t> digestAlgorithms;
    digestAlgorithms.reserve(signer.signedData.digests.size());
    for (const auto& digest : signer.signedData.digests) {
        digestAlgorithms.push_back(digest.algoId);
    }
    if (signatureAlgorithms != digestAlgorithms) {
        EVP_PKEY_free(certPubKey);
        X509_free(cert);
        SetErr(error,
            "signature algorithms do not match signed-data digests");
        return false;
    }

    const SignatureEntry* bestSignature = nullptr;
    const AlgoInfo* bestAlgorithm = nullptr;
    for (const auto& signature : signer.signatures) {
        const AlgoInfo* candidate = LookupAlgo(signature.algoId);
        if (candidate != nullptr &&
            (bestAlgorithm == nullptr ||
                SignatureStrength(*candidate) >
                    SignatureStrength(*bestAlgorithm))) {
            bestSignature = &signature;
            bestAlgorithm = candidate;
        }
    }
    if (bestSignature == nullptr || bestAlgorithm == nullptr) {
        EVP_PKEY_free(certPubKey);
        X509_free(cert);
        SetErr(error,
            "no supported (non-weak) signature algorithm present");
        return false;
    }

    // Cache computed content digests per digest md so repeated algorithms
    // (or multiple signers) don't re-hash the whole APK.
    std::array<uint8_t, EVP_MAX_MD_SIZE> sha256Digest{};
    std::array<uint8_t, EVP_MAX_MD_SIZE> sha512Digest{};
    bool haveSha256 = false, haveSha512 = false;

    {
        const auto& sigEntry = *bestSignature;
        const AlgoInfo* algo = bestAlgorithm;
        const bool wantSha512 = (algo->mdFn == &EVP_sha512);
        std::array<uint8_t, EVP_MAX_MD_SIZE>* digestSlot = wantSha512 ? &sha512Digest : &sha256Digest;
        bool* haveSlot = wantSha512 ? &haveSha512 : &haveSha256;
        unsigned int digestLen = 0;
        if (!*haveSlot) {
            if (!ComputeContentDigest(fd, sigBlockOffset, cdOffset, cdSize, eocdOffset, fileSize,
                                      algo->mdFn(), digestSlot, &digestLen, error)) {
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                return false;
            }
            *haveSlot = true;
        }
        digestLen = wantSha512 ? SHA512_DIGEST_LENGTH : SHA256_DIGEST_LENGTH;

        const DigestEntry* matchingDigest = nullptr;
        for (const auto& d : signer.signedData.digests) {
            if (d.algoId == sigEntry.algoId) matchingDigest = &d;
        }
        if (matchingDigest == nullptr || matchingDigest->len != digestLen ||
            std::memcmp(matchingDigest->data, digestSlot->data(), digestLen) != 0) {
            SetErr(error, "signed content digest does not match recomputed APK bytes");
            EVP_PKEY_free(certPubKey);
            X509_free(cert);
            return false;
        }

        if (!VerifyRawSignature(certPubKey, *algo, signer.signedData.raw, signer.signedData.rawLen,
                                sigEntry.data, sigEntry.len)) {
            SetErr(error, "cryptographic signature verification failed");
            EVP_PKEY_free(certPubKey);
            X509_free(cert);
            return false;
        }
        const auto existing = std::find_if(
            outContentDigests->begin(), outContentDigests->end(),
            [&sigEntry](const ApkVerifiedContentDigest& value) {
                return value.signatureAlgorithmId == sigEntry.algoId;
            });
        const std::vector<uint8_t> verifiedDigest(
            matchingDigest->data, matchingDigest->data + matchingDigest->len);
        if (existing != outContentDigests->end()) {
            if (existing->digest != verifiedDigest) {
                SetErr(error, "one signer declares conflicting content digests");
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                return false;
            }
        } else {
            outContentDigests->push_back(
                {sigEntry.algoId, std::move(verifiedDigest)});
        }
    }
    if (signer.signedData.rotationAttrMalformed) {
        EVP_PKEY_free(certPubKey);
        X509_free(cert);
        SetErr(error, "proof-of-rotation attribute is malformed");
        return false;
    }
    if (signer.signedData.rotationMinSdkAttrMalformed) {
        EVP_PKEY_free(certPubKey);
        X509_free(cert);
        SetErr(error,
            "rotation-min-sdk stripping attribute is malformed");
        return false;
    }

    if (signer.signedData.hasRotationAttr) {
        Cursor proof(signer.signedData.rotationAttr,
            signer.signedData.rotationAttrLen);
        uint32_t version = 0;
        if (!proof.ReadU32(&version) || version != 1) {
            EVP_PKEY_free(certPubKey);
            X509_free(cert);
            SetErr(error, "unsupported proof-of-rotation version");
            return false;
        }
        EVP_PKEY* previousKey = nullptr;
        uint32_t previousAlgorithm = 0;
        std::set<Sha256Digest> seenLineage;
        std::vector<uint8_t> terminalCertificate;
        while (!proof.AtEnd()) {
            if (outLineage->size() >= kMaxApkSignerCertificates) {
                EVP_PKEY_free(previousKey);
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                SetErr(error, "proof-of-rotation exceeds certificate limit");
                return false;
            }
            const uint8_t* levelData = nullptr;
            size_t levelLen = 0;
            if (!proof.ReadLenPrefixed(&levelData, &levelLen)) {
                EVP_PKEY_free(previousKey);
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                SetErr(error, "malformed proof-of-rotation level");
                return false;
            }
            Cursor level(levelData, levelLen);
            const uint8_t* signedData = nullptr;
            size_t signedDataLen = 0;
            uint32_t flags = 0;
            uint32_t nextAlgorithm = 0;
            const uint8_t* signature = nullptr;
            size_t signatureLen = 0;
            if (!level.ReadLenPrefixed(&signedData, &signedDataLen) ||
                !level.ReadU32(&flags) || !level.ReadU32(&nextAlgorithm) ||
                !level.ReadLenPrefixed(&signature, &signatureLen) ||
                !level.AtEnd()) {
                EVP_PKEY_free(previousKey);
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                SetErr(error, "malformed proof-of-rotation fields");
                return false;
            }
            if (previousKey != nullptr) {
                const AlgoInfo* proofAlgorithm = LookupAlgo(previousAlgorithm);
                if (proofAlgorithm == nullptr ||
                    !VerifyRawSignature(previousKey, *proofAlgorithm,
                        signedData, signedDataLen, signature, signatureLen)) {
                    EVP_PKEY_free(previousKey);
                    EVP_PKEY_free(certPubKey);
                    X509_free(cert);
                    SetErr(error, "proof-of-rotation signature verification failed");
                    return false;
                }
            }
            Cursor signedCursor(signedData, signedDataLen);
            const uint8_t* lineageCert = nullptr;
            size_t lineageCertLen = 0;
            uint32_t signedAlgorithm = 0;
            if (!signedCursor.ReadLenPrefixed(&lineageCert, &lineageCertLen) ||
                lineageCertLen == 0 || lineageCertLen > kMaxCertBytes ||
                !signedCursor.ReadU32(&signedAlgorithm) ||
                !signedCursor.AtEnd() ||
                (previousKey != nullptr && signedAlgorithm != previousAlgorithm)) {
                EVP_PKEY_free(previousKey);
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                SetErr(error, "proof-of-rotation signed-data mismatch");
                return false;
            }
            const uint8_t* lineageCursor = lineageCert;
            X509* lineageX509 = d2i_X509(
                nullptr, &lineageCursor, static_cast<long>(lineageCertLen));
            EVP_PKEY* nextKey =
                lineageX509 != nullptr ? X509_get_pubkey(lineageX509) : nullptr;
            if (lineageX509 == nullptr || nextKey == nullptr ||
                lineageCursor != lineageCert + lineageCertLen) {
                EVP_PKEY_free(nextKey);
                X509_free(lineageX509);
                EVP_PKEY_free(previousKey);
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                SetErr(error, "invalid proof-of-rotation certificate");
                return false;
            }
            const Sha256Digest lineageDigest =
                Sha256Of(lineageCert, lineageCertLen);
            if (!seenLineage.insert(lineageDigest).second) {
                EVP_PKEY_free(nextKey);
                X509_free(lineageX509);
                EVP_PKEY_free(previousKey);
                EVP_PKEY_free(certPubKey);
                X509_free(cert);
                SetErr(error, "duplicate proof-of-rotation certificate");
                return false;
            }
            outLineage->push_back({lineageDigest, flags});
            terminalCertificate.assign(
                lineageCert, lineageCert + lineageCertLen);
            EVP_PKEY_free(previousKey);
            previousKey = nextKey;
            previousAlgorithm = nextAlgorithm;
            X509_free(lineageX509);
        }
        EVP_PKEY_free(previousKey);
        if (outLineage->empty() || terminalCertificate.size() != leafCertLen ||
            std::memcmp(terminalCertificate.data(), leafCert, leafCertLen) != 0) {
            EVP_PKEY_free(certPubKey);
            X509_free(cert);
            SetErr(error, "proof-of-rotation terminal signer mismatch");
            return false;
        }
    }

    *outCertSha256 = Sha256Of(leafCert, leafCertLen);
    outCertDer->assign(leafCert, leafCert + leafCertLen);
    EVP_PKEY_free(certPubKey);
    X509_free(cert);
    return true;
}

}  // namespace

bool ApkSignatureVerifier::VerifyFd(int fd, uint32_t minSchemeVersion,
                                    ApkVerifiedIdentity* out,
                                    std::string* error)
{
    // The legacy package-boundary caller is the AOSP 15 compatibility
    // runtime. New policy-aware callers must use the overload below and
    // provide their versioned target platform explicitly.
    return VerifyFd(fd, minSchemeVersion, 35, out, error);
}

bool ApkSignatureVerifier::VerifyFd(int fd, uint32_t minSchemeVersion,
                                    uint32_t targetPlatformSdk,
                                    ApkVerifiedIdentity* out,
                                    std::string* error)
{
    if (out == nullptr || targetPlatformSdk == 0 ||
        (minSchemeVersion != 1 && minSchemeVersion != 2 &&
            minSchemeVersion != 3)) {
        SetErr(error, "invalid verifier arguments");
        return false;
    }
    struct stat st{};
    if (fstat(fd, &st) != 0) {
        const int savedErrno = errno;
        SetErr(error, "cannot stat verifier fd " + std::to_string(fd) +
            ": " + std::string(strerror(savedErrno)));
        return false;
    }
    if (lseek(fd, 0, SEEK_CUR) < 0) {
        const int savedErrno = errno;
        SetErr(error, "verifier fd " + std::to_string(fd) +
            " is not seekable: " + std::string(strerror(savedErrno)));
        return false;
    }
    const uint64_t fileSize = static_cast<uint64_t>(st.st_size);
    if (fileSize < kMinApkBytes || fileSize > kMaxApkBytes) {
        SetErr(error, "APK size outside accepted bounds (too small, or >1GiB)");
        return false;
    }

    uint64_t eocdOffset = 0;
    uint32_t cdOffset = 0, cdSize = 0;
    if (!FindEocd(fd, fileSize, &eocdOffset, &cdOffset, &cdSize, error)) return false;
    if (static_cast<uint64_t>(cdOffset) + cdSize > eocdOffset) {
        SetErr(error, "central directory extends past EOCD");
        return false;
    }

    uint64_t blockOffset = 0, pairsBegin = 0, pairsEnd = 0;
    if (!FindSigningBlock(fd, cdOffset, &blockOffset, &pairsBegin, &pairsEnd, error)) {
        if (minSchemeVersion <= 1 && VerifyV1JarSignature(fd, out, error)) return true;
        return false;
    }

    std::vector<std::pair<uint32_t, std::pair<uint64_t, uint64_t>>> pairs;
    if (!ReadIdValuePairs(fd, pairsBegin, pairsEnd, &pairs, error)) return false;

    // V3.1 and v3.0 are separate blocks. V3.1 is tried first only when it
    // contains exactly one signer for the versioned target platform; it
    // must never replace v3.0 merely because it occurs later in the pair
    // list.
    const std::pair<uint64_t, uint64_t>* v31Value = nullptr;
    const std::pair<uint64_t, uint64_t>* v3Value = nullptr;
    const std::pair<uint64_t, uint64_t>* v2Value = nullptr;
    for (const auto& entry : pairs) {
        auto bindUnique = [&](const std::pair<uint64_t, uint64_t>** slot,
                              const char* name) {
            if (*slot != nullptr) {
                SetErr(error, std::string("duplicate ") + name +
                    " signing block");
                return false;
            }
            *slot = &entry.second;
            return true;
        };
        if (entry.first == kV31BlockId &&
            !bindUnique(&v31Value, "v3.1")) {
            return false;
        }
        if (entry.first == kV3BlockId &&
            !bindUnique(&v3Value, "v3.0")) {
            return false;
        }
        if (entry.first == kV2BlockId &&
            !bindUnique(&v2Value, "v2")) {
            return false;
        }
    }
    if (v31Value == nullptr && v3Value == nullptr && v2Value == nullptr) {
        SetErr(error, "no v2 or v3 signature block found");
        return false;
    }

    auto parseBlock = [&](const std::pair<uint64_t, uint64_t>* value,
                          bool isV3,
                          std::vector<uint8_t>* storage,
                          std::vector<ParsedSigner>* parsed) {
        if (value == nullptr) return true;
        if (value->second == 0 ||
            value->second > kMaxSignerBlockBytes) {
            SetErr(error, "signature block value size rejected");
            return false;
        }
        storage->resize(value->second);
        if (!PReadAll(fd, value->first, storage->data(),
                storage->size())) {
            SetErr(error, "failed to read signature block value");
            return false;
        }
        return ParseSignersSequence(storage->data(), storage->size(),
            isV3, parsed, error);
    };

    std::vector<uint8_t> v31Storage;
    std::vector<uint8_t> v3Storage;
    std::vector<uint8_t> v2Storage;
    std::vector<ParsedSigner> v31Signers;
    std::vector<ParsedSigner> v3Signers;
    std::vector<ParsedSigner> v2Signers;
    if (!parseBlock(v31Value, true, &v31Storage, &v31Signers)) {
        return false;
    }

    auto applicableV3 = [&](std::vector<ParsedSigner>& candidates) {
        std::vector<ParsedSigner*> applicable;
        for (auto& signer : candidates) {
            if (targetPlatformSdk >= signer.minSdkVersion &&
                targetPlatformSdk <= signer.maxSdkVersion) {
                applicable.push_back(&signer);
            }
        }
        return applicable;
    };
    auto v31Applicable = applicableV3(v31Signers);
    std::vector<ParsedSigner*> v3Applicable;
    if (v31Applicable.empty() && v3Value != nullptr) {
        if (!parseBlock(v3Value, true, &v3Storage, &v3Signers)) {
            return false;
        }
        v3Applicable = applicableV3(v3Signers);
        if (v3Applicable.empty()) {
            SetErr(error,
                "v3.0 block has no signer for target platform SDK");
            return false;
        }

        uint32_t v31RotationMinSdk = 0;
        for (const auto& signer : v31Signers) {
            if (v31RotationMinSdk == 0 ||
                signer.minSdkVersion < v31RotationMinSdk) {
                v31RotationMinSdk = signer.minSdkVersion;
            }
        }
        bool v3HasRotationMinSdk = false;
        uint32_t v3RotationMinSdk = 0;
        for (const ParsedSigner* signer : v3Applicable) {
            if (!signer->signedData.hasRotationMinSdkAttr) continue;
            if (v3HasRotationMinSdk &&
                v3RotationMinSdk !=
                    signer->signedData.rotationMinSdkVersion) {
                SetErr(error,
                    "v3 signers disagree on rotation-min-sdk stripping protection");
                return false;
            }
            v3HasRotationMinSdk = true;
            v3RotationMinSdk =
                signer->signedData.rotationMinSdkVersion;
        }
        if (v31Value == nullptr && v3HasRotationMinSdk) {
            SetErr(error,
                "rotation-min-sdk stripping protection requires a v3.1 block");
            return false;
        }
        if (v31Value != nullptr &&
            (!v3HasRotationMinSdk ||
                v3RotationMinSdk != v31RotationMinSdk)) {
            SetErr(error,
                "v3.1 rotation minimum does not match v3.0 stripping protection");
            return false;
        }
    }
    std::vector<ParsedSigner*> chosenSigners;
    uint32_t effectiveScheme = 0;
    uint32_t chosenBlockId = 0;
    if (!v31Applicable.empty()) {
        chosenSigners = std::move(v31Applicable);
        effectiveScheme = 3;
        chosenBlockId = kV31BlockId;
    } else if (!v3Applicable.empty()) {
        chosenSigners = std::move(v3Applicable);
        effectiveScheme = 3;
        chosenBlockId = kV3BlockId;
    } else {
        if (!parseBlock(v2Value, false, &v2Storage, &v2Signers)) {
            return false;
        }
        if (v2Signers.empty()) {
            SetErr(error,
                "no signer supports the target platform SDK");
            return false;
        }
        for (auto& signer : v2Signers) {
            chosenSigners.push_back(&signer);
        }
        effectiveScheme = 2;
        chosenBlockId = kV2BlockId;
    }
    if (effectiveScheme < minSchemeVersion) {
        SetErr(error,
            "highest applicable scheme is below the required minimum");
        return false;
    }
    if (effectiveScheme == 3 && chosenSigners.size() != 1) {
        SetErr(error,
            "v3 signing block must have exactly one signer for target platform");
        return false;
    }

    ApkVerifiedIdentity identity;
    identity.schemeVersion = effectiveScheme;
    identity.v3BlockId = effectiveScheme == 3 ? chosenBlockId : 0;
    identity.apkSha256 = Sha256Digest{};  // filled by caller from the sealed fd (whole-file hash)

    for (const ParsedSigner* signer : chosenSigners) {
        Sha256Digest certSha256{};
        std::vector<uint8_t> certDer;
        std::vector<ApkVerifiedContentDigest> contentDigests;
        std::vector<ApkLineageCertificate> lineage;
        if (!VerifyAndCollectSigner(fd, *signer, blockOffset, cdOffset, cdSize, eocdOffset, fileSize,
                                    &certSha256, &certDer, &contentDigests,
                                    &lineage, error)) {
            return false;
        }
        for (const auto& contentDigest : contentDigests) {
            const auto existing = std::find_if(
                identity.verifiedContentDigests.begin(),
                identity.verifiedContentDigests.end(),
                [&contentDigest](const ApkVerifiedContentDigest& value) {
                    return value.signatureAlgorithmId ==
                        contentDigest.signatureAlgorithmId;
                });
            if (existing != identity.verifiedContentDigests.end()) {
                if (existing->digest != contentDigest.digest) {
                    SetErr(error, "signers disagree on verified content digest");
                    return false;
                }
            } else {
                identity.verifiedContentDigests.push_back(contentDigest);
            }
        }
        if (!lineage.empty()) {
            if (!identity.lineage.empty() ||
                chosenSigners.size() != 1) {
                SetErr(error, "ambiguous proof-of-rotation signer set");
                return false;
            }
            identity.lineage = std::move(lineage);
        }
        identity.currentSignerSha256.push_back(certSha256);
        identity.currentSignerCertificateDer.push_back(std::move(certDer));
    }
    if (std::set<Sha256Digest>(identity.currentSignerSha256.begin(),
                               identity.currentSignerSha256.end())
            .size() != identity.currentSignerSha256.size()) {
        SetErr(error, "duplicate signer certificate across signers");
        return false;
    }

    *out = std::move(identity);
    if (error != nullptr) error->clear();
    return true;
}

}  // namespace oh_adapter
