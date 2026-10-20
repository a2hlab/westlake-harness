#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include <dlfcn.h>
#include <assert.h>
#include <pthread.h>
static int fake_dladdr(const void *a,Dl_info *b){(void)a;(void)b;errno=ERANGE;return 0;}
#define dladdr fake_dladdr
#include "observer.c"
#undef dladdr
static int seen, calls; static unsigned getter_count;
static void *create(void *a,void*b,uint32_t c,void*d,const int32_t*e){(void)a;(void)b;(void)c;(void)d;(void)e;seen=errno;calls++;errno=EIO;return (void*)0x1234;}
static void cfg(void*b,wl_t27_cfg*c){(void)b;__atomic_add_fetch(&getter_count,1,__ATOMIC_RELAXED);c->width=576;errno=EDOM;}
static void *from(void*b){__atomic_add_fetch(&getter_count,1,__ATOMIC_RELAXED);return b;}
static const wl_t27_getters g={cfg,from};
static void *worker(void*x){for(int i=0;i<100;i++)wl_t27_cpu_native(i,1,x,x,x,&g,x);return 0;}
int main(void){
 errno=E2BIG;void*r=wl_t27_create_call(1,1,(void*)create,0,0,0,0,0);int after=errno;
 assert(calls==1&&r==(void*)0x1234);printf("create calls=%d provider_entry_errno=%d expected_entry=%d observed_exit_errno=%d provider_exit=%d\n",calls,seen,E2BIG,after,EIO);
 wl_t27_reset();getter_count=0;errno=E2BIG;wl_t27_cpu_native(1,1,0,0,0,0,0);assert(getter_count==0&&wl_t27_getter_calls()==0&&errno==E2BIG);
 wl_t27_import_config(2,1,(void*)1,(void*)1,0,0,&g);assert(getter_count==2&&wl_t27_getter_calls()==2&&errno==E2BIG);printf("null_getter=0 import_actual_getters=2 errno_preserved=1\n");
 wl_t27_reset();getter_count=0;pthread_t t[4];for(int i=0;i<4;i++)assert(pthread_create(&t[i],0,worker,(void*)1)==0);for(int i=0;i<4;i++)pthread_join(t[i],0);
 assert(wl_t27_count()==256&&wl_t27_dropped()==144&&getter_count==400&&wl_t27_getter_calls()==400);printf("concurrent count=256 dropped=144 actual_getters=400 ring_getters=400\n");
 return !(seen==E2BIG&&after==EIO);
}
