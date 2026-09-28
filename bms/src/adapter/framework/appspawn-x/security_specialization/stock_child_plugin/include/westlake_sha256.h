#ifndef WESTLAKE_SHA256_H
#define WESTLAKE_SHA256_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WLSHA256_DIGEST_SIZE UINT32_C(32)

typedef struct WlSha256Context {
    uint32_t state[8];
    uint64_t bit_length;
    uint8_t buffer[64];
    size_t buffer_length;
} WlSha256Context;

void WLSha256Init(WlSha256Context *context);
int WLSha256Update(WlSha256Context *context, const void *data, size_t size);
int WLSha256Final(WlSha256Context *context,
                  uint8_t output[WLSHA256_DIGEST_SIZE]);

#ifdef __cplusplus
}
#endif

#endif
