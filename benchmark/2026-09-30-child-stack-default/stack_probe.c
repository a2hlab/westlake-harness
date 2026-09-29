#define _GNU_SOURCE
#include <pthread.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
// OH libc exports these musl extensions, but this frozen SDK omits declarations.
extern int pthread_getattr_default_np(pthread_attr_t *);
extern int pthread_setattr_default_np(const pthread_attr_t *);
static void report(const char *label) {
    pthread_attr_t self, defaults;
    size_t current=0, fallback=0, guard=0;
    void *base=0;
    int a=pthread_getattr_np(pthread_self(),&self);
    if(!a){pthread_attr_getstack(&self,&base,&current);pthread_attr_getguardsize(&self,&guard);pthread_attr_destroy(&self);}
    int b=pthread_getattr_default_np(&defaults);
    if(!b){pthread_attr_getstacksize(&defaults,&fallback);pthread_attr_destroy(&defaults);}
    printf("STACKPROBE %s pid=%d getattr=%d base=%p stack=%zu guard=%zu default_rc=%d default=%zu\n",label,getpid(),a,base,current,guard,b,fallback);
    fflush(stdout);
}
static void *thread_main(void *unused) { (void)unused;report("new-pthread");return 0; }
int main(void) {
    report("initial-before");
    pthread_attr_t attr;
    int rc=pthread_attr_init(&attr);
    if(rc)return 2;
    if(!rc)rc=pthread_attr_setstacksize(&attr,8u*1024u*1024u);
    if(!rc)rc=pthread_setattr_default_np(&attr);
    pthread_attr_destroy(&attr);
    printf("STACKPROBE set-default rc=%d\n",rc);fflush(stdout);
    if(rc)return 2;
    report("initial-after");
    pid_t child=fork();
    if(child==0){report("fork-child");_exit(0);}
    if(child<0)return 3;
    int status=0;if(waitpid(child,&status,0)!=child || status!=0)return 4;
    pthread_t thread;rc=pthread_create(&thread,0,thread_main,0);
    if(rc)return 5;
    return pthread_join(thread,0)!=0;
}
