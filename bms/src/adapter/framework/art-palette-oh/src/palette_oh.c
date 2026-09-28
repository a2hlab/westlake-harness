/*
 * WestLake ART Palette platform boundary for OpenHarmony.
 *
 * This is deliberately C: Palette is a C ABI, and the target boundary must
 * not inherit unrelated libc++ compatibility shims. Thread priority is real;
 * unsupported platform capabilities report that fact explicitly.
 */

#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/resource.h>
#include <sys/types.h>

typedef int32_t palette_status_t;

#define PALETTE_STATUS_OK ((palette_status_t)0)
#define PALETTE_STATUS_CHECK_ERRNO ((palette_status_t)1)
#define PALETTE_STATUS_INVALID_ARGUMENT ((palette_status_t)2)
#define PALETTE_STATUS_NOT_SUPPORTED ((palette_status_t)3)
#define PALETTE_STATUS_FAILED_CHECK_LOG ((palette_status_t)4)

#define PALETTE_NORMAL_MANAGED_PRIORITY INT32_C(5)
#define PALETTE_MIN_MANAGED_PRIORITY INT32_C(1)
#define PALETTE_MAX_MANAGED_PRIORITY INT32_C(10)
#define PALETTE_MANAGED_PRIORITY_COUNT UINT32_C(10)

/* Frozen AOSP Android mapping: 19, 16, 13, 10, 0, -2, -4, -5, -6, -8. */
static const int kNiceValues[PALETTE_MANAGED_PRIORITY_COUNT] = {
    19, 16, 13, 10, 0, -2, -4, -5, -6, -8,
};

/* Real liblog owner maps this write to OH hilog. */
extern int __android_log_write(int priority, const char *tag,
                               const char *text);

palette_status_t PaletteSchedSetPriority(int32_t tid, int32_t priority)
{
    if (priority < PALETTE_MIN_MANAGED_PRIORITY ||
        priority > PALETTE_MAX_MANAGED_PRIORITY) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    const size_t index = (size_t)(priority - PALETTE_MIN_MANAGED_PRIORITY);
#if defined(WL_PALETTE_MUTANT_FAKE_SCHED_SUCCESS)
    (void)tid;
    (void)index;
    return PALETTE_STATUS_OK;
#else
    return setpriority(PRIO_PROCESS, (id_t)tid, kNiceValues[index]) == 0
               ? PALETTE_STATUS_OK
               : PALETTE_STATUS_CHECK_ERRNO;
#endif
}

palette_status_t PaletteSchedGetPriority(int32_t tid,
                                         int32_t *managed_priority)
{
    if (managed_priority == NULL) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    errno = 0;
    const int native_priority = getpriority(PRIO_PROCESS, (id_t)tid);
    if (native_priority == -1 && errno != 0) {
        *managed_priority = PALETTE_NORMAL_MANAGED_PRIORITY;
        return PALETTE_STATUS_CHECK_ERRNO;
    }
    for (int32_t priority = PALETTE_MIN_MANAGED_PRIORITY;
         priority <= PALETTE_MAX_MANAGED_PRIORITY; ++priority) {
        const size_t index =
            (size_t)(priority - PALETTE_MIN_MANAGED_PRIORITY);
        if (native_priority >= kNiceValues[index]) {
            *managed_priority = priority;
            return PALETTE_STATUS_OK;
        }
    }
    *managed_priority = PALETTE_MAX_MANAGED_PRIORITY;
    return PALETTE_STATUS_OK;
}

palette_status_t PaletteWriteCrashThreadStacks(const char *stacks,
                                                size_t stacks_len)
{
    if (stacks == NULL && stacks_len != 0U) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    if (stacks == NULL || __android_log_write(4, "ART", stacks) >= 0) {
        return PALETTE_STATUS_OK;
    }
    return PALETTE_STATUS_FAILED_CHECK_LOG;
}

/* Trace is an explicit disabled diagnostic capability. */
palette_status_t PaletteTraceEnabled(bool *enabled)
{
    if (enabled == NULL) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    *enabled = false;
    return PALETTE_STATUS_OK;
}

palette_status_t PaletteTraceBegin(const char *name)
{
    (void)name;
    return PALETTE_STATUS_OK;
}

palette_status_t PaletteTraceEnd(void)
{
    return PALETTE_STATUS_OK;
}

palette_status_t PaletteTraceIntegerValue(const char *name, int32_t value)
{
    (void)name;
    (void)value;
    return PALETTE_STATUS_OK;
}

/* Cross-process JIT zygote ashmem is compiled out of non-Bionic ART. */
palette_status_t PaletteAshmemCreateRegion(const char *name, size_t size,
                                           int *fd)
{
    (void)name;
    (void)size;
    if (fd == NULL) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    *fd = -1;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteAshmemSetProtRegion(int fd, int prot)
{
    (void)fd;
    (void)prot;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteCreateOdrefreshStagingDirectory(
    const char **staging_dir)
{
    if (staging_dir == NULL) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    *staging_dir = NULL;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteShouldReportDex2oatCompilation(bool *value)
{
    if (value == NULL) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    *value = false;
    return PALETTE_STATUS_OK;
}

palette_status_t PaletteNotifyStartDex2oatCompilation(int source_fd,
                                                       int art_fd, int oat_fd,
                                                       int vdex_fd)
{
    (void)source_fd;
    (void)art_fd;
    (void)oat_fd;
    (void)vdex_fd;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteNotifyEndDex2oatCompilation(int source_fd, int art_fd,
                                                     int oat_fd, int vdex_fd)
{
    (void)source_fd;
    (void)art_fd;
    (void)oat_fd;
    (void)vdex_fd;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteNotifyDexFileLoaded(const char *path)
{
    (void)path;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteNotifyOatFileLoaded(const char *path)
{
    (void)path;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteShouldReportJniInvocations(bool *value)
{
    if (value == NULL) {
        return PALETTE_STATUS_INVALID_ARGUMENT;
    }
    *value = false;
    return PALETTE_STATUS_OK;
}

palette_status_t PaletteNotifyBeginJniInvocation(void *env)
{
    (void)env;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteNotifyEndJniInvocation(void *env)
{
    (void)env;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteReportLockContention(
    void *env, int32_t wait_ms, const char *filename, int32_t line_number,
    const char *method_name, const char *owner_filename,
    int32_t owner_line_number, const char *owner_method_name,
    const char *proc_name, const char *thread_name)
{
    (void)env;
    (void)wait_ms;
    (void)filename;
    (void)line_number;
    (void)method_name;
    (void)owner_filename;
    (void)owner_line_number;
    (void)owner_method_name;
    (void)proc_name;
    (void)thread_name;
    return PALETTE_STATUS_NOT_SUPPORTED;
}

palette_status_t PaletteSetTaskProfiles(int32_t tid,
                                        const char *const profiles[],
                                        size_t profiles_len)
{
    (void)tid;
    (void)profiles;
    (void)profiles_len;
    return PALETTE_STATUS_NOT_SUPPORTED;
}
