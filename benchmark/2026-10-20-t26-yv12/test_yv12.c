#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <pthread.h>
/* Includes production TU to exercise failure seams without adding a public
 * mutation API. Assertions use independently computed pixel/layout answers. */
#include "yv12.c"
struct wrapper { int refs; void *oh; };
static int fail_acquire,fail_get,fail_release,fail_alloc;
static int acalls,rcalls,allocs,frees;
static struct r26_context *current;
static pthread_mutex_t eviction_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t eviction_cv=PTHREAD_COND_INITIALIZER;
static int release_block,release_entered,release_continue;

static int acquire(void *p){acalls++;if(fail_acquire)return 0;((struct wrapper*)p)->refs++;return 1;}
static void *get(void *p){return fail_get?NULL:((struct wrapper*)p)->oh;}
static int release(void *p){rcalls++;assert(pthread_mutex_trylock(&current->mutex)==0);pthread_mutex_unlock(&current->mutex);if(fail_release)return 0;
 pthread_mutex_lock(&eviction_mutex);if(release_block){release_entered=1;pthread_cond_broadcast(&eviction_cv);while(!release_continue)pthread_cond_wait(&eviction_cv,&eviction_mutex);}pthread_mutex_unlock(&eviction_mutex);
 ((struct wrapper*)p)->refs--;return 1;}
