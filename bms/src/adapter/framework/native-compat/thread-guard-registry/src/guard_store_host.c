#include <stdint.h>

uint64_t WLTG_StoreGuardAndReadback(uint64_t *address, uint64_t value)
{
    volatile uint64_t *slot = (volatile uint64_t *)address;
    *slot = value;
    return *slot;
}
