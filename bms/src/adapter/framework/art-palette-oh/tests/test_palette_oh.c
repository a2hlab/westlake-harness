#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define OK 0
#define CHECK_ERRNO 1
#define INVALID 2
#define NOT_SUPPORTED 3

int32_t PaletteSchedSetPriority(int32_t tid, int32_t priority);
int32_t PaletteSchedGetPriority(int32_t tid, int32_t *priority);
int32_t PaletteWriteCrashThreadStacks(const char *stacks, size_t size);
int32_t PaletteTraceEnabled(_Bool *enabled);
int32_t PaletteAshmemCreateRegion(const char *name, size_t size, int *fd);
int32_t PaletteCreateOdrefreshStagingDirectory(const char **directory);
int32_t PaletteSetTaskProfiles(int32_t tid, const char *const profiles[],
                               size_t count);

static int g_log_writes;

int __android_log_write(int priority, const char *tag, const char *text)
{
    if (priority == 4 && tag != NULL && text != NULL) {
        ++g_log_writes;
        return 1;
    }
    return -1;
}

static void Check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL %s\n", message);
        exit(1);
    }
}

static void TestValidationAndCapabilities(void)
{
    int32_t priority = 0;
    _Bool trace = 1;
    int fd = 77;
    const char *directory = "not-cleared";
    Check(PaletteSchedSetPriority(getpid(), 0) == INVALID,
          "priority zero accepted");
    Check(PaletteSchedSetPriority(getpid(), 11) == INVALID,
          "priority eleven accepted");
    Check(PaletteSchedGetPriority(getpid(), NULL) == INVALID,
          "null priority output accepted");
    Check(PaletteSchedGetPriority(INT32_C(2147483647), &priority) ==
              CHECK_ERRNO &&
              priority == 5,
          "missing tid did not fail with normal fallback");
    Check(PaletteTraceEnabled(&trace) == OK && !trace,
          "trace capability was not explicitly disabled");
    Check(PaletteWriteCrashThreadStacks("stack", 5) == OK &&
              g_log_writes == 1,
          "crash stack did not use log boundary");
    Check(PaletteAshmemCreateRegion("jit", 4096, &fd) == NOT_SUPPORTED &&
              fd == -1,
          "ashmem unsupported contract drift");
    Check(PaletteCreateOdrefreshStagingDirectory(&directory) ==
              NOT_SUPPORTED &&
              directory == NULL,
          "odrefresh unsupported contract drift");
    Check(PaletteSetTaskProfiles(getpid(), NULL, 0) == NOT_SUPPORTED,
          "task profiles falsely reported success");
}

static void TestRealPriorityWrite(void)
{
    const pid_t child = fork();
    Check(child >= 0, "fork failed");
    if (child == 0) {
        int32_t managed = 0;
        if (PaletteSchedSetPriority(getpid(), 1) != OK ||
            PaletteSchedGetPriority(getpid(), &managed) != OK || managed != 1) {
            _exit(91);
        }
        _exit(0);
    }
    int status = 0;
    Check(waitpid(child, &status, 0) == child, "waitpid failed");
    Check(WIFEXITED(status) && WEXITSTATUS(status) == 0,
          "real setpriority/getpriority mapping failed");
}

int main(void)
{
    TestValidationAndCapabilities();
    TestRealPriorityWrite();
    puts("PASS art_palette_oh real_priority=1 diagnostics_explicit=1");
    return 0;
}
