#include "provider_adapter.h"
#include <pthread.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv=PTHREAD_COND_INITIALIZER;
static int entered,go,lower_calls,first_rc;
static char window;
static struct r14_ops ops;
static int32_t lower_request(OHNativeWindow *w,OHNativeWindowBuffer **b,int *fd){
 assert(w==(void*)&window);pthread_mutex_lock(&mu);lower_calls++;
 if(lower_calls==1){entered=1;pthread_cond_broadcast(&cv);while(!go)pthread_cond_wait(&cv,&mu);}
 pthread_mutex_unlock(&mu);*b=NULL;*fd=-1;return 40601000;
}
static BufferHandle *handle(OHNativeWindowBuffer *b){(void)b;assert(0);return NULL;}
static int32_t convert(OHNativeWindowBuffer *b,OH_NativeBuffer **n){(void)b;(void)n;assert(0);return 0;}
static int32_t map(OH_NativeBuffer *b,void **n){(void)b;(void)n;assert(0);return 0;}
static int32_t unmap(OH_NativeBuffer *b){(void)b;assert(0);return 0;}
static int32_t flush(OHNativeWindow *w,OHNativeWindowBuffer *b,int fd,Region r){(void)w;(void)b;(void)fd;(void)r;assert(0);return 0;}
static int32_t abort_buffer(OHNativeWindow *w,OHNativeWindowBuffer *b){(void)w;(void)b;assert(0);return 0;}
static int unwrap(void *c,const void *w,OHNativeWindow **out){(void)c;*out=(void*)w;return 0;}
static int clock_ns(void *c,int64_t *n){(void)c;(void)n;assert(0);return 0;}
static int poll_fd(void *c,int fd,int ms,short *r,int *e){(void)c;(void)fd;(void)ms;(void)r;(void)e;assert(0);return 0;}
static int close_fd(void *c,int fd){(void)c;(void)fd;assert(0);return 0;}
static void *worker(void *unused){(void)unused;void *b=NULL;int fd=-1;first_rc=ops.request(ops.ctx,&window,&b,&fd);assert(!b && fd==-1);return NULL;}
int main(int argc,char **argv){
 assert(argc==3);struct r15_adapter *a=NULL;
 struct r15_provider p={lower_request,handle,convert,map,unmap,flush,abort_buffer};
 struct r15_capabilities c={NULL,unwrap,clock_ns,poll_fd,close_fd};assert(!r15_create(&p,&c,&a,&ops));
 pthread_t t;assert(!pthread_create(&t,NULL,worker,NULL));pthread_mutex_lock(&mu);while(!entered)pthread_cond_wait(&cv,&mu);pthread_mutex_unlock(&mu);
 int operation=!strcmp(argv[1],"flush")?R15_FLUSH:R15_ABORT;
 int rejected=operation==R15_FLUSH?ops.flush(ops.ctx,&window,NULL,-1,NULL):ops.abort(ops.ctx,&window,NULL);
 struct r15_record before={0},after={0};assert(!r15_record_for(a,(void*)&window,&before));assert(before.phase==1 && before.failed && before.calls[operation].suppressed==1 && !before.calls[operation].called);
 pthread_mutex_lock(&mu);go=1;pthread_cond_broadcast(&cv);pthread_mutex_unlock(&mu);assert(!pthread_join(t,NULL));
 int after_rc=r15_record_for(a,(void*)&window,&after);void *b=NULL;int fd=-1;int second=ops.request(ops.ctx,&window,&b,&fd);
 printf("{\"operation\":\"%s\",\"denied_rc\":%d,\"before_phase\":%u,\"before_failed\":%u,\"before_suppressed\":%u,\"first_rc\":%d,\"after_record_rc\":%d,\"second_rc\":%d,\"lower_calls\":%d}\n",argv[1],rejected,before.phase,before.failed,before.calls[operation].suppressed,first_rc,after_rc,second,lower_calls);fflush(stdout);
 assert(first_rc==40601000);
 if(!strcmp(argv[2],"cleared")){assert(after_rc==-ENOENT && lower_calls==2 && second==40601000);}
 else {assert(after_rc==0 && after.failed && after.calls[operation].suppressed==1 && lower_calls==1 && second==-EBUSY);}
 return 0;
}
