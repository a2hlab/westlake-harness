#include "nonce.h"

#include <stdlib.h>
#include <string.h>
#include <sys/random.h>

void nonce_generate(uint8_t out[SPAWN_NONCE_LEN]) {
    ssize_t got = getrandom(out, SPAWN_NONCE_LEN, 0);
    if (got != SPAWN_NONCE_LEN) {
        /* getrandom() should not partially fail for a 16-byte request under normal
         * operation; treat any deviation as fatal rather than silently degrading
         * nonce quality. */
        abort();
    }
}

#define NONCE_SET_CAPACITY 4096

struct NonceSet {
    uint8_t entries[NONCE_SET_CAPACITY][SPAWN_NONCE_LEN];
    size_t  count;
};

NonceSet *nonce_set_create(void) {
    NonceSet *set = calloc(1, sizeof(NonceSet));
    return set;
}

void nonce_set_destroy(NonceSet *set) {
    free(set);
}

bool nonce_set_try_consume(NonceSet *set, const uint8_t nonce[SPAWN_NONCE_LEN]) {
    for (size_t i = 0; i < set->count; i++) {
        if (memcmp(set->entries[i], nonce, SPAWN_NONCE_LEN) == 0) {
            return false; /* already consumed -> caller reports REJECT_NONCE_REPLAYED */
        }
    }
    if (set->count >= NONCE_SET_CAPACITY) {
        /* this round's test scope never approaches this bound (≤ tens of requests) */
        abort();
    }
    memcpy(set->entries[set->count], nonce, SPAWN_NONCE_LEN);
    set->count++;
    return true;
}
