#include "provider_adapter.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
_Static_assert(sizeof(void *)==8,"LP64 required");
_Static_assert(sizeof(struct Rect)==16 && offsetof(struct Rect,w)==8 && offsetof(struct Rect,h)==12,"OH xywh");
_Static_assert(sizeof(Region)==16 && offsetof(Region,rects)==0 && offsetof(Region,rectNumber)==8,"OH Region by value");
#ifdef R15_OH_SDK
#define MATCH(field,fn) _Static_assert(__builtin_types_compatible_p(__typeof__(((struct r15_provider *)0)->field),__typeof__(&(fn))),"SDK prototype: " #field)
MATCH(request,OH_NativeWindow_NativeWindowRequestBuffer);
MATCH(handle,OH_NativeWindow_GetBufferHandleFromNative);
MATCH(convert,OH_NativeBuffer_FromNativeWindowBuffer);
MATCH(map,OH_NativeBuffer_Map); MATCH(unmap,OH_NativeBuffer_Unmap);
MATCH(flush,OH_NativeWindow_NativeWindowFlushBuffer);
MATCH(abort,OH_NativeWindow_NativeWindowAbortBuffer);
#endif
enum { EMPTY,RESERVED,REQUESTED,CONVERTED,MAPPED,UNMAPPED };
struct r15_adapter { pthread_mutex_t mu; struct r15_provider p; struct r15_capabilities c; struct r15_record r[R15_RECORDS]; };
static int by_window(struct r15_adapter *a,void *w) {
 for(int i=0;i<R15_RECORDS;i++)if(a->r[i].phase && a->r[i].window==w)return i;
 return -1;
}
/* T30: true iff THIS record is still exactly the pristine RESERVED state that request() left before it
 * dropped the lock for the real provider call -- i.e. no concurrent flush/abort (which reach a RESERVED
 * record through by_window and deny->failed) polluted it during that unlocked window. Pure read; it only
 * authorizes clearing this call's OWN idx when the call also proves it took no resource. */
