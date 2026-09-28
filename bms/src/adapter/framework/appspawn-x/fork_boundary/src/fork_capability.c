#include "fork_capability.h"

#include <errno.h>
#include <poll.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int fork_capability_channel_create(int *out_parent_fd, int *out_child_fd) {
#ifdef MUTANT_FR001_SHARED_CHANNEL
    /* MUTANT: violates FR-001 ("private per-fork capability channel, non-shared
     * pathname/listener") by handing out the SAME cached socketpair to every
     * caller instead of a fresh one per fork request. test_edge_private_channel.c
     * must catch this via fstat() dev/inode identity on two independently
     * requested channels. */
    static int shared_fds[2] = { -1, -1 };
    static int initialized = 0;
    if (!initialized) {
        if (socketpair(AF_UNIX, SOCK_SEQPACKET, 0, shared_fds) != 0) {
            return -1;
        }
        initialized = 1;
    }
    *out_parent_fd = shared_fds[0];
    *out_child_fd = shared_fds[1];
    return 0;
#else
    int fds[2];
    if (socketpair(AF_UNIX, SOCK_SEQPACKET, 0, fds) != 0) {
        return -1;
    }
    *out_parent_fd = fds[0];
    *out_child_fd = fds[1];
    return 0;
#endif
}

int fork_capability_send_ack(int child_fd, const CapabilityAck *ack) {
    ssize_t sent = send(child_fd, ack, sizeof(*ack), 0);
    if (sent != (ssize_t)sizeof(*ack)) {
        return -1;
    }
    return 0;
}

int fork_capability_recv_ack(int parent_fd, int timeout_ms, CapabilityAck *out_ack) {
    struct pollfd pfd = { .fd = parent_fd, .events = POLLIN };
    int rc = poll(&pfd, 1, timeout_ms);
    if (rc == 0) {
        return 0; /* timeout */
    }
    if (rc < 0) {
        return -1;
    }
    memset(out_ack, 0, sizeof(*out_ack));
    ssize_t got = recv(parent_fd, out_ack, sizeof(*out_ack), 0);
    if (got == 0) {
        /* peer closed the channel (child exited) without ever sending a
         * message — this is NOT the same as a malformed message. poll()
         * reports a closed peer as "readable" too (POLLHUP), so without this
         * distinction a child that dies before ACKing would be misreported
         * as REJECT_MALFORMED_ACK instead of REJECT_CHILD_ERROR. */
        return -2;
    }
    if (got != (ssize_t)sizeof(*out_ack)) {
        return -1; /* malformed: SOCK_SEQPACKET preserves message boundaries, so a
                    * short/long non-empty read means the sender did not send a
                    * well-formed CapabilityAck — REJECT_MALFORMED_ACK at the caller. */
    }
    return 1;
}
