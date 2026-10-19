#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
static volatile uint64_t seen;
__attribute__((noinline, visibility("default")))
void r12_marker(uint64_t count) {
    seen = count;
    printf("R12_COUNT %" PRIu64 "\n", count);
    fflush(stdout);
}
static double elapsed(const struct timespec *start) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return 121.0;
    return (double)(now.tv_sec-start->tv_sec)+(now.tv_nsec-start->tv_nsec)/1e9;
}
int main(void) {
    struct timespec start;
    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) return 2;
    alarm(120); /* Independent self-exit backstop, never cleanup evidence. */
    uint64_t count=0;
    while (elapsed(&start)<120.0) {
        r12_marker(++count);
        struct timespec wait={0,250000000};
        while (nanosleep(&wait,&wait)!=0) { if (errno!=EINTR) return 3; }
    }
    return seen ? 0 : 4;
}
