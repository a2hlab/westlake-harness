/* Outer-loop re-check of #39: same TPIDR_EL0 facts as tp_probe, plus the field
 * metasec actually writes (cached_pid_ @ +20) and which libc/linker got mapped. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/syscall.h>

static void *worker(void *arg) {
    void *tp;
    __asm__ volatile("mrs %0, tpidr_el0" : "=r"(tp));
    void *self = (void *)pthread_self();
    pid_t tid = (pid_t)syscall(SYS_gettid);
    int32_t st_tid = *(int32_t *)((char *)self + 16);
    printf("thread2: tls[1]==self=%s tid@16=%d gettid=%d\n",
           ((void **)tp)[1] == self ? "yes" : "no", st_tid, tid);
    return arg;
}

int main(void) {
    void *tp;
    __asm__ volatile("mrs %0, tpidr_el0" : "=r"(tp));
    void *self = (void *)pthread_self();
    pid_t tid = (pid_t)syscall(SYS_gettid);
    int32_t st_tid = *(int32_t *)((char *)self + 16);
    int32_t cached_pid = *(int32_t *)((char *)self + 20);
    printf("main: tls[1]==self=%s tid@16=%d gettid=%d cached_pid@20=%d getpid=%d\n",
           ((void **)tp)[1] == self ? "yes" : "no", st_tid, tid, cached_pid, getpid());

    pthread_t t;
    pthread_create(&t, NULL, worker, NULL);
    pthread_join(t, NULL);

    FILE *m = fopen("/proc/self/maps", "r");
    char line[512];
    while (m && fgets(line, sizeof line, m)) {
        if (strstr(line, "r-xp") && (strstr(line, "linker") || strstr(line, "libc") || strstr(line, "ld-musl")))
            printf("map: %s", strchr(line, '/') ? strchr(line, '/') : line);
    }
    if (m) fclose(m);
    fflush(stdout);
    return ((void **)tp)[1] == self && st_tid == tid ? 0 : 2;
}
