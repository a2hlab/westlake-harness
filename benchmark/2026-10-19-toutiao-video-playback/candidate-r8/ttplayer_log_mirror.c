/* Exact-player diagnostic mirror. This is not a replacement system logger.
 * Original print/vprint semantics: reviewed liblog d8ad176b, ELF 7450/7548.
 * The unique consumer import, provider binding and OH execution need separate
 * validation. No constructor, threshold change, file creation or GOT writes.
 */
#include <errno.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdio.h>
#include <unistd.h>

extern int __android_log_vprint(int, const char *, const char *, va_list);

enum { MIRROR_BYTES = 1024, MIRROR_ATTEMPTS = 256, FORMAT_SCAN_LIMIT = 4096 };
static _Atomic unsigned mirror_attempts;

/* Reserve before looking at varargs. Saturation avoids eventual wraparound. */
static int reserve_mirror(void)
{
    unsigned old = atomic_load_explicit(&mirror_attempts, memory_order_relaxed);
    while (old < MIRROR_ATTEMPTS) {
        if (atomic_compare_exchange_weak_explicit(&mirror_attempts, &old, old + 1,
                memory_order_relaxed, memory_order_relaxed))
            return 1;
    }
    return 0;
}

static int is_digit(char c) { return c >= '0' && c <= '9'; }
static int is_flag(char c)
{
    return c == '-' || c == '+' || c == ' ' || c == '#' || c == '0';
}

/* A bounded, deliberately narrow printf subset. In particular, no positional
 * arguments or %n variants are evaluated by the mirror. The original backend
 * still receives every format, unchanged, exactly once.
 */
static int mirrorable_format(const char *fmt)
{
    size_t length = 0, i = 0;
    if (!fmt) return 0;
    while (length < FORMAT_SCAN_LIMIT && fmt[length]) ++length;
    if (length == FORMAT_SCAN_LIMIT) return 0;
    while (i < length) {
        if (fmt[i++] != '%') continue;
        if (i < length && fmt[i] == '%') { ++i; continue; }
        while (i < length && is_flag(fmt[i])) ++i;
        if (i < length && fmt[i] == '*') ++i;
        else while (i < length && is_digit(fmt[i])) ++i;
        if (i < length && fmt[i] == '.') {
            ++i;
            if (i < length && fmt[i] == '*') ++i;
            else while (i < length && is_digit(fmt[i])) ++i;
        }
        /* 0=none, 1=integer modifier, 2=l, 3=L. */
        int modifier = 0;
        if (i < length && fmt[i] == 'h') {
            ++i; if (i < length && fmt[i] == 'h') ++i;
            modifier = 1;
        } else if (i < length && fmt[i] == 'l') {
            ++i; modifier = 2;
            if (i < length && fmt[i] == 'l') { ++i; modifier = 1; }
        } else if (i < length && (fmt[i] == 'j' || fmt[i] == 'z' || fmt[i] == 't')) {
            ++i; modifier = 1;
        } else if (i < length && fmt[i] == 'L') {
            ++i; modifier = 3;
        }
        if (i == length) return 0;
        char conversion = fmt[i++];
        switch (conversion) {
        case 'd': case 'i': case 'o': case 'u': case 'x': case 'X':
            if (modifier == 3) return 0;
            break;
        case 'f': case 'F': case 'e': case 'E': case 'g': case 'G': case 'a': case 'A':
            if (modifier == 1) return 0;
            break;
        case 'c': case 's': case 'p': case 'm':
            if (modifier != 0) return 0;
            break;
        default:
            return 0;
        }
    }
    return 1;
}

static void mirror_once(int priority, const char *tag, const char *fmt,
                        va_list args, int entry_errno)
{
    if (!reserve_mirror()) return;
    if (!mirrorable_format(fmt)) {
        static const char skipped[] = "[WL-TTLOG skipped-format]\n";
        (void)write(STDERR_FILENO, skipped, sizeof skipped - 1);
        return;
    }
    char buffer[MIRROR_BYTES];
    int prefix = snprintf(buffer, sizeof buffer, "[WL-TTLOG p=%d tag=%.64s] ",
                          priority, tag ? tag : "(null)");
    if (prefix < 0 || (size_t)prefix >= sizeof buffer - 1) return;
    va_list copy;
    va_copy(copy, args);
    errno = entry_errno; /* %m observes the same errno as the original call. */
    size_t available = sizeof buffer - (size_t)prefix;
    int count = vsnprintf(buffer + prefix, available, fmt, copy);
    va_end(copy);
    if (count < 0) return;
    size_t payload = (size_t)count < available ? (size_t)count : available - 1;
    size_t bytes = (size_t)prefix + payload;
    buffer[bytes++] = '\n';
    /* fd2 is the existing child log. A failed/short write is never retried.
     * A bounded write can still block; no nonblocking guarantee is made.
     */
    (void)write(STDERR_FILENO, buffer, bytes);
}

__attribute__((visibility("default"), format(printf, 3, 4)))
int __wl_ttlog_00000659(int priority, const char *tag, const char *fmt, ...)
{
    int entry_errno = errno;
    va_list args;
    va_start(args, fmt);
    mirror_once(priority, tag, fmt, args, entry_errno);
    errno = entry_errno;
    int result = __android_log_vprint(priority, tag, fmt, args);
    int result_errno = errno;
    va_end(args);
    errno = result_errno;
    return result;
}
