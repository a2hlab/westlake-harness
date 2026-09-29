#include <gtest/gtest.h>
#include <cerrno>
#include <sys/wait.h>
#include <unistd.h>

namespace {
void RunGraph(const char* mode)
{
    const pid_t child = fork();
    ASSERT_GE(child, 0);
    if (child == 0) {
        execl(TRANSACTION_PYTHON, TRANSACTION_PYTHON, TRANSACTION_DRIVER,
            "--mode", mode, "--pm-root", TRANSACTION_PM_ROOT,
            "--build-dir", TRANSACTION_BUILD_DIR, "--cc", TRANSACTION_CC,
            "--cxx", TRANSACTION_CXX, "--ar", TRANSACTION_AR,
            static_cast<char*>(nullptr));
        _exit(127);
    }
    int status = 0;
    pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    ASSERT_EQ(waited, child);
    ASSERT_TRUE(WIFEXITED(status));
    EXPECT_EQ(WEXITSTATUS(status), 0) << "SPC46_PRODUCTION_GRAPH_FAILED";
}
TEST(SPC_46_Contract, Valid) { RunGraph("Valid"); }
TEST(SPC_46_Contract, Rejected) { RunGraph("Rejected"); }
}
