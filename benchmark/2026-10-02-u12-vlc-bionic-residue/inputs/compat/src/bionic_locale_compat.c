// Exact Bionic locale/ctype ABI required by the unmodified ZigZag arm64 DSOs.
//
// AOSP16 implements strtoll_l/strtoull_l as strong aliases of strtoll/strtoull,
// so the locale argument is intentionally ignored here as well.  `_ctype_` is
// the historical Bionic/OpenBSD pointer ABI: consumers load the exported
// pointer, then index the 257-byte C-locale classification table at c + 1.

#include <locale.h>
#include <stdlib.h>

long long strtoll_l(const char *nptr, char **endptr, int base, locale_t locale)
{
    (void)locale;
    return strtoll(nptr, endptr, base);
}

unsigned long long strtoull_l(
    const char *nptr, char **endptr, int base, locale_t locale)
{
    (void)locale;
    return strtoull(nptr, endptr, base);
}

#define BIONIC_CT_U 0x01
#define BIONIC_CT_L 0x02
#define BIONIC_CT_N 0x04
#define BIONIC_CT_S 0x08
#define BIONIC_CT_P 0x10
#define BIONIC_CT_C 0x20
#define BIONIC_CT_X 0x40
#define BIONIC_CT_B 0x80

static const char kBionicCtypeTable[1 + 256] = {
    0,
    BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C,
    BIONIC_CT_C, BIONIC_CT_C|BIONIC_CT_S, BIONIC_CT_C|BIONIC_CT_S, BIONIC_CT_C|BIONIC_CT_S, BIONIC_CT_C|BIONIC_CT_S, BIONIC_CT_C|BIONIC_CT_S, BIONIC_CT_C, BIONIC_CT_C,
    BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C,
    BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C, BIONIC_CT_C,
    BIONIC_CT_S|(char)BIONIC_CT_B, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P,
    BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P,
    BIONIC_CT_N, BIONIC_CT_N, BIONIC_CT_N, BIONIC_CT_N, BIONIC_CT_N, BIONIC_CT_N, BIONIC_CT_N, BIONIC_CT_N,
    BIONIC_CT_N, BIONIC_CT_N, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P,
    BIONIC_CT_P, BIONIC_CT_U|BIONIC_CT_X, BIONIC_CT_U|BIONIC_CT_X, BIONIC_CT_U|BIONIC_CT_X, BIONIC_CT_U|BIONIC_CT_X, BIONIC_CT_U|BIONIC_CT_X, BIONIC_CT_U|BIONIC_CT_X, BIONIC_CT_U,
    BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U,
    BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U,
    BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_U, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P,
    BIONIC_CT_P, BIONIC_CT_L|BIONIC_CT_X, BIONIC_CT_L|BIONIC_CT_X, BIONIC_CT_L|BIONIC_CT_X, BIONIC_CT_L|BIONIC_CT_X, BIONIC_CT_L|BIONIC_CT_X, BIONIC_CT_L|BIONIC_CT_X, BIONIC_CT_L,
    BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L,
    BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L,
    BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_L, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_P, BIONIC_CT_C,
};

_Static_assert(sizeof(kBionicCtypeTable) == 257,
               "Bionic _ctype_ table layout drifted");

const char *_ctype_ = kBionicCtypeTable;
