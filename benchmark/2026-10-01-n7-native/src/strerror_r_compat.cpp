// GNU strerror_r variant for the Bionic/Musl boundary.
//
// musl's strerror_r is the POSIX variant (returns int).  The GNU variant
// (glibc/bionic) returns char* — either the caller's buf or a static string.
// This provides the GNU semantic so Bionic-compiled code (libmozglue etc.)
// can call it without relocation failure.

#include <string.h>
#include <stdio.h>

extern "C" char *__gnu_strerror_r(int errnum, char *buf, size_t buflen)
{
    if (buf == nullptr || buflen == 0) {
        return const_cast<char *>("(invalid buffer)");
    }

    // musl strerror returns a thread-local static string; copy it into buf.
    const char *msg = strerror(errnum);
    if (msg != nullptr) {
        strncpy(buf, msg, buflen - 1);
        buf[buflen - 1] = '\0';
    } else {
        // Unknown errno: match glibc/bionic format.
        snprintf(buf, buflen, "Unknown error %d", errnum);
    }
    return buf;
}
