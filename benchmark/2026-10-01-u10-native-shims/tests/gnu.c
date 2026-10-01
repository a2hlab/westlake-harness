#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stddef.h>
#include <string.h>

extern char* __gnu_strerror_r(int, char*, size_t);

static void check(int error_number, size_t length) {
    unsigned char actual[66];
    unsigned char expected[66];
    memset(actual, 0xa5, sizeof(actual));
    memset(expected, 0xa5, sizeof(expected));
    (void)strerror_r(error_number, (char*)expected + 1, length);
    errno = EBUSY;
    char* result = __gnu_strerror_r(error_number, (char*)actual + 1, length);
    assert(result == (char*)actual + 1);
    assert(errno == EBUSY);
    assert(memcmp(actual, expected, sizeof(actual)) == 0);
    assert(actual[0] == 0xa5 && actual[length + 1] == 0xa5);
    if (error_number == EINVAL && length > 0 && length <= strlen(strerror(EINVAL))) {
        assert(actual[length] == 0);
    }
}

static void* concurrent(void* argument) {
    (void)argument;
    for (int iteration = 0; iteration < 1000; ++iteration) {
        check(EINVAL, 64);
        check(1234567, 2);
    }
    return NULL;
}

int main(void) {
    for (size_t length = 0; length <= 64; ++length) {
        check(EINVAL, length);
        check(1234567, length);
    }
    pthread_t workers[4];
    for (size_t index = 0; index < 4; ++index) {
        assert(pthread_create(&workers[index], NULL, concurrent, NULL) == 0);
    }
    for (size_t index = 0; index < 4; ++index) {
        assert(pthread_join(workers[index], NULL) == 0);
    }
    return 0;
}
