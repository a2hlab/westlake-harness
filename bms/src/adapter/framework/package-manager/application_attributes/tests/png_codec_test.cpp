#include <gtest/gtest.h>
#include <cerrno>
#include <sys/wait.h>
#include <unistd.h>
namespace {
void RunCodec(const char* mode)
{
    const pid_t child=fork(); ASSERT_GE(child,0);
    if (child==0) {
        execl(PNG_PYTHON,PNG_PYTHON,PNG_DRIVER,"--mode",mode,"--pm-root",PNG_PM_ROOT,
            "--build-dir",PNG_BUILD_DIR,"--zlib-root",PNG_ZLIB_ROOT,"--cc",PNG_CC,
            "--cxx",PNG_CXX,"--g1-apk",PNG_G1_APK,static_cast<char*>(nullptr));
        _exit(127);
    }
    int status=0; pid_t waited;
    do { waited=waitpid(child,&status,0); } while(waited<0 && errno==EINTR);
    ASSERT_EQ(waited,child); ASSERT_TRUE(WIFEXITED(status));
    EXPECT_EQ(WEXITSTATUS(status),0) << "SPC49_PRODUCTION_PATH_FAILED";
}
TEST(SPC_49_Contract, Valid) { RunCodec("valid"); }
TEST(SPC_49_Contract, Rejected) { RunCodec("rejected"); }
}
