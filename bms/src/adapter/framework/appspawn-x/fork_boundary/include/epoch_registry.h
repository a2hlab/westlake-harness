#ifndef EPOCH_REGISTRY_H
#define EPOCH_REGISTRY_H

#include "spawn_oracle.h"

typedef struct EpochRegistry EpochRegistry;

/* Creates a fresh registry with the given epoch value. Simulates "parent restart":
 * a new registry never shares request/nonce state with any prior instance
 * (research.md R3). */
EpochRegistry *epoch_registry_create(uint64_t epoch);
void epoch_registry_destroy(EpochRegistry *reg);

uint64_t epoch_registry_epoch(const EpochRegistry *reg);

/* Registers a new request in state PENDING_FORK. Allocates request_id, epoch,
 * nonce, and copies bundle_name/adapter_entry. Returns the request (owned by
 * the registry; do not free directly). */
SpawnRequest *epoch_registry_new_request(EpochRegistry *reg, uint32_t generation,
                                          const char *bundle_name,
                                          const char *adapter_entry);

/* FR-007: refuses a second fork() for a request that already left PENDING_FORK. */
bool epoch_registry_try_mark_forked(EpochRegistry *reg, SpawnRequest *req,
                                     pid_t fork_pid, int parent_channel_fd);

/* Looks up an in-flight (PENDING_ACK) request by fork_pid, or NULL. */
SpawnRequest *epoch_registry_find_pending_by_pid(EpochRegistry *reg, pid_t fork_pid);

bool nonce_registry_try_consume(EpochRegistry *reg, const uint8_t nonce[SPAWN_NONCE_LEN]);

/* Reconciles all PENDING_ACK requests left in `old_reg` after a simulated
 * parent restart: SIGKILL + blocking waitpid on each orphan's fork_pid, then
 * marks the request RECONCILED. Returns the number of orphans reconciled. */
int epoch_registry_reconcile(EpochRegistry *new_reg, EpochRegistry *old_reg);

#endif /* EPOCH_REGISTRY_H */
