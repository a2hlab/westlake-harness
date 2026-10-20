#define _GNU_SOURCE
#include <stdint.h>
#include "observer.c"
int main(void){wl_t27_record r;wl_hdr(&r,UINT64_MAX,UINT64_MAX,WL_T27_CREATE_CALL);r.pid=2147483647;r.tid=2147483647;r.create.addr=(void*)(uintptr_t)UINT64_MAX;r.create.base=(void*)(uintptr_t)0xffffeeee11112222ULL;r.create.rel_off=UINT64_MAX;r.create_ret=(void*)(uintptr_t)0xffffaaaa33334444ULL;r.window_buffer=(void*)(uintptr_t)0x777788889999aaaaULL;r.display=(void*)0x1234;r.target=0x3140;wl_t27_emit(&r);return 0;}
