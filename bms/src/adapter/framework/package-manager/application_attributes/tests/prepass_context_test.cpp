#include "prepass_context_wire.h"
#include <gtest/gtest.h>
#include <array>
#include <atomic>
#include <climits>
#include <cstring>
#include <string>
#include <thread>
#include <vector>
#include <sys/mman.h>
#include <sys/wait.h>
#include <cerrno>
#include <unistd.h>

extern "C" int prepass_context_c_probe(const PrepassContextWire*);
namespace {
static_assert(sizeof(PrepassContextWire) == 856 && alignof(PrepassContextWire) == 4);
using Digests = std::array<char*, 5>;
Digests Fields(PrepassContextWire& c)
{ return {c.contractSha256Hex, c.policySha256Hex, c.toolSha256Hex, c.topologySha256Hex, c.runtimeGenerationSealSha256Hex}; }
PrepassContextWire Context()
{
    PrepassContextWire c{}; c.abiVersion = PREPASS_CONTEXT_WIRE_ABI; c.structSize = sizeof(c); c.userId = 100;
    std::strcpy(c.requestId, "request-42"); std::strcpy(c.packageName, "org.example.game"); std::strcpy(c.candidateGeneration, "generation-9");
    int n = 0; for (auto* field : Fields(c)) { std::memset(field, "012ab"[n++], 64); field[64] = 0; } return c;
}
const std::string apk(64, 'f');
int Match(const PrepassContextWire& c, const PrepassContextWire& expected, const std::string& digest = apk)
{ return PrepassContextWire_MatchBoundInput(&c, digest.data(), digest.size(), &expected, apk.data(), apk.size()); }
TEST(SPC_52_Contract, Valid)
{
    // Compile and invoke the complete unchanged original source, with assertions enabled.
    const pid_t child = fork(); ASSERT_GE(child, 0);
    if (child == 0) { execl(CONTEXT_ORIGINAL_EXECUTABLE, CONTEXT_ORIGINAL_EXECUTABLE, static_cast<char*>(nullptr)); _exit(127); }
    int status = 0; pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    ASSERT_EQ(waited, child); ASSERT_TRUE(WIFEXITED(status)); EXPECT_EQ(WEXITSTATUS(status), 0);
    auto c = Context(); const auto before = c;
    EXPECT_EQ(prepass_context_c_probe(&c), PREPASS_CONTEXT_WIRE_OK);
    EXPECT_EQ(PrepassContextWire_ValidateBytes(&c, sizeof(c)), PREPASS_CONTEXT_WIRE_OK);
    EXPECT_EQ(PrepassContextWire_ValidateForApk(&c, apk.data(), apk.size()), PREPASS_CONTEXT_WIRE_OK);
    EXPECT_EQ(Match(c, c), PREPASS_CONTEXT_WIRE_OK);
    EXPECT_EQ(PrepassContextWire_MatchPackageUser(&c, c.packageName, 100), PREPASS_CONTEXT_WIRE_OK);
    EXPECT_EQ(std::memcmp(&c, &before, sizeof(c)), 0);
    // Full capacity minus NUL; explicit nonzero user identities, never user-zero assumptions.
    std::memset(c.requestId, 'r', sizeof(c.requestId)-1); std::memset(c.packageName, 'p', sizeof(c.packageName)-1);
    std::memset(c.candidateGeneration, 'g', sizeof(c.candidateGeneration)-1); c.userId = INT_MAX;
    EXPECT_EQ(Match(c, c), PREPASS_CONTEXT_WIRE_OK);
    std::vector<unsigned char> unaligned(sizeof(c) + 1); std::memcpy(unaligned.data()+1, &c, sizeof(c));
    EXPECT_EQ(PrepassContextWire_ValidateBytes(unaligned.data()+1, sizeof(c)), PREPASS_CONTEXT_WIRE_OK);
    std::atomic<int> failures{0}; std::vector<std::thread> threads;
    for (int t = 0; t < 8; ++t) threads.emplace_back([t, &failures] {
        auto local = Context(); local.userId = 31 + t; local.requestId[0] = static_cast<char>('A' + t);
        const auto expected = local;
        for (int i = 0; i < 250; ++i) {
            if (Match(local, expected) != PREPASS_CONTEXT_WIRE_OK) ++failures;
            auto bad = local; bad.policySha256Hex[0] = 'f';
            if (Match(bad, expected) != PREPASS_CONTEXT_WIRE_PROFILE_MISMATCH) ++failures;
        }
    });
    for (auto& thread : threads) thread.join(); EXPECT_EQ(failures.load(), 0);
}
TEST(SPC_52_Contract, Rejected)
{
    const auto good = Context(); auto c = good;
    EXPECT_EQ(PrepassContextWire_Validate(nullptr), PREPASS_CONTEXT_WIRE_MISSING);
    c.abiVersion++; EXPECT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_BAD_ABI);
    for (uint32_t size : {0u, 8u, static_cast<uint32_t>(sizeof(c)-1), static_cast<uint32_t>(sizeof(c)+1), UINT_MAX}) {
        c = good; c.structSize = size; EXPECT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_BAD_STRUCT_SIZE);
    }
    c = good; c.reservedZero = 1; EXPECT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_RESERVED_NONZERO);
    for (int i = 0; i < 3; ++i) { c = good; c.reservedTail[i] = 1; EXPECT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_RESERVED_NONZERO); }
    c = good; c.userId = -1; EXPECT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_BAD_IDENTITY);
    for (const auto item : {std::pair{offsetof(PrepassContextWire, requestId), sizeof(c.requestId)},
            {offsetof(PrepassContextWire, packageName), sizeof(c.packageName)},
            {offsetof(PrepassContextWire, candidateGeneration), sizeof(c.candidateGeneration)}}) {
        for (int mutation = 0; mutation < 3; ++mutation) {
            c = good; char* field = reinterpret_cast<char*>(&c) + item.first;
            if (mutation == 0) field[0] = 0;
            if (mutation == 1) std::memset(field, 'x', item.second);
            if (mutation == 2) field[item.second-1] = 'x';
            EXPECT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_BAD_IDENTITY);
        }
    }
    for (size_t d = 0; d < 5; ++d) {
        for (int mutation = 0; mutation < 5; ++mutation) {
            c = good; auto* field = Fields(c)[d];
            if (mutation == 0) field[0] = 0;
            if (mutation == 1) field[13] = 'G';
            if (mutation == 2) field[63] = 0;
            if (mutation == 3) field[64] = '0';
            if (mutation == 4) field[7] = static_cast<char>(0xff);
            EXPECT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_BAD_DIGEST);
        }
        c = good; Fields(c)[d][0] = 'f';
        ASSERT_EQ(PrepassContextWire_Validate(&c), PREPASS_CONTEXT_WIRE_OK);
        EXPECT_EQ(Match(c, good), PREPASS_CONTEXT_WIRE_PROFILE_MISMATCH);
    }
    c = good; c.packageName[0] = 'x'; EXPECT_EQ(Match(c, good), PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH);
    c = good; c.userId++; EXPECT_EQ(Match(c, good), PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH);
    c = good; c.requestId[0] = 'x'; EXPECT_EQ(Match(c, good), PREPASS_CONTEXT_WIRE_IDENTITY_MISMATCH);
    c = good; c.candidateGeneration[0] = 'x'; EXPECT_EQ(Match(c, good), PREPASS_CONTEXT_WIRE_IDENTITY_MISMATCH);
    EXPECT_EQ(Match(good, good, std::string(64,'0')), PREPASS_CONTEXT_WIRE_APK_MISMATCH);
    for (const auto& digest : {std::string{}, std::string(63,'a'), std::string(65,'a'), std::string(64,'A'), std::string(64,'g'), std::string(64,'\0')}) {
        EXPECT_EQ(PrepassContextWire_ValidateForApk(&good, digest.data(), digest.size()), PREPASS_CONTEXT_WIRE_BAD_DIGEST);
        EXPECT_NE(Match(good, good, digest), PREPASS_CONTEXT_WIRE_OK);
    }
    EXPECT_EQ(PrepassContextWire_ValidateForApk(&good, nullptr, 64), PREPASS_CONTEXT_WIRE_BAD_DIGEST);
    EXPECT_NE(PrepassContextWire_MatchBoundInput(&good, apk.data(), 64, nullptr, apk.data(), 64), PREPASS_CONTEXT_WIRE_OK);
    c = good; c.abiVersion++; EXPECT_NE(Match(good, c), PREPASS_CONTEXT_WIRE_OK);
    EXPECT_EQ(PrepassContextWire_MatchPackageUser(&good, nullptr, 100), PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH);
    std::array<char, PREPASS_CONTEXT_PACKAGE_CAPACITY> nonterminated{}; nonterminated.fill('x');
    EXPECT_EQ(PrepassContextWire_MatchPackageUser(&good, nonterminated.data(), 100), PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH);
    // Accessible lengths are exact; an adjacent guard page detects accidental overreads.
    const long page = sysconf(_SC_PAGESIZE); ASSERT_GT(page, static_cast<long>(sizeof(c)));
    void* memory = mmap(nullptr, page*2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    ASSERT_NE(memory, MAP_FAILED);
    struct Unmap { void* memory; size_t size; ~Unmap() { munmap(memory, size); } } unmap{memory, static_cast<size_t>(page*2)};
    ASSERT_EQ(mprotect(static_cast<char*>(memory)+page, page, PROT_NONE), 0);
    for (size_t size = 0; size < sizeof(c); ++size) {
        auto* ptr = static_cast<char*>(memory) + page - size; std::memcpy(ptr, &good, size);
        EXPECT_EQ(PrepassContextWire_ValidateBytes(ptr, size), PREPASS_CONTEXT_WIRE_BAD_STRUCT_SIZE) << size;
    }
    EXPECT_EQ(PrepassContextWire_ValidateBytes(nullptr, sizeof(c)), PREPASS_CONTEXT_WIRE_MISSING);
    EXPECT_EQ(PrepassContextWire_ValidateBytes(&good, sizeof(c)+1), PREPASS_CONTEXT_WIRE_BAD_STRUCT_SIZE);
}
}
