/* Deliberately deficient test double: forwards, but never mirrors.
 * NOT an implementation proposal. Normal mirror cases must reject it. */
#include "mock.h"
int __wl_ttlog_00000659(int priority, const char *tag, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int result = __android_log_vprint(priority, tag, fmt, ap);
    va_end(ap);
    return result;
}
