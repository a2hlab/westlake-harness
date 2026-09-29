#include "install_input_v2.h"
#include "game_install_plan_wire.h"
#include "install_packet_fixture.h"
#include <gtest/gtest.h>
#include <array>
#include <atomic>
#include <cstdarg>
#include <limits>
#include <new>
#include <execinfo.h>
#include <thread>
#include <vector>
extern "C" int install_input_c_probe(const void*, size_t, int32_t, uint64_t, void*, size_t);
namespace {
thread_local int failAllocation = -1;
thread_local int failDup = -1;
thread_local bool throwOther = false;
thread_local int allocationPosition = -1;
}
extern "C" void* __real__Znwm(size_t);
extern "C" void* __wrap__Znwm(size_t size)
{
    if (failAllocation == 0) {
        failAllocation = -1;
        if (throwOther) throw std::runtime_error("allocator edge exception");
        throw std::bad_alloc();
    }
    if (failAllocation > 0) --failAllocation;
    return __real__Znwm(size);
}
extern "C" int __real_fcntl(int, int, ...);
extern "C" int __wrap_fcntl(int fd, int command, ...)
{
    if (command == F_DUPFD_CLOEXEC) {
        va_list args; va_start(args, command); const int minimum = va_arg(args, int); va_end(args);
        if (failDup == 0) { failDup = -1; errno = EMFILE; return -1; }
        if (failDup > 0) --failDup;
        return __real_fcntl(fd, command, minimum);
    }
    if (command == F_ADD_SEALS || command == F_SETFD || command == F_SETFL) {
        va_list args; va_start(args, command); const int arg = va_arg(args, int); va_end(args);
        return __real_fcntl(fd, command, arg);
    }
    return __real_fcntl(fd, command);
}
namespace {
using namespace install_packet_fixture;
int Acquire(const ApkInstallPlanV2& plan, OhAdapterInstallInputV2* output, uint64_t flags = UINT64_MAX)
{
    return install_input_c_probe(&plan, sizeof(plan), plan.context.userId, flags, output, sizeof(*output));
}
void Empty(const OhAdapterInstallInputV2& output)
{
    OhAdapterInstallInputV2 expected; OhAdapterInstallInputV2_Init(&expected);
    EXPECT_EQ(std::memcmp(&expected, &output, sizeof(output)), 0) << "SPC24_FAILURE_NO_DTO_OR_FD";
}
TEST(SPC_24_Contract, AbiAndOwnership)
{
    Packet packet;
    const auto count = FdCount(); const auto snapshot = packet.plan;
    for (uint64_t flags : {uint64_t{0}, UINT64_C(0x8000000100000000), UINT64_MAX}) {
        OhAdapterInstallInputV2 output;
        ASSERT_EQ(Acquire(packet.plan, &output, flags), APK_INSTALL_PLAN_V2_OK);
        EXPECT_EQ(output.requestedFlags, flags); EXPECT_EQ(output.userId, 27);
        EXPECT_EQ(output.plan.context.userId, 27);
        EXPECT_NE(output.plan.manifestSigning.fd, packet.plan.manifestSigning.fd);
        EXPECT_NE(output.plan.artifacts[0].apk.fd, packet.plan.artifacts[0].apk.fd);
        EXPECT_NE(output.plan.artifacts[0].prepass.fd, packet.plan.artifacts[0].prepass.fd);
        EXPECT_EQ(FdCount(), count + 3);
        for (int fd : {output.plan.manifestSigning.fd, output.plan.artifacts[0].apk.fd, output.plan.artifacts[0].prepass.fd})
            EXPECT_NE(fcntl(fd, F_GETFD) & FD_CLOEXEC, 0);
        EXPECT_EQ(ApkInstallPlanV2_Validate(&output.plan), APK_INSTALL_PLAN_V2_OK);
        OhAdapterInstallInputV2_Release(&output); OhAdapterInstallInputV2_Release(&output);
        Empty(output); EXPECT_EQ(FdCount(), count);
        EXPECT_EQ(std::memcmp(&snapshot, &packet.plan, sizeof(snapshot)), 0);
    }
    EXPECT_EQ(oh_adapter_install_input_abi_v2(), (UINT64_C(2) << 32) | sizeof(OhAdapterInstallInputV2));
    std::atomic<int> failures{0}; std::vector<std::thread> workers;
    for (unsigned i = 0; i < 8; ++i) workers.emplace_back([&, i] {
        for (unsigned n = 0; n < 10; ++n) {
            const uint64_t flags = UINT64_C(0x8000000000000000) | (uint64_t{i} << 32) | n;
            OhAdapterInstallInputV2 output;
            if (Acquire(packet.plan, &output, flags) != APK_INSTALL_PLAN_V2_OK || output.requestedFlags != flags ||
                output.userId != packet.plan.context.userId) ++failures;
            OhAdapterInstallInputV2_Release(&output);
        }
    });
    for (auto& worker : workers) worker.join();
    EXPECT_EQ(failures, 0); EXPECT_EQ(FdCount(), count);
    // Byte APIs may receive unaligned buffers; the typed release receives a
    // copied aligned owner and closes exactly those transferred descriptors.
    std::vector<unsigned char> in(sizeof(packet.plan) + 1), out(sizeof(OhAdapterInstallInputV2) + 1);
    std::memcpy(in.data() + 1, &packet.plan, sizeof(packet.plan));
    ASSERT_EQ(install_input_c_probe(in.data()+1, sizeof(packet.plan), 27, UINT64_MAX,
        out.data()+1, sizeof(OhAdapterInstallInputV2)), APK_INSTALL_PLAN_V2_OK);
    OhAdapterInstallInputV2 owned; std::memcpy(&owned, out.data()+1, sizeof(owned));
    OhAdapterInstallInputV2_Release(&owned); EXPECT_EQ(FdCount(), count);
}
TEST(SPC_24_Contract, BadInputAndFailure)
{
    std::set_terminate([] {
        std::fprintf(stderr, "SPC24_OOM_TERMINATED position=%d\n", allocationPosition);
        void* frames[64]; const int count = backtrace(frames, 64);
        backtrace_symbols_fd(frames, count, STDERR_FILENO);
        std::abort();
    });
    void* warmup[1]; backtrace(warmup, 1);
    Packet packet; OhAdapterInstallInputV2 output;
    const auto count = FdCount();
    EXPECT_EQ(install_input_c_probe(&packet.plan, sizeof(packet.plan), -1, 0, &output, sizeof(output)), APK_INSTALL_PLAN_V2_BAD_CONTEXT);
    Empty(output);
    EXPECT_EQ(install_input_c_probe(&packet.plan, sizeof(packet.plan), 28, 0, &output, sizeof(output)), APK_INSTALL_PLAN_V2_BAD_CONTEXT); Empty(output);
    EXPECT_EQ(install_input_c_probe(nullptr, sizeof(packet.plan), 27, 0, &output, sizeof(output)), APK_INSTALL_PLAN_V2_BAD_ARGUMENT); Empty(output);
    for (size_t length : {size_t{0}, size_t{7}, sizeof(packet.plan)-1, sizeof(packet.plan)+1, SIZE_MAX}) {
        EXPECT_EQ(install_input_c_probe(&packet.plan, length, 27, 0, &output, sizeof(output)), APK_INSTALL_PLAN_V2_BAD_SIZE);
        Empty(output);
    }
    for (size_t capacity : {size_t{0}, sizeof(output)-1, sizeof(output)+1, SIZE_MAX}) {
        std::memset(&output, 0x5a, sizeof(output)); const auto before = output;
        EXPECT_EQ(install_input_c_probe(&packet.plan, sizeof(packet.plan), 27, 0, &output, capacity), APK_INSTALL_PLAN_V2_BAD_SIZE);
        EXPECT_EQ(std::memcmp(&before, &output, sizeof(output)), 0);
    }
    EXPECT_EQ(install_input_c_probe(&packet.plan, sizeof(packet.plan), 27, 0, nullptr, sizeof(output)), APK_INSTALL_PLAN_V2_BAD_ARGUMENT);
    std::array<unsigned char, sizeof(OhAdapterInstallInputV2)> overlapping{};
    std::memcpy(overlapping.data(), &packet.plan, sizeof(packet.plan)); const auto before = overlapping;
    EXPECT_EQ(install_input_c_probe(overlapping.data(), sizeof(packet.plan), 27, 0,
        overlapping.data(), overlapping.size()), APK_INSTALL_PLAN_V2_BAD_ARGUMENT);
    EXPECT_EQ(overlapping, before);
    for (int mutation = 0; mutation < 5; ++mutation) {
        auto bad = packet.plan;
        if (mutation == 0) bad.abiVersion = 1;
        if (mutation == 1) bad.structSize = sizeof(GameInstallPlanV1);
        if (mutation == 2) std::memset(bad.context.packageName, 'x', sizeof(bad.context.packageName));
        if (mutation == 3) bad.artifactCount = UINT32_MAX;
        if (mutation == 4) bad.manifestSigning.byteLength = UINT64_MAX;
        EXPECT_NE(Acquire(bad, &output), APK_INSTALL_PLAN_V2_OK); Empty(output); EXPECT_EQ(FdCount(), count);
    }
    // Short input immediately precedes an inaccessible page. Length must be
    // rejected before any full-object read; this is not a fake pointer test.
    const size_t page = static_cast<size_t>(sysconf(_SC_PAGESIZE));
    auto* guard = static_cast<char*>(mmap(nullptr, page*2, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0));
    ASSERT_NE(guard, MAP_FAILED); ASSERT_EQ(mprotect(guard+page, page, PROT_NONE), 0);
    EXPECT_EQ(install_input_c_probe(guard+page-1, 1, 27, 0, &output, sizeof(output)), APK_INSTALL_PLAN_V2_BAD_SIZE);
    Empty(output); munmap(guard, page*2);
    bool exhausted = false;
    for (int position = 0; position < 4096; ++position) {
        allocationPosition = position; failAllocation = position;
        const int status = Acquire(packet.plan, &output);
        failAllocation = -1;
        if (status == APK_INSTALL_PLAN_V2_OK) { OhAdapterInstallInputV2_Release(&output); exhausted = true; break; }
        EXPECT_EQ(status, APK_INSTALL_PLAN_V2_RESOURCE_ERROR) << "SPC24_OOM_CONTAINED position=" << position;
        Empty(output); ASSERT_EQ(FdCount(), count);
    }
    EXPECT_TRUE(exhausted) << "SPC24_ALLOCATION_SWEEP_COMPLETE";
    failAllocation = 0; throwOther = true;
    const int exceptional = Acquire(packet.plan, &output);
    failAllocation = -1; throwOther = false;
    EXPECT_EQ(exceptional, APK_INSTALL_PLAN_V2_RESOURCE_ERROR); Empty(output);
    for (int position = 0; position < 6; ++position) {
        failDup = position;
        EXPECT_NE(Acquire(packet.plan, &output), APK_INSTALL_PLAN_V2_OK);
        failDup = -1; Empty(output); EXPECT_EQ(FdCount(), count);
    }
    EXPECT_EQ(ApkInstallPlanV2_Validate(&packet.plan), APK_INSTALL_PLAN_V2_OK);
}
}
