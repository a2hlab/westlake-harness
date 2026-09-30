#define _GNU_SOURCE 1
#include <errno.h>
#include <dlfcn.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/select.h>
/* Copied functions: Westlake 532633da webview_bionic_shim.c. */
int __register_atfork(void (*prepare)(void), void (*parent)(void),
                      void (*child)(void), void *dso)
{
    (void)dso;
    fprintf(stderr, "[WESTLAKE-WEBVIEW-BIONIC] __register_atfork\n");
    return pthread_atfork(prepare, parent, child);
}

void __FD_CLR_chk(int fd, fd_set *set, size_t set_size)
{
    if (fd < 0 || (size_t)fd >= set_size * 8) {
        abort();
    }
    FD_CLR(fd, set);
}

int __FD_ISSET_chk(int fd, const fd_set *set, size_t set_size)
{
    if (fd < 0 || (size_t)fd >= set_size * 8) {
        abort();
    }
    return FD_ISSET(fd, set);
}

void __FD_SET_chk(int fd, fd_set *set, size_t set_size)
{
    if (fd < 0 || (size_t)fd >= set_size * 8) {
        abort();
    }
    FD_SET(fd, set);
}

extern int* __errno_location(void);
int* __errno(void) {
    return __errno_location();
}

/* Westlake property table/reader, Android ABI value buffer is 92 bytes. */
#define WEBVIEW_PROP_VALUE_MAX 92
static int read_oh_property(const char *name, char *value, size_t value_size)
{
    typedef int (*ReadParamFn)(const char *, char *, uint32_t *);
    static ReadParamFn read_param;
    static int resolved;
    if (!resolved) {
        read_param = (ReadParamFn)dlsym(RTLD_DEFAULT, "SystemReadParam");
        resolved = 1;
    }
    value[0] = '\0';
    if (read_param == NULL) {
        return 0;
    }
    uint32_t length = (uint32_t)value_size;
    if (read_param(name, value, &length) != 0) {
        value[0] = '\0';
        return 0;
    }
    value[value_size - 1] = '\0';
    return (int)strlen(value);
}

/*
 * Android-shaped property names OH's parameter store does not hold.
 *
 * Every name an Android caller asks for is absent from OH's store, so each read came back empty:
 * Chromium's sys_info_android.cc logged "Can't parse dalvik.vm.heapsize" and the four build
 * properties it reads for its own version gating were empty too. Worse than empty, they
 * disagreed with the process: android.os.SystemProperties answers these from a table in
 * framework/android-runtime/src/android_os_SystemProperties.cpp, so Java said SDK 34 while
 * native said nothing at all, and a caller that gates on one and branches on the other sees a
 * device that cannot exist.
 *
 * The values below are that table's, and must track it. Only names absent from OH's store fall
 * through to here, so a board that really does answer one wins.
 *
 * ro.arch and dalvik.vm.heapsize are not in that table because nothing in Java asks for them.
 * The heap size is a hint Chromium clamps into a sane range rather than a number it trusts; it is
 * reported as a plain Android default instead of a measurement, because this runtime's ART heap
 * ceiling is not the app's to know.
 */
static const struct {
    const char *name;
    const char *value;
} g_android_properties[] = {
    { "ro.build.version.sdk",      "34" },
    { "ro.build.version.release",  "14" },
    { "ro.build.version.codename", "REL" },
    { "ro.build.id",               "oh-adapter" },
    { "ro.arch",                   "arm64" },
    { "dalvik.vm.heapsize",        "512m" },
};

int __system_property_get(const char *name, char *value)
{
    if (name == NULL || value == NULL) {
        return 0;
    }
    int length = read_oh_property(name, value, WEBVIEW_PROP_VALUE_MAX);
    if (length == 0) {
        for (size_t i = 0; i < sizeof(g_android_properties) / sizeof(g_android_properties[0]); ++i) {
            if (strcmp(name, g_android_properties[i].name) == 0) {
                snprintf(value, WEBVIEW_PROP_VALUE_MAX, "%s", g_android_properties[i].value);
                length = (int)strlen(value);
                break;
            }
        }
    }
    fprintf(stderr, "[WESTLAKE-WEBVIEW-BIONIC] property %s=%s\n", name, value);
    return length;
}


void android_set_abort_message(const char *message)
{
    fprintf(stderr, "[WESTLAKE-WEBVIEW-BIONIC] abort message: %s\n",
            message != NULL ? message : "<null>");
}
