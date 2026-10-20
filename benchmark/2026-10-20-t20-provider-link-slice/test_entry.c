/* Real POSIX callback and linked-wrapper tests; fake provider is NOT an OH run. */
#include "entry.c"
#include <assert.h>
#include <stdio.h>
static int unwrap_calls;
static int reject(void *v,const void *w,OHNativeWindow **o){(void)v;(void)w;unwrap_calls++;*o=NULL;return -ENODEV;}
static int request(OHNativeWindow *w,OHNativeWindowBuffer **b,int *fd){(void)w;*b=NULL;*fd=-1;return -EIO;}
static BufferHandle *handle(OHNativeWindowBuffer *b){(void)b;return NULL;}
static int convert(OHNativeWindowBuffer *b,OH_NativeBuffer **n){(void)b;*n=NULL;return -EIO;}
static int map(OH_NativeBuffer *b,void **p){(void)b;*p=NULL;return -EIO;}
static int unmap(OH_NativeBuffer *b){(void)b;return -EIO;}
static int flush(OHNativeWindow *w,OHNativeWindowBuffer *b,int fd,Region r){(void)w;(void)b;(void)fd;(void)r;return -EIO;}
static int abort_buffer(OHNativeWindow *w,OHNativeWindowBuffer *b){(void)w;(void)b;return -EIO;}
static int failure;
static int32_t hprefix[6]={-1,2,8,2,16,12};static unsigned char pixels[16];static int window_id,buffer_id,native_id;
static int accept(void *v,const void *w,OHNativeWindow **o){(void)v;(void)w;*o=(OHNativeWindow*)&window_id;return 0;}
static int request_ok(OHNativeWindow *w,OHNativeWindowBuffer **b,int *fd){(void)w;*b=(OHNativeWindowBuffer*)&buffer_id;*fd=-1;return failure?-EIO:0;}
static BufferHandle *handle_ok(OHNativeWindowBuffer *b){(void)b;return (BufferHandle*)hprefix;}
static int convert_ok(OHNativeWindowBuffer *b,OH_NativeBuffer **n){(void)b;*n=(OH_NativeBuffer*)&native_id;return 0;}
static int map_ok(OH_NativeBuffer *b,void **p){(void)b;*p=pixels;return 0;}
static int unmap_ok(OH_NativeBuffer *b){(void)b;return 0;}
static int flush_ok(OHNativeWindow *w,OHNativeWindowBuffer *b,int fd,Region r){(void)w;(void)b;assert(fd==-1 && r.rectNumber==1 && r.rects[0].w==2);return 0;}
int main(void){
 int64_t a,b;assert(os_clock(NULL,&a)==0);assert(os_clock(NULL,&b)==0 && b>=a);assert(os_clock(NULL,NULL)==-EINVAL);
 int f[2];assert(pipe(f)==0);short events;int error;assert(os_poll(NULL,f[0],0,&events,&error)==0 && !events && !error);
 assert(write(f[1],"x",1)==1);assert(os_poll(NULL,f[0],1,&events,&error)==1 && (events&POLLIN) && !error);
 assert(os_close(NULL,f[0])==0);assert(os_close(NULL,f[0])==-EBADF);assert(os_close(NULL,f[1])==0);assert(os_poll(NULL,-1,0,&events,&error)==-1 && error==EINVAL);
 struct r15_provider p={request,handle,convert,map,unmap,flush,abort_buffer};struct r20_owner own={NULL,reject};struct r20_context *c=(void*)1;
 assert(r20_create(NULL,&own,&c)==-ENOSYS && c==NULL);struct r15_provider missing=p;missing.flush=NULL;assert(r20_create(&missing,&own,&c)==-ENOSYS && c==NULL);
 assert(r20_create(&p,&own,&c)==0 && c);struct r14_buffer buf;memset(&buf,0xff,sizeof(buf));struct r14_report report;
 assert(r20_lock(c,(void*)1,&buf,NULL,&report)==-ENODEV && unwrap_calls==1 && buf.bits==NULL && report.request_called==0);
 assert(r20_unlock(c,(void*)1,&report)==-EBUSY);assert(r20_destroy(c)==0);
 assert(r20_lock(NULL,(void*)1,&buf,NULL,&report)==-EINVAL && buf.bits==NULL);assert(r20_destroy(NULL)==-EINVAL);
 struct r15_provider good={request_ok,handle_ok,convert_ok,map_ok,unmap_ok,flush_ok,abort_buffer};own.unwrap=accept;
 assert(r20_create(&good,&own,&c)==0);assert(r20_lock(c,(void*)1,&buf,NULL,&report)==0 && buf.bits==pixels && buf.stride==2);
 assert(r20_destroy(c)==-EBUSY);assert(r20_unlock(c,(void*)1,&report)==0);assert(r20_destroy(c)==0);
 failure=1;assert(r20_create(&good,&own,&c)==0);assert(r20_lock(c,(void*)1,&buf,NULL,&report)==-EIO && report.retained);assert(r20_destroy(c)==-EBUSY);
 /* The uncertain context intentionally remains owned until process exit. */
 puts("PASS real-clock monotonic; real-pipe timeout/readiness/close; missing-provider refusal; owner refusal never requests; empty lifecycle; invalid context");return 0;
}
