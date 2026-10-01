#pragma once
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

struct RawResourceFile { std::vector<char> data; };
using unzFile = RawResourceFile*;
struct unz_file_info { unsigned long uncompressed_size; };
constexpr int UNZ_OK = 0;
inline unzFile unzOpen(const char* filename) {
    std::ifstream input(filename, std::ios::binary);
    if (!input) return nullptr;
    return new RawResourceFile{{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()}};
}
inline int unzLocateFile(unzFile, const char* name, int) { return std::string(name) == "resources.arsc" ? 0 : -1; }
inline int unzGetCurrentFileInfo(unzFile file, unz_file_info* info, void*, unsigned long, void*, unsigned long, void*, unsigned long) {
    info->uncompressed_size = file->data.size();
    return 0;
}
inline int unzOpenCurrentFile(unzFile) { return 0; }
inline int unzReadCurrentFile(unzFile file, void* output, unsigned length) {
    const auto count = std::min(static_cast<size_t>(length), file->data.size());
    std::memcpy(output, file->data.data(), count);
    return static_cast<int>(count);
}
inline int unzCloseCurrentFile(unzFile) { return 0; }
inline int unzClose(unzFile file) { delete file; return 0; }
