#include "install_packet_fixture.h"
#include "game_install_plan_wire.h"
#include "apk_install_plan_v2.h"
#include "manifest_facts_v1.h"
#include "prepass_bundle.h"
#include "manifest_fixture.h"
#include <gtest/gtest.h>
#include <nlohmann/json.hpp>
#include <array>
#include <cerrno>
#include <cstring>
#include <cstdio>
#include <dirent.h>
#include <fcntl.h>
#include <functional>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
extern "C" int install_wire_c_probe(const ApkInstallPlanV2*);
namespace {
using namespace oh_adapter::package_transaction;
using namespace oh_adapter::manifest_facts;
using namespace manifest_fixture;
using Json = nlohmann::json;
using namespace install_packet_fixture;
void Original()
{
    pid_t child=fork(); ASSERT_GE(child,0);
    if (child==0) { execl(WIRE_ORIGINAL_EXECUTABLE,WIRE_ORIGINAL_EXECUTABLE,static_cast<char*>(nullptr)); _exit(127); }
    int status; pid_t waited; do { waited=waitpid(child,&status,0); } while(waited<0 && errno==EINTR);
    ASSERT_EQ(waited,child); ASSERT_TRUE(WIFEXITED(status)); EXPECT_EQ(WEXITSTATUS(status),0);
}
void CrossTargetLayout()
{
    // Actual freestanding C compilation checks declarations/layout, not OH
    // linking or execution. No fake headers are inserted for a target ABI.
    for (const char* target : {"i386-unknown-linux-gnu", "x86_64-unknown-linux-gnu", "armv7-unknown-linux-gnueabi", "aarch64-unknown-linux-gnu"}) {
        pid_t child=fork(); ASSERT_GE(child,0);
        if (child==0) {
            execl(WIRE_C_COMPILER, WIRE_C_COMPILER, "-target", target, "-std=c11", "-ffreestanding", "-fsyntax-only",
                "-I", WIRE_JNI_DIRECTORY, WIRE_C_PROBE_SOURCE, static_cast<char*>(nullptr)); _exit(127);
        }
        int status=0; pid_t waited; do { waited=waitpid(child,&status,0); } while(waited<0 && errno==EINTR);
        ASSERT_EQ(waited,child); ASSERT_TRUE(WIFEXITED(status));
        EXPECT_EQ(WEXITSTATUS(status),0) << "SPC50_V2_ALIGNMENT_8 target=" << target;
    }
}
void BadPayload(const Packet& packet, const std::string& bytes)
{
    TemporaryFd temp{Seal(bytes)}; auto bad=packet.plan; bad.manifestSigning=temp.span;
    EXPECT_NE(ApkInstallPlanV2_Validate(&bad),APK_INSTALL_PLAN_V2_OK) << bytes.substr(0,100);
}
// Build bytes directly so the fixture itself never constructs a deep JSON DOM.
void MetadataDepth(const Packet& packet, size_t arrays, int expected)
{
    auto bytes = packet.metadata.dump(); bytes.pop_back();
    bytes += ",\"zzExtension\":" + std::string(arrays, '[') + "0" + std::string(arrays, ']') + "}";
    TemporaryFd temp{Seal(bytes)}; auto plan = packet.plan; plan.manifestSigning = temp.span;
    const pid_t child = fork(); ASSERT_GE(child, 0);
    if (child == 0) {
        const auto before = FdCount();
        const int result = ApkInstallPlanV2_Validate(&plan);
        std::fprintf(stderr, "SPC50_METADATA_DEPTH_BOUNDED arrays=%zu status=%d expected=%d\n", arrays, result, expected);
        _exit(result == expected && FdCount() == before ? 0 : 1);
    }
    int status = 0; pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    ASSERT_EQ(waited, child);
    ASSERT_TRUE(WIFEXITED(status)) << "SPC50_METADATA_DEPTH_BOUNDED arrays=" << arrays;
    EXPECT_EQ(WEXITSTATUS(status), 0) << "SPC50_METADATA_DEPTH_BOUNDED arrays=" << arrays;
}
TEST(SPC_50_Contract, Valid)
{
    Original(); CrossTargetLayout(); const auto before=FdCount();
    for (const auto bits : {std::pair{0u,0u},{3u,17u},{0xffffffffu,0xffffffffu}}) {
        Packet packet(bits.first,bits.second);
        ASSERT_TRUE(packet.receipt.facts); EXPECT_TRUE(packet.receipt.facts->versionName.empty()); EXPECT_TRUE(packet.receipt.facts->components.empty());
        const auto snapshot=packet.plan; const auto count=FdCount();
        ASSERT_EQ(install_wire_c_probe(&packet.plan),APK_INSTALL_PLAN_V2_OK);
        EXPECT_EQ(ApkInstallPlanV2_ValidateBytes(&packet.plan,sizeof(packet.plan)),APK_INSTALL_PLAN_V2_OK);
        EXPECT_EQ(std::memcmp(&snapshot,&packet.plan,sizeof(snapshot)),0); EXPECT_EQ(FdCount(),count);
        EXPECT_EQ(lseek(packet.plan.artifacts[0].apk.fd,0,SEEK_CUR),static_cast<off_t>(packet.plan.artifacts[0].apk.byteLength));
        EXPECT_EQ(packet.plan.versionMajorBits,bits.first); EXPECT_EQ(packet.plan.versionMinorBits,bits.second);
        int fd=packet.plan.artifacts[0].apk.fd; ApkInstallPlanV2_Release(&packet.plan); ApkInstallPlanV2_Release(&packet.plan);
        errno=0; EXPECT_EQ(fcntl(fd,F_GETFD),-1); EXPECT_EQ(errno,EBADF); EXPECT_EQ(packet.plan.artifacts[0].apk.fd,-1);
    }
    EXPECT_EQ(FdCount(),before);
    GameInstallPlanWire legacy{}; legacy.abiVersion=GAME_INSTALL_PLAN_WIRE_ABI; legacy.structSize=sizeof(legacy);
    EXPECT_EQ(GameInstallPlanWire_TrySetVersion(&legacy,0,0xffffffffu),GAME_INSTALL_PLAN_WIRE_OK); EXPECT_EQ(legacy.versionCode,0xffffffffu);
    const auto unchanged=legacy; EXPECT_EQ(GameInstallPlanWire_TrySetVersion(&legacy,1,7),GAME_INSTALL_PLAN_WIRE_VERSION_REQUIRES_V2);
    EXPECT_EQ(std::memcmp(&legacy,&unchanged,sizeof(legacy)),0);
}
TEST(SPC_50_Contract, Rejected)
{
    Packet packet; const auto count=FdCount();
    using Mutation=std::function<void(ApkInstallPlanV2&)>;
    const std::vector<Mutation> mutations={
        [](auto& p){p.abiVersion=1;},[](auto& p){p.structSize--;},[](auto& p){p.capabilities=0;},[](auto& p){p.capabilities|=8;},
        [](auto& p){p.reservedZero=1;},[](auto& p){p.reservedTail[6]=1;},[](auto& p){p.context.reservedZero=1;},
        [](auto& p){p.context.userId++;},[](auto& p){p.context.requestId[0]='x';},[](auto& p){p.context.policySha256Hex[0]='b';},
        [](auto& p){p.versionPresenceBits=4;},[](auto& p){p.majorSource=0;},[](auto& p){p.majorSource=APK_INSTALL_VERSION_SOURCE_DEFAULT;},
        [](auto& p){p.versionPresenceBits=0;},[](auto& p){p.versionMajorBits++;},[](auto& p){p.versionMinorBits++;},
        [](auto& p){p.artifactCount=0;},[](auto& p){p.artifactCount=65;},[](auto& p){p.artifacts[0].role=99;},
        [](auto& p){p.artifacts[0].reservedZero=1;},[](auto& p){p.artifacts[0].artifactId[127]='x';},
        [](auto& p){p.artifactSetSha256Hex[0]=p.artifactSetSha256Hex[0]=='0'?'1':'0';},[](auto& p){p.payloadSchemaVersion=1;},
        [](auto& p){p.artifacts[0].apk.fd=-1;},[](auto& p){p.artifacts[0].apk.fd=1000000;},
        [](auto& p){p.artifacts[0].apk.byteLength=0;},[](auto& p){p.artifacts[0].apk.byteLength++;},
        [](auto& p){p.artifacts[0].apk.sha256Hex[0]='A';},[](auto& p){p.artifacts[0].apk.sha256Hex[0]=p.artifacts[0].apk.sha256Hex[0]=='0'?'1':'0';},
        [](auto& p){p.artifacts[0].apk.reservedTail[0]=1;},[](auto& p){p.artifacts[0].prepass.fd=p.artifacts[0].apk.fd;},
        [](auto& p){p.manifestSigning.fd=-1;},[](auto& p){p.manifestSigning.sha256Hex[0]=p.manifestSigning.sha256Hex[0]=='0'?'1':'0';},
        [](auto& p){p.artifacts[63].prepass.byteLength=1;}};
    for(size_t i=0;i<mutations.size();++i){auto bad=packet.plan;mutations[i](bad);EXPECT_NE(ApkInstallPlanV2_Validate(&bad),APK_INSTALL_PLAN_V2_OK)<<i;}
    EXPECT_EQ(FdCount(),count);
    std::string apk(packet.plan.artifacts[0].apk.byteLength, '\0');
    ASSERT_EQ(pread(packet.plan.artifacts[0].apk.fd, apk.data(), apk.size(), 0), static_cast<ssize_t>(apk.size()));
    constexpr int allSeals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;
    for (const int missing : {F_SEAL_WRITE, F_SEAL_SHRINK, F_SEAL_GROW, F_SEAL_SEAL}) {
        TemporaryFd temp{Seal(apk, allSeals & ~missing)};
        auto unsealed = packet.plan; unsealed.artifacts[0].apk = temp.span;
        EXPECT_EQ(ApkInstallPlanV2_Validate(&unsealed), APK_INSTALL_PLAN_V2_UNSEALED_FD) << missing;
    }
    MetadataDepth(packet, 4, APK_INSTALL_PLAN_V2_OK);
    MetadataDepth(packet, 63, APK_INSTALL_PLAN_V2_OK);
    MetadataDepth(packet, 64, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    MetadataDepth(packet, 30000, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    auto bad = packet.plan;
    for(const auto& bytes:{std::string{},std::string("{}"),packet.metadata.dump()+"\n"}) BadPayload(packet,bytes);
    for (const Mutation& change : std::vector<Mutation>{[](auto& p){p.context.packageName[0]='x';},[](auto& p){p.context.candidateGeneration[0]='x';}}) {bad=packet.plan;change(bad);EXPECT_NE(ApkInstallPlanV2_Validate(&bad),APK_INSTALL_PLAN_V2_OK);}
    auto body=packet.metadata; body["schemaVersion"]=1; BadPayload(packet,body.dump());
    body=packet.metadata; body["manifest"]["versionV2"]["major"]=3; BadPayload(packet,body.dump());
    body=packet.metadata; body["manifest"]["versionV2"]["minor"]="017"; BadPayload(packet,body.dump());
    body=packet.metadata; body["signing"]["verified"]=false; BadPayload(packet,body.dump());
    body=packet.metadata; body["signing"]["signerCertificateDigests"]=Json::array(); BadPayload(packet,body.dump());
    body=packet.metadata; body["manifest"]["facts"]["packageName"]="org.other"; BadPayload(packet,body.dump());
    EXPECT_EQ(ApkInstallPlanV2_Validate(nullptr),APK_INSTALL_PLAN_V2_BAD_ARGUMENT);
    GameInstallPlanV1 v1{}; EXPECT_NE(ApkInstallPlanV2_ValidateBytes(&v1,sizeof(v1)),APK_INSTALL_PLAN_V2_OK);
    EXPECT_NE(ApkInstallPlanV2_ValidateBytes(&packet.plan,sizeof(packet.plan)-1),APK_INSTALL_PLAN_V2_OK);
    EXPECT_NE(GameInstallPlanWire_Validate(reinterpret_cast<const GameInstallPlanWire*>(&packet.plan)),GAME_INSTALL_PLAN_WIRE_OK);
    EXPECT_EQ(FdCount(),count);
}
}
