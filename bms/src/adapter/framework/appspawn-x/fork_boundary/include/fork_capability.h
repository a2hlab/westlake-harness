#ifndef FORK_CAPABILITY_H
#define FORK_CAPABILITY_H

#include "spawn_oracle.h"

/* Creates a socketpair(AF_UNIX, SOCK_SEQPACKET) private per-fork channel.
 * out_parent_fd / out_child_fd are the two endpoints; the caller (before fork())
 * holds both. After fork(), the parent branch MUST close out_child_fd and the
 * child branch MUST close out_parent_fd — see research.md R1. Returns 0 on
 * success, -1 on failure (errno set). */
int fork_capability_channel_create(int *out_parent_fd, int *out_child_fd);

/* child side: send exactly one CapabilityAck message. Returns 0 on success. */
int fork_capability_send_ack(int child_fd, const CapabilityAck *ack);

/* parent side: non-blocking-with-timeout receive.
 * Returns  1 if a well-formed CapabilityAck was read into *out_ack.
 * Returns  0 on timeout (no data within timeout_ms).
 * Returns -1 on a malformed non-empty message (wrong length) or poll() error.
 * Returns -2 if the peer closed the channel without ever sending a message
 *            (e.g. the child exited before ACKing) — the caller should check
 *            child liveness (waitpid) rather than treat this as malformed. */
int fork_capability_recv_ack(int parent_fd, int timeout_ms, CapabilityAck *out_ack);

#endif /* FORK_CAPABILITY_H */
