/* Format/layout adaptation from f12c webview_bionic_shim.c:3901-4078.
 * Ownership/error handling is independently narrowed; see DONOR.md. */
#include "window_module.h"
#include "observe29.h"
#include "yv12.h"
#include "observation.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <poll.h>
_Static_assert(sizeof(void *)==8,"64-bit offline ABI required");
_Static_assert(sizeof(struct r14_buffer)==48 && offsetof(struct r14_buffer,bits)==16 && offsetof(struct r14_buffer,reserved)==24,"Android Buffer layout");
_Static_assert(sizeof(struct r14_rect)==16 && offsetof(struct r14_rect,bottom)==12,"Android Rect layout");
enum state { FREE,CLAIMED,LOCKED,COMPLETING,FAILED };
struct slot { struct r26_token token; enum state state; const void *wrapper; void *oh,*buffer,*native; struct r14_rect rect; struct r14_report report; };
struct r14_module { struct r26_context *extension; pthread_mutex_t mutex; struct r14_ops ops; struct slot slots[R14_SLOTS]; };
void r14_attach_yv12(struct r14_module *m,struct r26_context *extension) { m->extension=extension; }
static int negative(int rc) { return rc<0?rc:-EIO; }
int r14_create(const struct r14_ops *o,struct r14_module **out) {
 if(!out)return -EINVAL;
 *out=NULL;
 if(!o || !o->unwrap || !o->request || !o->handle || !o->convert || !o->map || !o->unmap || !o->flush || !o->abort || !o->clock_ns || !o->poll_fd || !o->close_fd)return -ENOSYS;
 struct r14_module *m=calloc(1,sizeof(*m));if(!m)return -ENOMEM;
 int e=pthread_mutex_init(&m->mutex,NULL);if(e){free(m);return -e;}
 m->ops=*o;*out=m;return 0;
}
int r14_destroy(struct r14_module *m) {
 if(!m)return -EINVAL;
 pthread_mutex_lock(&m->mutex);
 for(int i=0;i<R14_SLOTS;i++)if(m->slots[i].state!=FREE){pthread_mutex_unlock(&m->mutex);return -EBUSY;}
 pthread_mutex_unlock(&m->mutex);pthread_mutex_destroy(&m->mutex);free(m);return 0;
}
static void complete(struct r14_module *m,int i,struct r14_report *r,int success) {
 pthread_mutex_lock(&m->mutex);
 if(success)memset(&m->slots[i],0,sizeof(m->slots[i]));
 else {r->retained=1;m->slots[i].report=*r;m->slots[i].state=FAILED;}
 pthread_mutex_unlock(&m->mutex);
}
static int fence_wait(struct r14_module *m,int fd) {
 const struct r14_ops *o=&m->ops;int64_t start,last,now;
 if(o->clock_ns(o->ctx,&start)!=0 || start<0 || start>INT64_MAX-(int64_t)R14_FENCE_MS*1000000)return -EIO;
 int64_t end=start+(int64_t)R14_FENCE_MS*1000000;last=start;
 for(;;){
  if(o->clock_ns(o->ctx,&now)!=0 || now<last)return -EIO;
  last=now;if(now>=end)return -ETIMEDOUT;
  int ms=(int)((end-now+999999)/1000000);short events=0;int err=0;
  int rc=o->poll_fd(o->ctx,fd,ms,&events,&err);
  if(rc<0){if(err==EINTR || err==EAGAIN)continue;return err>0?-err:-EIO;}
  if(rc==0)return -ETIMEDOUT;
  if(o->clock_ns(o->ctx,&now)!=0 || now<last)return -EIO;
  if(now>=end)return -ETIMEDOUT;
  if((events&(POLLERR|POLLNVAL|POLLHUP)) || !(events&POLLIN))return -EIO;
  return 0;
 }
}
static int format(int h,int *bytes) {
 switch(h){case 12:*bytes=4;return 1;case 11:*bytes=4;return 2;case 13:*bytes=3;return 3;case 3:*bytes=2;return 4;case 20:*bytes=4;return 5;case 39:*bytes=8;return 0x16;case 34:*bytes=4;return 0x2b;default:*bytes=0;return 0;}
}
/* Stage identifies the operation/check, not a guessed provider root cause.
 * A local validation has no raw callee return: called=raw_valid=0. Cleanup
 * outcomes are recorded separately and never replace the first failed step. */
