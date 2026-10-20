#define _GNU_SOURCE 1
#include "observation.h"
#include "observer.h"
#include <dlfcn.h>
#include <errno.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
#ifdef R15_OH_SDK
#include <native_buffer/native_buffer.h>
#else
typedef struct OH_NativeBuffer OH_NativeBuffer;
typedef struct {int32_t width,height,format,usage,stride;} OH_NativeBuffer_Config;
#endif
_Static_assert(sizeof(OH_NativeBuffer_Config)==20,"exact SDK config extent");
_Static_assert(offsetof(OH_NativeBuffer_Config,usage)==12 && offsetof(OH_NativeBuffer_Config,stride)==16,"SDK usage/stride order");
/* This is the SDK's VOID two-argument getter, not either From... overload. */
typedef void (*get_config_fn)(OH_NativeBuffer *,OH_NativeBuffer_Config *);
/* Only the older, NON-UNDERSCORED symbol has this pointer(one-arg) ABI. */
typedef void *(*old_from_fn)(void *);
struct getters {get_config_fn config;old_from_fn from;};
static struct getters cpu,imports;
static uint64_t operation;
static uint64_t op(void){return __atomic_add_fetch(&operation,1,__ATOMIC_RELAXED);}
static const char *leaf(const char *s){const char *p=s?strrchr(s,'/'):NULL;return p?p+1:(s?s:"");}
static int member(void *f,void *base){Dl_info i={0};return f && base && dladdr(f,&i) && i.dli_fbase==base && !strcmp(leaf(i.dli_fname),"libsurface.z.so");}
static void bind(struct getters *g,void *handle,void *base,int old_conversion){
 int saved=errno;g->config=NULL;g->from=NULL;
 if(handle && base){
  void *f=dlsym(handle,"OH_NativeBuffer_GetConfig");if(member(f,base))g->config=(get_config_fn)f;
  if(old_conversion){f=dlsym(handle,"OH_NativeBufferFromNativeWindowBuffer");if(member(f,base))g->from=(old_from_fn)f;}
 }
 errno=saved;
}
void wl_r27_bind_cpu(void *h,void *b){bind(&cpu,h,b,0);}
void wl_r27_bind_import(void *h,void *b){bind(&imports,h,b,1);}
static void config(const struct getters *g,void *n,wl_t27_cfg *out){
 int saved=errno;OH_NativeBuffer_Config c={WL_T27_UNKNOWN_I32,WL_T27_UNKNOWN_I32,WL_T27_UNKNOWN_I32,WL_T27_UNKNOWN_I32,WL_T27_UNKNOWN_I32};
 g->config((OH_NativeBuffer*)n,&c);
 /* Named field copies avoid making the observer struct a foreign ABI cast. */
 out->width=c.width;out->height=c.height;out->format=c.format;out->usage_low32=c.usage;out->stride=c.stride;errno=saved;
}
static void cpu_config(void *n,wl_t27_cfg *o){config(&cpu,n,o);}
static void import_config(void *n,wl_t27_cfg *o){config(&imports,n,o);}
static void *old_from(void *b){int saved=errno;void *n=imports.from(b);errno=saved;return n;}
void wl_r27_cpu(uint64_t txn,void *window,void *buffer,void *native){
 wl_t27_getters g={cpu.config?cpu_config:NULL,NULL};wl_t27_cpu_native(op(),txn,window,buffer,native,&g,native);
}
void wl_r27_output(uint64_t txn,void *native,const struct r14_buffer *out){
 wl_t27_getters g={cpu.config?cpu_config:NULL,NULL};wl_t27_android_output(op(),txn,out->width,out->height,out->stride,out->format,&g,native);
}
static uint64_t import_txn(unsigned slot,uint64_t gen){return (UINT64_C(1)<<63)|((gen&UINT64_C(0x7fffffffffffff))<<8)|(slot&255u);}
void wl_r27_import(void *input,void *buffer,unsigned slot,uint64_t gen){
 wl_t27_getters g={imports.config?import_config:NULL,imports.from?old_from:NULL};wl_t27_import_config(op(),import_txn(slot,gen),input,buffer,(int32_t)slot,(int32_t)gen,&g);
}
void *wl_r27_create(unsigned slot,uint64_t gen,void *fn,void *display,void *context,unsigned target,void *buffer,const int32_t *attrs){
 return wl_t27_create_call(op(),import_txn(slot,gen),fn,display,context,target,buffer,attrs);
}
