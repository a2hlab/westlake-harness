// loopback_probe.c — does connect() to a CLOSED 127.0.0.1:port fast-fail with ECONNREFUSED
// (like Linux/Android) or hang? Confirms the AppManager '正在验证' platform-diff finding:
// AppManager Ops.connectAdb blocks forever -> never reaches fallbackToNoRoot -> stuck splash.
//
// Build (OH clang arm64):  clang --target=aarch64-linux-ohos -static -O2 loopback_probe.c -o loopback_probe
// Build (Android ref, NDK):  aarch64-linux-android<API>-clang -static -O2 loopback_probe.c -o loopback_probe
// Run:  ./loopback_probe <port>   (use a port with NO listener, e.g. 5555 if no adbd, or 59999)
//
// Uses a BLOCKING connect with no app-imposed timeout (mirrors AppManager's Ops.connectAdb which
// has no connect timeout). Prints errno + elapsed ms. A watchdog thread hard-caps the wait at 10s
// so the probe itself never hangs the shell.

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>

static volatile int g_done = 0;
static void* watchdog(void* a){
    (void)a;
    for(int i=0;i<100 && !g_done;i++){ struct timespec ts={0,100*1000*1000}; nanosleep(&ts,0); }
    if(!g_done){ fprintf(stderr,"[PROBE] connect still BLOCKED after 10s -> HANG (no fast-refuse)\n"); _exit(3); }
    return 0;
}

static double now_ms(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec*1e3 + t.tv_nsec/1e6; }

int main(int argc,char**argv){
    int port = argc>1 ? atoi(argv[1]) : 59999;
    pthread_t wd; pthread_create(&wd,0,watchdog,0);

    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in sa; memset(&sa,0,sizeof(sa));
    sa.sin_family = AF_INET; sa.sin_port = htons(port);
    inet_pton(AF_INET, "127.0.0.1", &sa.sin_addr);

    fprintf(stderr,"[PROBE] connect 127.0.0.1:%d (blocking, no timeout)...\n", port);
    double t0 = now_ms();
    int rc = connect(fd, (struct sockaddr*)&sa, sizeof(sa));
    double dt = now_ms() - t0;
    int e = errno;
    g_done = 1;

    if(rc==0){
        fprintf(stderr,"[PROBE] connect SUCCEEDED in %.1f ms (a listener IS present on %d)\n", dt, port);
    } else if(e==ECONNREFUSED){
        fprintf(stderr,"[PROBE] ECONNREFUSED in %.1f ms -> FAST-REFUSE (like Linux/Android). %s\n",
                dt, dt<100?"NOT the hang.":"slow refuse.");
    } else {
        fprintf(stderr,"[PROBE] connect failed errno=%d (%s) in %.1f ms\n", e, strerror(e), dt);
    }
    close(fd);
    return rc==0?0:(e==ECONNREFUSED?1:2);
}