static void observed_step(struct r29_record *d,int stage,int called,int raw,uintptr_t provider) {
 d->stage=stage;d->called=called;d->raw_valid=called;d->raw_rc=called?raw:0;
 d->provider=provider;d->valid&=~R29_PROVIDER;if(provider)d->valid|=R29_PROVIDER;
}
/* T30: a PURE predicate (no side effects, no provider calls). It reports whether this failed Request
 * provably acquired NO resource, so the reservation can be released instead of conservatively retained.
 * Strict by contract: the Request ran and failed, no buffer/native, nothing mapped, fd==-1, and none of
 * handle/convert/map/unmap/flush/abort/close ran. ANY acquired resource, mapped buffer, fd!=-1, or
 * cleanup step keeps the old conservative retained path. Ownership is never inferred from the error code. */
static int t30_request_resource_free(const struct r14_report *r,const void *buffer,const void *native,int mapped,int fd) {
 return r->request_called && r->request_rc && !buffer && !native && !mapped && fd==-1
        && !r->handle_called && !r->convert_called && !r->map_called
        && !r->unmap_called && !r->flush_called && !r->abort_called && !r->close_called;
}
int r14_lock(struct r14_module *m,const void *wrapper,struct r14_buffer *out,struct r14_rect *dirty,struct r14_report *report) {
 struct r26_token token={0};int claimed=0;struct r14_report r={0};int rc=-EINVAL,idx=-1,fd=-1,mapped=0;void *oh=NULL,*buffer=NULL,*native=NULL,*bits=NULL;
 struct r29_record d={.phase=R29_ENTRY,.call=r29_call_id(),.self=(uintptr_t)r14_lock,.wrapper=(uintptr_t)wrapper};
 if(out)memset(out,0,sizeof(*out));if(dirty)memset(dirty,0,sizeof(*dirty));if(report)*report=r;
 if(!m || !wrapper || !out){d.rc=-EINVAL;d.invalid=1;d.stage=d.failure_stage=30;r29_emit(&d);return -EINVAL;}
 r29_emit(&d);
 const struct r14_ops *o=&m->ops;
 rc=o->unwrap(o->ctx,wrapper,&oh);observed_step(&d,31,1,rc,(uintptr_t)o->unwrap);if(rc || !oh){rc=rc?negative(rc):-ENODEV;goto done;}
 d.oh=(uintptr_t)oh;d.valid|=R29_OH;
 if(m->extension){rc=r26_lock_begin(m->extension,wrapper,oh,&token);d.phase=R29_CACHE;observed_step(&d,32,1,rc,(uintptr_t)r26_lock_begin);d.rc=rc;d.failure_stage=rc?32:0;r29_emit(&d);if(rc)goto done;claimed=1;}
 pthread_mutex_lock(&m->mutex);
 for(int i=0;i<R14_SLOTS;i++){
  if(m->slots[i].state!=FREE && (m->slots[i].oh==oh || m->slots[i].wrapper==wrapper)){pthread_mutex_unlock(&m->mutex);rc=-EBUSY;observed_step(&d,35,0,0,0);goto done;}
  if(idx<0 && m->slots[i].state==FREE)idx=i;
 }
 if(idx<0){pthread_mutex_unlock(&m->mutex);rc=-ENOSPC;observed_step(&d,36,0,0,0);goto done;}
 m->slots[idx].state=CLAIMED;m->slots[idx].wrapper=wrapper;m->slots[idx].oh=oh;pthread_mutex_unlock(&m->mutex);
 r.request_called=1;r.request_rc=o->request(o->ctx,oh,&buffer,&fd);
 observed_step(&d,37,1,r.request_rc,(uintptr_t)o->request);
 rc=r.request_rc?negative(r.request_rc):(!buffer?-EIO:0);
 if(fd>=0){
  if(!rc){d.fence_called=1;rc=fence_wait(m,fd);d.fence_rc=rc;observed_step(&d,38,1,rc,(uintptr_t)fence_wait);}
  r.close_called=1;r.close_rc=o->close_fd(o->ctx,fd);if(!rc && r.close_rc){rc=negative(r.close_rc);observed_step(&d,39,1,r.close_rc,(uintptr_t)o->close_fd);}
 }else if(fd != -1 && !rc){rc=-EINVAL;observed_step(&d,43,0,0,0);}
 if(rc)goto fail;
 struct r14_handle h={0};r.handle_called=1;r.handle_rc=o->handle(o->ctx,buffer,&h);observed_step(&d,44,1,r.handle_rc,(uintptr_t)o->handle);if(r.handle_rc){rc=negative(r.handle_rc);goto fail;}
 r.convert_called=1;r.convert_rc=o->convert(o->ctx,buffer,&native);observed_step(&d,45,1,r.convert_rc,(uintptr_t)o->convert);if(r.convert_rc || !native){rc=r.convert_rc?negative(r.convert_rc):-EIO;goto fail;}
 wl_r27_cpu(token.generation,oh,buffer,native);
 r.map_called=1;r.map_rc=o->map(o->ctx,native,&bits);observed_step(&d,46,1,r.map_rc,(uintptr_t)o->map);if(r.map_rc){rc=negative(r.map_rc);goto fail;}mapped=1;
 int bytes=0,fmt=format(h.format,&bytes);
 if(!bits || !fmt || h.width<=0 || h.height<=0 || h.width>INT32_MAX || h.height>INT32_MAX || h.stride_bytes<=0 || h.stride_bytes>INT32_MAX || h.stride_bytes%bytes || h.stride_bytes/bytes<h.width || h.size_bytes<=0 || (uint64_t)h.stride_bytes>SIZE_MAX/(uint64_t)h.height || (uint64_t)h.stride_bytes*(uint64_t)h.height>(uint64_t)h.size_bytes){rc=-EINVAL;observed_step(&d,47,0,0,0);goto fail;}
 struct r14_buffer answer={.width=(int32_t)h.width,.height=(int32_t)h.height,.stride=(int32_t)(h.stride_bytes/bytes),.format=fmt,.bits=bits};
 struct r14_rect rect={0,0,(int32_t)h.width,(int32_t)h.height};
 if(m->extension){d.prepare_called=1;rc=r26_prepare(m->extension,token,&h,&answer);d.prepare_rc=rc;observed_step(&d,48,1,rc,(uintptr_t)r26_prepare);if(rc)goto fail;}
 wl_r27_output(token.generation,native,&answer); /* prepared, not published */
 d.phase=R29_OUTPUT;d.valid|=R29_LAYOUT;d.buffer=(uintptr_t)buffer;d.native=(uintptr_t)native;d.bits=(uintptr_t)answer.bits;d.width=answer.width;d.height=answer.height;d.stride=answer.stride;d.format=answer.format;observed_step(&d,33,0,0,0);d.rc=0;r29_emit(&d);
 pthread_mutex_lock(&m->mutex);struct slot *s=&m->slots[idx];s->token=token;s->buffer=buffer;s->native=native;s->rect=rect;s->report=r;*out=answer;if(dirty)*dirty=rect;s->state=LOCKED;pthread_mutex_unlock(&m->mutex);
 rc=0;goto done;
fail:
 if(mapped){r.unmap_called=1;r.unmap_rc=o->unmap(o->ctx,native);}
 /* Failed Unmap or Flush never permits cancel: backend ownership is unknown. */
 if(buffer && (!mapped || !r.unmap_rc)){r.abort_called=1;r.abort_rc=o->abort(o->ctx,oh,buffer);}
 r.primary=rc;
 /* T30: only a PROVEN resource-free failure releases this reservation (slot FREE, retained stays 0) so a
  * legitimate later lock is not permanently rejected; every other failure keeps the original conservative
  * retained/FAILED path. complete(...,1) is the existing success/free arm; r.retained is left 0, so the
  * existing done: r26_finish(token, r.retained) restores R26 to IDLE and pair.c releases the owner ref once.
  * The original normalized error (rc) and raw request rc are returned unchanged -- the failure is not hidden. */
 int recoverable=t30_request_resource_free(&r,buffer,native,mapped,fd);
 pthread_mutex_lock(&m->mutex);m->slots[idx].buffer=buffer;m->slots[idx].native=native;pthread_mutex_unlock(&m->mutex);
 complete(m,idx,&r,recoverable);
done:
 if(rc && claimed)(void)r26_finish(m->extension,token,r.retained);
 r.primary=rc;if(report)*report=r;
 d.phase=R29_RETURN;d.valid|=R29_REPORT;d.rc=rc;d.failure_stage=rc?d.stage:0;d.buffer=(uintptr_t)buffer;d.native=(uintptr_t)native;d.request_called=r.request_called;d.request_rc=r.request_rc;d.handle_called=r.handle_called;d.handle_rc=r.handle_rc;d.native_convert_called=r.convert_called;d.native_convert_rc=r.convert_rc;d.map_called=r.map_called;d.map_rc=r.map_rc;d.close_called=r.close_called;d.close_rc=r.close_rc;d.unmap_called=r.unmap_called;d.unmap_rc=r.unmap_rc;d.flush_called=r.flush_called;d.flush_rc=r.flush_rc;d.abort_called=r.abort_called;d.abort_rc=r.abort_rc;d.retained=r.retained;r29_emit(&d);return rc;
}
int r14_unlock(struct r14_module *m,const void *wrapper,struct r14_report *report) {
 struct r29_record d={.phase=R29_FLUSH,.call=r29_call_id(),.self=(uintptr_t)r14_unlock,.wrapper=(uintptr_t)wrapper};
 struct r14_report r={0};if(report)*report=r;if(!m || !wrapper){d.rc=-EINVAL;d.invalid=1;d.stage=d.failure_stage=40;r29_emit(&d);return -EINVAL;}
 int idx=-1;struct slot copy;
 pthread_mutex_lock(&m->mutex);
 for(int i=0;i<R14_SLOTS;i++)if(m->slots[i].state!=FREE && m->slots[i].wrapper==wrapper){idx=i;break;}
 if(idx<0 || m->slots[idx].state!=LOCKED){pthread_mutex_unlock(&m->mutex);if(report)report->primary=-EBUSY;d.rc=-EBUSY;d.stage=d.failure_stage=41;r29_emit(&d);return -EBUSY;}
 m->slots[idx].state=COMPLETING;copy=m->slots[idx];pthread_mutex_unlock(&m->mutex);
 const struct r14_ops *o=&m->ops;r=copy.report;
 int conversion=m->extension?r26_before_unmap(m->extension,copy.token):0;
 d.conversion_called=m->extension!=NULL;d.conversion_rc_valid=d.conversion_called;d.conversion_rc=conversion;
 if(conversion)observed_step(&d,49,1,conversion,(uintptr_t)r26_before_unmap);
 r.unmap_called=1;r.unmap_rc=o->unmap(o->ctx,copy.native);
 int rc=conversion?conversion:(r.unmap_rc?negative(r.unmap_rc):0);
 if(!conversion && r.unmap_rc)observed_step(&d,50,1,r.unmap_rc,(uintptr_t)o->unmap);
 if(conversion && !r.unmap_rc){r.abort_called=1;r.abort_rc=o->abort(o->ctx,copy.oh,copy.buffer);}
 if(!rc){r.flush_called=1;r.flush_rc=o->flush(o->ctx,copy.oh,copy.buffer,-1,&copy.rect);observed_step(&d,51,1,r.flush_rc,(uintptr_t)o->flush);if(r.flush_rc)rc=negative(r.flush_rc);}
 if(m->extension)(void)r26_finish(m->extension,copy.token,rc!=0);
 r.primary=rc;complete(m,idx,&r,rc==0);if(report)*report=r;
 d.valid|=R29_OH|R29_REPORT;d.oh=(uintptr_t)copy.oh;d.buffer=(uintptr_t)copy.buffer;d.native=(uintptr_t)copy.native;d.rc=rc;d.failure_stage=rc?d.stage:0;if(!rc)d.stage=42;d.unmap_called=r.unmap_called;d.unmap_rc=r.unmap_rc;d.flush_called=r.flush_called;d.flush_rc=r.flush_rc;d.abort_called=r.abort_called;d.abort_rc=r.abort_rc;d.retained=r.retained;r29_emit(&d);return rc;
}
int r14_report_for(struct r14_module *m,const void *wrapper,struct r14_report *report) {
 if(!m || !wrapper || !report)return -EINVAL;
 pthread_mutex_lock(&m->mutex);
 for(int i=0;i<R14_SLOTS;i++)if(m->slots[i].state!=FREE && m->slots[i].wrapper==wrapper){*report=m->slots[i].report;pthread_mutex_unlock(&m->mutex);return 0;}
 pthread_mutex_unlock(&m->mutex);return -ENOENT;
}
