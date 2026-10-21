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

/* Additional property cache/read API: exact Westlake 532633da bodies. */
#define WEBVIEW_PROP_NAME_MAX 128
#define WEBVIEW_PROP_CACHE_SIZE 64

struct prop_info {
    char name[WEBVIEW_PROP_NAME_MAX];
    char value[WEBVIEW_PROP_VALUE_MAX];
    uint32_t serial;
};

static struct prop_info g_property_cache[WEBVIEW_PROP_CACHE_SIZE];
static size_t g_property_count;
static uint32_t g_property_serial;
static pthread_mutex_t g_property_mutex = PTHREAD_MUTEX_INITIALIZER;

const struct prop_info *__system_property_find(const char *name)
{
    if (name == NULL) {
        return NULL;
    }
    char value[WEBVIEW_PROP_VALUE_MAX];
    if (read_oh_property(name, value, sizeof(value)) == 0) {
        return NULL;
    }

    pthread_mutex_lock(&g_property_mutex);
    struct prop_info *entry = NULL;
    for (size_t i = 0; i < g_property_count; ++i) {
        if (strcmp(g_property_cache[i].name, name) == 0) {
            entry = &g_property_cache[i];
            break;
        }
    }
    if (entry == NULL && g_property_count < WEBVIEW_PROP_CACHE_SIZE) {
        entry = &g_property_cache[g_property_count++];
        snprintf(entry->name, sizeof(entry->name), "%s", name);
    }
    if (entry != NULL) {
        snprintf(entry->value, sizeof(entry->value), "%s", value);
        entry->serial = ++g_property_serial;
    }
    pthread_mutex_unlock(&g_property_mutex);
    return entry;
}

void __system_property_read_callback(
        const struct prop_info *property,
        void (*callback)(void *, const char *, const char *, uint32_t),
        void *cookie)
{
    if (property != NULL && callback != NULL) {
        callback(cookie, property->name, property->value, property->serial);
    }
}


/* Android OpenSL ES extension identifiers on the OpenHarmony audio boundary. */
#include <dlfcn.h>
#include <stdint.h>

typedef struct SlInterfaceId {
    uint32_t time_low;
    uint16_t time_mid;
    uint16_t time_high_and_version;
    uint16_t clock_sequence;
    uint8_t node[6];
} SlInterfaceId;

typedef const SlInterfaceId* SlInterfaceIdPtr;

static const SlInterfaceId kAndroidConfiguration = {
    0x89f6a7e0, 0xbeac, 0x11df, 0x8b5c,
    {0x00, 0x02, 0xa5, 0xd5, 0xc5, 0x1b},
};
static const SlInterfaceId kAndroidSimpleBufferQueue = {
    0x198e4940, 0xc5d7, 0x11df, 0xa2a6,
    {0x00, 0x02, 0xa5, 0xd5, 0xc5, 0x1b},
};

/* ELF data symbols: Android clients load the pointer stored in each one. */
__attribute__((visibility("default")))
SlInterfaceIdPtr SL_IID_ANDROIDCONFIGURATION = &kAndroidConfiguration;

__attribute__((visibility("default")))
SlInterfaceIdPtr SL_IID_ANDROIDSIMPLEBUFFERQUEUE = &kAndroidSimpleBufferQueue;

__attribute__((constructor))
static void westlake_map_simple_buffer_queue(void) {
    /* OH implements the standard buffer queue and compares IID pointers.
     * Android's simple queue is API-compatible for PCM playback, so use the
     * exact IID pointer exported by OH when it is present. */
    SlInterfaceIdPtr* oh_buffer_queue =
            (SlInterfaceIdPtr*)dlsym(RTLD_DEFAULT, "SL_IID_BUFFERQUEUE");
    if (oh_buffer_queue != 0 && *oh_buffer_queue != 0) {
        SL_IID_ANDROIDSIMPLEBUFFERQUEUE = *oh_buffer_queue;
    }
}
