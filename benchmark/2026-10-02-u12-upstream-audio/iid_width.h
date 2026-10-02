#ifndef WESTLAKE_U12_IID_WIDTH_H
#define WESTLAKE_U12_IID_WIDTH_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct U12AndroidId {
    uint32_t time_low;
    uint16_t time_mid;
    uint16_t time_hi_and_version;
    uint16_t clock_seq;
    uint8_t node[6];
};

_Static_assert(sizeof(struct U12AndroidId) == 16, "Android IID size");
_Static_assert(sizeof(struct SLInterfaceID_) == 24, "Pinned OH IID size");
_Static_assert(offsetof(struct SLInterfaceID_, time_mid) == 8, "Pinned OH IID field");

static int U12EqualAndroidIds(const void* first, const void* second)
{
    return first && second && memcmp(first, second, sizeof(struct U12AndroidId)) == 0;
}

static int U12EqualAndroidOwnerId(const void* android, SLInterfaceID owner)
{
    if (!android || !owner || owner->time_low > UINT32_MAX) return 0;
    struct U12AndroidId value;
    memcpy(&value, android, sizeof(value));
    return value.time_low == owner->time_low && value.time_mid == owner->time_mid &&
           value.time_hi_and_version == owner->time_hi_and_version && value.clock_seq == owner->clock_seq &&
           memcmp(value.node, owner->node, sizeof(value.node)) == 0;
}

#endif
