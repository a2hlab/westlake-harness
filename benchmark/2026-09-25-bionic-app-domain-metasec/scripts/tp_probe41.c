/* #41 probe: like #39's tp_probe, plus it prints its own SELinux domain
 * (/proc/self/attr/current) so we can prove which domain actually ran it. */
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <pthread.h>
#include <sys/syscall.h>

static void print_attr(const char *p, const char *label){
    char buf[256]; int fd = open(p, O_RDONLY);
    if (fd < 0){ printf("%s = <open failed>\n", label); return; }
    ssize_t n = read(fd, buf, sizeof buf - 1); close(fd);
    if (n <= 0){ printf("%s = <empty>\n", label); return; }
    while (n && (buf[n-1]=='\n'||buf[n-1]=='\0')) n--;
    buf[n]=0; printf("%s = %s\n", label, buf);
}

int main(void){
    void *tp; __asm__ volatile("mrs %0, tpidr_el0" : "=r"(tp));
    void **slots = (void**)tp;
    void *slot1 = slots[1], *self = (void*)pthread_self();
    pid_t tid = (pid_t)syscall(SYS_gettid);
    printf("bionic41 tp_probe up\n");
    print_attr("/proc/self/attr/current", "selinux_domain");
    printf("uid=%d gid=%d pid=%d\n", getuid(), getgid(), getpid());
    printf("tls[1]=%p pthread_self=%p slot1==self=%s\n", slot1, self, slot1==self?"yes":"no");
    if (self){
        int32_t st_tid = *(int32_t*)((char*)self+16);
        int32_t cpid  = *(int32_t*)((char*)self+20);
        printf("pthread.tid@16=%d gettid=%d match=%s\n", st_tid, tid, st_tid==tid?"yes":"no");
        printf("pthread.cached_pid@20=%d getpid=%d match=%s\n", cpid, getpid(), cpid==getpid()?"yes":"no");
    }
    fflush(stdout);
    return slot1==self?0:2;
}
