#include <stdint.h>
#include <stdio.h>
#include <string.h>

unsigned long adler32_impl(unsigned long adler, const uint8_t* buf,
                           unsigned int len) __asm__("adler32");
unsigned long adler32_combine_impl(unsigned long adler1,
                                   unsigned long adler2,
                                   long len2) __asm__("adler32_combine");

static int failures;

static void check(int condition, const char* label)
{
    if (!condition) {
        fprintf(stderr, "FAIL %s\n", label);
        failures++;
    }
}

static uint32_t next_word(uint32_t* state)
{
    *state = *state * UINT32_C(1664525) + UINT32_C(1013904223);
    return *state;
}

int main(void)
{
    static const uint8_t wikipedia[] = "Wikipedia";
    uint8_t bytes[4096];
    static uint8_t long_bytes[131123];
    uint32_t state = UINT32_C(0x41504b31);

    check(adler32_impl(1, wikipedia, 9) == 0x11e60398UL,
          "known_vector_wikipedia");
    check(adler32_impl(0, NULL, 0) == 1UL, "null_buffer_contract");
    check(adler32_combine_impl(1, 1, -1) == 0xffffffffUL,
          "negative_length_rejected");

    for (unsigned int i = 0; i < sizeof(bytes); ++i) {
        bytes[i] = (uint8_t)(next_word(&state) >> 24);
    }
    for (unsigned int i = 0; i < sizeof(long_bytes); ++i) {
        long_bytes[i] = (uint8_t)(next_word(&state) >> 24);
    }

    for (unsigned int total = 0; total <= sizeof(bytes); total += 17) {
        for (unsigned int split = 0; split <= total; split += 13) {
            unsigned long whole = adler32_impl(1, bytes, total);
            unsigned long left = adler32_impl(1, bytes, split);
            unsigned long right = adler32_impl(1, bytes + split,
                                               total - split);
            unsigned long combined = adler32_combine_impl(
                left, right, (long)(total - split));
            check(combined == whole, "combine_matches_concatenation");
        }
    }

    {
        const unsigned int splits[] = { 0, 1, 65520, 65521, 65522, 100003 };
        unsigned long whole = adler32_impl(1, long_bytes,
                                           (unsigned int)sizeof(long_bytes));
        for (unsigned int i = 0; i < sizeof(splits) / sizeof(splits[0]); ++i) {
            unsigned int split = splits[i];
            unsigned long left = adler32_impl(1, long_bytes, split);
            unsigned long right = adler32_impl(
                1, long_bytes + split,
                (unsigned int)sizeof(long_bytes) - split);
            check(adler32_combine_impl(
                      left, right, (long)(sizeof(long_bytes) - split)) == whole,
                  "combine_modulus_boundaries");
        }
    }

    if (failures != 0) return 1;
    printf("PASS adler32_zlib_semantics\n");
    return 0;
}
