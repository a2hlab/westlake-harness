#define _DEFAULT_SOURCE
#include "provider_adapter.h"
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <poll.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"assertion %s:%d: %s\n",__FILE__,__LINE__,#x);abort();}}while(0)
struct env;
struct OH_NativeBuffer {struct NativeWindow *owner;};
struct NativeWindowBuffer {struct NativeWindow *owner;};
/* Two-layer journal is owned entirely by the fake provider, not by the adapter. */
struct event {const char *name;int id,value;};
struct gate {pthread_mutex_t mu;pthread_cond_t cv;int entered,release;};
struct NativeWindow {
 struct env *e;int id;struct NativeWindow *alias;unsigned char *prefix;void *allocation;size_t page;
 struct NativeWindowBuffer b;struct OH_NativeBuffer n;
 struct NativeWindowBuffer *requested;struct OH_NativeBuffer *converted;
 int request_rc,fd,convert_rc,map_rc,unmap_rc,flush_rc,abort_lower_rc;
 int null_request,null_convert,null_handle,map_kind; /* 0 pointer,1 NULL,2 allones,3 second internal Map fails */
 struct gate *gate;const char *gate_at;
};
struct env {pthread_mutex_t journal_mu;struct event ev[4096];int used;struct NativeWindow w[12];struct r15_adapter *a;struct r14_module *m;struct r14_ops ops;};
static void journal(struct NativeWindow *w,const char *name,int value) {
 struct env *e=w->e;pthread_mutex_lock(&e->journal_mu);CHECK(e->used<4096);e->ev[e->used++]=(struct event){name,w->id,value};pthread_mutex_unlock(&e->journal_mu);
}
static int count(struct env *e,int id,const char *name) {int n=0;pthread_mutex_lock(&e->journal_mu);for(int i=0;i<e->used;i++)n+=e->ev[i].id==id && !strcmp(e->ev[i].name,name);pthread_mutex_unlock(&e->journal_mu);return n;}
static void pause_provider(struct NativeWindow *w,const char *at) {
 if(!w->gate || strcmp(w->gate_at,at))return;
 struct gate *g=w->gate;pthread_mutex_lock(&g->mu);g->entered=1;pthread_cond_broadcast(&g->cv);while(!g->release)pthread_cond_wait(&g->cv,&g->mu);pthread_mutex_unlock(&g->mu);
}
static int32_t request_p(OHNativeWindow *w,OHNativeWindowBuffer **b,int *fd) {
 journal(w,"public.request",w->request_rc);pause_provider(w,"request");*b=w->null_request?NULL:w->requested;*fd=w->fd;return w->request_rc;
}
static BufferHandle *handle_p(OHNativeWindowBuffer *b){struct NativeWindow *w=b->owner;journal(w,"public.handle",0);return w->null_handle?NULL:(BufferHandle *)w->prefix;}
static int32_t convert_p(OHNativeWindowBuffer *b,OH_NativeBuffer **n){struct NativeWindow *w=b->owner;journal(w,"public.convert",w->convert_rc);*n=w->null_convert?NULL:w->converted;return w->convert_rc;}
static int32_t map_p(OH_NativeBuffer *n,void **bits) {
 struct NativeWindow *w=n->owner;journal(w,"public.map",w->map_rc);pause_provider(w,"map");
 journal(w,"internal.Map",0);
 if(!w->map_rc){journal(w,"internal.GetVirAddr",0);journal(w,"internal.Map",w->map_kind==3?50007000:0);}
 *bits=(w->map_kind==1 || w->map_kind==3)?NULL:w->map_kind==2?(void *)UINTPTR_MAX:(void *)w->prefix;
 return w->map_rc;
}
static int32_t unmap_p(OH_NativeBuffer *n){struct NativeWindow *w=n->owner;journal(w,"public.unmap",w->unmap_rc);pause_provider(w,"unmap");journal(w,"internal.Unmap",w->unmap_rc);return w->unmap_rc;}
static int32_t flush_p(OHNativeWindow *w,OHNativeWindowBuffer *b,int fd,Region region){
 CHECK(b==w->requested);CHECK(fd==-1);CHECK(region.rectNumber==1);CHECK(region.rects);
 journal(w,"region.x",region.rects->x);journal(w,"region.y",region.rects->y);
 journal(w,"region.w",(int)region.rects->w);journal(w,"region.h",(int)region.rects->h);
 journal(w,"public.flush",w->flush_rc);pause_provider(w,"flush");return w->flush_rc;
}
static int32_t abort_p(OHNativeWindow *w,OHNativeWindowBuffer *b){CHECK(b==w->requested);journal(w,"public.abort",0);journal(w,"internal.CancelBuffer",w->abort_lower_rc);return 0;}
static int unwrap_c(void *v,const void *wrapper,OHNativeWindow **w){(void)v;OHNativeWindow *input=(OHNativeWindow *)wrapper;*w=input->alias?input->alias:input;return 0;}
static int clock_c(void *v,int64_t *n){(void)v;*n=100000;return 0;}
static int poll_c(void *v,int fd,int ms,short *re,int *err){(void)v;CHECK(fd==7);CHECK(ms>0 && ms<=3000);*re=POLLIN;*err=0;return 1;}
static int close_c(void *v,int fd){struct env *e=v;CHECK(fd==7);journal(&e->w[0],"close.fence",fd);return 0;}
static void put(struct NativeWindow *w,int offset,int32_t x){memcpy(w->prefix+offset,&x,4);}
static struct env *make(void) {
 struct env *e=calloc(1,sizeof(*e));CHECK(e);CHECK(!pthread_mutex_init(&e->journal_mu,NULL));
 for(int i=0;i<12;i++){
  struct NativeWindow *w=&e->w[i];w->e=e;w->id=i;w->fd=-1;w->b.owner=w;w->n.owner=w;w->requested=&w->b;w->converted=&w->n;
  w->page=(size_t)sysconf(_SC_PAGESIZE);w->allocation=mmap(NULL,w->page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);CHECK(w->allocation!=MAP_FAILED);
  CHECK(!mprotect((char *)w->allocation+w->page,w->page,PROT_NONE));w->prefix=(unsigned char *)w->allocation+w->page-24;
  put(w,4,8);put(w,8,32);put(w,12,4);put(w,16,128);put(w,20,12);
 }
 struct r15_provider p={request_p,handle_p,convert_p,map_p,unmap_p,flush_p,abort_p};
 struct r15_capabilities c={e,unwrap_c,clock_c,poll_c,close_c};
 CHECK(!r15_create(&p,&c,&e->a,&e->ops));CHECK(!r14_create(&e->ops,&e->m));return e;
}
static int lock_w(struct env *e,int i,struct r14_report *r){struct r14_buffer b;memset(&b,0x55,sizeof(b));struct r14_rect d;int rc=r14_lock(e->m,&e->w[i],&b,&d,r);if(rc){struct r14_buffer z={0};struct r14_rect dz={0};CHECK(!memcmp(&b,&z,sizeof(b)));CHECK(!memcmp(&d,&dz,sizeof(d)));}else {CHECK(b.bits==e->w[i].prefix);CHECK(b.stride>=b.width);CHECK(d.left==0 && d.top==0 && d.right==b.width && d.bottom==b.height);}return rc;}
static void emit(struct env *e,const char *name) {
 printf("{\"case\":\"%s\",\"status\":\"PASS\",\"journal\":[",name);
 for(int i=0;i<e->used;i++)printf("%s{\"layer_event\":\"%s\",\"window\":%d,\"value\":%d}",i?",":"",e->ev[i].name,e->ev[i].id,e->ev[i].value);
 puts("]}");
}
static void retained(struct env *e,int i){struct r14_report r;CHECK(r14_lock(e->m,&e->w[i],&(struct r14_buffer){0},NULL,&r)==-EBUSY);CHECK(r14_destroy(e->m)==-EBUSY);CHECK(r15_destroy(e->a)==-EBUSY);}
static void pair(void) {
 int formats[]={12,11,13,3,20,39,34},bpp[]={4,4,3,2,4,8,4},android[]={1,2,3,4,5,22,43};
 for(int k=0;k<7;k++){
  struct env *e=make();struct NativeWindow *w=&e->w[0];put(w,4,7);put(w,12,3);put(w,20,formats[k]);put(w,8,11*bpp[k]);put(w,16,33*bpp[k]+17);w->fd=7;
  struct r14_report r;struct r14_buffer actual;struct r14_rect dirty;CHECK(!r14_lock(e->m,w,&actual,&dirty,&r));CHECK(actual.width==7 && actual.height==3 && actual.stride==11 && actual.format==android[k] && actual.bits==w->prefix);CHECK(dirty.left==0 && dirty.top==0 && dirty.right==7 && dirty.bottom==3);for(unsigned z=0;z<6;z++)CHECK(actual.reserved[z]==0);CHECK(!r14_unlock(e->m,w,&r));CHECK(count(e,0,"public.map")==1 && count(e,0,"internal.Map")==2);CHECK(count(e,0,"public.unmap")==1 && count(e,0,"public.flush")==1 && count(e,0,"public.abort")==0);CHECK(count(e,0,"close.fence")==1);
  CHECK(r15_record_for(e->a,w,&(struct r15_record){0})==-ENOENT);CHECK(!lock_w(e,0,&r));CHECK(!r14_unlock(e->m,w,&r));CHECK(!r14_destroy(e->m));CHECK(!r15_destroy(e->a));char label[64];snprintf(label,sizeof(label),"pair-format-%d",formats[k]);emit(e,label);
 }
}
static void layout(void) {
 int offset[]={4,8,12,16,20,4,8,8,16};int32_t val[]={-1,-1,-1,-1,-1,INT32_MAX,31,16,127};
 for(int k=0;k<9;k++){
  struct env *e=make();put(&e->w[0],offset[k],val[k]);struct r14_report r;CHECK(lock_w(e,0,&r)!=0);CHECK(!count(e,0,"public.flush"));CHECK(count(e,0,"public.unmap")==1);retained(e,0);char n[50];snprintf(n,sizeof(n),"layout-invalid-%d",k);emit(e,n);
 }
 {struct env *e=make();void *b=NULL;int fd;CHECK(!e->ops.request(e->a,&e->w[0],&b,&fd));put(&e->w[0],4,-1);put(&e->w[0],8,INT32_MAX);struct r14_handle h;CHECK(!e->ops.handle(e->a,b,&h));CHECK(h.width==-1 && h.stride_bytes==INT32_MAX);emit(e,"signed32-copy-at-guard-page");}
 struct r14_rect regions[]={{4,6,12,10},{8,0,2,4},{0,4,8,2},{INT32_MIN,0,INT32_MAX,4},{0,INT32_MIN,8,INT32_MAX},{0,0,0,4}};
 for(int k=0;k<6;k++){
  struct env *e=make();struct r14_report r;CHECK(!lock_w(e,0,&r));CHECK(!e->ops.unmap(e->a,&e->w[0].n));int rc=e->ops.flush(e->a,&e->w[0],&e->w[0].b,-1,&regions[k]);
  if(!k){CHECK(!rc);int x=0,y=0,w=0,h=0;for(int j=0;j<e->used;j++){struct event *ev=&e->ev[j];if(!strcmp(ev->name,"region.x"))x=ev->value;if(!strcmp(ev->name,"region.y"))y=ev->value;if(!strcmp(ev->name,"region.w"))w=ev->value;if(!strcmp(ev->name,"region.h"))h=ev->value;}CHECK(x==4 && y==6 && w==8 && h==4);}
  else {CHECK(rc!=0);CHECK(!count(e,0,"public.flush"));}
  char n[50];snprintf(n,sizeof(n),"region-%d",k);emit(e,n);
 }
}
static void failures(void) {
 {struct env *e=make();e->w[0].request_rc=-99;e->w[0].fd=7;struct r14_report r;CHECK(lock_w(e,0,&r)!=0);CHECK(r.request_rc==-99 && r.close_called && count(e,0,"close.fence")==1);CHECK(!count(e,0,"public.abort"));retained(e,0);emit(e,"request-error-owned-fence");}
 for(int kind=1;kind<=3;kind++){
  struct env *e=make();e->w[0].map_kind=kind;e->w[0].abort_lower_rc=-73;struct r14_report r;CHECK(lock_w(e,0,&r)!=0);CHECK(count(e,0,"public.map")==1);struct r15_record ar;CHECK(!r15_record_for(e->a,&e->w[0],&ar));CHECK(ar.calls[R15_MAP].raw_valid && ar.calls[R15_MAP].raw_rc==0);
  if(kind==2){CHECK(!count(e,0,"public.unmap") && !count(e,0,"public.abort"));CHECK(ar.calls[R15_UNMAP].suppressed==1 && !ar.calls[R15_UNMAP].raw_valid);CHECK(r.unmap_called && r.unmap_rc && !r.abort_called);}
  else {CHECK(count(e,0,"public.unmap")==1 && count(e,0,"public.abort")==1);CHECK(ar.calls[R15_ABORT].raw_valid && ar.calls[R15_ABORT].raw_rc==0);CHECK(count(e,0,"internal.Map")==2);}
  retained(e,0);char n[40];snprintf(n,sizeof(n),"map-null-sentinel-second-%d",kind);emit(e,n);
 }
 {struct env *e=make();e->w[0].map_rc=50007000;struct r14_report r;CHECK(lock_w(e,0,&r)!=0);CHECK(!count(e,0,"public.unmap") && !count(e,0,"public.abort"));struct r15_record ar;CHECK(!r15_record_for(e->a,&e->w[0],&ar));CHECK(ar.calls[R15_MAP].raw_rc==50007000 && ar.calls[R15_ABORT].suppressed==1);retained(e,0);emit(e,"map-error-nonnull");}
 for(int k=0;k<5;k++){
  struct env *e=make();if(k==0)e->w[0].request_rc=-17;if(k==1)e->w[0].null_request=1;if(k==2)e->w[0].fd=-2;if(k==3)e->w[0].null_handle=1;if(k==4)e->w[0].null_convert=1;
  struct r14_report r;CHECK(lock_w(e,0,&r)!=0);CHECK(!count(e,0,"public.map"));if(k<3)CHECK(!count(e,0,"public.abort"));retained(e,0);char n[50];snprintf(n,sizeof(n),"request-conversion-failure-%d",k);emit(e,n);
 }
 for(int k=0;k<3;k++){
  struct env *e=make();if(k<2)e->w[0].unmap_rc=-83;else e->w[0].flush_rc=-91;
  struct r14_report r;if(k==0){e->w[0].map_kind=1;CHECK(lock_w(e,0,&r)!=0);}else{CHECK(!lock_w(e,0,&r));CHECK(r14_unlock(e->m,&e->w[0],&r)!=0);}
  CHECK(!count(e,0,"public.abort"));CHECK(count(e,0,"public.flush")== (k==2));retained(e,0);char n[50];snprintf(n,sizeof(n),"unmap-flush-error-%d",k);emit(e,n);
 }
}
struct worker {struct env *e;int id,unlock,rc;};
static void *run(void *p){struct worker *w=p;struct r14_report r;w->rc=w->unlock?r14_unlock(w->e->m,&w->e->w[w->id],&r):lock_w(w->e,w->id,&r);return NULL;}
static void gate_init(struct gate *g){memset(g,0,sizeof(*g));CHECK(!pthread_mutex_init(&g->mu,NULL));CHECK(!pthread_cond_init(&g->cv,NULL));}
static void entered(struct gate *g){pthread_mutex_lock(&g->mu);while(!g->entered)pthread_cond_wait(&g->cv,&g->mu);pthread_mutex_unlock(&g->mu);}
static void release(struct gate *g){pthread_mutex_lock(&g->mu);g->release=1;pthread_cond_broadcast(&g->cv);pthread_mutex_unlock(&g->mu);}
static void concurrency(void) {
 const char *at[]={"request","map","unmap","flush"};
 for(int k=0;k<4;k++){
  struct env *e=make();struct r14_report r;if(k>=2)CHECK(!lock_w(e,0,&r));struct gate g;gate_init(&g);e->w[0].gate=&g;e->w[0].gate_at=at[k];struct worker w={e,0,k>=2,99};pthread_t t;CHECK(!pthread_create(&t,NULL,run,&w));entered(&g);
  CHECK(lock_w(e,0,&r)==-EBUSY);e->w[10].alias=&e->w[0];CHECK(lock_w(e,10,&r)==-EBUSY);CHECK(!count(e,10,"public.request"));CHECK(!lock_w(e,1,&r));CHECK(!r14_unlock(e->m,&e->w[1],&r));release(&g);CHECK(!pthread_join(t,NULL));CHECK(!w.rc);if(k<2)CHECK(!r14_unlock(e->m,&e->w[0],&r));char n[40];snprintf(n,sizeof(n),"barrier-%s",at[k]);emit(e,n);
 }
 {struct env *e=make();struct r14_report r;for(int i=0;i<8;i++){e->w[i].request_rc=-1;CHECK(lock_w(e,i,&r)!=0);}CHECK(lock_w(e,8,&r)==-ENOSPC);CHECK(!count(e,8,"public.request"));void *b;int fd;CHECK(e->ops.request(e->a,&e->w[9],&b,&fd)==-ENOSPC);CHECK(!count(e,9,"public.request"));emit(e,"eight-retained-ninth-no-side-effect");}
 for(int k=0;k<2;k++){
  struct env *e=make();struct r14_report r;CHECK(!lock_w(e,0,&r));if(k==0)e->w[1].requested=&e->w[0].b;else e->w[1].converted=&e->w[0].n;
  CHECK(lock_w(e,1,&r)!=0);CHECK(r14_unlock(e->m,&e->w[0],&r)!=0);CHECK(!count(e,0,"public.unmap") && !count(e,0,"public.abort") && !count(e,1,"public.abort"));if(k){struct r15_record ar;CHECK(!r15_record_for(e->a,&e->w[0],&ar));CHECK(ar.calls[R15_UNMAP].suppressed==1 && !ar.calls[R15_UNMAP].raw_valid);}retained(e,0);retained(e,1);emit(e,k?"duplicate-native":"duplicate-buffer");
 }
 {struct env *e=make();struct gate g;gate_init(&g);e->w[0].gate=&g;e->w[0].gate_at="map";struct worker w={e,0,0,99};pthread_t t;CHECK(!pthread_create(&t,NULL,run,&w));entered(&g);e->w[1].converted=&e->w[0].n;struct r14_report r;CHECK(lock_w(e,1,&r)!=0);release(&g);CHECK(!pthread_join(t,NULL));CHECK(w.rc!=0);CHECK(!count(e,0,"public.unmap") && !count(e,0,"public.abort"));emit(e,"duplicate-during-map-no-publish");}
}
int main(int argc,char **argv){CHECK(argc==2);if(!strcmp(argv[1],"pair"))pair();else if(!strcmp(argv[1],"layout"))layout();else if(!strcmp(argv[1],"failures"))failures();else if(!strcmp(argv[1],"concurrency"))concurrency();else return 2;return 0;}
