#ifndef SPAWN_ORACLE_H
#define SPAWN_ORACLE_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <sys/types.h>

#define SPAWN_NONCE_LEN 16
#define SPAWN_BUNDLE_NAME_LEN 128
#define SPAWN_ADAPTER_ENTRY_LEN 64

typedef enum {
    SPAWN_STATE_PENDING_FORK = 0,
    SPAWN_STATE_PENDING_ACK,
    SPAWN_STATE_ACKED_SUCCESS,
    SPAWN_STATE_REJECTED,
    SPAWN_STATE_RECONCILED,
} SpawnState;

/* distinct failure codes — every rejection path maps to exactly one of these */
typedef enum {
    SPAWN_SUCCESS = 0,
    REJECT_FORK_FAILED,
    REJECT_DOUBLE_FORK,
    REJECT_MALFORMED_ACK,
    REJECT_EPOCH_MISMATCH,
    REJECT_PID_MISMATCH,
    REJECT_NONCE_UNKNOWN,
    REJECT_NONCE_REPLAYED,
    REJECT_GENERATION_MISMATCH,
    REJECT_SPECIALIZATION_FAILED,
    REJECT_ADAPTER_ENTRY_MISMATCH,
    REJECT_TIMEOUT,
    REJECT_CHILD_ERROR,
    REJECT_CONCURRENT_WAITER,
} SpawnOutcome;

/* wire message sent by child over the private per-fork channel (contracts/capability_ack.md) */
typedef struct {
    uint64_t epoch;
    pid_t    fork_pid;
    uint8_t  nonce[SPAWN_NONCE_LEN];
    uint32_t generation;
    int32_t  specialization_result; /* 0 == OH security specialization stub succeeded */
    int32_t  adapter_entry_result;  /* 0 == runtime adapter entry was observed */
    char     adapter_entry[SPAWN_ADAPTER_ENTRY_LEN];
} CapabilityAck;

typedef struct {
    uint64_t request_id;
    uint64_t epoch;
    uint32_t generation;
    char     bundle_name[SPAWN_BUNDLE_NAME_LEN];
    pid_t    expected_fork_pid;
    uint8_t  nonce[SPAWN_NONCE_LEN];
    char     adapter_entry[SPAWN_ADAPTER_ENTRY_LEN];
    int      channel_fd;   /* parent-side socketpair endpoint */
    bool     owns_child_process; /* true only for a child created by spawn_oracle_fork() */
    atomic_bool fork_claimed; /* one request may issue at most one real fork */
    atomic_bool wait_claimed; /* exactly one consumer may finalize the ACK */
    SpawnState state;
    SpawnOutcome outcome;
    int      child_wait_status; /* filled on REJECT_CHILD_ERROR */
} SpawnRequest;

typedef struct EpochRegistry EpochRegistry;

/* result returned to the caller (AppMgr-equivalent) on SPAWN_SUCCESS */
typedef struct {
    pid_t pid;
    char  bundle_name[SPAWN_BUNDLE_NAME_LEN];
    /* 仅表示协议 ACK 已通过 adapter-entry 字段校验；不构成产品 runtime handoff 证据。 */
    char  adapter_entry[SPAWN_ADAPTER_ENTRY_LEN];
} SpawnSuccessInfo;

struct ChildEntryOptions; /* forward-declared; full definition in child_entry.h */

/* Top-level protocol entry points (src/spawn_oracle.c). `reg` and `req` come
 * from epoch_registry_new_request(). child_opts may be NULL for the default
 * (non-test-injected) child behavior. */
SpawnOutcome spawn_oracle_fork(EpochRegistry *reg, SpawnRequest *req,
                                const struct ChildEntryOptions *child_opts);

/* Blocks (bounded by timeout_ms) waiting for the child's CapabilityAck,
 * validates it per contracts/capability_ack.md's fixed check order, and on
 * SPAWN_SUCCESS fills *out_info. Always sets req->outcome and req->state to a
 * terminal value before returning. */
SpawnOutcome spawn_oracle_wait_ack(EpochRegistry *reg, SpawnRequest *req, int timeout_ms,
                                    SpawnSuccessInfo *out_info);

#endif /* SPAWN_ORACLE_H */
