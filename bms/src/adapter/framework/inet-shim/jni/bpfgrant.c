#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/syscall.h>
#include <linux/bpf.h>

static long bpf(int cmd, union bpf_attr *attr){ return syscall(__NR_bpf, cmd, attr, sizeof(*attr)); }

int main(int argc, char** argv){
    if(argc<3){ fprintf(stderr,"usage: %s <uid> <map_name> [value]\n", argv[0]); return 2; }
    uint32_t uid = (uint32_t)strtoul(argv[1],0,10);
    const char* want = argv[2];
    uint8_t val = (argc>3)? (uint8_t)atoi(argv[3]) : 1;

    uint32_t id = 0; int found=0;
    while(1){
        union bpf_attr a; memset(&a,0,sizeof a); a.start_id=id;
        if(bpf(BPF_MAP_GET_NEXT_ID,&a)!=0){ if(errno==ENOENT) break; perror("next_id"); break; }
        id = a.next_id;
        union bpf_attr g; memset(&g,0,sizeof g); g.map_id=id;
        int fd = (int)bpf(BPF_MAP_GET_FD_BY_ID,&g);
        if(fd<0) continue;
        struct bpf_map_info info; memset(&info,0,sizeof info);
        union bpf_attr q; memset(&q,0,sizeof q); q.info.bpf_fd=fd; q.info.info_len=sizeof info; q.info.info=(uint64_t)(uintptr_t)&info;
        if(bpf(BPF_OBJ_GET_INFO_BY_FD,&q)==0){
            if(strncmp(info.name, want, sizeof(info.name))==0 || strncmp(info.name,want,15)==0){
                printf("map id=%u name=%s key_sz=%u val_sz=%u max=%u\n", id, info.name, info.key_size, info.value_size, info.max_entries);
                /* read current */
                uint8_t cur=0xff; union bpf_attr lu; memset(&lu,0,sizeof lu);
                lu.map_fd=fd; lu.key=(uint64_t)(uintptr_t)&uid; lu.value=(uint64_t)(uintptr_t)&cur;
                if(bpf(BPF_MAP_LOOKUP_ELEM,&lu)==0) printf("  before: uid=%u -> %d\n", uid, cur); else printf("  before: uid=%u -> (absent, errno=%d)\n", uid, errno);
                /* update */
                union bpf_attr u; memset(&u,0,sizeof u);
                u.map_fd=fd; u.key=(uint64_t)(uintptr_t)&uid; u.value=(uint64_t)(uintptr_t)&val; u.flags=0;
                if(bpf(BPF_MAP_UPDATE_ELEM,&u)==0){ printf("  UPDATED uid=%u -> %d OK\n", uid, val); found++; }
                else printf("  update FAILED errno=%d\n", errno);
                uint8_t chk=0xff; memset(&lu,0,sizeof lu); lu.map_fd=fd; lu.key=(uint64_t)(uintptr_t)&uid; lu.value=(uint64_t)(uintptr_t)&chk;
                if(bpf(BPF_MAP_LOOKUP_ELEM,&lu)==0) printf("  after:  uid=%u -> %d\n", uid, chk);
            }
        }
        close(fd);
    }
    printf("done, matched %d map(s)\n", found);
    return found?0:1;
}
