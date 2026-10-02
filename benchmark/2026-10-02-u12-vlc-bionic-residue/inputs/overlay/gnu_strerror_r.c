#include <errno.h>
#include <stddef.h>
#include <string.h>

char* __gnu_strerror_r(int error_number, char* buffer, size_t buffer_length) {
    int saved_errno = errno;
    (void)strerror_r(error_number, buffer, buffer_length);
    errno = saved_errno;
    return buffer;
}
