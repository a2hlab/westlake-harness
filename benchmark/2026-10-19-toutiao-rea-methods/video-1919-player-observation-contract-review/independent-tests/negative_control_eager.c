/* Deliberately wrong: eagerly evaluates formats before original filtering.
 * NOT a mirror implementation or candidate. */
#include "mock.h"
#include <stdio.h>
int __wl_ttlog_00000659(int priority, const char *tag, const char *fmt, ...) {
    va_list ap, copy;
    char discarded[128];
    va_start(ap, fmt);
    va_copy(copy, ap);
    vsnprintf(discarded, sizeof(discarded), fmt, copy);
    va_end(copy);
    int result = __android_log_vprint(priority, tag, fmt, ap);
    va_end(ap);
    return result;
}
