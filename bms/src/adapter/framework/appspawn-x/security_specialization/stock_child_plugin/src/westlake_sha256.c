/* Minimal streaming SHA-256 for the pre-load plugin identity gate. */

#include "westlake_sha256.h"

#include <limits.h>
#include <string.h>

static const uint32_t kRoundConstants[64] = {
    UINT32_C(0x428a2f98), UINT32_C(0x71374491), UINT32_C(0xb5c0fbcf),
    UINT32_C(0xe9b5dba5), UINT32_C(0x3956c25b), UINT32_C(0x59f111f1),
    UINT32_C(0x923f82a4), UINT32_C(0xab1c5ed5), UINT32_C(0xd807aa98),
    UINT32_C(0x12835b01), UINT32_C(0x243185be), UINT32_C(0x550c7dc3),
    UINT32_C(0x72be5d74), UINT32_C(0x80deb1fe), UINT32_C(0x9bdc06a7),
    UINT32_C(0xc19bf174), UINT32_C(0xe49b69c1), UINT32_C(0xefbe4786),
    UINT32_C(0x0fc19dc6), UINT32_C(0x240ca1cc), UINT32_C(0x2de92c6f),
    UINT32_C(0x4a7484aa), UINT32_C(0x5cb0a9dc), UINT32_C(0x76f988da),
    UINT32_C(0x983e5152), UINT32_C(0xa831c66d), UINT32_C(0xb00327c8),
    UINT32_C(0xbf597fc7), UINT32_C(0xc6e00bf3), UINT32_C(0xd5a79147),
    UINT32_C(0x06ca6351), UINT32_C(0x14292967), UINT32_C(0x27b70a85),
    UINT32_C(0x2e1b2138), UINT32_C(0x4d2c6dfc), UINT32_C(0x53380d13),
    UINT32_C(0x650a7354), UINT32_C(0x766a0abb), UINT32_C(0x81c2c92e),
    UINT32_C(0x92722c85), UINT32_C(0xa2bfe8a1), UINT32_C(0xa81a664b),
    UINT32_C(0xc24b8b70), UINT32_C(0xc76c51a3), UINT32_C(0xd192e819),
    UINT32_C(0xd6990624), UINT32_C(0xf40e3585), UINT32_C(0x106aa070),
    UINT32_C(0x19a4c116), UINT32_C(0x1e376c08), UINT32_C(0x2748774c),
    UINT32_C(0x34b0bcb5), UINT32_C(0x391c0cb3), UINT32_C(0x4ed8aa4a),
    UINT32_C(0x5b9cca4f), UINT32_C(0x682e6ff3), UINT32_C(0x748f82ee),
    UINT32_C(0x78a5636f), UINT32_C(0x84c87814), UINT32_C(0x8cc70208),
    UINT32_C(0x90befffa), UINT32_C(0xa4506ceb), UINT32_C(0xbef9a3f7),
    UINT32_C(0xc67178f2),
};

static uint32_t RotateRight(uint32_t value, uint32_t amount)
{
    return (value >> amount) | (value << (UINT32_C(32) - amount));
}

