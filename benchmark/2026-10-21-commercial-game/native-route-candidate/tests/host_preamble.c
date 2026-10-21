#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include <limits.h>
#include "oh_dlns_abi.h"
#include "westlake_bionic_pthread_bridge.h"
#define APPSPAWN_LOGI(...) ((void)0)
#define APPSPAWN_LOGE(...) ((void)0)
#define WLASC_NOINLINE
static int inherits,abi_calls,runtime_calls,audio_calls,open_calls,failure;
static char owners[8][256],libs[8][4096];
void dlns_init(Dl_namespace*n,const char*s){snprintf(n->name,sizeof(n->name),"%s",s);}
int dlns_get(const char*s,Dl_namespace*n){if(failure)return EPERM;dlns_init(n,s);return 0;}
int dlns_create2(Dl_namespace*n,const char*p,int f){(void)n;(void)p;(void)f;return 0;}
int dlns_set_namespace_separated(const char*n,bool s){(void)n;(void)s;return 0;}
int dlns_set_namespace_permitted_paths(const char*n,const char*p){(void)n;(void)p;return 0;}
int dlns_set_namespace_allowed_libs(const char*n,const char*p){(void)n;(void)p;return 0;}
int dlns_inherit(Dl_namespace*n,Dl_namespace*p,const char*l){(void)n;assert(inherits<8);strcpy(owners[inherits],p->name);strcpy(libs[inherits++],l);return 0;}
void* dlopen_ns(Dl_namespace*n,const char*f,int m){(void)n;open_calls++;if(m&RTLD_NOLOAD)return NULL;
 if(strstr(f,"libwestlake_native_abi.so")){assert((m&(RTLD_NOW|RTLD_GLOBAL))==(RTLD_NOW|RTLD_GLOBAL));abi_calls++;}
 else if(strstr(f,"liboh_android_runtime.so"))runtime_calls++;
 else if(strstr(f,"libOpenSLES.so"))audio_calls++;
 return (void*)1;
}
static void* fake_dlsym(void*h,const char*s){(void)h;(void)s;return (void*)1;}
#define dlsym fake_dlsym
#include "resident-compat.h"
#include "zlib-route.h"
