#include "westlake_sha256.h"

#include <stdio.h>
#include <string.h>

static int failures;

static uint8_t Nibble(char value)
{
    return value <= '9' ? (uint8_t)(value - '0') :
        (uint8_t)(value - 'a' + 10);
}

static int Check(const char *name, const char *input, const char *expected)
{
    WlSha256Context context;
    uint8_t output[WLSHA256_DIGEST_SIZE];
    size_t index;
    WLSha256Init(&context);
    for (index = 0; index < strlen(input); ++index) {
        if (WLSha256Update(&context, input + index, 1U) != 0) {
            return -1;
        }
    }
    if (WLSha256Final(&context, output) != 0) {
        return -1;
    }
    for (index = 0; index < sizeof(output); ++index) {
        uint8_t byte = (uint8_t)((Nibble(expected[index * 2U]) << 4U) |
                                 Nibble(expected[index * 2U + 1U]));
        if (output[index] != byte) {
            fprintf(stderr, "FAIL %s byte=%zu\n", name, index);
            return -1;
        }
    }
    return 0;
}

int main(void)
{
    failures += Check(
        "empty", "",
        "e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855") != 0;
    failures += Check(
        "abc", "abc",
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad") != 0;
    failures += Check(
        "two_blocks",
        "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
        "248d6a61d20638b8e5c026930c3e6039"
        "a33ce45964ff2167f6ecedd419db06c1") != 0;
    if (failures != 0) {
        return 1;
    }
    printf("RESULT PASS tests=3\n");
    return 0;
}
