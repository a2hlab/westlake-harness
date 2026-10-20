#define _GNU_SOURCE
#include <stdint.h>
#include "observer.c"
int main(int argc,char **argv){wl_t27_record r;wl_hdr(&r,UINT64_MAX,UINT64_MAX,WL_T27_CREATE_CALL);r.pid=2147483647;r.tid=2147483647;r.create.addr=(void*)(uintptr_t)UINT64_MAX;r.create.base=(void*)(uintptr_t)0xffffeeee11112222ULL;r.create.rel_off=UINT64_MAX;r.create_ret=(void*)(uintptr_t)0xffffaaaa33334444ULL;r.window_buffer=(void*)(uintptr_t)0x777788889999aaaaULL;r.display=(void*)0x1234;r.target=0x3140;r.window=r.native=r.converted=r.input_native=r.context=(void*)(uintptr_t)UINT64_MAX;r.attribs=(void*)(uintptr_t)UINT64_MAX;static char huge[3000];if(argc>1){memset(huge,'x',sizeof huge-1);r.create.file=huge;}(void)argv;wl_t27_emit(&r);return 0;}