static void Transform(WlSha256Context *context, const uint8_t block[64])
{
    uint32_t words[64];
    uint32_t a;
    uint32_t b;
    uint32_t c;
    uint32_t d;
    uint32_t e;
    uint32_t f;
    uint32_t g;
    uint32_t h;
    size_t index;
    for (index = 0; index < 16U; ++index) {
        words[index] = ((uint32_t)block[index * 4U] << 24U) |
            ((uint32_t)block[index * 4U + 1U] << 16U) |
            ((uint32_t)block[index * 4U + 2U] << 8U) |
            (uint32_t)block[index * 4U + 3U];
    }
    for (index = 16U; index < 64U; ++index) {
        uint32_t sigma0 = RotateRight(words[index - 15U], 7U) ^
            RotateRight(words[index - 15U], 18U) ^
            (words[index - 15U] >> 3U);
        uint32_t sigma1 = RotateRight(words[index - 2U], 17U) ^
            RotateRight(words[index - 2U], 19U) ^
            (words[index - 2U] >> 10U);
        words[index] = words[index - 16U] + sigma0 +
            words[index - 7U] + sigma1;
    }

    a = context->state[0];
    b = context->state[1];
    c = context->state[2];
    d = context->state[3];
    e = context->state[4];
    f = context->state[5];
    g = context->state[6];
    h = context->state[7];
    for (index = 0; index < 64U; ++index) {
        uint32_t big_sigma1 = RotateRight(e, 6U) ^ RotateRight(e, 11U) ^
            RotateRight(e, 25U);
        uint32_t choose = (e & f) ^ ((~e) & g);
        uint32_t first = h + big_sigma1 + choose +
            kRoundConstants[index] + words[index];
        uint32_t big_sigma0 = RotateRight(a, 2U) ^ RotateRight(a, 13U) ^
            RotateRight(a, 22U);
        uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        uint32_t second = big_sigma0 + majority;
        h = g;
        g = f;
        f = e;
        e = d + first;
        d = c;
        c = b;
        b = a;
        a = first + second;
    }
    context->state[0] += a;
    context->state[1] += b;
    context->state[2] += c;
    context->state[3] += d;
    context->state[4] += e;
    context->state[5] += f;
    context->state[6] += g;
    context->state[7] += h;
}

void WLSha256Init(WlSha256Context *context)
{
    if (context == NULL) {
        return;
    }
    context->state[0] = UINT32_C(0x6a09e667);
    context->state[1] = UINT32_C(0xbb67ae85);
    context->state[2] = UINT32_C(0x3c6ef372);
    context->state[3] = UINT32_C(0xa54ff53a);
    context->state[4] = UINT32_C(0x510e527f);
    context->state[5] = UINT32_C(0x9b05688c);
    context->state[6] = UINT32_C(0x1f83d9ab);
    context->state[7] = UINT32_C(0x5be0cd19);
    context->bit_length = UINT64_C(0);
    context->buffer_length = 0U;
    (void)memset(context->buffer, 0, sizeof(context->buffer));
}

int WLSha256Update(WlSha256Context *context, const void *data, size_t size)
{
    const uint8_t *bytes = (const uint8_t *)data;
    if (context == NULL || (bytes == NULL && size != 0U) ||
        size > (UINT64_MAX - context->bit_length) / UINT64_C(8)) {
        return -1;
    }
    context->bit_length += (uint64_t)size * UINT64_C(8);
    while (size != 0U) {
        size_t take = sizeof(context->buffer) - context->buffer_length;
        if (take > size) {
            take = size;
        }
        (void)memcpy(context->buffer + context->buffer_length, bytes, take);
        context->buffer_length += take;
        bytes += take;
        size -= take;
        if (context->buffer_length == sizeof(context->buffer)) {
            Transform(context, context->buffer);
            context->buffer_length = 0U;
        }
    }
    return 0;
}

int WLSha256Final(WlSha256Context *context,
                  uint8_t output[WLSHA256_DIGEST_SIZE])
{
    uint64_t true_bit_length;
    size_t index;
    if (context == NULL || output == NULL || context->buffer_length >= 64U) {
        return -1;
    }
    true_bit_length = context->bit_length;
    context->buffer[context->buffer_length++] = UINT8_C(0x80);
    if (context->buffer_length > 56U) {
        while (context->buffer_length < 64U) {
            context->buffer[context->buffer_length++] = UINT8_C(0);
        }
        Transform(context, context->buffer);
        context->buffer_length = 0U;
    }
    while (context->buffer_length < 56U) {
        context->buffer[context->buffer_length++] = UINT8_C(0);
    }
    for (index = 0; index < 8U; ++index) {
        context->buffer[56U + index] =
            (uint8_t)(true_bit_length >> (56U - index * 8U));
    }
    Transform(context, context->buffer);
    for (index = 0; index < 8U; ++index) {
        output[index * 4U] = (uint8_t)(context->state[index] >> 24U);
        output[index * 4U + 1U] =
            (uint8_t)(context->state[index] >> 16U);
        output[index * 4U + 2U] =
            (uint8_t)(context->state[index] >> 8U);
        output[index * 4U + 3U] = (uint8_t)context->state[index];
    }
    (void)memset(context, 0, sizeof(*context));
    return 0;
}
