/* Arithmetic only derived from archived libandroid_webview_core_shim.c
 * 605-647. Cache, budgets and ownership are independent; no legacy loader. */
#include "yv12.h"
#include "rgbx.h"
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
enum r26_state { R26_FREE,R26_IDLE,R26_ACTIVE,R26_EVICTING,R26_FAILED };
struct entry {
 enum r26_state state; const void *wrapper; void *oh;
 uint64_t generation; int reference,known,geometry,new_entry,acquire_rc,release_rc; int32_t format;
 void *scratch,*dest; struct r26_layout layout; struct r14_handle packed;
 int converted,opaque;
};
struct r26_context {
 pthread_mutex_t mutex; struct r26_owner owner; struct r26_alloc allocator;
 struct entry entries[R26_SLOTS]; uint64_t generation; size_t reserved;
};
static void *zero_default(void *unused,size_t n){(void)unused;return calloc(1,n);}
static void free_default(void *unused,void *p){(void)unused;free(p);}
static int add(size_t a,size_t b,size_t *r){if(a>SIZE_MAX-b)return -EOVERFLOW;*r=a+b;return 0;}
static int mul(size_t a,size_t b,size_t *r){if(b && a>SIZE_MAX/b)return -EOVERFLOW;*r=a*b;return 0;}
static int align16(size_t v,size_t *r){size_t t;int rc=add(v,15,&t);if(rc)return rc;*r=t&~(size_t)15;return 0;}
int r26_layout(int64_t w,int64_t h,struct r26_layout *out){
 if(!out)return -EINVAL;memset(out,0,sizeof(*out));
 if(w<=0 || h<=0 || w>INT32_MAX || h>INT32_MAX)return -EINVAL;
 struct r26_layout x={.w=(size_t)w,.h=(size_t)h};size_t c;
 if(align16(x.w,&x.ys) || align16(x.ys/2,&x.cs) || add(x.h,1,&x.ch))return -EOVERFLOW;
 x.ch/=2;
 if(mul(x.ys,x.h,&x.v) || mul(x.cs,x.ch,&c) || add(x.v,c,&x.u) || add(x.u,c,&x.total))return -EOVERFLOW;
 if(x.total>R26_LIMIT || x.ys>INT32_MAX)return -E2BIG;
 *out=x;return 0;
}
static int packed_check(const struct r26_layout *l,const struct r14_handle *h,const void *dst){
 size_t tight,rows;
 if(!h || !dst || h->format!=12 || h->width!=(int64_t)l->w || h->height!=(int64_t)l->h || h->stride_bytes<=0 || h->size_bytes<=0)return -EINVAL;
 if(mul(l->w,4,&tight) || (uint64_t)h->stride_bytes>SIZE_MAX || (uint64_t)h->size_bytes>SIZE_MAX || (size_t)h->stride_bytes<tight || h->stride_bytes%4 || mul((size_t)h->stride_bytes,l->h,&rows) || rows>(size_t)h->size_bytes)return -EINVAL;
 return 0;
}
static unsigned char clamp(int x){return x<0?0:x>255?255:(unsigned char)x;}
/* Explicit floor division matches the donor's signed arithmetic shift. */
static int floor256(int x){return x>=0?x/256:-((-x+255)/256);}
int r26_convert(const struct r26_layout *l,const void *src,size_t bytes,const struct r14_handle *h,void *dst){
 if(!l || !src)return -EINVAL;
 struct r26_layout checked;int rc=r26_layout((int64_t)l->w,(int64_t)l->h,&checked);
 if(rc)return rc;
 if(l->w!=checked.w || l->h!=checked.h || l->ys!=checked.ys || l->cs!=checked.cs || l->ch!=checked.ch || l->v!=checked.v || l->u!=checked.u || l->total!=checked.total || bytes<l->total)return -EINVAL;
 rc=packed_check(l,h,dst);if(rc)return rc;
 /* Entire validation completes before the first write. No failing operations
  * or external callbacks below this point. */
 const unsigned char *y=src,*v=y+l->v,*u=y+l->u;unsigned char *d=dst;
 for(size_t row=0;row<l->h;row++)for(size_t col=0;col<l->w;col++){
  int c=(int)y[row*l->ys+col]-16; if(c<0)c=0;
  int du=(int)u[(row/2)*l->cs+col/2]-128,ev=(int)v[(row/2)*l->cs+col/2]-128;
  unsigned char *p=d+row*(size_t)h->stride_bytes+col*4;
  p[0]=clamp(floor256(298*c+409*ev+128));p[1]=clamp(floor256(298*c-100*du-208*ev+128));p[2]=clamp(floor256(298*c+516*du+128));p[3]=255;
 }
 return 0;
}
int r26_create(const struct r26_owner *o,const struct r26_alloc *a,struct r26_context **out){
 if(!out)return -EINVAL;*out=NULL;
 if(!o || !o->acquire || !o->get || !o->release || (a && (!a->zero || !a->free)))return -ENOSYS;
 struct r26_context *c=calloc(1,sizeof(*c));if(!c)return -ENOMEM;
 int rc=pthread_mutex_init(&c->mutex,NULL);if(rc){free(c);return -rc;}
 c->owner=*o;c->allocator=a?*a:(struct r26_alloc){NULL,zero_default,free_default};*out=c;return 0;
}
/* mutex held; tokens are unique across reuse, so a stale finish cannot release
 * a newer transaction. External provider/free callbacks never run here. */
