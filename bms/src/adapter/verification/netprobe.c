/*
 * netprobe.c - Standalone AF_INET socket permission probe for AonB D600.
 *
 * Drops to a target app uid/gid and tries to create AF_INET/AF_INET6 sockets.
 * Intended to verify the eBPF/NET-GID socket grant path (G6/N2).
 *
 * Must run as root so it can set supplementary groups and drop privileges.
 *
 * Usage:
 *   netprobe [uid] [gid]
 *
 * Build (OH NDK, aarch64-linux-ohos):
 *   clang --target=aarch64-linux-ohos --sysroot=$OH_NDK/sysroot -O2 \
 *         -o netprobe netprobe.c
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

static void try_socket(const char* label, int domain, int type) {
    errno = 0;
    int fd = socket(domain, type, 0);
    int e = errno;
    if (fd >= 0) {
        printf("[netprobe] %s fd=%d OK\n", label, fd);
        close(fd);
    } else {
        printf("[netprobe] %s fd=%d errno=%d (%s)%s\n",
               label, fd, e, strerror(e),
               (e == EPERM) ? " <<< BLOCKED" : "");
    }
}

int main(int argc, char** argv) {
    uid_t uid = (argc > 1) ? (uid_t)strtoul(argv[1], 0, 10) : 0;
    gid_t gid = (argc > 2) ? (gid_t)strtoul(argv[2], 0, 10) : uid;

    printf("[netprobe] start euid=%d target uid=%u gid=%u\n",
           (int)geteuid(), (unsigned)uid, (unsigned)gid);

    /* Supplementary groups commonly used for Android networking on OH. */
    gid_t groups[] = { gid, 3003 /* AID_INET */, 3004 /* AID_INET_RAW */ };
    if (setgroups(sizeof(groups)/sizeof(groups[0]), groups) < 0) {
        printf("[netprobe] setgroups failed errno=%d (%s)\n", errno, strerror(errno));
    } else {
        printf("[netprobe] setgroups OK\n");
    }

    if (setgid(gid) < 0)
        printf("[netprobe] setgid failed errno=%d (%s)\n", errno, strerror(errno));
    if (setuid(uid) < 0)
        printf("[netprobe] setuid failed errno=%d (%s)\n", errno, strerror(errno));

    printf("[netprobe] dropped uid=%d gid=%d\n", (int)getuid(), (int)getgid());

    try_socket("AF_INET  SOCK_STREAM", AF_INET,  SOCK_STREAM);
    try_socket("AF_INET  SOCK_DGRAM ", AF_INET,  SOCK_DGRAM);
    try_socket("AF_INET6 SOCK_STREAM", AF_INET6, SOCK_STREAM);

    printf("[netprobe] done\n");
    return 0;
}
