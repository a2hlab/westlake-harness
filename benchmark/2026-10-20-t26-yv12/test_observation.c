#define _GNU_SOURCE 1
#include <assert.h>
#include <stdio.h>
#include <dlfcn.h>
static void *fake_dlsym(void *,const char *);
static int fake_dladdr(const void *,Dl_info *);
#define dlsym fake_dlsym
#define dladdr fake_dladdr
#include "observation.c"
#include "yv12.h"
#undef dlsym
#undef dladdr
static int handle_token,base,foreign_base,native_buffer,window_buffer;
static int absent,foreign,from_missing,get_calls,from_calls,create_calls,underscore_lookup;
static void typed_config(OH_NativeBuffer *b,OH_NativeBuffer_Config *c){assert(b==(void*)&native_buffer);get_calls++;*c=(OH_NativeBuffer_Config){17,3,12,0x12345,80};errno=EIO;}
static void *typed_old_from(void *b){assert(b==&window_buffer);from_calls++;errno=ENODEV;return &native_buffer;}
static void *fake_dlsym(void *h,const char *n){assert(h==&handle_token);if(!strcmp(n,"OH_NativeBuffer_GetConfig"))return absent?NULL:(void*)typed_config;if(!strcmp(n,"OH_NativeBufferFromNativeWindowBuffer"))return from_missing?NULL:(void*)typed_old_from;if(!strcmp(n,"OH_NativeBuffer_FromNativeWindowBuffer")){underscore_lookup++;assert(0);}return NULL;}
static int fake_dladdr(const void *p,Dl_info *i){memset(i,0,sizeof(*i));assert(p==(void*)typed_config || p==(void*)typed_old_from);i->dli_fbase=foreign?&foreign_base:&base;i->dli_fname="/system/lib64/libsurface.z.so";return 1;}
static void *real_create(void *d,void *c,uint32_t t,void *b,const int32_t *a){assert(d==(void*)1 && c==(void*)2 && t==0x34e1 && b==&window_buffer && a==(void*)3);assert(errno==7);create_calls++;errno=5;return (void*)4;}
int main(void){
 for(unsigned variant=0;variant<3;variant++){
  wl_t27_reset();get_calls=from_calls=0;absent=variant==1;foreign=variant==2;
  errno=7;wl_r27_bind_cpu(&handle_token,&base);wl_r27_bind_import(&handle_token,&base);assert(errno==7);
  struct r14_buffer out={17,3,32,R26_YV12,&window_buffer,{0}};
  wl_r27_cpu(31,(void*)9,&window_buffer,&native_buffer);assert(errno==7);
  wl_r27_output(31,&native_buffer,&out);assert(errno==7);
  wl_r27_import(&native_buffer,&window_buffer,2,3);assert(errno==7);
  wl_t27_record r[3];assert(wl_t27_snapshot(r,3)==3);
  assert(r[0].txn_id==r[1].txn_id && r[1].scratch_format==R26_YV12 && r[1].scratch_pix_stride==32);
  if(variant==0){assert(get_calls==3 && from_calls==1);for(unsigned i=0;i<3;i++)assert(r[i].cfg.width==17 && r[i].cfg.height==3 && r[i].cfg.format==12 && r[i].cfg.usage_low32==0x12345 && r[i].cfg.stride==80);}
  else{assert(get_calls==0 && from_calls==(variant==1?1:0));for(unsigned i=0;i<3;i++)assert(r[i].cfg.format==WL_T27_UNKNOWN_I32);}
 }
 absent=foreign=0;from_missing=1;get_calls=from_calls=0;wl_r27_bind_import(&handle_token,&base);wl_r27_import(&native_buffer,&window_buffer,0,4);assert(get_calls==0 && from_calls==0);
 errno=7;assert(wl_r27_create(1,3,(void*)real_create,(void*)1,(void*)2,0x34e1,&window_buffer,(void*)3)==(void*)4);assert(errno==5 && create_calls==1 && underscore_lookup==0);
 puts("PASS 5 exact-prototype/same-instance/UNKNOWN/single-create scenarios");return 0;
}