static struct entry *token_entry(struct r26_context *c,struct r26_token t){
 if(t.slot>=R26_SLOTS)return NULL;struct entry *e=&c->entries[t.slot];
 return e->state==R26_ACTIVE && e->generation==t.generation?e:NULL;
}
static void claim(struct r26_context *c,unsigned i,int geometry,struct r26_token *t){
 struct entry *e=&c->entries[i];e->state=R26_ACTIVE;e->geometry=geometry;e->generation=++c->generation;*t=(struct r26_token){i,e->generation};
}
/* Called with mutex held, returns unlocked. EVICTING exclusively owns the
 * reference until release finishes, and is not a reusable/free slot. */
static int evict(struct r26_context *c,unsigned i){
 struct entry *e=&c->entries[i];e->state=R26_EVICTING;void *w=(void*)e->wrapper;int reference=e->reference;
 pthread_mutex_unlock(&c->mutex);
 int rc=reference?c->owner.release(w):1;
 pthread_mutex_lock(&c->mutex);
 if(rc==1)memset(e,0,sizeof(*e));else {e->release_rc=rc;e->state=R26_FAILED;}
 pthread_mutex_unlock(&c->mutex);return rc==1?0:-EPROTO;
}
int r26_geometry_begin(struct r26_context *c,void *w,struct r26_token *t){
 if(!c || !w || !t)return -EINVAL;
 /* At most one eviction/retry. Concurrent use may consume the freed slot. */
 for(unsigned attempt=0;attempt<2;attempt++){
  pthread_mutex_lock(&c->mutex);int free_slot=-1,idle=-1;
  for(unsigned i=0;i<R26_SLOTS;i++){
   struct entry *e=&c->entries[i];
   if(e->state!=R26_FREE && e->wrapper==w){
    if(e->state!=R26_IDLE){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
    for(unsigned j=0;j<R26_SLOTS;j++)if(j!=i && c->entries[j].oh==e->oh && c->entries[j].state!=R26_FREE && c->entries[j].state!=R26_IDLE){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
    e->new_entry=0;claim(c,i,1,t);pthread_mutex_unlock(&c->mutex);return 0;
   }
   if(e->state==R26_FREE && free_slot<0)free_slot=(int)i;
   if(e->state==R26_IDLE && idle<0)idle=(int)i;
  }
  if(free_slot<0){if(idle<0 || attempt){pthread_mutex_unlock(&c->mutex);return -ENOSPC;}int rc=evict(c,(unsigned)idle);if(rc)return rc;continue;}
  unsigned i=(unsigned)free_slot;struct entry *e=&c->entries[i];e->wrapper=w;e->new_entry=1;claim(c,i,1,t);pthread_mutex_unlock(&c->mutex);
  int rc=c->owner.acquire(w);void *oh=rc==1?c->owner.get(w):NULL;
  pthread_mutex_lock(&c->mutex);e->acquire_rc=rc;e->reference=rc==1;e->oh=oh;
  int error=rc==1?(oh?0:-ENODEV):-ENODEV;
  for(unsigned j=0;!error && j<R26_SLOTS;j++)if(j!=i && c->entries[j].state!=R26_FREE && c->entries[j].state!=R26_IDLE && c->entries[j].oh==oh)error=-EBUSY;
  if(error){(void)evict(c,i);return error;} /* first error; failed release stays FAILED with raw rc */
  pthread_mutex_unlock(&c->mutex);return 0;
 }
 return -ENOSPC;
}
int r26_geometry_end(struct r26_context *c,struct r26_token t,int32_t format,int result,int uncertain){
 if(!c)return -EINVAL;pthread_mutex_lock(&c->mutex);struct entry *e=token_entry(c,t);
 if(!e || !e->geometry){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
 if(uncertain){e->state=R26_FAILED;pthread_mutex_unlock(&c->mutex);return 0;}
 if(result && e->new_entry)return evict(c,t.slot);
 if(!result && format>0){
  e->format=format;e->known=1;
  /* Geometry changes the shared OH object. Alias caches cannot keep stale
   * request history; their original-path fallback can establish it anew. */
  for(unsigned i=0;i<R26_SLOTS;i++)if(i!=t.slot && c->entries[i].state==R26_IDLE && c->entries[i].oh==e->oh)c->entries[i].known=0;
 }
 e->state=R26_IDLE;e->new_entry=0;pthread_mutex_unlock(&c->mutex);return 0;
}
int r26_lock_begin(struct r26_context *c,const void *w,void *oh,struct r26_token *t){
 if(!c || !w || !oh || !t)return -EINVAL;
 for(unsigned attempt=0;attempt<2;attempt++){
 pthread_mutex_lock(&c->mutex);int idx=-1,free_slot=-1,idle=-1;
 for(unsigned i=0;i<R26_SLOTS;i++){
  struct entry *e=&c->entries[i];
  if(e->state==R26_FREE){if(free_slot<0)free_slot=(int)i;continue;}
  if((e->wrapper==w || e->oh==oh) && e->state!=R26_IDLE){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
  if(e->state==R26_IDLE && idle<0)idle=(int)i;
  if(e->wrapper==w){if(e->oh!=oh){pthread_mutex_unlock(&c->mutex);return -EXDEV;}idx=(int)i;}
 }
 if(idx<0)idx=free_slot;
 if(idx<0){if(idle<0 || attempt){pthread_mutex_unlock(&c->mutex);return -ENOSPC;}int rc=evict(c,(unsigned)idle);if(rc)return rc;continue;}
 struct entry *e=&c->entries[idx];e->wrapper=w;e->oh=oh;e->new_entry=!e->reference;claim(c,(unsigned)idx,0,t);pthread_mutex_unlock(&c->mutex);return 0;
 }
 return -ENOSPC;
}
int r26_prepare(struct r26_context *c,struct r26_token t,const struct r14_handle *h,struct r14_buffer *out){
 if(!c || !h || !out)return -EINVAL;pthread_mutex_lock(&c->mutex);struct entry *e=token_entry(c,t);
 if(!e || e->geometry || e->scratch || e->opaque){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
 if(e->known && e->format==2){
  int rc=r28_prepare(h,out);
  if(!rc){e->opaque=1;e->packed=*h;e->dest=out->bits;}
  pthread_mutex_unlock(&c->mutex);return rc;
 }
 if(!e->known || e->format!=R26_YV12){pthread_mutex_unlock(&c->mutex);return 0;}
 struct r26_layout l;int rc=r26_layout(h->width,h->height,&l);
 if(!rc)rc=packed_check(&l,h,out->bits);
 if(!rc && (out->format!=1 || out->width!=h->width || out->height!=h->height || (int64_t)out->stride*4!=h->stride_bytes))rc=-EINVAL;
 if(!rc && l.total>R26_TOTAL-c->reserved)rc=-ENOSPC;
 if(rc){pthread_mutex_unlock(&c->mutex);return rc;}
 c->reserved+=l.total;pthread_mutex_unlock(&c->mutex);
 void *scratch=c->allocator.zero(c->allocator.ctx,l.total);
 pthread_mutex_lock(&c->mutex);
 if(!scratch){c->reserved-=l.total;pthread_mutex_unlock(&c->mutex);return -ENOMEM;}
 e->scratch=scratch;e->layout=l;e->packed=*h;e->dest=out->bits;
 out->stride=(int32_t)l.ys;out->format=R26_YV12;out->bits=scratch;
 pthread_mutex_unlock(&c->mutex);return 0;
}
int r26_before_unmap(struct r26_context *c,struct r26_token t){
 if(!c)return -EINVAL;pthread_mutex_lock(&c->mutex);struct entry *e=token_entry(c,t);
 if(!e || e->geometry || e->converted){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
 if(e->opaque){
  e->converted=1;struct entry copy=*e;pthread_mutex_unlock(&c->mutex);
  return r28_opaque(&copy.packed,copy.dest);
 }
 if(!e->scratch){pthread_mutex_unlock(&c->mutex);return 0;}
 /* ACTIVE is held exclusively by the R14 COMPLETING transaction. */
 e->converted=1;struct entry copy=*e;pthread_mutex_unlock(&c->mutex);
 return r26_convert(&copy.layout,copy.scratch,copy.layout.total,&copy.packed,copy.dest);
}
int r26_finish(struct r26_context *c,struct r26_token t,int retained){
 if(!c)return -EINVAL;pthread_mutex_lock(&c->mutex);struct entry *e=token_entry(c,t);
 if(!e || e->geometry){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
 if(retained){e->state=R26_FAILED;pthread_mutex_unlock(&c->mutex);return 0;}
 void *p=e->scratch;size_t bytes=p?e->layout.total:0;
 /* Keep ACTIVE while the injected allocator runs outside the mutex. */
 pthread_mutex_unlock(&c->mutex);if(p)c->allocator.free(c->allocator.ctx,p);pthread_mutex_lock(&c->mutex);
 c->reserved-=bytes;
 if(e->reference){e->scratch=NULL;e->dest=NULL;e->converted=0;e->opaque=0;e->state=R26_IDLE;}else memset(e,0,sizeof(*e));
 pthread_mutex_unlock(&c->mutex);return 0;
}
int r26_poison(struct r26_context *c,const void *w){
 if(!c)return -EINVAL;pthread_mutex_lock(&c->mutex);int rc=-ENOENT;
 for(unsigned i=0;i<R26_SLOTS;i++)if(c->entries[i].state!=R26_FREE && c->entries[i].wrapper==w){c->entries[i].state=R26_FAILED;rc=0;break;}
 pthread_mutex_unlock(&c->mutex);return rc;
}
size_t r26_reserved(struct r26_context *c){pthread_mutex_lock(&c->mutex);size_t n=c->reserved;pthread_mutex_unlock(&c->mutex);return n;}
int r26_destroy(struct r26_context *c){
 if(!c)return -EINVAL;pthread_mutex_lock(&c->mutex);
 for(unsigned i=0;i<R26_SLOTS;i++)if(c->entries[i].state!=R26_FREE && c->entries[i].state!=R26_IDLE){pthread_mutex_unlock(&c->mutex);return -EBUSY;}
 pthread_mutex_unlock(&c->mutex);
 for(unsigned i=0;i<R26_SLOTS;i++){pthread_mutex_lock(&c->mutex);if(c->entries[i].state==R26_IDLE){int rc=evict(c,i);if(rc)return rc;}else pthread_mutex_unlock(&c->mutex);}
 pthread_mutex_destroy(&c->mutex);free(c);return 0;
}
