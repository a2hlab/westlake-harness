/* #41 helper v2: dyntransition (setcon) to a target domain like appspawn does to
 * the forked child, then test .so-load and execmem perms. Because stdout writes
 * fail once we leave su, ALL results are encoded in the exit code:
 *   bit0(1)=mmap PROT_EXEC on file OK   bit1(2)=mprotect anon PROT_EXEC OK
 *   bit2(4)=open(file) OK               bit3(8)=setcon write OK
 *   bit4(16)=current domain == target after setcon
 * usage: dommap <context|-> <file> */
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>

static int readf(const char*p,char*b,int n){int fd=open(p,O_RDONLY);if(fd<0)return -1;int r=read(fd,b,n-1);close(fd);if(r<0)return -1;while(r&&(b[r-1]=='\n'||b[r-1]==0))r--;b[r]=0;return r;}

int main(int argc,char**argv){
    if(argc<3){fprintf(stderr,"usage: dommap <context|-> <file>\n");return 128;}
    char cur[256]; readf("/proc/self/attr/current",cur,sizeof cur);
    printf("before=%s target=%s file=%s\n",cur,argv[1],argv[2]); fflush(stdout);
    int bits=0;
    if(strcmp(argv[1],"-")){
        int fd=open("/proc/self/attr/current",O_WRONLY);
        if(fd>=0){ if(write(fd,argv[1],strlen(argv[1]))>=0) bits|=8; close(fd); }
    } else bits|=8;
    char now[256]; if(readf("/proc/self/attr/current",now,sizeof now)>0 &&
                      (!strcmp(argv[1],"-")||!strcmp(now,argv[1]))) bits|=16;
    int fd=open(argv[2],O_RDONLY);
    if(fd>=0){ bits|=4;
        void*m=mmap(0,4096,PROT_READ|PROT_EXEC,MAP_PRIVATE,fd,0);
        if(m!=MAP_FAILED){bits|=1;munmap(m,4096);}
        close(fd);
    }
    void*a=mmap(0,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(a!=MAP_FAILED){ if(mprotect(a,4096,PROT_READ|PROT_EXEC)==0) bits|=2; munmap(a,4096); }
    return bits;
}
