#define _GNU_SOURCE 1
#include <errno.h>
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
