#ifndef SPAWN_NONCE_H
#define SPAWN_NONCE_H

#include "spawn_oracle.h"

/* CSPRNG one-use nonce generation (research.md R2) */
void nonce_generate(uint8_t out[SPAWN_NONCE_LEN]);

/* consumed-nonce set, scoped to a single EpochRegistry instance */
typedef struct NonceSet NonceSet;

NonceSet *nonce_set_create(void);
void nonce_set_destroy(NonceSet *set);

/* returns true and marks consumed if nonce not seen before; returns false if already consumed */
bool nonce_set_try_consume(NonceSet *set, const uint8_t nonce[SPAWN_NONCE_LEN]);

#endif /* SPAWN_NONCE_H */
