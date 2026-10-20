#define _POSIX_C_SOURCE 200809L
#include "entry.h"
#include <errno.h>
#include <limits.h>
#include <poll.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
struct r20_context { struct r20_owner owner; struct r15_adapter *adapter; struct r14_module *module; };
static int owner_unwrap(void *v,const void *wrapper,OHNativeWindow **out) {
 struct r20_context *c=v;*out=NULL;
 return c->owner.unwrap(c->owner.ctx,wrapper,out);
}
static int os_clock(void *unused,int64_t *out) {
 (void)unused;if(!out)return -EINVAL;*out=0;struct timespec t;
 if(clock_gettime(CLOCK_MONOTONIC,&t))return -errno;
 if(t.tv_sec<0 || t.tv_nsec<0 || t.tv_nsec>=1000000000L || (uint64_t)t.tv_sec>(uint64_t)INT64_MAX/1000000000)return -EOVERFLOW;
 int64_t sec=(int64_t)t.tv_sec*1000000000;
 if(sec>INT64_MAX-t.tv_nsec)return -EOVERFLOW;
 *out=sec+t.tv_nsec;return 0;
}
static int os_poll(void *unused,int fd,int timeout_ms,short *events,int *saved_errno) {
 (void)unused;if(!events || !saved_errno)return -1;
 *events=0;*saved_errno=0;
 if(fd<0 || timeout_ms<0){*saved_errno=EINVAL;return -1;}
 struct pollfd p={.fd=fd,.events=POLLIN,.revents=0};int rc=poll(&p,1,timeout_ms);int error=errno;
 *events=p.revents;if(rc<0)*saved_errno=error;return rc;
}
static int os_close(void *unused,int fd) {
 (void)unused;if(fd<0)return -EINVAL;
 /* A failed close has uncertain fd ownership; never retry a possibly reused fd. */
 if(close(fd))return -errno;return 0;
}
int r20_create(const struct r15_provider *provider,const struct r20_owner *owner,struct r20_context **out) {
 if(!out)return -EINVAL;*out=NULL;if(!provider || !owner || !owner->unwrap)return -ENOSYS;
 struct r20_context *c=calloc(1,sizeof(*c));if(!c)return -ENOMEM;c->owner=*owner;
 const struct r15_capabilities caps={c,owner_unwrap,os_clock,os_poll,os_close};struct r14_ops ops;
 int rc=r15_create(provider,&caps,&c->adapter,&ops);if(rc){free(c);return rc;}
 rc=r14_create(&ops,&c->module);
 if(rc){ /* No operation has run; the newly-created adapter has no reservations. */
  int cleanup=r15_destroy(c->adapter);if(cleanup){*out=c;return cleanup;}free(c);return rc;
 }
 *out=c;return 0;
}
int r20_lock(struct r20_context *c,const void *wrapper,struct r14_buffer *out,struct r14_rect *rect,struct r14_report *report) {
 if(!c || !c->module){if(out)memset(out,0,sizeof(*out));if(rect)memset(rect,0,sizeof(*rect));if(report)memset(report,0,sizeof(*report));return -EINVAL;}
 return r14_lock(c->module,wrapper,out,rect,report);
}
int r20_unlock(struct r20_context *c,const void *wrapper,struct r14_report *report) {
 if(!c || !c->module){if(report)memset(report,0,sizeof(*report));return -EINVAL;}return r14_unlock(c->module,wrapper,report);
}
int r20_report(struct r20_context *c,const void *wrapper,struct r14_report *report) {
 if(!c || !c->module)return -EINVAL;return r14_report_for(c->module,wrapper,report);
}
int r20_destroy(struct r20_context *c) {
 if(!c)return -EINVAL;
 if(c->module){int rc=r14_destroy(c->module);if(rc)return rc;c->module=NULL;}
 int rc=r15_destroy(c->adapter);if(rc)return rc;
 free(c);return 0;
}
