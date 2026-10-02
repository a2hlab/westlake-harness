#pragma once
#include <cstdint>
#include <cstring>
#include <climits>

// WindowSessionAdapter names each root with its actual OH session. Other
// layers inherit an explicit parent; an unknown owner must stay unbound.
inline int32_t oh_surface_session_identity(const char* name, int32_t parent) {
    constexpr const char prefix[] = "OH_Surface_";
    if (!name || std::strncmp(name, prefix, sizeof(prefix) - 1) != 0)
        return parent > 0 ? parent : 0;
    const char* p = name + sizeof(prefix) - 1;
    if (!*p) return 0;
    int32_t value = 0;
    for (; *p; ++p) {
        if (*p < '0' || *p > '9' || value > (INT32_MAX - (*p - '0')) / 10)
            return 0;
        value = value * 10 + (*p - '0');
    }
    return value;
}
