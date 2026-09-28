#pragma once
#include <cstdint>
#include <cstddef>
#define SHA256_DIGEST_LENGTH 32
typedef struct SHA256state_st { uint8_t data[64]; uint32_t state[8]; uint64_t bitlen; } SHA256_CTX;
#ifdef __cplusplus
extern "C" {
#endif
inline int SHA256_Init(SHA256_CTX*) { return 1; }
inline int SHA256_Update(SHA256_CTX*, const void*, size_t) { return 1; }
inline int SHA256_Final(unsigned char*, SHA256_CTX*) { return 1; }
inline unsigned char* SHA256(const unsigned char*, size_t, unsigned char* md) { return md; }
#ifdef __cplusplus
}
#endif