static int t30_reserved_pristine(const struct r15_record *r,const void *w) {
 if(r->phase!=RESERVED || (const void *)r->window!=w || r->buffer || r->native || r->uncertain || r->failed)return 0;
 for(int op=0;op<R15_OPERATIONS;op++){
  const struct r15_call *c=&r->calls[op];
  unsigned want_called=(op==R15_REQUEST)?1u:0u;
  if(c->called!=want_called || c->suppressed || c->raw_valid || c->adapter_error || c->raw_rc)return 0;
 }
 return 1;
}
static int by_identity(struct r15_adapter *a,void *v,int native) {
 int found=-1;
 for(int i=0;i<R15_RECORDS;i++)if(a->r[i].phase && v && (native?(void *)a->r[i].native:(void *)a->r[i].buffer)==v){if(found>=0)return -1;found=i;}
 return found;
}
static void raw(struct r15_record *r,int op,int rc) { r->calls[op].raw_valid=1;r->calls[op].raw_rc=rc; }
static int deny(struct r15_record *r,int op,int err) {r->calls[op].suppressed++;r->calls[op].adapter_error=err;r->failed=1;return err;}
/* Ambiguous duplicate identities are never resolved by picking the first. */
static int deny_identity(struct r15_adapter *a,void *value,int native,int op) {
 for(int i=0;i<R15_RECORDS;i++)if(a->r[i].phase && value && (native?(void *)a->r[i].native:(void *)a->r[i].buffer)==value)deny(&a->r[i],op,-EPROTO);
 return -EPROTO;
}
static int collision(struct r15_adapter *a,int idx,int native) {
 void *v=native?(void *)a->r[idx].native:(void *)a->r[idx].buffer;int hit=0;
 for(int i=0;i<R15_RECORDS;i++)if(i!=idx && a->r[i].phase && v && (native?(void *)a->r[i].native:(void *)a->r[i].buffer)==v){a->r[i].uncertain=1;a->r[i].failed=1;hit=1;}
 if(hit){a->r[idx].uncertain=1;a->r[idx].failed=1;}return hit;
}
static int unwrap(void *v,const void *w,void **out) {
 struct r15_adapter *a=v;OHNativeWindow *oh=NULL;int rc=a->c.unwrap(a->c.ctx,w,&oh);*out=oh;return rc;
}
static int request(void *v,void *w,void **out,int *fence) {
 struct r15_adapter *a=v;int idx=-1;*out=NULL;*fence=-1;
 pthread_mutex_lock(&a->mu);
 if(by_window(a,w)>=0){pthread_mutex_unlock(&a->mu);return -EBUSY;}
 for(int i=0;i<R15_RECORDS;i++)if(!a->r[i].phase){idx=i;break;}
 if(idx<0){pthread_mutex_unlock(&a->mu);return -ENOSPC;}
 struct r15_record *r=&a->r[idx];r->phase=RESERVED;r->window=w;r->calls[R15_REQUEST].called++;
 pthread_mutex_unlock(&a->mu);
 OHNativeWindowBuffer *b=NULL;int fd=-1;int rc=a->p.request(w,&b,&fd);
 pthread_mutex_lock(&a->mu);
 /* T30: capture the recovery pre-condition BEFORE any self-write. If a concurrent flush/abort reached
  * this RESERVED record (by_window) and marked it failed/suppressed during the unlocked provider call,
  * it is no longer pristine and recovery is disqualified -- the concurrent evidence is preserved. */
 int recoverable_eligible=t30_reserved_pristine(r,w);
 r->buffer=b;raw(r,R15_REQUEST,rc);r->phase=REQUESTED;
 int bad=collision(a,idx,0);if(rc || !b || fd < -1 || bad){r->uncertain=1;r->failed=1;if(!rc)r->calls[R15_REQUEST].adapter_error=-EPROTO;}
 *out=b;*fence=fd;int result=rc?rc:(r->uncertain?-EPROTO:0);
 /* T30: clear ONLY this idx record (never by_window to an older one), and only when it was pristine
  * RESERVED (no concurrent pollution) AND this request provably took no resource (rc!=0, no buffer,
  * fd==-1, no duplicate-identity collision). A later legitimate request on the same window is then not
  * permanently blocked at the by_window -EBUSY guard. The original raw rc is already in `result`; any
  * acquired buffer, a fence (fd!=-1), a collision, or concurrent pollution keeps the record conservative. */
 if(recoverable_eligible && rc && !b && fd==-1 && !bad)memset(r,0,sizeof(*r));
 pthread_mutex_unlock(&a->mu);return result;
}
static int handle(void *v,void *b,struct r14_handle *out) {
 struct r15_adapter *a=v;memset(out,0,sizeof(*out));pthread_mutex_lock(&a->mu);int i=by_identity(a,b,0);
 if(i<0){int rc=deny_identity(a,b,0,R15_HANDLE);pthread_mutex_unlock(&a->mu);return rc;}struct r15_record *r=&a->r[i];
 if(r->uncertain || r->failed || r->phase!=REQUESTED){int rc=deny(r,R15_HANDLE,-EPROTO);pthread_mutex_unlock(&a->mu);return rc;}
 r->calls[R15_HANDLE].called++;pthread_mutex_unlock(&a->mu);
 const unsigned char *p=(const unsigned char *)a->p.handle(b);
 int32_t width=0,stride=0,height=0,size=0,format=0;
 if(p){memcpy(&width,p+4,4);memcpy(&stride,p+8,4);memcpy(&height,p+12,4);memcpy(&size,p+16,4);memcpy(&format,p+20,4);}
 pthread_mutex_lock(&a->mu);int rc=0;
 /* handle returns a pointer, not an rc: raw_valid deliberately remains false. */
 if(!p || r->uncertain){rc=-EPROTO;r->failed=1;r->calls[R15_HANDLE].adapter_error=rc;}
 else {*out=(struct r14_handle){width,height,stride,size,format};}
 pthread_mutex_unlock(&a->mu);return rc;
}
static int convert(void *v,void *b,void **out) {
 struct r15_adapter *a=v;*out=NULL;pthread_mutex_lock(&a->mu);int i=by_identity(a,b,0);
 if(i<0){int rc=deny_identity(a,b,0,R15_CONVERT);pthread_mutex_unlock(&a->mu);return rc;}struct r15_record *r=&a->r[i];
 if(r->uncertain || r->failed || r->phase!=REQUESTED){int rc=deny(r,R15_CONVERT,-EPROTO);pthread_mutex_unlock(&a->mu);return rc;}
 r->calls[R15_CONVERT].called++;pthread_mutex_unlock(&a->mu);
 OH_NativeBuffer *n=NULL;int rc=a->p.convert(b,&n);
 pthread_mutex_lock(&a->mu);raw(r,R15_CONVERT,rc);r->native=n;int bad=collision(a,i,1);
 if(rc || !n || bad || r->uncertain){r->failed=1;if(!rc)r->calls[R15_CONVERT].adapter_error=-EPROTO;}
 else r->phase=CONVERTED;
 *out=n;int result=rc?rc:((!n || r->uncertain)?-EPROTO:0);pthread_mutex_unlock(&a->mu);return result;
}
static int map(void *v,void *n,void **out) {
 struct r15_adapter *a=v;*out=NULL;pthread_mutex_lock(&a->mu);int i=by_identity(a,n,1);
 if(i<0){int rc=deny_identity(a,n,1,R15_MAP);pthread_mutex_unlock(&a->mu);return rc;}struct r15_record *r=&a->r[i];
 if(r->uncertain || r->failed || r->phase!=CONVERTED){int rc=deny(r,R15_MAP,-EPROTO);pthread_mutex_unlock(&a->mu);return rc;}
 r->calls[R15_MAP].called++;pthread_mutex_unlock(&a->mu);void *bits=NULL;int rc=a->p.map(n,&bits);
 pthread_mutex_lock(&a->mu);raw(r,R15_MAP,rc);
 if(rc || bits==(void *)UINTPTR_MAX){r->uncertain=1;r->failed=1;}
 if(!rc)r->phase=MAPPED;
 if(!rc && !r->uncertain)*out=bits;
 else if(!rc)r->calls[R15_MAP].adapter_error=-EPROTO;
 pthread_mutex_unlock(&a->mu);return rc; /* preserve public0; R14 sees NULL and calls our unmap thunk */
}
static int unmap(void *v,void *n) {
 struct r15_adapter *a=v;pthread_mutex_lock(&a->mu);int i=by_identity(a,n,1);
 if(i<0){int rc=deny_identity(a,n,1,R15_UNMAP);pthread_mutex_unlock(&a->mu);return rc;}struct r15_record *r=&a->r[i];
 if(r->uncertain || r->phase!=MAPPED || r->calls[R15_UNMAP].called){int rc=deny(r,R15_UNMAP,-EPROTO);pthread_mutex_unlock(&a->mu);return rc;}
 r->calls[R15_UNMAP].called++;pthread_mutex_unlock(&a->mu);int rc=a->p.unmap(n);
 pthread_mutex_lock(&a->mu);raw(r,R15_UNMAP,rc);
 if(rc){r->failed=1;r->uncertain=1;}else r->phase=UNMAPPED;
 int result=rc;if(!rc && r->uncertain){result=-EPROTO;r->calls[R15_UNMAP].adapter_error=result;}
 pthread_mutex_unlock(&a->mu);return result;
}
static int flush(void *v,void *w,void *b,int fd,const struct r14_rect *rect) {
 struct r15_adapter *a=v;pthread_mutex_lock(&a->mu);int i=by_window(a,w);
 if(i<0){pthread_mutex_unlock(&a->mu);return -EPROTO;}struct r15_record *r=&a->r[i];
 int64_t width=rect?(int64_t)rect->right-rect->left:0,height=rect?(int64_t)rect->bottom-rect->top:0;
 if(!rect || width<=0 || height<=0 || width>INT32_MAX || height>INT32_MAX || fd!=-1 || r->buffer!=b || r->phase!=UNMAPPED || r->failed || r->uncertain || r->calls[R15_FLUSH].called){int rc=deny(r,R15_FLUSH,-EINVAL);pthread_mutex_unlock(&a->mu);return rc;}
 r->calls[R15_FLUSH].called++;pthread_mutex_unlock(&a->mu);
 struct Rect ohrect={rect->left,rect->top,(uint32_t)width,(uint32_t)height};Region region={&ohrect,1};
 int rc=a->p.flush(w,b,-1,region);pthread_mutex_lock(&a->mu);raw(r,R15_FLUSH,rc);
 int result=rc;if(rc){r->failed=1;r->uncertain=1;}else if(r->uncertain){result=-EPROTO;r->failed=1;r->calls[R15_FLUSH].adapter_error=result;}else memset(r,0,sizeof(*r));
 pthread_mutex_unlock(&a->mu);return result;
}
static int abort_buffer(void *v,void *w,void *b) {
 struct r15_adapter *a=v;pthread_mutex_lock(&a->mu);int i=by_window(a,w);
 if(i<0){pthread_mutex_unlock(&a->mu);return -EPROTO;}struct r15_record *r=&a->r[i];
 if(r->buffer!=b || !b || r->uncertain || r->phase==MAPPED || r->calls[R15_ABORT].called || r->calls[R15_FLUSH].called){int rc=deny(r,R15_ABORT,-EPROTO);pthread_mutex_unlock(&a->mu);return rc;}
 r->failed=1;r->calls[R15_ABORT].called++;pthread_mutex_unlock(&a->mu);int rc=a->p.abort(w,b);
 pthread_mutex_lock(&a->mu);raw(r,R15_ABORT,rc);pthread_mutex_unlock(&a->mu);return rc;
}
static int clock_ns(void *v,int64_t *n){struct r15_adapter *a=v;return a->c.clock_ns(a->c.ctx,n);}
static int poll_fd(void *v,int fd,int ms,short *re,int *err){struct r15_adapter *a=v;return a->c.poll_fd(a->c.ctx,fd,ms,re,err);}
static int close_fd(void *v,int fd){struct r15_adapter *a=v;return a->c.close_fd(a->c.ctx,fd);}
int r15_create(const struct r15_provider *p,const struct r15_capabilities *c,struct r15_adapter **out,struct r14_ops *ops) {
 if(!out || !ops)return -EINVAL;*out=NULL;memset(ops,0,sizeof(*ops));
 if(!p || !c || !p->request || !p->handle || !p->convert || !p->map || !p->unmap || !p->flush || !p->abort || !c->unwrap || !c->clock_ns || !c->poll_fd || !c->close_fd)return -ENOSYS;
 struct r15_adapter *a=calloc(1,sizeof(*a));if(!a)return -ENOMEM;int rc=pthread_mutex_init(&a->mu,NULL);if(rc){free(a);return -rc;}a->p=*p;a->c=*c;
 *ops=(struct r14_ops){a,unwrap,request,handle,convert,map,unmap,flush,abort_buffer,clock_ns,poll_fd,close_fd};*out=a;return 0;
}
int r15_record_for(struct r15_adapter *a,OHNativeWindow *w,struct r15_record *out) {
 if(!a || !out)return -EINVAL;pthread_mutex_lock(&a->mu);int i=by_window(a,w);if(i>=0)*out=a->r[i];pthread_mutex_unlock(&a->mu);return i>=0?0:-ENOENT;
}
int r15_destroy(struct r15_adapter *a) {
 if(!a)return -EINVAL;pthread_mutex_lock(&a->mu);for(int i=0;i<R15_RECORDS;i++)if(a->r[i].phase){pthread_mutex_unlock(&a->mu);return -EBUSY;}pthread_mutex_unlock(&a->mu);pthread_mutex_destroy(&a->mu);free(a);return 0;
}
