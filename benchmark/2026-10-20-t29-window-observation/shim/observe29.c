#define _GNU_SOURCE 1
#include "observe29.h"
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/syscall.h>
#endif

#define R29_IDENTITIES 16
#define R29_EPOCHS 8
#define R29_LINE 768
struct identity {
 uintptr_t wrapper,oh;
 unsigned used,oh_valid,epoch,config_valid;
 int w,h,fmt;
 unsigned char count[R29_PHASES][2];
};
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static struct identity ids[R29_IDENTITIES];
static struct r29_stats stats;
static uint64_t sequence;
/* Owned for this DSO's lifetime. Never reused/rebound, never handed to callers.
 * Keeping the original file description avoids a check-fd2/write-fd2 race. */
static int sink=-1;
static struct stat sink_identity;

uint64_t r29_call_id(void) {
 uint64_t n=__atomic_load_n(&sequence,__ATOMIC_RELAXED);
 while(n!=UINT64_MAX && !__atomic_compare_exchange_n(&sequence,&n,n+1,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){}
 return n==UINT64_MAX?n:n+1;
}
static int sink_check(void) {
 if(stats.sink_state==2)return 0;
 if(!stats.sink_state){
  int fd=fcntl(STDERR_FILENO,F_DUPFD_CLOEXEC,3);
  struct stat s;
  if(fd<0){stats.sink_state=2;return 0;}
  if(fstat(fd,&s) || !S_ISREG(s.st_mode)){
   (void)close(fd);stats.sink_state=2;return 0;
  }
  sink=fd;sink_identity=s;stats.sink_state=1;
 }
 struct stat s;
 if(fstat(sink,&s) || !S_ISREG(s.st_mode) || s.st_dev!=sink_identity.st_dev || s.st_ino!=sink_identity.st_ino){
  stats.sink_state=2;return 0;
 }
 return 1;
}
/* Return 1 for first ordinary cap notice, 2 for the reserved final hard limit.
 * These quotas are disjoint from the thirty invalid/overflow records. */
static int notice(int hard) {
 if(hard){if(stats.final_exhaustion)return 0;stats.final_exhaustion=1;return 2;}
 if(stats.first_limit)return 0;stats.first_limit=1;return 1;
}
static int eligible(const struct r29_record *r,unsigned *key,unsigned *epoch) {
 *key=UINT32_MAX;*epoch=0;
 if(r->invalid || !r->wrapper || r->phase>=R29_PHASES){
  if(stats.invalids<30){stats.invalids++;return 3;}
  return notice(0);
 }
 struct identity *e=NULL;
 for(unsigned i=0;i<R29_IDENTITIES;i++){
  if(ids[i].used && ids[i].wrapper==r->wrapper){e=&ids[i];*key=i;break;}
 }
 if(!e){
  for(unsigned i=0;i<R29_IDENTITIES;i++)if(!ids[i].used){
   e=&ids[i];*key=i;e->used=1;e->wrapper=r->wrapper;stats.identities++;break;
  }
  if(!e)return notice(1);
 }
 int changed=0;
 if(r->valid&R29_OH){
  if(e->oh_valid && e->oh!=r->oh)changed=1;
  e->oh=r->oh;e->oh_valid=1;
 }
 if(r->transition && (r->valid&R29_REQUEST)){
  if(e->config_valid && (e->w!=r->w || e->h!=r->h || e->fmt!=r->fmt))changed=1;
  e->w=r->w;e->h=r->h;e->fmt=r->fmt;e->config_valid=1;
 }
 if(changed){
  /* Saturated epochs remain saturated; a later event must not re-open quota. */
  if(e->epoch<R29_EPOCHS)e->epoch++;
  if(e->epoch<R29_EPOCHS)memset(e->count,0,sizeof(e->count));
 }
 *epoch=e->epoch;
 if(e->epoch>=R29_EPOCHS)return notice(1);
 unsigned failure=(r->rc!=0 || r->raw_rc!=0);
 if(e->count[r->phase][failure]>=2)return notice(0);
 e->count[r->phase][failure]++;return 3;
}
void r29_emit(const struct r29_record *r) {
 int saved=errno;
 if(!r){errno=saved;return;}
 pthread_mutex_lock(&mu);
 unsigned key=UINT32_MAX,epoch=0;
 /* No formatting, clock, fstat or write on an exhausted hot path. */
 int kind=eligible(r,&key,&epoch);
 if(!kind){stats.skipped++;pthread_mutex_unlock(&mu);errno=saved;return;}
 stats.eligible++;
 if(!sink_check()){stats.losses++;pthread_mutex_unlock(&mu);errno=saved;return;}
 struct timespec t={0};stats.timed++;
 int clock_rc=clock_gettime(CLOCK_MONOTONIC,&t);
 uint64_t ns=clock_rc?0:(uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;
 uint64_t tid=0;
#if defined(__linux__)
 tid=(uint64_t)syscall(SYS_gettid);
#elif defined(__APPLE__)
 (void)pthread_threadid_np(NULL,&tid);
#endif
 char line[R29_LINE];stats.formatted++;
 int n;
 if(kind<3){
  n=snprintf(line,sizeof(line),"[WL-R29] %s side=cpu key=%u epoch=%u identity=%u invalid=%u eligible=%"PRIu64" ns=%"PRIu64"\n",
   kind==2?"FINAL_EXHAUSTION":"FIRST_LIMIT",key,epoch,stats.identities,stats.invalids,stats.eligible,ns);
 }else{
  n=snprintf(line,sizeof(line),
   "[WL-R29] side=cpu p=%u c=%"PRIu64" ns=%"PRIu64" tid=%"PRIu64" key=%u ep=%u v=%x"
   " self=%"PRIxPTR" caller=%"PRIxPTR" w=%"PRIxPTR" oh=%"PRIxPTR
   " buf=%"PRIxPTR" native=%"PRIxPTR" bits=%"PRIxPTR" provider=%"PRIxPTR
   " called=%d raw_valid=%d raw=%d rc=%d stage=%d failure_stage=%d conversion=%d/%d/%d"
   " req=%d,%d,%d out=%d,%d,%d,%d hist=%d,%d"
   " Q=%d/%d/%d H=%d/%d/%d N=%d/%d/%d M=%d/%d/%d"
   " fence=%d/%d/%d close=%d/%d/%d prepare=%d/%d/%d"
   " U=%d/%d/%d F=%d/%d/%d B=%d/%d/%d retained=%d A=%d/%d/%d R=%d/%d/%d errno=%d\n",
   r->phase,r->call,ns,tid,key,epoch,r->valid,r->self,r->caller,r->wrapper,r->oh,
   r->buffer,r->native,r->bits,r->provider,r->called,r->raw_valid,r->raw_rc,r->rc,r->stage,r->failure_stage,
   r->conversion_called,r->conversion_rc_valid,r->conversion_rc,
   r->w,r->h,r->fmt,r->width,r->height,r->stride,r->format,r->history_known,r->history_format,
   r->request_called,r->request_called,r->request_rc,
   r->handle_called,r->handle_called,r->handle_rc,
   r->native_convert_called,r->native_convert_called,r->native_convert_rc,
   r->map_called,r->map_called,r->map_rc,
   r->fence_called,r->fence_called,r->fence_rc,
   r->close_called,r->close_called,r->close_rc,
   r->prepare_called,r->prepare_called,r->prepare_rc,
   r->unmap_called,r->unmap_called,r->unmap_rc,
   r->flush_called,r->flush_called,r->flush_rc,
   r->abort_called,r->abort_called,r->abort_rc,r->retained,
   r->acquire_called,r->acquire_called,r->acquire_rc,
   r->release_called,r->release_called,r->release_rc,saved);
 }
 if(n<0){stats.losses++;pthread_mutex_unlock(&mu);errno=saved;return;}
 size_t bytes=(size_t)n;
 if(bytes>=sizeof(line)){
  static const char tail[]=" TRUNC\n";
  bytes=sizeof(line)-1;memcpy(line+bytes-(sizeof(tail)-1),tail,sizeof(tail)-1);
 }
 stats.writes++;
 ssize_t wrote=write(sink,line,bytes);
 if(wrote>0)stats.bytes+=(uint64_t)wrote;
 if(wrote!=(ssize_t)bytes){stats.losses++;stats.sink_state=2;}
 pthread_mutex_unlock(&mu);errno=saved;
}
void r29_stats_read(struct r29_stats *out) {
 int saved=errno;pthread_mutex_lock(&mu);if(out)*out=stats;pthread_mutex_unlock(&mu);errno=saved;
}
