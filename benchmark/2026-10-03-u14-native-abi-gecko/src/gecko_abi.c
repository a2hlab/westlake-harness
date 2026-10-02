/*
 * libwestlake_native_abi: the 10 bionic exports Gecko (firefox / fennec 156) needs in the route-A native domain
 * (benchmark/2026-10-03-gecko-fatal-before-bind: musl-order replay of libmozglue / libxul). Linked as an extra object
 * next to native_abi.o / stdio.o; exported at version LIBC through native_abi_gecko.map. Bodies are copied, not
 * rewritten:
 *   __gnu_strerror_r, __open_2, __cmsg_nxthdr, strtoll_l, strtoull_l, __strncpy_chk2, __pthread_cleanup_push/pop
 *       vm-copies/westlake-current framework/webview-shim/webview_bionic_shim.c @532633d
 *       (lines 1481, 1619, 1630, 1680, 1686, 1749, 1861-1883; the old-route libwebview_bionic_shim.so 85c789f4)
 *   __assert2
 *       vm-copies/westlake-current framework/appspawn-x/bionic_compat/src/bionic_assert_compat.c @e2b0bf6 line 133
 *   android_dlopen_ext
 *       NOT in this file (outer decision 04:11): src/android_dlopen_ext.c + android_dlext_abi.h, copied unchanged from
 *       benchmark/2026-10-01-u10-native-shims/overlay (7337a393), the source of the deployed libbionic_compat
 *       015aa3a6's android_dlopen_ext: forward to __loader_android_dlopen_ext only when that backend exists; empty
 *       extinfo or flags == 0 -> plain dlopen; otherwise ENOTSUP + "[U10-DLEXT] backend absent; refusing extension".
 *       (86882caf had the bare AOSP libdl.cpp forward, which on route A resolves the weak backend to 0.)
 */
#include <errno.h>
#include <fcntl.h>
#include <locale.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

/* ---- webview_bionic_shim.c @532633d:1481 ---- */
char *__gnu_strerror_r(int error_number, char *buffer, size_t buffer_size)
{
    if (buffer == NULL || buffer_size == 0) {
        return (char *)strerror(error_number);
    }
    if (strerror_r(error_number, buffer, buffer_size) != 0) {
        snprintf(buffer, buffer_size, "Unknown error %d", error_number);
    }
    return buffer;
}

/* ---- webview_bionic_shim.c @532633d:1619 ---- */
int __open_2(const char *path, int flags)
{
    if ((flags & O_CREAT) != 0) {
        fprintf(stderr,
                "[WESTLAKE-WEBVIEW-BIONIC] __open_2 rejected O_CREAT path=%s\n",
                path != NULL ? path : "<null>");
        abort();
    }
    return open(path, flags);
}

/* ---- webview_bionic_shim.c @532633d:1630 ---- */
struct cmsghdr *__cmsg_nxthdr(struct msghdr *message, struct cmsghdr *control)
{
    struct cmsghdr *next = (struct cmsghdr *)((char *)control +
            CMSG_ALIGN(control->cmsg_len));
    size_t length = (size_t)((char *)(next + 1) - (char *)message->msg_control);
    return length > message->msg_controllen ? NULL : next;
}

/* ---- webview_bionic_shim.c @532633d:1680 / 1686 ---- */
long long strtoll_l(const char *text, char **end, int base, locale_t locale)
{
    (void)locale;
    return strtoll(text, end, base);
}

unsigned long long strtoull_l(const char *text, char **end, int base, locale_t locale)
{
    (void)locale;
    return strtoull(text, end, base);
}

/* ---- webview_bionic_shim.c @532633d:1749 ---- */
char *__strncpy_chk2(char *dst, const char *src, size_t count,
                     size_t dst_size, size_t src_size)
{
    if (count > dst_size) {
        fprintf(stderr,
                "[WESTLAKE-WEBVIEW-BIONIC] __strncpy_chk2 write overflow count=%zu dst=%zu\n",
                count, dst_size);
        abort();
    }

    char *result = dst;
    const char *source_start = src;
    while (count != 0) {
        if ((size_t)(src - source_start) >= src_size) {
            fprintf(stderr,
                    "[WESTLAKE-WEBVIEW-BIONIC] __strncpy_chk2 read overflow src=%zu\n",
                    src_size);
            abort();
        }
        *dst = *src;
        ++dst;
        ++src;
        --count;
        if (dst[-1] == '\0') {
            memset(dst, 0, count);
            break;
        }
    }
    return result;
}

/* ---- webview_bionic_shim.c @532633d:1855-1883 ----
 * pthread_cleanup_push/pop: bionic's headers expand these into calls that
 * link a caller-owned record onto a per-thread list; musl keeps its own
 * layout. bionic has no pthread_cancel, so only explicit pop runs handlers.
 */
typedef struct WebviewBionicCleanup {
    struct WebviewBionicCleanup *prev;
    void (*routine)(void *);
    void *arg;
} WebviewBionicCleanup;

static __thread WebviewBionicCleanup *g_cleanup_head;

void __pthread_cleanup_push(WebviewBionicCleanup *c, void (*routine)(void *), void *arg)
{
    c->routine = routine;
    c->arg = arg;
    c->prev = g_cleanup_head;
    g_cleanup_head = c;
}

void __pthread_cleanup_pop(WebviewBionicCleanup *c, int execute)
{
    g_cleanup_head = c->prev;
    if (execute) {
        c->routine(c->arg);
    }
}

/* ---- bionic_assert_compat.c @e2b0bf6:133 ---- */
/* WESTLAKE §755 (2026-08-20): match AOSP bionic's fail-fast contract. */
__attribute__((noreturn, visibility("default")))
void __assert2(const char* file, int line, const char* function,
               const char* failed_expression) {
    fprintf(stderr, "%s:%d: %s: assertion \"%s\" failed\n",
            file ? file : "?", line, function ? function : "?",
            failed_expression ? failed_expression : "?");
    fflush(stderr);
    abort();
}
