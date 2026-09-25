/* tp_probe: minimal aarch64 program to confirm the Bionic thread-pointer layout.
 * On arm64 Bionic, TPIDR_EL0 points at the TLS block; slot 1 holds the
 * pthread_internal_t pointer, which is exactly what pthread_self() returns.
 * That slot-1 == pthread_self() identity is the ABI fact metasec relies on. */
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/syscall.h>

int main(void) {
    void *tp;
    __asm__ volatile("mrs %0, tpidr_el0" : "=r"(tp));
    void **slots = (void **)tp;
    void *slot1 = slots[1];              /* TLS_SLOT_THREAD_ID */
    void *self  = (void *)pthread_self();
    void *guard = slots[5];              /* TLS_SLOT_STACK_GUARD */
    pid_t tid   = (pid_t)syscall(SYS_gettid);

    printf("bionic39 tp_probe up\n");
    printf("tpidr_el0    = %p\n", tp);
    printf("tls[1]       = %p\n", slot1);
    printf("pthread_self = %p\n", self);
    printf("tls[5]guard  = %p\n", guard);
    printf("gettid       = %d\n", tid);
    printf("slot1==self  = %s\n", slot1 == self ? "yes" : "no");

    /* pthread_internal_t on this Bionic family: tid @ +16, cached_pid_ @ +20 */
    if (self) {
        int32_t st_tid = *(int32_t *)((char *)self + 16);
        printf("pthread.tid@16 = %d (match=%s)\n", st_tid, st_tid == tid ? "yes" : "no");
    }
    fflush(stdout);
    return slot1 == self ? 0 : 2;
}