static void *alloc(void *p,size_t n){(void)p;allocs++;return fail_alloc?NULL:calloc(1,n);}
static void dealloc(void *p,void *v){(void)p;frees++;free(v);}
static void create(void){struct r26_owner o={acquire,get,release};struct r26_alloc a={NULL,alloc,dealloc};assert(r26_create(&o,&a,&current)==0);}
static void geometry(struct wrapper *w,int format){struct r26_token t;assert(r26_geometry_begin(current,w,&t)==0);assert(r26_geometry_end(current,t,format,0,0)==0);}
static void clean(void){assert(r26_destroy(current)==0);current=NULL;}
static unsigned cases;
#define PASS() do {cases++;} while(0)
static void pixels(int w,int h){
 struct r26_layout l;assert(r26_layout(w,h,&l)==0);
 size_t ys=((size_t)w+15)/16*16,cs=(ys/2+15)/16*16,ch=((size_t)h+1)/2;
 assert(l.ys==ys && l.cs==cs && l.ch==ch && l.v==ys*(size_t)h && l.u==l.v+cs*ch && l.total==l.u+cs*ch);
 unsigned char *src=calloc(1,l.total+16);size_t stride=(size_t)w*4+12,size=stride*(size_t)h;unsigned char *dst=malloc(size+16);assert(src&&dst);
 struct r14_handle bh={w,h,(int64_t)stride,(int64_t)size,12};
 /* Exact independently selected vectors: limited-range black, white, red. */
 const unsigned char y[]={16,235,81},v[]={128,128,240},u[]={128,128,90},rgb[][3]={{0,0,0},{255,255,255},{255,0,0}};
 for(unsigned k=0;k<3;k++){
  memset(src,y[k],l.v);memset(src+l.v,v[k],cs*ch);memset(src+l.u,u[k],cs*ch);memset(src+l.total,0x5a,16);memset(dst,0xa7,size+16);
  assert(r26_convert(&l,src,l.total,&bh,dst)==0);
  for(int row=0;row<h;row++)for(int x=0;x<w;x++){size_t n=(size_t)row*stride+(size_t)x*4;assert(!memcmp(dst+n,rgb[k],3)&&dst[n+3]==255);}
  for(int row=0;row<h;row++)for(size_t n=(size_t)w*4;n<stride;n++)assert(dst[(size_t)row*stride+n]==0xa7);
  for(unsigned n=0;n<16;n++){assert(src[l.total+n]==0x5a);assert(dst[size+n]==0xa7);}PASS();
 }
 memset(dst,0x43,size+16);struct r14_handle bad=bh;bad.format=11;
 assert(r26_convert(&l,src,l.total,&bad,dst)==-EINVAL);bad=bh;bad.size_bytes--;assert(r26_convert(&l,src,l.total,&bad,dst)==-EINVAL);
 bad=bh;bad.stride_bytes=4*w-1;assert(r26_convert(&l,src,l.total,&bad,dst)==-EINVAL);
 assert(r26_convert(&l,src,l.total-1,&bh,dst)==-EINVAL);
 struct r26_layout broken=l;broken.u++;assert(r26_convert(&broken,src,l.total,&bh,dst)==-EINVAL);
 for(size_t n=0;n<size+16;n++)assert(dst[n]==0x43);PASS();free(src);free(dst);
}
static pthread_mutex_t barrier_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t barrier_cv=PTHREAD_COND_INITIALIZER;
static unsigned barrier_count,barrier_generation;
static void barrier(void){pthread_mutex_lock(&barrier_mutex);unsigned g=barrier_generation;if(++barrier_count==2){barrier_count=0;barrier_generation++;pthread_cond_broadcast(&barrier_cv);}else while(g==barrier_generation)pthread_cond_wait(&barrier_cv,&barrier_mutex);pthread_mutex_unlock(&barrier_mutex);}
struct race {struct wrapper *w;struct r26_token t;int rc;};
static void *race_lock(void *p){struct race *r=p;barrier();r->rc=r26_lock_begin(current,r->w,r->w->oh,&r->t);barrier();return NULL;}
static void *race_geometry(void *p){struct race *r=p;r->rc=r26_geometry_begin(current,r->w,&r->t);return NULL;}
int main(void){
 const int dims[][2]={{576,1024},{1920,1080},{1,1},{3,5},{17,3}};
 for(unsigned i=0;i<5;i++)pixels(dims[i][0],dims[i][1]);
 struct r26_layout l;assert(r26_layout(0,3,&l)==-EINVAL);assert(r26_layout(-1,3,&l)==-EINVAL);assert(r26_layout(INT64_MAX,INT64_MAX,&l)==-EINVAL);assert(r26_layout(INT32_MAX,INT32_MAX,&l)!=0);PASS();
 assert(r26_layout(4096,5461,&l)==0 && l.total==R26_LIMIT);assert(r26_layout(4096,5462,&l)==-E2BIG);PASS();
 int oh[10];struct wrapper w[10];for(unsigned i=0;i<10;i++)w[i]=(struct wrapper){1,&oh[i]};
 create();for(unsigned i=0;i<8;i++)geometry(&w[i],R26_YV12);
 struct r26_token t;assert(r26_lock_begin(current,&w[8],w[8].oh,&t)==0);assert(w[0].refs==1);unsigned char dst[512];
 struct r14_handle h={17,3,80,240,12};struct r14_buffer out={17,3,20,1,dst,{0}};int before=allocs;
 assert(r26_prepare(current,t,&h,&out)==0 && out.bits==dst && out.format==1 && allocs==before);assert(r26_before_unmap(current,t)==0);assert(r26_finish(current,t,0)==0);assert(r26_finish(current,t,0)==-EBUSY);PASS();clean();
 for(unsigned i=0;i<9;i++)assert(w[i].refs==1);
 create();geometry(&w[0],R26_YV12);assert(r26_geometry_begin(current,&w[0],&t)==0);assert(r26_geometry_end(current,t,2,-19,0)==0);
 assert(r26_lock_begin(current,&w[0],w[0].oh,&t)==0);out=(struct r14_buffer){17,3,20,1,dst,{0}};
 assert(r26_prepare(current,t,&h,&out)==0 && out.format==R26_YV12 && out.stride==32);assert(r26_reserved(current)>0);
 struct r26_token other;assert(r26_geometry_begin(current,&w[0],&other)==-EBUSY);assert(r26_destroy(current)==-EBUSY);
 memset(out.bits,128,r26_reserved(current));assert(r26_before_unmap(current,t)==0);assert(r26_before_unmap(current,t)==-EBUSY);assert(r26_finish(current,t,0)==0);assert(r26_reserved(current)==0);PASS();
 assert(r26_geometry_begin(current,&w[0],&t)==0);assert(r26_geometry_end(current,t,0,0,0)==0);assert(r26_lock_begin(current,&w[0],w[0].oh,&t)==0);
 out=(struct r14_buffer){17,3,20,1,dst,{0}};fail_alloc=1;assert(r26_prepare(current,t,&h,&out)==-ENOMEM && out.bits==dst && r26_reserved(current)==0);fail_alloc=0;assert(r26_finish(current,t,0)==0);PASS();
 /* Two distinct wrapper addresses unwrap to the same OH object. */
 struct wrapper alias={1,w[0].oh};geometry(&alias,2);
 assert(r26_lock_begin(current,&w[0],w[0].oh,&t)==0);out=(struct r14_buffer){17,3,20,1,dst,{0}};before=allocs;
 assert(r26_prepare(current,t,&h,&out)==0 && out.format==1 && allocs==before);assert(r26_finish(current,t,0)==0);PASS();
 struct race a={.w=&w[0]},b={.w=&alias};pthread_t ta,tb;
 assert(!pthread_create(&ta,NULL,race_lock,&a));assert(!pthread_create(&tb,NULL,race_lock,&b));pthread_join(ta,NULL);pthread_join(tb,NULL);
 assert((a.rc==0 && b.rc==-EBUSY)||(b.rc==0 && a.rc==-EBUSY));assert(r26_finish(current,a.rc==0?a.t:b.t,0)==0);PASS();clean();assert(alias.refs==1);
 create();struct r26_token tokens[8];for(unsigned i=0;i<8;i++)assert(r26_lock_begin(current,&w[i],w[i].oh,&tokens[i])==0);
 assert(r26_lock_begin(current,&w[8],w[8].oh,&t)==-ENOSPC);assert(r26_geometry_begin(current,&w[8],&t)==-ENOSPC);
 for(unsigned i=0;i<8;i++)assert(r26_finish(current,tokens[i],0)==0);PASS();clean();
 create();fail_acquire=1;assert(r26_geometry_begin(current,&w[0],&t)==-ENODEV);fail_acquire=0;fail_get=1;assert(r26_geometry_begin(current,&w[0],&t)==-ENODEV);fail_get=0;assert(w[0].refs==1);PASS();clean();
 /* Real total reservation: three 4096x4096 scratch transactions exceed64MiB. */
 create();struct r14_handle big={4096,4096,16384,67108864,12};unsigned char sentinel;struct r14_buffer bo={4096,4096,4096,1,&sentinel,{0}};
 for(unsigned i=0;i<3;i++)geometry(&w[i],R26_YV12);
 for(unsigned i=0;i<3;i++){assert(r26_lock_begin(current,&w[i],w[i].oh,&tokens[i])==0);struct r14_buffer x=bo;int rc=r26_prepare(current,tokens[i],&big,&x);assert(rc==(i<2?0:-ENOSPC));}
 for(unsigned i=0;i<3;i++)assert(r26_finish(current,tokens[i],0)==0);assert(r26_reserved(current)==0);PASS();clean();
 /* A real provider release pauses outside the cache mutex. The other thread
  * observes EVICTING, cannot claim/reuse that wrapper, and no ABA is published. */
 create();for(unsigned i=0;i<8;i++)geometry(&w[i],R26_YV12);
 release_block=1;release_entered=0;release_continue=0;struct race ev={.w=&w[8]};pthread_t te;assert(!pthread_create(&te,NULL,race_geometry,&ev));
 pthread_mutex_lock(&eviction_mutex);while(!release_entered)pthread_cond_wait(&eviction_cv,&eviction_mutex);pthread_mutex_unlock(&eviction_mutex);
 assert(r26_lock_begin(current,&w[0],w[0].oh,&t)==-EBUSY);assert(w[0].refs==2);
 pthread_mutex_lock(&eviction_mutex);release_continue=1;pthread_cond_broadcast(&eviction_cv);pthread_mutex_unlock(&eviction_mutex);pthread_join(te,NULL);release_block=0;
 assert(ev.rc==0 && w[0].refs==1);assert(r26_geometry_end(current,ev.t,R26_YV12,0,0)==0);PASS();clean();
 /* If lock wins first, its cached reference is not selected for eviction. */
 create();for(unsigned i=0;i<8;i++)geometry(&w[i],R26_YV12);assert(r26_lock_begin(current,&w[0],w[0].oh,&t)==0);
 struct r26_token new_geometry;assert(r26_geometry_begin(current,&w[8],&new_geometry)==0);assert(w[0].refs==2 && w[1].refs==1);
 assert(r26_geometry_end(current,new_geometry,2,0,0)==0);assert(r26_finish(current,t,0)==0);PASS();clean();
 /* Failed cache release remains non-reusable; restore only test fixture later. */
 create();geometry(&w[0],R26_YV12);fail_release=1;assert(r26_destroy(current)==-EPROTO);assert(r26_geometry_begin(current,&w[0],&t)==-EBUSY);assert(r26_destroy(current)==-EBUSY);fail_release=0;
 current->entries[0].state=R26_IDLE;clean();PASS();
 create();fail_get=1;fail_release=1;assert(r26_geometry_begin(current,&w[0],&t)==-ENODEV);assert(current->entries[0].state==R26_FAILED && current->entries[0].release_rc==0 && w[0].refs==2);fail_get=0;fail_release=0;current->entries[0].state=R26_IDLE;clean();PASS();
 printf("PASS %u actual C cases; allocations=%d frees=%d\n",cases,allocs,frees);return 0;
}
