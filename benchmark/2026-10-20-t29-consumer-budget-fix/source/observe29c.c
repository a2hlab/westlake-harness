#define _GNU_SOURCE 1
#include "observe29c.h"
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

/* ---- core state: a faithful copy of shim/observe29.c's proven mutex/atomic/sink algorithm ---- */
#define R29C_IDENTITIES 16
#define R29C_EPOCHS 8
#define R29C_LINE 768
struct identity {
 uintptr_t wrapper,oh;
 unsigned used,oh_valid,epoch,config_valid;
 uintptr_t cfg_newwin; int cfg_tex,cfg_detached;
 unsigned char count[R29C_PHASES][2];
};
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static struct identity ids[R29C_IDENTITIES];
static struct r29c_stats stats;
static uint64_t sequence;
/* Owned for this DSO's lifetime. Never reused/rebound, never handed to callers.
 * Keeping the original file description avoids a check-fd2/write-fd2 race. */
static int sink=-1;
static struct stat sink_identity;

uint64_t r29c_call_id(void) {
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
static int eligible(const struct r29c_record *r,unsigned *key,unsigned *epoch) {
 *key=UINT32_MAX;*epoch=0;
 if(r->invalid || !r->wrapper || r->phase>=R29C_PHASES){
  if(stats.invalids<30){stats.invalids++;return 3;}
  return notice(0);
 }
 struct identity *e=NULL;
 for(unsigned i=0;i<R29C_IDENTITIES;i++){
  if(ids[i].used && ids[i].wrapper==r->wrapper){e=&ids[i];*key=i;break;}
 }
 if(!e){
  for(unsigned i=0;i<R29C_IDENTITIES;i++)if(!ids[i].used){
   e=&ids[i];*key=i;e->used=1;e->wrapper=r->wrapper;stats.identities++;break;
  }
  if(!e)return notice(1);
 }
 int changed=0;
 if(r->valid&R29C_OH){
  if(e->oh_valid && e->oh!=r->oh)changed=1;
  e->oh=r->oh;e->oh_valid=1;
 }
 /* consumer "configuration" = the producer window + attach state the method just observed */
 if(r->transition){
  uintptr_t nw=(r->valid&R29C_NEWWIN)?r->new_window:0;
  int tx=(r->valid&R29C_TEX)?r->tex_name:0;
  int dt=r->detached_valid?r->detached:0;
  if(e->config_valid && (e->cfg_newwin!=nw || e->cfg_tex!=tx || e->cfg_detached!=dt))changed=1;
  e->cfg_newwin=nw;e->cfg_tex=tx;e->cfg_detached=dt;e->config_valid=1;
 }
 if(changed){
  /* Saturated epochs remain saturated; a later event must not re-open quota. */
  if(e->epoch<R29C_EPOCHS)e->epoch++;
  if(e->epoch<R29C_EPOCHS)memset(e->count,0,sizeof(e->count));
 }
 *epoch=e->epoch;
 if(e->epoch>=R29C_EPOCHS)return notice(1);
 unsigned failure=(r->existing_exception_branch || r->rc!=0 || r->raw_rc!=0 ||
  (r->ref_called && r->ref_rc_valid && (r->valid&R29C_REFRC) && r->ref_rc!=0) ||
  (r->unref_called && r->unref_rc_valid && (r->valid&R29C_UNREFRC) && r->unref_rc!=0));
 if(e->count[r->phase][failure]>=2)return notice(0);
 e->count[r->phase][failure]++;return 3;
}
void r29c_observe(const struct r29c_record *r) {
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
 char line[R29C_LINE];stats.formatted++;
 int n;
 if(kind<3){
  n=snprintf(line,sizeof(line),"[WL-R29] %s side=consumer key=%u epoch=%u identity=%u invalid=%u eligible=%"PRIu64" ns=%"PRIu64"\n",
   kind==2?"FINAL_EXHAUSTION":"FIRST_LIMIT",key,epoch,stats.identities,stats.invalids,stats.eligible,ns);
 }else{
  n=snprintf(line,sizeof(line),
   "[WL-R29] side=consumer p=%u c=%"PRIu64" ns=%"PRIu64" tid=%"PRIu64" key=%u ep=%u v=%x"
   " self=%"PRIxPTR" caller=%"PRIxPTR" wrap=%"PRIxPTR" oh=%"PRIxPTR
   " state=%"PRIxPTR" image=%"PRIxPTR" provider=%"PRIxPTR
   " called=%d raw=%d rc=%d oldw=%"PRIxPTR" neww=%"PRIxPTR" tex=%d"
   " rel=%d/%d det=%d/%d exbranch=%d ref=%d/%d/%d unref=%d/%d/%d errno=%d\n",
   r->phase,r->call,ns,tid,key,epoch,r->valid,r->self,r->caller,r->wrapper,r->oh,
   r->state,r->image,r->provider,r->called,r->raw_rc,r->rc,
   r->old_window,r->new_window,r->tex_name,
   r->released_valid,r->released,r->detached_valid,r->detached,r->existing_exception_branch,
   r->ref_called,r->ref_rc_valid,r->ref_rc,r->unref_called,r->unref_rc_valid,r->unref_rc,saved);
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
void r29c_stats_read(struct r29c_stats *out) {
 int saved=errno;pthread_mutex_lock(&mu);if(out)*out=stats;pthread_mutex_unlock(&mu);errno=saved;
}
