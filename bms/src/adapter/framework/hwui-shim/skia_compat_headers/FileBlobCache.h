#pragma once
#include <cstdint>
#include <cstddef>
#include <string>
#include <memory>
namespace android {
class BlobCache {
public:
    BlobCache(size_t = 0, size_t = 0, size_t = 0) {}
    enum class InsertResult { kInserted = 0, kKeyTooLarge = 1, kValueTooLarge = 2, kDidClean = 3, kNotEnoughSpace = 4, kInvalidValueSize = 5, kInvalidKeySize = 6, kKeyTooBig = 7, kValueTooBig = 8, kCombinedTooBig = 9 };
    InsertResult set(const void*, size_t, const void*, size_t) { return InsertResult::kInserted; }
    InsertResult set(const std::string&, size_t, const void*, size_t) { return InsertResult::kInserted; }
    size_t get(const void*, size_t, void*, size_t) { return 0; }
};
class FileBlobCache : public BlobCache {
public:
    FileBlobCache(size_t a, size_t b, const std::string&) : BlobCache(a, b, 0) {}
    FileBlobCache(size_t a, size_t b, size_t c, const std::string&) : BlobCache(a, b, c) {}
    void writeToFile() {}
    void clear() {}
};
}
