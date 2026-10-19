#define _POSIX_C_SOURCE 200809L
#include "window_module.h"
#include <pthread.h>
#include <assert.h>
#include <errno.h>
#include <poll.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Reusable real thread rendezvous, implemented with pthread mutex/condition on
 * macOS (which does not provide pthread_barrier_t). No sleeps or fake scheduler. */
struct barrier { pthread_mutex_t mu; pthread_cond_t cv; unsigned count,generation; };
static void bi(struct barrier *b){memset(b,0,sizeof(*b));assert(!pthread_mutex_init(&b->mu,NULL));assert(!pthread_cond_init(&b->cv,NULL));}
static void bw(struct barrier *b){pthread_mutex_lock(&b->mu);unsigned g=b->generation;if(++b->count==2){b->count=0;b->generation++;pthread_cond_broadcast(&b->cv);}else while(g==b->generation)pthread_cond_wait(&b->cv,&b->mu);pthread_mutex_unlock(&b->mu);}
static void bd(struct barrier *b){pthread_mutex_destroy(&b->mu);pthread_cond_destroy(&b->cv);}
struct window {int id,request_rc,null_buffer,fd,handle_rc,convert_rc,null_native,map_rc,null_bits,unmap_rc,flush_rc,abort_rc,close_rc;struct r14_handle h;};
struct poll_step {int rc,err;short flags;int64_t elapsed;};
struct event {const char *name;int id,value;};
struct fixture {pthread_mutex_t mu;struct window w[10];int wrappers[11];struct event journal[1024];int n,active[10],overlap;struct poll_step polls[8];int np,poll_index;int64_t now;int clock_rc;int block_id;const char *block_event;struct barrier entered,resume;struct r14_module *m;};
static void loge(struct fixture *f,const char *name,int id,int value){pthread_mutex_lock(&f->mu);assert(f->n<1024);f->journal[f->n++]=(struct event){name,id,value};pthread_mutex_unlock(&f->mu);}
static void enter(struct fixture *f,struct window *w,const char *name){pthread_mutex_lock(&f->mu);if(++f->active[w->id]!=1)f->overlap++;pthread_mutex_unlock(&f->mu);loge(f,name,w->id,0);if(f->block_event && f->block_id==w->id && !strcmp(name,f->block_event)){bw(&f->entered);bw(&f->resume);}}
static void leave(struct fixture *f,struct window *w){pthread_mutex_lock(&f->mu);assert(f->active[w->id]==1);f->active[w->id]--;pthread_mutex_unlock(&f->mu);}
static int unwrap(void *c,const void *wr,void **oh){struct fixture *f=c;for(int i=0;i<11;i++)if(wr==&f->wrappers[i]){*oh=&f->w[i==10?0:i];return 0;}return -ENODEV;}
static int request(void *c,void *oh,void **buf,int *fd){struct fixture *f=c;struct window *w=oh;enter(f,w,"request");*buf=w->null_buffer?NULL:w;*fd=w->fd;int rc=w->request_rc;leave(f,w);return rc;}
static int handle(void *c,void *buf,struct r14_handle *h){struct fixture *f=c;struct window *w=buf;enter(f,w,"handle");*h=w->h;int rc=w->handle_rc;leave(f,w);return rc;}
static int convert(void *c,void *buf,void **nb){struct fixture *f=c;struct window *w=buf;enter(f,w,"convert");*nb=w->null_native?NULL:w;int rc=w->convert_rc;leave(f,w);return rc;}
static int map(void *c,void *nb,void **bits){struct fixture *f=c;struct window *w=nb;enter(f,w,"map");*bits=w->null_bits?NULL:(void *)&f->wrappers[w->id];int rc=w->map_rc;leave(f,w);return rc;}
static int unmap(void *c,void *nb){struct fixture *f=c;struct window *w=nb;enter(f,w,"unmap");int rc=w->unmap_rc;leave(f,w);return rc;}
static int flush(void *c,void *oh,void *buf,int fd,const struct r14_rect *r){struct fixture *f=c;struct window *w=oh;assert(buf==oh && fd==-1);assert(r->left==0 && r->top==0 && r->right==w->h.width && r->bottom==w->h.height);enter(f,w,"flush");int rc=w->flush_rc;leave(f,w);return rc;}
static int abort_buffer(void *c,void *oh,void *buf){struct fixture *f=c;struct window *w=oh;assert(oh==buf);enter(f,w,"abort");int rc=w->abort_rc;leave(f,w);return rc;}
static int clock_ns(void *c,int64_t *t){struct fixture *f=c;pthread_mutex_lock(&f->mu);*t=f->now;int rc=f->clock_rc;pthread_mutex_unlock(&f->mu);return rc;}
static int poll_fd(void *c,int fd,int ms,short *events,int *err){struct fixture *f=c;assert(fd==17 && ms>0 && ms<=3000);loge(f,"poll",0,ms);assert(f->poll_index<f->np);struct poll_step s=f->polls[f->poll_index++];f->now+=s.elapsed;*events=s.flags;*err=s.err;return s.rc;}
static int close_fd(void *c,int fd){struct fixture *f=c;assert(fd==17);loge(f,"close",0,fd);return f->w[0].close_rc;}
static struct r14_ops ops(struct fixture *f){return (struct r14_ops){.ctx=f,.unwrap=unwrap,.request=request,.handle=handle,.convert=convert,.map=map,.unmap=unmap,.flush=flush,.abort=abort_buffer,.clock_ns=clock_ns,.poll_fd=poll_fd,.close_fd=close_fd};}
static void init(struct fixture *f){memset(f,0,sizeof(*f));assert(!pthread_mutex_init(&f->mu,NULL));bi(&f->entered);bi(&f->resume);f->block_id=-1;for(int i=0;i<10;i++){f->w[i].id=i;f->w[i].fd=-1;f->w[i].h=(struct r14_handle){16,8,64,512,12};}struct r14_ops o=ops(f);assert(!r14_create(&o,&f->m));}
static int count(struct fixture *f,const char *name,int id){int n=0;pthread_mutex_lock(&f->mu);for(int i=0;i<f->n;i++)if(!strcmp(name,f->journal[i].name) && f->journal[i].id==id)n++;pthread_mutex_unlock(&f->mu);return n;}
static void finish(struct fixture *f,const char *name,int retained){assert(!f->overlap);assert(r14_destroy(f->m)==(retained?-EBUSY:0));printf("{\"case\":\"%s\",\"status\":\"PASS\",\"journal\":[",name);for(int i=0;i<f->n;i++)printf("%s[\"%s\",%d,%d]",i?",":"",f->journal[i].name,f->journal[i].id,f->journal[i].value);puts("]}");pthread_mutex_destroy(&f->mu);bd(&f->entered);bd(&f->resume);/* Failed module intentionally quarantined until process exit; no force reset. */}
static int lockw(struct fixture *f,int id,struct r14_buffer *b,struct r14_report *r){return r14_lock(f->m,&f->wrappers[id],b,NULL,r);}
static void cleared(const struct r14_buffer *b){struct r14_buffer z={0};assert(!memcmp(b,&z,sizeof(z)));}
static void reject(struct fixture *f,const char *name,int maps,int unmaps,int aborts){struct r14_buffer b;memset(&b,0xa5,sizeof(b));struct r14_report r;assert(lockw(f,0,&b,&r)<0);cleared(&b);assert(r.retained && r.primary<0);assert(count(f,"close",0)==(f->w[0].fd>=0));assert(count(f,"map",0)==maps && count(f,"unmap",0)==unmaps && count(f,"abort",0)==aborts && !count(f,"flush",0));struct r14_report stored;assert(!r14_report_for(f->m,&f->wrappers[0],&stored));assert(!memcmp(&r,&stored,sizeof(r)));int n=count(f,"request",0);assert(lockw(f,10,&b,NULL)==-EBUSY);assert(r14_unlock(f->m,&f->wrappers[0],NULL)==-EBUSY);assert(count(f,"request",0)==n);finish(f,name,1);}
static void pair_tests(void){
 int formats[]={12,11,13,3,20,39,34},android[]={1,2,3,4,5,0x16,0x2b},bpp[]={4,4,3,2,4,8,4};
 for(int i=0;i<7;i++){struct fixture f;init(&f);f.w[0].h.format=formats[i];f.w[0].h.stride_bytes=20*bpp[i];f.w[0].h.size_bytes=f.w[0].h.stride_bytes*8;if(i==0){f.w[0].fd=17;f.polls[0]=(struct poll_step){1,0,POLLIN,1000000};f.np=1;}struct r14_buffer b;struct r14_rect d;struct r14_report r;assert(!r14_lock(f.m,&f.wrappers[0],&b,&d,&r));assert(b.width==16 && b.height==8 && b.stride==20 && b.format==android[i] && b.bits && d.right==16 && d.bottom==8);assert(!r14_unlock(f.m,&f.wrappers[0],&r));assert(count(&f,"unmap",0)==1 && count(&f,"flush",0)==1 && !count(&f,"abort",0));const char *order[]={"request","handle","convert","map","unmap","flush"};int k=0;for(int j=0;j<f.n;j++)if(strcmp(f.journal[j].name,"poll") && strcmp(f.journal[j].name,"close")){assert(k<6 && !strcmp(f.journal[j].name,order[k++]));}assert(k==6);if(i==0){assert(f.n==8);assert(!strcmp(f.journal[0].name,"request") && !strcmp(f.journal[1].name,"poll") && !strcmp(f.journal[2].name,"close") && !strcmp(f.journal[5].name,"map"));}assert(count(&f,"close",0)==(i==0));f.w[0].fd=-1;assert(!lockw(&f,0,&b,&r));assert(!r14_unlock(f.m,&f.wrappers[0],NULL));char n[40];snprintf(n,sizeof(n),"format-%d-success-reuse",formats[i]);finish(&f,n,0);}
}
static void failures(void){
 struct fixture f;init(&f);struct r14_ops o=ops(&f);struct r14_module *m=NULL;
#define MISSING(field) do {struct r14_ops q=o;q.field=NULL;assert(r14_create(&q,&m)==-ENOSYS && !m);}while(0)
 MISSING(unwrap);MISSING(request);MISSING(handle);MISSING(convert);MISSING(map);MISSING(unmap);MISSING(flush);MISSING(abort);MISSING(clock_ns);MISSING(poll_fd);MISSING(close_fd);
 struct r14_buffer b;struct r14_rect d;memset(&b,1,sizeof(b));assert(r14_lock(f.m,(void *)(uintptr_t)1,&b,&d,NULL)==-ENODEV);cleared(&b);assert(r14_lock(f.m,NULL,&b,NULL,NULL)==-EINVAL);assert(r14_lock(f.m,&f.wrappers[0],NULL,NULL,NULL)==-EINVAL);assert(f.n==0);finish(&f,"missing-capabilities-and-untrusted-wrapper",0);
 init(&f);f.w[0].request_rc=-37;f.w[0].fd=17;reject(&f,"request-error-owned-fence",0,0,1);
}
static void failure_matrix(void){
 struct fixture f;
 init(&f);f.w[0].request_rc=-37;f.w[0].null_buffer=1;reject(&f,"request-error-no-output-retained",0,0,0);
 init(&f);f.w[0].null_buffer=1;reject(&f,"request-null-buffer",0,0,0);
 init(&f);f.w[0].handle_rc=-8;reject(&f,"handle-error",0,0,1);
 init(&f);f.w[0].convert_rc=-9;reject(&f,"conversion-error",0,0,1);
 init(&f);f.w[0].null_native=1;reject(&f,"conversion-null",0,0,1);
 init(&f);f.w[0].map_rc=-10;reject(&f,"map-error-nonnull-bits",1,0,1);
 init(&f);f.w[0].map_rc=-10;f.w[0].null_bits=1;reject(&f,"map-error-null-bits",1,0,1);
 init(&f);f.w[0].null_bits=1;reject(&f,"map-success-null-bits",1,1,1);
 init(&f);f.w[0].h.format=999;reject(&f,"unsupported-format",1,1,1);
 init(&f);f.w[0].h.width=0;reject(&f,"zero-width",1,1,1);
 init(&f);f.w[0].h.height=-1;reject(&f,"negative-height",1,1,1);
 init(&f);f.w[0].h.stride_bytes=63;reject(&f,"stride-not-divisible",1,1,1);
 init(&f);f.w[0].h.stride_bytes=60;reject(&f,"stride-short-width",1,1,1);
 init(&f);f.w[0].h.size_bytes=511;reject(&f,"allocation-too-small",1,1,1);
 init(&f);f.w[0].h.height=INT64_MAX;reject(&f,"dimension-overflow",1,1,1);
 init(&f);f.w[0].h.stride_bytes=INT64_MAX;reject(&f,"stride-overflow",1,1,1);
 init(&f);f.w[0].h.format=999;f.w[0].unmap_rc=-17;reject(&f,"validation-unmap-error-no-abort",1,1,0);
 init(&f);f.w[0].map_rc=-10;f.w[0].abort_rc=-18;reject(&f,"abort-error-preserved",1,0,1);
 struct poll_step cases[]={{0,0,0,0},{1,0,POLLHUP,1},{1,0,POLLERR,1},{1,0,POLLNVAL,1},{1,0,POLLIN|POLLHUP,1},{1,0,0,1},{-1,EIO,0,1},{1,0,POLLIN,3000000000LL}};
 for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){init(&f);f.w[0].fd=17;f.polls[0]=cases[i];f.np=1;char n[32];snprintf(n,sizeof(n),"fence-terminal-%u",i);reject(&f,n,0,0,1);}
 init(&f);f.w[0].fd=17;f.clock_rc=-1;reject(&f,"clock-failure",0,0,1);
 init(&f);f.w[0].fd=17;f.now=INT64_MAX;reject(&f,"deadline-overflow",0,0,1);
 init(&f);f.w[0].fd=-2;reject(&f,"invalid-negative-fd",0,0,1);
 init(&f);f.w[0].fd=17;f.w[0].close_rc=-4;f.polls[0]=(struct poll_step){1,0,POLLIN,1};f.np=1;reject(&f,"close-error-no-retry",0,0,1);
 init(&f);f.w[0].fd=17;f.np=3;for(int i=0;i<3;i++)f.polls[i]=(struct poll_step){-1,i==1?EAGAIN:EINTR,0,1000000000};
 struct r14_buffer b;struct r14_report r;assert(lockw(&f,0,&b,&r)==-ETIMEDOUT);assert(f.poll_index==3 && r.close_called==1);int pi=0;for(int i=0;i<f.n;i++)if(!strcmp(f.journal[i].name,"poll"))assert(f.journal[i].value==3000-1000*pi++);assert(pi==3 && !count(&f,"map",0));finish(&f,"eintr-eagain-total-deadline",1);
 init(&f);f.w[0].fd=17;f.polls[0]=(struct poll_step){-1,EAGAIN,0,100000000};f.polls[1]=(struct poll_step){1,0,POLLIN,1};f.np=2;assert(!lockw(&f,0,&b,&r));assert(count(&f,"poll",0)==2 && count(&f,"close",0)==1);assert(!r14_unlock(f.m,&f.wrappers[0],NULL));finish(&f,"eagain-then-ready",0);
}
struct thread_args {struct fixture *f;int unlock,rc;};
static void *worker(void *arg){struct thread_args *a=arg;struct r14_buffer b;a->rc=a->unlock?r14_unlock(a->f->m,&a->f->wrappers[0],NULL):lockw(a->f,0,&b,NULL);return NULL;}
static void concurrency(void){
 const char *stages[]={"request","map","unmap","flush"};
 for(int j=0;j<4;j++){
  struct fixture f;init(&f);struct r14_buffer b;int unlocking=j>=2;if(unlocking)assert(!lockw(&f,0,&b,NULL));f.block_id=0;f.block_event=stages[j];struct thread_args a={&f,unlocking,999};pthread_t t;assert(!pthread_create(&t,NULL,worker,&a));bw(&f.entered);
  assert(lockw(&f,0,&b,NULL)==-EBUSY);assert(lockw(&f,10,&b,NULL)==-EBUSY);assert(r14_unlock(f.m,&f.wrappers[0],NULL)==-EBUSY);assert(r14_unlock(f.m,&f.wrappers[10],NULL)==-EBUSY);
  assert(!lockw(&f,1,&b,NULL));assert(!r14_unlock(f.m,&f.wrappers[1],NULL));bw(&f.resume);assert(!pthread_join(t,NULL));assert(a.rc==0);f.block_event=NULL;if(!unlocking)assert(!r14_unlock(f.m,&f.wrappers[0],NULL));assert(count(&f,"request",0)==1 && count(&f,"map",0)==1 && count(&f,"unmap",0)==1 && count(&f,"flush",0)==1);char n[60];snprintf(n,sizeof(n),"barrier-%s-alias-other-window",stages[j]);finish(&f,n,0);
 }
 struct fixture f;struct r14_buffer b;struct r14_report r;
 for(int which=0;which<2;which++){init(&f);assert(!lockw(&f,0,&b,NULL));if(which)f.w[0].flush_rc=-63;else f.w[0].unmap_rc=-62;assert(r14_unlock(f.m,&f.wrappers[0],&r)==(which?-63:-62));assert(r.retained && count(&f,"unmap",0)==1 && count(&f,"flush",0)==which && !count(&f,"abort",0));assert(r14_unlock(f.m,&f.wrappers[0],NULL)==-EBUSY);assert(lockw(&f,10,&b,NULL)==-EBUSY);struct r14_report q;assert(!r14_report_for(f.m,&f.wrappers[0],&q));assert(q.primary==r.primary && q.unmap_rc==r.unmap_rc && q.flush_rc==r.flush_rc);finish(&f,which?"flush-failure-retained":"unmap-failure-retained",1);}
 init(&f);for(int i=0;i<8;i++){f.w[i].request_rc=-37;f.w[i].null_buffer=1;assert(lockw(&f,i,&b,&r)==-37 && r.retained);}
 assert(lockw(&f,8,&b,NULL)==-ENOSPC && !count(&f,"request",8));assert(!count(&f,"abort",0));assert(r14_destroy(f.m)==-EBUSY);finish(&f,"eight-empty-request-errors-quarantine",1);
 init(&f);for(int i=0;i<8;i++)assert(!lockw(&f,i,&b,NULL));assert(r14_destroy(f.m)==-EBUSY);assert(lockw(&f,8,&b,NULL)==-ENOSPC && !count(&f,"request",8));assert(lockw(&f,10,&b,NULL)==-EBUSY);assert(!r14_unlock(f.m,&f.wrappers[3],NULL));assert(!lockw(&f,8,&b,NULL));for(int i=0;i<9;i++)if(i!=3)assert(!r14_unlock(f.m,&f.wrappers[i],NULL));finish(&f,"eight-slots-and-release-reuse",0);
}
int main(int argc,char **argv){assert(argc==2);if(!strcmp(argv[1],"pair"))pair_tests();else if(!strcmp(argv[1],"failures")){failures();failure_matrix();}else if(!strcmp(argv[1],"concurrency"))concurrency();else return 2;return 0;}
