#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <dirent.h>
#include <time.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/uio.h>

static long long nowms(void) {struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000LL+t.tv_nsec/1000000;}
static int readtext(const char *p,char *b,size_t n) {int f=open(p,O_RDONLY|O_CLOEXEC);if(f<0)return -1;ssize_t r=read(f,b,n-1);close(f);if(r<0)return -1;b[r]=0;for(int i=0;i<r;i++)if(b[i]=='\n'||b[i]=='\t')b[i]=' ';return 0;}
static int sample(int pid,int tid,int seconds,const char *tap) {
 char p[256],b[8192];long long start=nowms(),next=start,java=start;
 for(;nowms()-start<seconds*1000LL;next+=50){
  long long ms=nowms();printf("%lld",ms);
  const char *names[]={"wchan","syscall","stat"};
  for(int i=0;i<3;i++){snprintf(p,sizeof(p),"/proc/%d/task/%d/%s",pid,tid,names[i]);if(readtext(p,b,sizeof(b)))strcpy(b,"UNREADABLE");printf("\t%s",b);}
  putchar('\n');
  if(tap&&ms>=java){int fd=open(tap,O_WRONLY|O_TRUNC|O_CLOEXEC);if(fd>=0){write(fd,"T\n",2);close(fd);printf("JAVA_REQUEST\t%lld\n",ms);}java+=500;}
  fflush(stdout);long long delay=next+50-nowms();if(delay>0)usleep(delay*1000);if(delay< -1000)next=nowms();
 }
 return 0;
}
static int pause_npth(int pid,int seconds) {
 char p[256],b[4096];snprintf(p,sizeof(p),"/proc/%d/task",pid);DIR *d=opendir(p);if(!d){perror("task");return 1;}struct dirent *de;int tid=0;
 while((de=readdir(d))){int id=atoi(de->d_name);if(!id)continue;snprintf(p,sizeof(p),"/proc/%d/task/%d/comm",pid,id);if(!readtext(p,b,sizeof(b))&&!strncmp(b,"npth-dumper-thr",15)){tid=id;break;}}closedir(d);
 if(!tid){puts("NO_NPTH_THREAD");return 2;}
 if(ptrace(PTRACE_SEIZE,tid,0,0)){perror("SEIZE");return 3;}
 if(ptrace(PTRACE_INTERRUPT,tid,0,0)){perror("INTERRUPT");ptrace(PTRACE_DETACH,tid,0,0);return 4;}
 int status;if(waitpid(tid,&status,__WALL)<0||!WIFSTOPPED(status)){perror("wait");ptrace(PTRACE_DETACH,tid,0,0);return 5;}
 struct {uint64_t x[31],sp,pc,pstate;} regs;struct iovec io={&regs,sizeof(regs)};
 if(ptrace(PTRACE_GETREGSET,tid,(void*)1,&io)){perror("GETREGSET");ptrace(PTRACE_DETACH,tid,0,0);return 6;}
 snprintf(p,sizeof(p),"/proc/%d/maps",pid);FILE *f=fopen(p,"r");unsigned long long lo,hi,off,rel=0;int match=0;
 while(f&&fgets(b,sizeof(b),f))if(strstr(b,"/libnpth.so")&&sscanf(b,"%llx-%llx %*s %llx",&lo,&hi,&off)==3&&lo<=regs.pc&&regs.pc<hi){rel=regs.pc-lo+off;match=rel==0x179c0||rel==0x179c4||rel==0x179c8;break;}if(f)fclose(f);
 printf("MATCH pid=%d tid=%d pc=0x%llx offset=0x%llx x21=0x%llx\n",pid,tid,(unsigned long long)regs.pc,rel,(unsigned long long)regs.x[21]);
 if(!match){puts("NOT_LOOP_DETACH");ptrace(PTRACE_DETACH,tid,0,0);return 7;}
 unsigned long cur=regs.x[21];for(int i=0;i<8&&cur;i++){errno=0;long value=ptrace(PTRACE_PEEKDATA,tid,(void*)cur,0);printf("CHAIN address=0x%lx next=0x%lx errno=%d\n",cur,(unsigned long)value,errno);if(errno||cur==(unsigned long)value)break;cur=value;}
 printf("PAUSED_MATCHED_LOOP uptime=%lld seconds=%d\n",nowms(),seconds);fflush(stdout);sleep(seconds);
 int rc=ptrace(PTRACE_DETACH,tid,0,0);printf("DETACH uptime=%lld rc=%d errno=%d\n",nowms(),rc,errno);return 0;
}
int main(int argc,char **argv){setbuf(stdout,NULL);if(argc>=4&&!strcmp(argv[1],"pause"))return pause_npth(atoi(argv[2]),atoi(argv[3]));if(argc>=5&&!strcmp(argv[1],"sample"))return sample(atoi(argv[2]),atoi(argv[3]),atoi(argv[4]),argc>5?argv[5]:NULL);fprintf(stderr,"proc38 pause PID SEC | sample PID TID SEC [TAP_FILE]\n");return 64;}
