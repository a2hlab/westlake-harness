#define _GNU_SOURCE 1
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static int fault;
static unsigned attempts;
static ssize_t observed_write(int fd,const void *p,size_t n){
 attempts++;
 if(fault==1){errno=EPIPE;return -1;}
 if(fault==2){errno=EINTR;return -1;}
 if(fault==3){errno=EIO;return (ssize_t)n-1;}
 return write(fd,p,n);
}
#define write observed_write
#include "observe29.c"
#undef write
static struct r29_record rec(uintptr_t w){
 return (struct r29_record){.phase=R29_ENTRY,.wrapper=w,.call=1};
}
static void pipe_stderr(void){
 int p[2];assert(pipe(p)==0);assert(close(p[0])==0);
 assert(dup2(p[1],2)==2);assert(close(p[1])==0);
}
static void emit_preserve(struct r29_record *r){
 errno=EDOM;r29_emit(r);assert(errno==EDOM);
}
static void *worker(void *unused){
 (void)unused;struct r29_record r=rec(1);
 for(unsigned i=0;i<10000;i++)emit_preserve(&r);
 return NULL;
}
int main(int argc,char **argv){
 assert(argc==2);const char *mode=argv[1];
 struct r29_record r=rec(1);struct r29_stats a,b;
 if(!strcmp(mode,"pipe")){
  struct sigaction old,after;assert(sigaction(SIGPIPE,NULL,&old)==0);
  pipe_stderr();emit_preserve(&r);r29_stats_read(&a);
  assert(sigaction(SIGPIPE,NULL,&after)==0);
  assert(a.sink_state==2 && a.writes==0 && attempts==0 && a.formatted==0 && a.timed==0);
  assert(old.sa_handler==after.sa_handler);
 }else if(!strcmp(mode,"fd2_rebind")){
  emit_preserve(&r);r29_stats_read(&a);assert(a.sink_state==1);
  int original=dup(2);assert(original>=0);pipe_stderr();
  r=rec(2);emit_preserve(&r);r29_stats_read(&b);
  assert(b.writes==a.writes+1 && b.sink_state==1);
  assert(dup2(original,2)==2);assert(close(original)==0);
 }else if(!strcmp(mode,"sink_drift")){
  emit_preserve(&r);r29_stats_read(&a);
  int p[2];assert(pipe(p)==0);assert(close(p[0])==0);
  assert(dup2(p[1],sink)==sink);assert(close(p[1])==0);
  r=rec(2);emit_preserve(&r);r29_stats_read(&b);
  assert(b.sink_state==2 && b.writes==a.writes);
 }else if(!strcmp(mode,"epipe") || !strcmp(mode,"eintr") || !strcmp(mode,"short")){
  fault=!strcmp(mode,"epipe")?1:(!strcmp(mode,"eintr")?2:3);
  emit_preserve(&r);r29_stats_read(&a);
  assert(attempts==1 && a.writes==1 && a.losses==1 && a.sink_state==2);
  r=rec(2);emit_preserve(&r);assert(attempts==1);
 }else if(!strcmp(mode,"hot_new") || !strcmp(mode,"parallel")){
  if(!strcmp(mode,"parallel")){
   pthread_t t[8];for(unsigned i=0;i<8;i++)assert(!pthread_create(&t[i],NULL,worker,NULL));
   for(unsigned i=0;i<8;i++)assert(!pthread_join(t[i],NULL));
  }else worker(NULL);
  r29_stats_read(&a);assert(a.writes==3 && a.first_limit==1);
  worker(NULL);r29_stats_read(&b);
  assert(a.formatted==b.formatted && a.timed==b.timed && a.writes==b.writes);
  r=rec(2);r.oh=123;r.valid=R29_OH;emit_preserve(&r);r29_stats_read(&b);
  assert(b.writes==a.writes+1 && b.identities==2);
 }else if(!strcmp(mode,"reserve")){
  r.invalid=1;for(unsigned i=0;i<100;i++)emit_preserve(&r);
  r29_stats_read(&a);assert(a.invalids==30 && a.first_limit==1 && !a.final_exhaustion);
  for(unsigned i=1;i<=17;i++){r=rec(i);emit_preserve(&r);}
  r29_stats_read(&b);assert(b.identities==16 && b.final_exhaustion==1 && b.writes==48);
 }else if(!strcmp(mode,"total")){
  for(unsigned w=1;w<=16;w++)for(unsigned ep=0;ep<8;ep++)for(unsigned ph=0;ph<6;ph++)for(int err=0;err<2;err++)for(unsigned n=0;n<2;n++){
   r=rec(w);r.transition=1;r.valid=R29_REQUEST|R29_OH;r.w=17+(int)ep;r.h=3;r.fmt=2;r.oh=100+w;r.phase=ph;r.rc=err?-EBUSY:0;emit_preserve(&r);
  }
  for(unsigned n=0;n<30;n++){r=rec(0);r.invalid=1;emit_preserve(&r);}
  r=rec(1);emit_preserve(&r);r=rec(17);emit_preserve(&r);
  r29_stats_read(&a);assert(a.writes==3104 && a.bytes<=2383872 && a.first_limit==1 && a.final_exhaustion==1);
  for(unsigned i=0;i<10000;i++)emit_preserve(&r);
  r29_stats_read(&b);assert(b.writes==a.writes && b.formatted==a.formatted && b.timed==a.timed);
 }else if(!strcmp(mode,"epochs")){
  for(unsigned i=0;i<9;i++){r=rec(1);r.transition=1;r.valid=R29_REQUEST;r.w=17+(int)i;emit_preserve(&r);}
  r29_stats_read(&a);assert(a.writes==9 && a.final_exhaustion==1);
  r=rec(1);r.transition=0;for(unsigned i=0;i<100;i++)emit_preserve(&r);
  r29_stats_read(&b);assert(a.writes==b.writes);
  r=rec(2);emit_preserve(&r);r29_stats_read(&b);assert(b.writes==a.writes+1);
 }else if(!strcmp(mode,"long")){
  memset(&r,0x7f,sizeof(r));r.invalid=0;r.phase=R29_ENTRY;r.valid=UINT32_MAX;
  emit_preserve(&r);r29_stats_read(&a);
  assert(a.writes==1 && a.bytes<768);
 }else assert(!"unknown test");
 printf("PASS observe29 %s\n",mode);return 0;
}
