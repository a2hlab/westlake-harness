#include "zip_error.h"

#include <cstdio>
#include <cstring>

const char* ErrorCodeString(int32_t error_code);

namespace {

struct Case {
  int code;
  const char* expected;
};

constexpr Case kCanonicalCases[] = {
    {0, "Success"},
    {-1, "Iteration ended"},
    {-2, "Zlib error"},
    {-3, "Invalid file"},
    {-4, "Invalid handle"},
    {-5, "Duplicate entries in archive"},
    {-6, "Empty archive"},
    {-7, "Entry not found"},
    {-8, "Invalid offset"},
    {-9, "Inconsistent information"},
    {-10, "Invalid entry name"},
    {-11, "I/O error"},
    {-12, "File mapping failed"},
    {-13, "Allocation failed"},
    {-14, "Unsupported zip entry size"},
    {1, "Unknown return code"},
    {-15, "Unknown return code"},
    {32767, "Unknown return code"},
};

}  // namespace

int main() {
  for (const auto& test : kCanonicalCases) {
    const char* actual = ErrorCodeString(test.code);
    if (actual == nullptr || std::strcmp(actual, test.expected) != 0) {
      std::fprintf(stderr, "FAIL code=%d expected='%s' actual='%s'\n",
                   test.code, test.expected, actual == nullptr ? "<null>" : actual);
      return 1;
    }
  }

  std::printf("PASS ErrorCodeString canonical_cases=%zu\n",
              sizeof(kCanonicalCases) / sizeof(kCanonicalCases[0]));
  return 0;
}
